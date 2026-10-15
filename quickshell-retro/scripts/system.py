#!/usr/bin/env python3
"""Small, dependency-free telemetry and action bridge for the Spidey shell.

Snapshots are read-only. Actions accept a fixed set of names and never execute
shell text. Optional desktop tools are detected at runtime, so previews also work
on machines without a Wayland session.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Sequence


SYS_POWER = Path("/sys/class/power_supply")
SYS_NETWORK = Path("/sys/class/net")
SYS_BACKLIGHT = Path("/sys/class/backlight")
COMMAND_TIMEOUT = 1.5


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
    output = optional_output(["playerctl", "metadata", "--format", "{{status}}\x1f{{title}}\x1f{{artist}}"])
    fields = output.split("\x1f", 2)
    if len(fields) != 3:
        return {"available": False, "playing": False, "title": "NO ACTIVE TRANSMISSION", "artist": ""}
    return {
        "available": True, "playing": fields[0].strip().lower() == "playing",
        "title": clean_text(fields[1]) or "UNTITLED TRANSMISSION", "artist": clean_text(fields[2]),
    }


def demo_snapshot() -> dict:
    return {
        "demo": True, "cpu": 21.0, "memory": 47.0, "disk": 38.0, "uptime": 12943,
        "battery": {"present": True, "percent": 93.0, "charging": False},
        "network": {"connected": True, "interface": "wlan0", "name": "MILES-NET"},
        "volume": {"available": True, "percent": 64.0, "muted": False},
        "brightness": {"available": True, "percent": 72.0},
        "media": {"available": True, "playing": True, "title": "CITY SWING // 104.8", "artist": "QUEENS RADIO"},
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
        "media-play-pause": ["playerctl", "play-pause"],
        "media-next": ["playerctl", "next"],
        "media-previous": ["playerctl", "previous"],
    }
    launches = {
        "terminal": [["kitty"], ["foot"], ["alacritty"], ["wezterm"], ["ghostty"]],
        "browser": [["firefox"], ["chromium"], ["google-chrome-stable"], ["brave"], ["xdg-open", "https://spideytracker.net/intl/br/"]],
        "files": [["xdg-open", str(Path.home())], ["thunar"], ["dolphin"], ["nautilus"]],
        "network": [["nm-connection-editor"], ["iwgtk"], ["gnome-control-center", "network"]],
        "launcher": [["fuzzel", "--background=122743ff", "--text=e4f8ffff", "--selection=49c7f4ff", "--selection-text=122743ff", "--border-color=49c7f4ff", "--border-width=2", "--border-radius=0", "--font=monospace:size=11"], ["wofi", "--show", "drun"], ["rofi", "-show", "drun"]],
        "lock": [["hyprlock"], ["swaylock", "-f", "-c", "080b12"]],
    }
    if name in ("volume-set", "brightness-set"):
        amount = numeric_value(value)
        argv = (
            ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{amount}%"]
            if name == "volume-set" else ["brightnessctl", "-c", "backlight", "set", f"{amount}%"]
        )
        run_command(argv)
    elif value is not None:
        raise ActionError(f"Action {clean_text(name)} does not accept a value.")
    elif name in commands:
        run_command(commands[name])
    elif name in launches:
        return launch(launches[name])
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
