#!/usr/bin/env python3
"""Small, dependency-free telemetry and action bridge for the Spidey shell.

Snapshots are read-only. Actions accept a fixed set of names and never execute
shell text. Optional desktop tools are detected at runtime, so previews also work
on machines without a Wayland session.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from typing import Sequence


SYS_POWER = Path("/sys/class/power_supply")
SYS_NETWORK = Path("/sys/class/net")
SYS_BACKLIGHT = Path("/sys/class/backlight")
COMMAND_TIMEOUT = 1.5
SHELL_ROOT = Path(__file__).resolve().parents[1]
APP_CONFIG = SHELL_ROOT / "config" / "apps.json"
APP_ACTIONS = frozenset({"terminal", "browser", "files", "network", "launcher", "lock"})


def load_helper(name: str):
    """Load a sibling module when invoked directly or imported by fixture tests."""
    spec = importlib.util.spec_from_file_location(f"spidey_{name}", Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


media = load_helper("media")
workspace = load_helper("workspace")


class ActionError(Exception):
    """An expected unavailable command, invalid argument, or desktop failure."""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def clean_text(value: str, limit: int = 180) -> str:
    """Keep external metadata plain, bounded, and free of terminal controls."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", value).split())[:limit]


def percent(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return round(max(0.0, min(100.0, value)), 1)


def run_command(argv: Sequence[str], timeout: float = COMMAND_TIMEOUT) -> str:
    """Run an argv list with a bounded lifetime and predictable output locale."""
    if not argv or not shutil.which(argv[0]):
        raise ActionError(f"Required program is unavailable: {argv[0] if argv else 'unknown'}")
    try:
        result = subprocess.run(
            list(argv), capture_output=True, text=True, check=False,
            timeout=timeout, env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ActionError(f"{argv[0]} timed out.") from exc
    except OSError as exc:
        raise ActionError(f"Could not start {argv[0]}: {exc.strerror or 'operating system error'}") from exc
    if result.returncode:
        detail = clean_text(result.stderr)
        suffix = f": {detail}" if detail else "."
        raise ActionError(f"{argv[0]} failed{suffix}")
    return result.stdout.strip()


def optional_output(argv: Sequence[str]) -> str:
    try:
        return run_command(argv)
    except ActionError:
        return ""


def cpu_counters(contents: str) -> tuple[int, int] | None:
    fields = contents.partition("\n")[0].split()
    if len(fields) < 5 or fields[0] != "cpu":
        return None
    try:
        # Guest time is already included in user/nice; do not count it twice.
        values = [int(field) for field in fields[1:9]]
    except ValueError:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return idle, sum(values)


def cpu_percent(before: str, after: str) -> float:
    first, last = cpu_counters(before), cpu_counters(after)
    if first is None or last is None:
        return 0.0
    total = last[1] - first[1]
    idle = last[0] - first[0]
    if total <= 0 or idle < 0:
        return 0.0
    return percent((total - idle) * 100 / total)


def memory_percent(contents: str) -> float:
    values = {}
    for line in contents.splitlines():
        key, separator, rest = line.partition(":")
        if separator:
            try:
                values[key] = int(rest.split()[0])
            except (ValueError, IndexError):
                continue
    total = values.get("MemTotal", 0)
    if total <= 0:
        return 0.0
    available = values.get("MemAvailable")
    if available is None:
        available = sum(values.get(key, 0) for key in ("MemFree", "Buffers", "Cached"))
    return percent((total - available) * 100 / total)


def child_paths(parent: Path) -> list[Path]:
    try:
        return sorted(parent.iterdir())
    except OSError:
        return []


def number_file(path: Path) -> float | None:
    try:
        number = float(read_text(path))
        return number if math.isfinite(number) else None
    except ValueError:
        return None


def battery_status(base: Path = SYS_POWER) -> dict:
    batteries = []
    for device in child_paths(base):
        if read_text(device / "type").lower() != "battery":
            continue
        if read_text(device / "present") == "0":
            continue
        capacity = number_file(device / "capacity")
        if capacity is None:
            # Some devices expose energy/charge but no precomputed capacity.
            for unit in ("energy", "charge"):
                now = number_file(device / f"{unit}_now")
                full = number_file(device / f"{unit}_full")
                if now is not None and full is not None and full > 0:
                    capacity = now * 100 / full
                    break
        if capacity is not None:
            batteries.append((capacity, read_text(device / "status").lower() == "charging"))
    if not batteries:
        return {"present": False, "percent": 0.0, "charging": False}
    return {
        "present": True,
        "percent": percent(sum(item[0] for item in batteries) / len(batteries)),
        "charging": any(item[1] for item in batteries),
    }


def network_status(base: Path = SYS_NETWORK) -> dict:
    # Device names and connection labels only; never query connection secrets.
    output = optional_output(["nmcli", "-t", "-e", "no", "-f", "DEVICE,STATE,CONNECTION", "device", "status"])
    for line in output.splitlines():
        fields = line.split(":", 2)
        if len(fields) == 3 and fields[1] == "connected" and fields[0] != "lo":
            return {"connected": True, "interface": clean_text(fields[0]), "name": clean_text(fields[2])}
    for interface in child_paths(base):
        if interface.name == "lo":
            continue
        state = read_text(interface / "operstate")
        carrier = read_text(interface / "carrier")
        if state == "up" and carrier != "0":
            return {"connected": True, "interface": interface.name, "name": interface.name}
    return {"connected": False, "interface": "", "name": "OFFLINE"}


def volume_status() -> dict:
    output = optional_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    match = re.search(r"Volume:\s*([0-9]+(?:\.[0-9]+)?)", output)
    if match is None:
        return {"available": False, "percent": 0.0, "muted": False}
    return {"available": True, "percent": percent(float(match.group(1)) * 100), "muted": "[MUTED]" in output}


def brightness_status(base: Path = SYS_BACKLIGHT) -> dict:
    output = optional_output(["brightnessctl", "-c", "backlight", "-m", "info"])
    for line in output.splitlines():
        fields = line.split(",")
        if len(fields) >= 4:
            match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)%", fields[3])
            if match:
                return {"available": True, "percent": percent(float(match.group(1)))}
    for device in child_paths(base):
        current = number_file(device / "brightness")
        maximum = number_file(device / "max_brightness")
        if current is not None and maximum is not None and maximum > 0:
            return {"available": True, "percent": percent(current * 100 / maximum)}
    return {"available": False, "percent": 0.0}


def media_status() -> dict:
    return media.snapshot(optional_output, clean_text)


def demo_snapshot() -> dict:
    return {
        "demo": True, "cpu": 21.0, "memory": 47.0, "disk": 38.0, "uptime": 12943,
        "battery": {"present": True, "percent": 93.0, "charging": False},
        "network": {"connected": True, "interface": "wlan0", "name": "MILES-NET"},
        "volume": {"available": True, "percent": 64.0, "muted": False},
        "brightness": {"available": True, "percent": 72.0},
        "media": {"available": True, "playing": True, "player": "", "title": "CITY SWING // 104.8", "artist": "QUEENS RADIO"},
    }


def snapshot(demo: bool = False) -> dict:
    if demo:
        return demo_snapshot()
    before = read_text(Path("/proc/stat"))
    time.sleep(0.12)
    cpu = cpu_percent(before, read_text(Path("/proc/stat")))
    try:
        usage = shutil.disk_usage(Path.home())
        disk = percent(usage.used * 100 / usage.total) if usage.total else 0.0
    except OSError:
        disk = 0.0
    try:
        uptime = max(0, int(float(read_text(Path("/proc/uptime")).split()[0])))
    except (ValueError, IndexError, OverflowError):
        uptime = 0
    return {
        "demo": False, "cpu": cpu,
        "memory": memory_percent(read_text(Path("/proc/meminfo"))),
        "disk": disk, "uptime": uptime, "battery": battery_status(),
        "network": network_status(), "volume": volume_status(),
        "brightness": brightness_status(), "media": media_status(),
    }


def launch(candidates: Sequence[Sequence[str]]) -> dict:
    for argv in candidates:
        executable = shutil.which(argv[0])
        if executable is None:
            continue
        try:
            subprocess.Popen(
                [executable, *argv[1:]], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise ActionError(f"Could not launch {argv[0]}: {exc.strerror or 'operating system error'}") from exc
        return {"success": True, "program": argv[0]}
    names = ", ".join(argv[0] for argv in candidates)
    raise ActionError(f"Install one of these programs: {names}")


def themed_command(program: str, config_relative: str) -> list[str]:
    """Use this rice's separate config when installed; preserve normal fallback."""
    config_root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    config = config_root / config_relative
    return [program, "--config", str(config)] if config.is_file() else [program]


def read_app_config(path: Path, *, optional: bool = False) -> dict:
    """Read explicit argv lists; invalid configuration must not launch a fallback."""
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        if optional:
            return {}
        raise ActionError(f"Application configuration is missing: {path}") from exc
    except OSError as exc:
        raise ActionError(f"Could not read application configuration: {path}") from exc
    except UnicodeError as exc:
        raise ActionError(f"Application configuration must use UTF-8: {path}") from exc
    try:
        config = json.loads(contents)
    except (ValueError, UnicodeError) as exc:
        raise ActionError(f"Invalid JSON in application configuration: {path}") from exc
    if not isinstance(config, dict):
        raise ActionError(f"Application configuration must be a JSON object: {path}")
    for name, candidates in config.items():
        if name not in APP_ACTIONS:
            raise ActionError(f"Unknown application action {clean_text(str(name))} in {path}")
        if not isinstance(candidates, list) or not candidates:
            raise ActionError(f"Application {name} needs a nonempty list of commands in {path}")
        for argv in candidates:
            if not isinstance(argv, list) or not argv or not isinstance(argv[0], str) or not argv[0] or any(
                not isinstance(arg, str) or "\x00" in arg for arg in argv
            ):
                raise ActionError(f"Application {name} commands need argument arrays with a nonempty program in {path}")
    return config


def app_candidates(name: str) -> list[list[str]]:
    """Merge per-user actions over repository defaults and expand path tokens."""
    config_root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    config = read_app_config(APP_CONFIG)
    config.update(read_app_config(config_root / "spidey" / "apps.json", optional=True))
    if name not in config:
        raise ActionError(f"No application commands configured for {name} in {APP_CONFIG}")
    tokens = {"{home}": str(Path.home()), "{config}": str(config_root), "{shell}": str(SHELL_ROOT)}
    candidates = []
    for command in config[name]:
        argv = []
        for arg in command:
            for token, value in tokens.items():
                arg = arg.replace(token, value)
            argv.append(arg)
        if name == "lock" and argv == ["hyprlock"]:
            argv = themed_command("hyprlock", "hypr-spidey/hyprlock.conf")
        if name == "launcher" and Path(argv[0]).name in ("rofi", "rofi-wayland") and not any(
            arg == "-terminal" or arg.startswith("-terminal=") for arg in argv[1:]
        ):
            terminals = app_candidates("terminal")
            terminal = next((candidate for candidate in terminals if shutil.which(candidate[0])), terminals[0])
            # Rofi 2 reparses command-line settings as RASI, stripping shell
            # quotes from raw -terminal values. Apply a quoted RASI string in
            # the later theme pass, preserving the argv string for execution.
            setting = json.dumps(shlex.join(terminal), ensure_ascii=False)
            argv.extend(["-theme-str", f"configuration {{ terminal: {setting}; }}"])
        candidates.append(argv)
    return candidates


def numeric_value(value: str | None) -> str:
    try:
        number = float(value) if value is not None else math.nan
    except ValueError as exc:
        raise ActionError("Value must be a number from 0 to 100.") from exc
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise ActionError("Value must be a number from 0 to 100.")
    return f"{number:g}"


def screenshot() -> dict:
    if not shutil.which("grim") or not shutil.which("slurp"):
        raise ActionError("Screenshots require grim and slurp.")
    geometry = run_command(["slurp"], timeout=60)
    if not re.fullmatch(r"-?\d+,-?\d+ [1-9]\d*x[1-9]\d*", geometry):
        raise ActionError("Screenshot selection was cancelled or invalid.")
    folder = Path.home() / "Pictures" / "SpideyTracker"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ActionError("Could not create ~/Pictures/SpideyTracker.") from exc
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    destination = folder / f"spidey-{timestamp}.png"
    run_command(["grim", "-g", geometry, str(destination)], timeout=15)
    return {"success": True, "path": str(destination)}


def action(name: str, value: str | None = None) -> dict:
    commands = {
        "volume-up": ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"],
        "volume-down": ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
        "volume-mute": ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
        "brightness-up": ["brightnessctl", "-c", "backlight", "set", "+5%"],
        "brightness-down": ["brightnessctl", "-c", "backlight", "set", "5%-"],
    }
    if name in ("volume-set", "brightness-set"):
        amount = numeric_value(value)
        argv = (
            ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{amount}%"]
            if name == "volume-set" else ["brightnessctl", "-c", "backlight", "set", f"{amount}%"]
        )
        run_command(argv)
    elif name in media.MEDIA_COMMANDS:
        run_command(media.command(name, value, optional_output, ActionError))
    elif name == "workspace":
        workspace.activate(value, run_command, ActionError)
    elif value is not None:
        raise ActionError(f"Action {clean_text(name)} does not accept a value.")
    elif name in commands:
        run_command(commands[name])
    elif name in APP_ACTIONS:
        return launch(app_candidates(name))
    elif name == "screenshot":
        return screenshot()
    else:
        raise ActionError(f"Unknown action: {clean_text(name)}")
    return {"success": True}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use deterministic preview telemetry; actions are disabled.")
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = commands.add_parser("snapshot", help="Print one telemetry snapshot as JSON.")
    snapshot_parser.add_argument("--demo", action="store_true", default=argparse.SUPPRESS)
    action_parser = commands.add_parser("action", help="Run a whitelisted desktop action.")
    action_parser.add_argument("name")
    action_parser.add_argument("value", nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(args.demo)
        elif args.demo:
            raise ActionError("Desktop actions are disabled in demo mode.")
        else:
            result = action(args.name, args.value)
    except ActionError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
