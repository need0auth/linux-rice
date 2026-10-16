#!/usr/bin/env python3
"""Exercise media discovery and controls against real MPRIS D-Bus services.

Run with ``python3 tests/integration/mpris.py``. The test creates its own
dbus-run-session, never touches desktop players, and needs playerctl plus a
Python interpreter with PyGObject (python-gobject on Arch). SPIDEY_GI_PYTHON
can point at that interpreter when it differs from the test runner's Python.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BROWSER = "chromium.instance4242"
OTHER = "vlc"
BUS_PREFIX = "org.mpris.MediaPlayer2."
OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
ROOT_INTERFACE = "org.mpris.MediaPlayer2"

INTROSPECTION = """<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/><method name="Previous"/><method name="Pause"/>
    <method name="PlayPause"/><method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
    <method name="SetPosition"><arg name="TrackId" type="o" direction="in"/>
      <arg name="Position" type="x" direction="in"/></method>
    <method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="read"/>
    <property name="Rate" type="d" access="read"/>
    <property name="Shuffle" type="b" access="read"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="read"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>"""


def fixture() -> None:
    # Only this isolated helper needs GI. Production telemetry remains stdlib-only.
    from gi.repository import Gio, GLib

    class Player:
        def __init__(self, name: str, status: str, title: str, artist: str):
            self.name, self.status, self.title, self.artist = name, status, title, artist
            self.events = []
            self.connection = Gio.DBusConnection.new_for_address_sync(
                os.environ["DBUS_SESSION_BUS_ADDRESS"],
                Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
                | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
                None, None,
            )
            info = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION)
            self.registrations = [
                self.connection.register_object(
                    OBJECT_PATH, interface, self.method, self.property, None,
                )
                for interface in info.interfaces
            ]
            reply = self.connection.call_sync(
                "org.freedesktop.DBus", "/org/freedesktop/DBus",
                "org.freedesktop.DBus", "RequestName",
                GLib.Variant("(su)", (BUS_PREFIX + name, 0)),
                GLib.VariantType.new("(u)"), Gio.DBusCallFlags.NONE, 5000, None,
            )
            assert reply.unpack()[0] == 1, f"Could not own fixture bus name {name}"

        def property(self, connection, sender, path, interface, name):
            metadata = {
                "mpris:trackid": GLib.Variant("o", "/org/mpris/MediaPlayer2/track/1"),
                "xesam:title": GLib.Variant("s", self.title),
                "xesam:artist": GLib.Variant("as", [self.artist] if self.artist else []),
                "xesam:url": GLib.Variant("s", "https://www.youtube.com/watch?v=fixture"),
            }
            values = {
                "Identity": GLib.Variant("s", "Brave" if self.name == BROWSER else "VLC"),
                "DesktopEntry": GLib.Variant("s", "brave-browser" if self.name == BROWSER else "vlc"),
                "SupportedUriSchemes": GLib.Variant("as", ["https"]),
                "SupportedMimeTypes": GLib.Variant("as", ["video/webm"]),
                "PlaybackStatus": GLib.Variant("s", self.status),
                "LoopStatus": GLib.Variant("s", "None"),
                "Metadata": GLib.Variant("a{sv}", metadata),
                "Position": GLib.Variant("x", 0),
                "Rate": GLib.Variant("d", 1.0),
                "Volume": GLib.Variant("d", 1.0),
                "MinimumRate": GLib.Variant("d", 1.0),
                "MaximumRate": GLib.Variant("d", 1.0),
            }
            return values.get(name, GLib.Variant("b", name.startswith("Can")))

        def changed(self):
            self.connection.emit_signal(
                None, OBJECT_PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                GLib.Variant("(sa{sv}as)", (PLAYER_INTERFACE, {
                    "PlaybackStatus": GLib.Variant("s", self.status),
                    "Metadata": self.property(None, None, None, None, "Metadata"),
                }, [])),
            )

        def method(self, connection, sender, path, interface, method, parameters, invocation):
            self.events.append(method)
            if method == "PlayPause":
                self.status = "Paused" if self.status == "Playing" else "Playing"
            elif method in ("Play", "Pause", "Stop"):
                self.status = {"Play": "Playing", "Pause": "Paused", "Stop": "Stopped"}[method]
            self.changed()
            invocation.return_value(None)

        def close(self):
            for registration in self.registrations:
                self.connection.unregister_object(registration)
            self.connection.close_sync(None)

    players = {
        OTHER: Player(OTHER, "Paused", "Paused desktop track", "Desktop artist"),
        BROWSER: Player(BROWSER, "Playing", "YouTube fixture: rooftop swing", "Daily Bugle"),
    }
    loop = GLib.MainLoop()

    def command(channel, condition):
        line = sys.stdin.readline()
        if not line:
            loop.quit()
            return False
        try:
            request = json.loads(line)
            operation, name = request["op"], request.get("player")
            if operation == "events":
                response = {key: player.events for key, player in players.items()}
            elif operation == "update":
                player = players[name]
                for key in ("status", "title", "artist"):
                    if key in request:
                        setattr(player, key, request[key])
                player.changed()
                response = {"ok": True}
            elif operation == "remove":
                players.pop(name).close()
                response = {"ok": True}
            elif operation == "quit":
                loop.quit()
                response = {"ok": True}
            else:
                raise ValueError(f"Unknown fixture operation {operation}")
            print(json.dumps(response), flush=True)
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), flush=True)
        return True

    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP, command)
    print(json.dumps({"ready": True}), flush=True)
    loop.run()
    for player in players.values():
        player.close()


def read_reply(process: subprocess.Popen) -> dict:
    readable, _, _ = select.select([process.stdout], [], [], 10)
    if not readable:
        raise AssertionError("MPRIS fixture did not respond within ten seconds")
    line = process.stdout.readline()
    if not line:
        raise AssertionError(f"MPRIS fixture exited unexpectedly ({process.poll()})")
    result = json.loads(line)
    assert "error" not in result, result
    return result


def exercise() -> None:
    spec = importlib.util.spec_from_file_location("spidey_system", ROOT / "quickshell/scripts/system.py")
    system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(system)
    gi_python = os.environ.get("SPIDEY_GI_PYTHON", "/usr/bin/python3")
    subprocess.run([gi_python, "-c", "from gi.repository import Gio, GLib"], check=True)
    checks = []
    process = subprocess.Popen(
        [gi_python, str(Path(__file__).resolve()), "--fixture"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
    )

    def request(operation, **kwargs):
        process.stdin.write(json.dumps({"op": operation, **kwargs}) + "\n")
        process.stdin.flush()
        return read_reply(process)

    def media(**expected):
        actual = system.media_status()
        for key, value in expected.items():
            assert actual.get(key) == value, {"expected": expected, "actual": actual}
        return actual

    def action(name, player, *, succeeds=True):
        result = subprocess.run(
            [sys.executable, str(ROOT / "quickshell/scripts/system.py"), "action", name, player],
            capture_output=True, text=True, timeout=15,
        )
        payload = json.loads(result.stdout)
        assert (result.returncode == 0) is succeeds, payload
        assert payload["success"] is succeeds, payload

    try:
        assert read_reply(process) == {"ready": True}
        listed = subprocess.run(
            ["playerctl", "--list-all"], check=True, text=True, capture_output=True,
        ).stdout.splitlines()
        assert set(listed) == {BROWSER, OTHER}, listed
        media(available=True, player=BROWSER, playing=True,
              title="YouTube fixture: rooftop swing", artist="Daily Bugle")
        checks.append("Playing Brave-style Chromium session beats paused desktop player")

        # Another session starts after the UI takes its snapshot. Clicks must
        # still control the browser identified by that snapshot.
        request("update", player=OTHER, status="Playing")
        for name in ("media-next", "media-previous"):
            action(name, BROWSER)
        assert request("events") == {OTHER: [], BROWSER: ["Next", "Previous"]}
        checks.append("CLI next and previous target displayed browser even when another player starts")

        request("update", player=OTHER, status="Stopped")
        action("media-play-pause", BROWSER)
        media(available=True, player=BROWSER, playing=False)
        assert request("events")[BROWSER] == ["Next", "Previous", "PlayPause"]
        checks.append("Play/pause changes browser playback and is reflected in telemetry")

        request("update", player=BROWSER, status="Playing", title="YouTube clip\nLIVE", artist="")
        media(player=BROWSER, playing=True, title="YouTube clip LIVE", artist="")
        checks.append("Live browser title changes and empty artist metadata remain readable")

        request("update", player=OTHER, status="Paused")
        request("remove", player=BROWSER)
        action("media-next", BROWSER, succeeds=False)
        assert request("events") == {OTHER: []}
        media(available=True, player=OTHER, playing=False, title="Paused desktop track")
        checks.append("Disappeared browser rejects stale controls and telemetry discovers remaining player")

        request("remove", player=OTHER)
        media(available=False, playing=False)
        checks.append("Closing every session clears media availability")
        report = {"passed": True, "checks": checks}
        if os.environ.get("ARTIFACT_ROOT"):
            folder = Path(os.environ["ARTIFACT_ROOT"])
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "mpris.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        if process.poll() is None:
            try:
                request("quit")
                process.wait(timeout=5)
            except (AssertionError, BrokenPipeError, subprocess.TimeoutExpired):
                process.kill()
                process.wait(timeout=5)
        process.stdin.close()
        process.stdout.close()


def main() -> None:
    if sys.argv[1:] == ["--fixture"]:
        fixture()
    elif sys.argv[1:] == ["--isolated"]:
        exercise()
    elif not sys.argv[1:]:
        for program in ("dbus-run-session", "playerctl"):
            if not shutil.which(program):
                raise SystemExit(f"Integration check requires {program}")
        os.execvp("dbus-run-session", [
            "dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()), "--isolated",
        ])
    else:
        raise SystemExit("Usage: python3 tests/integration/mpris.py")


if __name__ == "__main__":
    main()
