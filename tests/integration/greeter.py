#!/usr/bin/env python3
"""Exercise the real graphical greeter against a private fake greetd socket.

Requires Quickshell with Quickshell.Services.Greetd (the Arch package includes
it). No system greetd service, PAM, real account or real credentials are used.
QS_BINARY selects Quickshell; ARTIFACT_ROOT optionally retains safe diagnostics.
The fixture implements greetd's length-prefixed JSON protocol and never records
authentication responses. All test credentials live only in process memory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import select
import shutil
import socket
import struct
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
USERNAME = "spidey-fixture"
SESSION_COMMAND = ["dbus-run-session", "Hyprland"]
SESSION_ENVIRONMENT = [
    "XDG_SESSION_TYPE=wayland", "XDG_CURRENT_DESKTOP=Hyprland",
    "XDG_SESSION_DESKTOP=Hyprland",
]


class FakeGreetd:
    """A single private greetd connection, with bounded frames and safe logs."""

    def __init__(self, path: Path):
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(str(path))
        path.chmod(0o600)
        self.listener.listen(1)
        self.listener.settimeout(15)
        self.connection = None
        self.events = []

    def close(self):
        if self.connection:
            self.connection.close()
        self.listener.close()

    def accept(self):
        self.connection, _ = self.listener.accept()
        self.connection.settimeout(15)

    def exact(self, length):
        data = bytearray()
        while len(data) < length:
            part = self.connection.recv(length - len(data))
            if not part:
                raise AssertionError("Greeter closed the fake greetd socket early")
            data.extend(part)
        return bytes(data)

    def receive(self, expected, **fields):
        size = struct.unpack("<I", self.exact(4))[0]
        if not 0 < size <= 65536:
            raise AssertionError("Invalid greetd frame length")
        message = json.loads(self.exact(size))
        # Responses may contain secrets: retain only the request type and keys.
        self.events.append({"type": message.get("type"), "keys": sorted(message)})
        if message.get("type") != expected:
            raise AssertionError(f"Expected {expected}, received request type {message.get('type')}")
        for name, value in fields.items():
            if message.get(name) != value:
                raise AssertionError(f"Unexpected {expected} field: {name}")
        return message

    def send(self, **message):
        data = json.dumps(message, separators=(",", ":")).encode("utf-8")
        self.connection.sendall(struct.pack("<I", len(data)) + data)

    def quiet(self, message, timeout=0.2):
        if select.select([self.connection], [], [], timeout)[0]:
            raise AssertionError(message)

    def challenge(self, message, kind="secret"):
        self.send(type="auth_message", auth_message_type=kind, auth_message=message)


def environment(work: Path, fixture_secrets: dict) -> dict:
    env = dict(os.environ)
    for name in (
        "GREETD_SOCK", "DISPLAY", "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE",
        "SPIDEY_PREVIEW", "SPIDEY_SCREENSHOT", "QT_SCREEN_SCALE_FACTORS",
    ):
        env.pop(name, None)
    for suffix in ("RUNTIME_DIR", "CONFIG_HOME", "CACHE_HOME", "STATE_HOME", "DATA_HOME"):
        directory = work / suffix.lower()
        directory.mkdir(mode=0o700)
        env["XDG_" + suffix] = str(directory)
    env.update({
        "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
        "QT_SCALE_FACTOR": "1", "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
        "QML_DISK_CACHE_PATH": str(work / "qml-cache"),
        "SPIDEY_GREETER_TEST_USER": USERNAME,
        "SPIDEY_GREETER_ASSETS": (ROOT / "quickshell/assets").as_uri(),
        "SPIDEY_GREETER_WALLPAPER": (ROOT / "assets/wallpapers/spidey-city.png").as_uri(),
        **fixture_secrets,
    })
    return env


def no_secret_files(work: Path, values: list[str]):
    for path in work.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if any(value.encode() in data for value in values):
            raise AssertionError("Authentication response persisted to a greeter file")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def authenticate(executable, artifacts):
    secret_names = (
        "SPIDEY_GREETER_TEST_BAD_SECRET", "SPIDEY_GREETER_TEST_GOOD_SECRET",
        "SPIDEY_GREETER_TEST_CANCEL_SECRET", "SPIDEY_GREETER_TEST_VISIBLE_RESPONSE",
    )
    fixture_secrets = {name: "fixture-" + secrets.token_hex(16) for name in secret_names}
    values = list(fixture_secrets.values())
    output = ""
    process = None
    checks = []
    events = []
    report = {"passed": False, "checks": checks, "requests": events}

    with tempfile.TemporaryDirectory(prefix="spidey-greetd-") as temporary:
        work = Path(temporary)
        work.chmod(0o700)
        config = work / "greeter"
        shutil.copytree(ROOT / "greeter", config, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(Path(__file__).with_name("greeter-harness.qml"), config / "shell.qml")
        env = environment(work, fixture_secrets)
        socket_path = work / "greetd.sock"
        fixture = FakeGreetd(socket_path)
        env["GREETD_SOCK"] = str(socket_path)
        env["SPIDEY_GREETER_PREVIEW"] = "0"

        try:
            process = subprocess.Popen(
                [executable, "-p", str(config), "--no-color"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            fixture.accept()
            fixture.receive("create_session", username=USERNAME)
            fixture.quiet("Greeter responded or launched before an authentication challenge")
            checks.append("Username creates a session without submitting a password early")
            fixture.challenge("Fixture rejected password")
            fixture.receive("post_auth_message_response", response=fixture_secrets[secret_names[0]])
            fixture.send(type="error", error_type="auth_error", description="Authentication failed")
            fixture.receive("cancel_session")
            fixture.send(type="success")
            checks.append("Rejected credentials cancel the authentication session")

            fixture.receive("create_session", username=USERNAME)
            fixture.challenge("Fixture cancel password")
            fixture.receive("cancel_session")
            fixture.send(type="success")
            checks.append("Cancel clears an entered password without submitting it")

            fixture.receive("create_session", username=USERNAME)
            fixture.challenge("Fixture accepted password")
            fixture.receive("post_auth_message_response", response=fixture_secrets[secret_names[1]])
            fixture.challenge("Fixture visible code", "visible")
            fixture.receive("post_auth_message_response", response=fixture_secrets[secret_names[3]])
            fixture.challenge("Fixture authentication information", "info")
            info_response = fixture.receive("post_auth_message_response")
            if "response" in info_response:
                raise AssertionError("Informational PAM message must not repeat a credential")
            fixture.quiet("Greeter launched before successful authentication")
            fixture.send(type="success")
            start = fixture.receive("start_session", cmd=SESSION_COMMAND, env=SESSION_ENVIRONMENT)
            if any(any(value in entry for value in values) for entry in start["env"]):
                raise AssertionError("Authentication response leaked into session environment")
            fixture.send(type="success")
            checks.append("Secret, visible and informational prompts complete before Hyprland starts")
            output, _ = process.communicate(timeout=10)
            if process.returncode or "GREETER_AUTH_INTERACTIONS_PASSED" not in output:
                raise AssertionError("Greeter interaction harness failed; see greeter-auth.log")
            if any(value in output for value in values):
                raise AssertionError("Authentication response leaked into greeter output")
            no_secret_files(work, values)
            checks.append("Input fields clear on submit, failure and cancel; responses stay out of logs and files")
            report["passed"] = True
        except Exception as error:
            report["error"] = str(error)
            raise
        finally:
            stop(process)
            if process and not output:
                output, _ = process.communicate(timeout=3)
            fixture.close()
            events.extend(fixture.events)
            for value in values:
                output = output.replace(value, "<REDACTED FIXTURE RESPONSE>")
            (artifacts / "greeter-auth.log").write_text(output, encoding="utf-8")
            (artifacts / "greeter-auth.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def preview(executable, artifacts):
    """The production preview must not even connect to an available socket."""
    report = {"passed": False, "checks": []}
    output = ""
    process = None
    with tempfile.TemporaryDirectory(prefix="spidey-greeter-preview-") as temporary:
        work = Path(temporary)
        work.chmod(0o700)
        config = work / "greeter"
        shutil.copytree(ROOT / "greeter", config, ignore=shutil.ignore_patterns("__pycache__"))
        env = environment(work, {})
        socket_path = work / "greetd.sock"
        fixture = FakeGreetd(socket_path)
        image_path = artifacts / "greeter-preview.png"
        env.update({
            "GREETD_SOCK": str(socket_path), "SPIDEY_GREETER_PREVIEW": "1",
            "SPIDEY_PREVIEW_WIDTH": "1366", "SPIDEY_PREVIEW_HEIGHT": "768",
            "SPIDEY_SCREENSHOT": str(image_path),
        })
        try:
            process = subprocess.Popen(
                [executable, "-p", str(config), "--no-color"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            output, _ = process.communicate(timeout=15)
            if process.returncode:
                raise AssertionError("Production greeter preview failed; see greeter-preview.log")
            if select.select([fixture.listener], [], [], 0)[0]:
                raise AssertionError("Preview connected to greetd despite authentication being disabled")
            report["checks"].append("Production preview never contacts an available fake greetd socket")
            data = image_path.read_bytes()
            if (data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR"
                    or struct.unpack(">II", data[16:24]) != (1366, 768) or len(data) < 4096):
                raise AssertionError("Production greeter preview did not render the expected image")
            report["checks"].append("Production login screen renders at laptop resolution")
            report["passed"] = True
        except Exception as error:
            report["error"] = str(error)
            raise
        finally:
            stop(process)
            if process and not output:
                output, _ = process.communicate(timeout=3)
            fixture.close()
            (artifacts / "greeter-preview.log").write_text(output, encoding="utf-8")
            (artifacts / "greeter-preview.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main():
    executable = os.environ.get("QS_BINARY") or shutil.which("qs") or shutil.which("quickshell")
    if not executable:
        raise SystemExit("Quickshell is required; set QS_BINARY or add qs to PATH")
    requested = os.environ.get("ARTIFACT_ROOT")
    artifacts = Path(requested).expanduser().resolve() if requested else Path(
        tempfile.mkdtemp(prefix="spidey-greeter-artifacts-"))
    artifacts.mkdir(parents=True, exist_ok=True)
    print(f"Greeter artifacts: {artifacts}", flush=True)
    try:
        authenticate(executable, artifacts)
        preview(executable, artifacts)
    except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as error:
        raise SystemExit(f"Greeter regression failed: {error}\nArtifacts: {artifacts}") from error
    print("Private greetd protocol, authentication UI and session launch checks passed")


if __name__ == "__main__":
    main()
