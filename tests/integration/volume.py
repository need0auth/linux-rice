#!/usr/bin/env python3
"""Drive the production top-bar volume popup against private fake audio.

The QML fixture uses QtTest pointer and keyboard events, real Telemetry actions,
and the real system.py bridge. A private PATH contains only Python and a fake
wpctl, so this check cannot change the machine's audio. QS_BINARY selects the
Quickshell executable; ARTIFACT_ROOT optionally retains logs and a screenshot.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]

# Keep this executable separate from the production bridge. Commands and state
# are deliberately small and private; a delayed mute exercises action overlap.
FAKE_WPCTL = r'''#!/usr/bin/env python3
import fcntl
import json
import os
from pathlib import Path
import sys
import time

root = Path(os.environ["SPIDEY_AUDIO_FIXTURE"])
arguments = sys.argv[1:]
if arguments and arguments[0] == "set-mute":
    time.sleep(0.7)
with (root / "lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = json.loads((root / "state.json").read_text())
    if arguments == ["get-volume", "@DEFAULT_AUDIO_SINK@"]:
        if not state["available"]:
            raise SystemExit(1)
        print("Volume: %.2f%s" % (state["percent"] / 100, " [MUTED]" if state["muted"] else ""))
        raise SystemExit(0)
    if arguments == ["set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]:
        state["muted"] = not state["muted"]
    elif len(arguments) == 5 and arguments[:4] == ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@"]:
        assert arguments[4].endswith("%"), "Expected a bounded absolute volume"
        value = float(arguments[4][:-1])
        assert 0 <= value <= 100, "Volume escaped its bounds"
        state["percent"] = value
    elif arguments == ["fixture-external", "19"]:
        state["percent"] = 19
    elif arguments == ["fixture-unavailable"]:
        state["available"] = False
    else:
        raise SystemExit("Unexpected private audio command")
    (root / "state.json").write_text(json.dumps(state))
    with (root / "commands.jsonl").open("a") as stream:
        stream.write(json.dumps({"arguments": arguments, "state": state, "time": time.monotonic()}) + "\n")
'''


def main():
    executable = os.environ.get("QS_BINARY") or shutil.which("qs") or shutil.which("quickshell")
    if not executable:
        raise SystemExit("Quickshell is required; set QS_BINARY or add qs to PATH")
    executable = str(Path(shutil.which(executable) or executable).resolve())
    artifacts = Path(os.environ["ARTIFACT_ROOT"]) if os.environ.get("ARTIFACT_ROOT") else None
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spidey-volume-") as temporary:
        work = Path(temporary)
        config = work / "shell"
        shutil.copytree(ROOT / "quickshell", config, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(Path(__file__).with_suffix(".qml"), config / "shell.qml")
        binary = work / "bin"
        binary.mkdir()
        (binary / "python3").symlink_to(sys.executable)
        wpctl = binary / "wpctl"
        wpctl.write_text(FAKE_WPCTL)
        wpctl.chmod(0o700)
        audio = work / "audio"
        audio.mkdir(mode=0o700)
        (audio / "state.json").write_text(json.dumps({"available": True, "percent": 42, "muted": False}))
        env = dict(os.environ)
        for name in (
            "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS",
            "SPIDEY_SCREENSHOT", "QT_SCREEN_SCALE_FACTORS",
        ):
            env.pop(name, None)
        for suffix in ("RUNTIME_DIR", "CONFIG_HOME", "CACHE_HOME", "STATE_HOME", "DATA_HOME"):
            directory = work / suffix.lower()
            directory.mkdir(mode=0o700)
            env["XDG_" + suffix] = str(directory)
        env.update({
            "PATH": str(binary), "SPIDEY_AUDIO_FIXTURE": str(audio),
            "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
            "QT_SCALE_FACTOR": "1", "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
            "SPIDEY_DEMO": "0", "SPIDEY_PREVIEW": "1",
            "SPIDEY_VOLUME_SCREENSHOT": str(artifacts / "volume-popup.png") if artifacts else "",
        })
        try:
            result = subprocess.run(
                [executable, "-p", str(config), "--no-color"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=25, check=False,
            )
            output = result.stdout
        except subprocess.TimeoutExpired as error:
            output = (error.stdout or b"").decode(errors="replace")
            if artifacts:
                (artifacts / "volume.log").write_text(output)
            raise SystemExit(output or "Volume interaction test timed out") from error
        commands_file = audio / "commands.jsonl"
        commands = [json.loads(line) for line in commands_file.read_text().splitlines()] if commands_file.exists() else []
        keyboard = "VOLUME_INTERACTIONS_PASSED native-focus" in output
        report = {"passed": False, "keyboard": keyboard, "commands": commands}
        try:
            if result.returncode or "VOLUME_INTERACTIONS_PASSED" not in output:
                raise AssertionError(output or "Volume interaction test exited without a result")
            actions = [event["arguments"] for event in commands]
            volumes = [float(command[-1][:-1]) for command in actions if command[0] == "set-volume"]
            assert volumes == [73, 27, 0, 100], f"Unexpected slider updates: {volumes}"
            mute_index = actions.index(["set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
            assert actions[mute_index + 1] == ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "27%"], "Queued final drag was lost while mute was running"
            unavailable_index = actions.index(["fixture-unavailable"])
            assert not any(command[0] == "set-volume" for command in actions[unavailable_index + 1:]), "Disabled slider changed audio"
            report["passed"] = True
        finally:
            if artifacts:
                (artifacts / "volume.log").write_text(output)
                (artifacts / "volume-results.json").write_text(json.dumps(report, indent=2) + "\n")
        controls = "pointer and keyboard" if keyboard else "legacy pointer"
        print(f"Top-bar volume {controls} controls, queued actions, bounds and external changes passed")


if __name__ == "__main__":
    main()
