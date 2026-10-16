#!/usr/bin/env python3
"""Restart only this checkout's shells on the installing user's Wayland session."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time


class UpgradeError(Exception):
    pass


def normal_path(path):
    return os.path.normpath(os.path.abspath(path))


def session_key(environment):
    runtime = environment.get("XDG_RUNTIME_DIR", "")
    display = environment.get("WAYLAND_DISPLAY", "")
    if not runtime or not os.path.isabs(runtime) or not display:
        return None
    socket = display if os.path.isabs(display) else os.path.join(runtime, display)
    return {"runtime": normal_path(runtime), "socket": normal_path(socket)}


@dataclass
class ProcessInfo:
    uid: int
    environment: dict
    token: str
    active: bool = True


def read_process(pid):
    """Read session identity without printing or retaining unrelated environment."""
    directory = Path("/proc") / str(pid)
    try:
        owner = directory.stat().st_uid
        fields = (directory / "stat").read_text().rsplit(")", 1)[1].split()
        token = fields[19]  # Linux /proc stat field 22: process start time.
        active = fields[0] not in ("Z", "X")
        environment = {}
        if active:
            for entry in (directory / "environ").read_bytes().split(b"\0"):
                key, separator, value = entry.partition(b"=")
                if separator and key in (b"XDG_RUNTIME_DIR", b"WAYLAND_DISPLAY"):
                    environment[key.decode("ascii")] = os.fsdecode(value)
        return ProcessInfo(owner, environment, token, active)
    except FileNotFoundError:
        return None


class RuntimeUpgrade:
    def __init__(self, repo_root, config_root, state_file, dry_run=False,
                 environment=None, runner=subprocess.run, process_reader=read_process,
                 output=print, binary=None):
        self.repo_root = Path(repo_root).resolve()
        self.config_root = Path(config_root).absolute()
        self.state_file = Path(state_file)
        self.dry_run = dry_run
        self.environment = dict(os.environ if environment is None else environment)
        self.runner = runner
        self.process_reader = process_reader
        self.output = output
        self.uid = os.getuid()
        self.binary = binary or shutil.which("qs") or shutil.which("quickshell")

    def live_session(self):
        session = session_key(self.environment)
        if session is None:
            return None
        try:
            runtime = Path(session["runtime"]).stat()
            socket = Path(session["socket"]).stat()
            if runtime.st_uid == self.uid and stat.S_ISDIR(runtime.st_mode) and stat.S_ISSOCK(socket.st_mode):
                return session
        except OSError:
            pass
        return None

    def owned_paths(self):
        sources = {normal_path(self.repo_root / name) for name in ("quickshell", "quickshell-retro")}
        paths = {str(Path(source) / "shell.qml") for source in sources}
        for name in ("spidey", "spidey-retro"):
            link = self.config_root / "quickshell" / name
            if link.is_symlink():
                target = normal_path(link.parent / os.readlink(link))
                if target in sources:
                    paths.add(normal_path(link / "shell.qml"))
        return paths

    def command(self, arguments, environment=None):
        command_environment = dict(self.environment if environment is None else environment)
        # Explicit paths/IDs must not inherit an unrelated shell selection.
        for name in ("QS_CONFIG_PATH", "QS_CONFIG_NAME", "QS_MANIFEST"):
            command_environment.pop(name, None)
        try:
            result = self.runner([self.binary, *arguments], env=command_environment,
                                 capture_output=True, text=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise UpgradeError(f"Quickshell {arguments[0]} could not complete ({type(error).__name__}).") from error
        if result.returncode:
            raise UpgradeError(f"Quickshell {arguments[0]} failed (exit {result.returncode}).")
        return result

    def instances(self):
        result = self.command(["list", "--all", "--json"])
        # Both supported versions print this message instead of an empty JSON list.
        if result.stdout.strip() in ("", "No running instances."):
            return []
        try:
            instances = json.loads(result.stdout)
        except (ValueError, TypeError) as error:
            raise UpgradeError("Quickshell returned an unreadable instance list; leave running shells untouched.") from error
        if not isinstance(instances, list):
            raise UpgradeError("Quickshell returned an unexpected instance list.")
        for item in instances:
            if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]+", item["id"])
                    or not isinstance(item.get("pid"), int) or isinstance(item["pid"], bool)
                    or item["pid"] <= 0 or not isinstance(item.get("config_path"), str)
                    or not os.path.isabs(item["config_path"])):
                raise UpgradeError("Quickshell returned an invalid instance record; leave running shells untouched.")
        identifiers = [item["id"] for item in instances]
        if len(identifiers) != len(set(identifiers)):
            raise UpgradeError("Quickshell returned duplicate instance identifiers.")
        return instances

    def state(self, was_running, session):
        return {"version": 1, "repo_root": str(self.repo_root),
                "config_root": str(self.config_root), "session": session,
                "was_running": was_running}

    def write_state(self, value):
        if self.dry_run:
            return
        descriptor = os.open(self.state_file, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            info = os.fstat(stream.fileno())
            if info.st_uid != self.uid or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise UpgradeError("Runtime state must be a private file owned by the installing user.")
            os.fchmod(stream.fileno(), 0o600)
            stream.truncate(0)
            json.dump(value, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

    def read_state(self):
        try:
            descriptor = os.open(self.state_file, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor) as stream:
            info = os.fstat(stream.fileno())
            if (info.st_uid != self.uid or not stat.S_ISREG(info.st_mode)
                    or info.st_mode & 0o077 or info.st_size > 16384):
                raise UpgradeError("Refuse unsafe runtime state file.")
            contents = stream.read()
        if not contents.strip():
            return None
        try:
            value = json.loads(contents)
        except ValueError as error:
            raise UpgradeError("Runtime state is unreadable.") from error
        if (not isinstance(value, dict) or value.get("version") != 1
                or value.get("repo_root") != str(self.repo_root)
                or value.get("config_root") != str(self.config_root)
                or not isinstance(value.get("was_running"), bool)):
            raise UpgradeError("Runtime state does not belong to this installation.")
        return value

    def wait_for_exit(self, instance, original):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = self.process_reader(instance["pid"])
            if current is None or not current.active or current.token != original.token:
                return
            time.sleep(0.05)
        raise UpgradeError(f"Managed instance {instance['id']} did not exit; installation cannot continue.")

    def stop(self):
        session = self.live_session()
        if session is None or not self.binary:
            self.output("No live Wayland session or Quickshell executable; leave running shells unchanged.")
            self.write_state(self.state(False, session))
            return
        owned = self.owned_paths()
        selected = []
        # Capture and validate the entire list before sending any stop requests.
        for instance in self.instances():
            if normal_path(instance["config_path"]) not in owned:
                continue
            try:
                process = self.process_reader(instance["pid"])
            except OSError:
                process = None
            if (process is None or process.uid != self.uid or not process.active
                    or session_key(process.environment) != session):
                self.output(f"Leave instance {instance['id']} unchanged: its current Wayland session cannot be verified.")
                continue
            selected.append((instance, process))
        self.write_state(self.state(False, session))
        stopped = False
        for instance, original in selected:
            self.output(f"{'Would stop' if self.dry_run else 'Stop'} managed Quickshell instance {instance['id']}.")
            if self.dry_run:
                continue
            current = self.process_reader(instance["pid"])
            if current is None or not current.active or current.token != original.token:
                continue
            if current.uid != self.uid or session_key(current.environment) != session:
                raise UpgradeError("A managed instance changed session before it could be stopped.")
            # Save recovery intent immediately before asking this exact instance to exit.
            self.write_state(self.state(True, session))
            try:
                # Quickshell itself compares the original display spelling, even
                # when an absolute socket and a relative name identify the same display.
                kill_environment = dict(self.environment, **current.environment)
                self.command(["kill", "--id", instance["id"]], kill_environment)
                self.wait_for_exit(instance, original)
            except (UpgradeError, OSError):
                if not stopped:
                    try:
                        current = self.process_reader(instance["pid"])
                        if current is not None and current.active and current.token == original.token:
                            # A failed stop that left every shell alive needs no recovery launch.
                            self.write_state(self.state(False, session))
                    except OSError:
                        pass
                raise
            stopped = True
        if selected and self.dry_run:
            self.output("Would start one updated Spidey shell: " + shlex.join(self.launch_command()))
        elif not selected:
            self.output("No managed Spidey shell is running on this Wayland session; leave the desktop unchanged.")

    def launch_command(self):
        return [self.binary, "-p", str(self.config_root / "quickshell" / "spidey"), "--no-duplicate", "--daemonize"]

    def resume(self):
        value = self.read_state()
        if value is None or not value["was_running"]:
            return
        session = self.live_session()
        if session is None or value["session"] != session or not self.binary:
            self.output("Cannot restart on the original Wayland session; start qs -c spidey after logging in.")
            return
        self.output(f"{'Would start' if self.dry_run else 'Start'} one updated Spidey shell.")
        if self.dry_run:
            return
        environment = dict(self.environment, XDG_CONFIG_HOME=str(self.config_root))
        for name in ("SPIDEY_PREVIEW", "SPIDEY_DEMO", "SPIDEY_SCREENSHOT"):
            environment.pop(name, None)
        self.command(self.launch_command()[1:], environment)
        self.write_state(self.state(False, session))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--config-root", required=True, type=Path)
    parser.add_argument("--state-file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("action", choices=("stop", "resume"))
    arguments = parser.parse_args()
    try:
        upgrade = RuntimeUpgrade(arguments.repo_root, arguments.config_root, arguments.state_file, arguments.dry_run)
        getattr(upgrade, arguments.action)()
    except (UpgradeError, OSError) as error:
        print(f"Runtime upgrade failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
