#!/usr/bin/env python3
"""Render the real Hyprlock config in a private headless Sway session.

Requires sway, swaymsg, grim, hyprlock, and a Mesa software EGL driver. The test
never submits a password or changes PAM. It verifies a real session lock and
the rendered panel at two output sizes, then terminates only its own processes.
ARTIFACT_ROOT selects a persistent directory for logs, screenshots and reports.
"""

import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import zlib


REPO_ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1600, 1000), (1366, 768))


def binary(name):
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Required executable is missing or not executable: {name}")
    return str(Path(resolved).resolve())


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)


def png_pixels(path):
    """Read grim's non-interlaced RGB/RGBA PNG without adding a dependency."""
    image = path.read_bytes()
    if image[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Lockscreen screenshot is not a PNG")
    offset, compressed, dimensions = 8, bytearray(), None
    while offset < len(image):
        length = struct.unpack_from(">I", image, offset)[0]
        kind, data = image[offset + 4:offset + 8], image[offset + 8:offset + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
            if depth != 8 or color not in (2, 6) or compression or filtering or interlace:
                raise AssertionError("Unexpected screenshot PNG encoding")
            dimensions = width, height, 3 if color == 2 else 4
        elif kind == b"IDAT":
            compressed.extend(data)
        offset += 12 + length
    if dimensions is None:
        raise AssertionError("Screenshot PNG has no dimensions")
    width, height, channels = dimensions
    stride = width * channels
    encoded = zlib.decompress(compressed)
    if len(encoded) != height * (stride + 1):
        raise AssertionError("Screenshot PNG has unexpected scanline data")
    previous, rows = bytearray(stride), []
    for y in range(height):
        offset = y * (stride + 1)
        filtering, row = encoded[offset], bytearray(encoded[offset + 1:offset + stride + 1])
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            up = previous[x]
            upper_left = previous[x - channels] if x >= channels else 0
            if filtering == 1:
                predictor = left
            elif filtering == 2:
                predictor = up
            elif filtering == 3:
                predictor = (left + up) // 2
            elif filtering == 4:
                prediction = left + up - upper_left
                distances = (abs(prediction - left), abs(prediction - up), abs(prediction - upper_left))
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            elif filtering == 0:
                continue
            else:
                raise AssertionError(f"Unknown PNG filter: {filtering}")
            row[x] = (row[x] + predictor) & 255
        rows.append(row)
        previous = row

    def pixel(x, y):
        return tuple(rows[y][x * channels:x * channels + 3])

    return width, height, pixel


def check_size(width, height, tools, artifact_root):
    prefix = artifact_root / f"lockscreen-{width}x{height}"
    report = {"size": [width, height], "passwords_submitted": 0}
    processes = []
    with tempfile.TemporaryDirectory(prefix="spidey-lock-") as temporary:
        work = Path(temporary)
        runtime = work / "run"
        runtime.mkdir(mode=0o700)
        env = dict(os.environ)
        for name in ("HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY", "SWAYSOCK", "DISPLAY"):
            env.pop(name, None)
        env.update({
            "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_CACHE_HOME": str(work / "cache"),
            "XDG_DATA_HOME": str(work / "data"),
            "XDG_STATE_HOME": str(work / "state"),
            "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "1",
            "WLR_RENDERER": "pixman",
            "WLR_LIBINPUT_NO_DEVICES": "1",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "FONTCONFIG_FILE": str(REPO_ROOT / "config/hypr/fontconfig.conf"),
            "SPIDEY_LOCK_ASSETS": str(REPO_ROOT / "config/hypr/lock-assets"),
            "SPIDEY_WALLPAPER": str(REPO_ROOT / "assets/wallpapers/spidey-city.png"),
        })
        for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            Path(env[name]).mkdir()
        config = work / "sway.conf"
        config.write_text(
            f"output HEADLESS-1 mode {width}x{height}\n"
            "output * scale 1\n"
            "output * bg #070e28 solid_color\n"
            "seat seat0 fallback true\n", encoding="utf-8")

        def launch(name, arguments):
            log_path = Path(f"{prefix}-{name}.log")
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(arguments, env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            processes.append((name, process, log_path))
            return process

        def run(arguments):
            result = subprocess.run(arguments, env=env, capture_output=True,
                                    text=True, timeout=15, check=False)
            if result.returncode:
                raise RuntimeError(f"Command failed: {arguments!r}\n{result.stdout}{result.stderr}")
            return result

        def wait_for(predicate, description, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                for name, process, log_path in processes:
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited with {process.returncode}; see {log_path}")
                value = predicate()
                if value:
                    return value
                time.sleep(0.1)
            raise TimeoutError(f"Timed out waiting for {description}")

        try:
            launch("sway", [tools["sway"], "-c", str(config), "-d"])
            socket = wait_for(lambda: next(runtime.glob("sway-ipc.*.sock"), None), "Sway IPC")
            display = wait_for(lambda: next((path for path in runtime.glob("wayland-*")
                                             if path.is_socket()), None), "private Wayland socket")
            env.update({"SWAYSOCK": str(socket), "WAYLAND_DISPLAY": display.name})
            def output_ready():
                outputs = json.loads(run([tools["swaymsg"], "-t", "get_outputs", "-r"]).stdout)
                return any(output.get("active") and output.get("rect", {}).get("width") == width
                           and output.get("rect", {}).get("height") == height for output in outputs)

            wait_for(output_ready, f"{width}x{height} headless output")
            launch("hyprlock", [tools["hyprlock"], "--config", str(REPO_ROOT / "config/hypr/hyprlock.conf"),
                                "--grace", "0", "--no-fade-in"])
            lock_log = Path(f"{prefix}-hyprlock.log")
            wait_for(lambda: "onLockLocked called" in lock_log.read_text(errors="replace"),
                     "Hyprlock's ext-session-lock locked event")
            # Let asynchronous label/image loading settle before examining pixels.
            time.sleep(1)
            run([tools["grim"], str(prefix.with_suffix(".png"))])
            text = lock_log.read_text(errors="replace")
            for error in ("Config has errors", "Config threw", "Hyprlock threw", "invalid texture",
                          "Failed to initialize EGL", "Failed to create EGL", "Failed to match an EGL config"):
                if error in text:
                    raise AssertionError(f"Hyprlock reported {error}; see {lock_log}")
            actual_width, actual_height, pixel = png_pixels(prefix.with_suffix(".png"))
            if (actual_width, actual_height) != (width, height):
                raise AssertionError("Lockscreen screenshot dimensions differ from the output")
            left, top = (width - 544) // 2, (height - 588) // 2
            # Both opaque edge colors must survive image loading and centering.
            checks = {
                "cyan frame": (pixel(left + 5, top + 292), (73, 199, 244)),
                "ice bevel": (pixel(left + 9, top + 292), (140, 234, 255)),
                "navy panel": (pixel(left + 24, top + 292), (25, 36, 80)),
            }
            report["rendered_colors"] = {name: list(actual) for name, (actual, _) in checks.items()}
            for name, (actual, expected) in checks.items():
                if any(abs(a - b) > 2 for a, b in zip(actual, expected)):
                    raise AssertionError(f"{name} was not rendered in its expected position: {actual} != {expected}")
            background_colors = {pixel(x, y)
                                 for y in range(20, height - 20, 40)
                                 for x in range(20, width - 20, 40)
                                 if not (left <= x < left + 544 and top <= y < top + 588)}
            report["wallpaper_sample_colors"] = len(background_colors)
            if len(background_colors) < 12:
                raise AssertionError("The wallpaper appears to be missing or covered by an opaque layer")
            report.update({"session_locked": True, "passed": True})
            print(f"Real Hyprlock locked and rendered at {width}x{height}; no password submitted.", flush=True)
        except Exception as error:
            report.update({"passed": False, "error": str(error)})
            raise
        finally:
            prefix.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            for _, process, _ in reversed(processes):
                stop(process)


def main():
    requested_root = os.environ.get("ARTIFACT_ROOT")
    artifact_root = Path(requested_root).expanduser().resolve() if requested_root else Path(
        tempfile.mkdtemp(prefix="spidey-lockscreen-artifacts-"))
    artifact_root.mkdir(parents=True, exist_ok=True)
    print(f"Lockscreen artifacts: {artifact_root}", flush=True)
    try:
        tools = {name: binary(name) for name in ("sway", "swaymsg", "grim", "hyprlock")}
        for width, height in SIZES:
            check_size(width, height, tools, artifact_root)
    except (AssertionError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Lockscreen regression failed: {error}\nArtifacts: {artifact_root}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
