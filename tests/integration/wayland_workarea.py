#!/usr/bin/env python3
"""Check real layer-shell reservations in an isolated headless Sway session.

Run directly with Python 3. Requires sway, swaymsg, grim, and Quickshell on PATH;
QS_BINARY can select another Quickshell executable. ARTIFACT_ROOT selects the
directory for logs, screenshots, and geometry JSON. Otherwise a persistent
temporary artifact directory is created and printed. No live desktop is used.
"""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1600, 1000), (1366, 768))
PROBE_TITLE = "SPIDEY WORKAREA PROBE"
PROBE_QML = """import QtQuick
import Quickshell

ShellRoot {
    FloatingWindow {
        title: "SPIDEY WORKAREA PROBE"
        implicitWidth: 800
        implicitHeight: 600
        color: "#e8edf2"
        Text {
            anchors.centerIn: parent
            text: "TILED WINDOW\\nWORKAREA PROBE"
            color: "#122743"
            font.pixelSize: 28
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
"""


def binary(name):
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Required executable is missing or not executable: {name}")
    return str(Path(resolved).resolve())


def tree_nodes(node):
    yield node
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        yield from tree_nodes(child)


def stop(process):
    # Each child starts its own session; this also stops only its descendants.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)


def check_size(width, height, tools, artifact_root):
    prefix = artifact_root / f"workarea-{width}x{height}"
    geometry_path = prefix.with_suffix(".json")
    report = {"size": [width, height], "expected": {
        "x": 100, "y": 76, "width": width - 100, "height": height - 174,
    }, "checks": []}
    processes = []
    critical_processes = []

    # Keep sockets short and separate from retained logs and screenshots.
    with tempfile.TemporaryDirectory(prefix="spidey-wl-") as temporary:
        work = Path(temporary)
        runtime = work / "run"
        runtime.mkdir(mode=0o700)
        env = dict(os.environ)
        for name in (
            "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY", "SWAYSOCK", "DISPLAY",
            "SPIDEY_PREVIEW", "SPIDEY_SCREENSHOT", "QT_SCREEN_SCALE_FACTORS",
        ):
            env.pop(name, None)
        env.update({
            "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_CACHE_HOME": str(work / "cache"),
            "XDG_DATA_HOME": str(work / "data"),
            "XDG_STATE_HOME": str(work / "state"),
            "QML_DISK_CACHE_PATH": str(work / "cache" / "qml"),
            "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "1",
            "WLR_RENDERER": "pixman",
            "WLR_LIBINPUT_NO_DEVICES": "1",
            "QT_QPA_PLATFORM": "wayland",
            "QT_QUICK_BACKEND": "software",
            "QT_SCALE_FACTOR": "1",
            "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
            "SPIDEY_DEMO": "1",
        })
        for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            Path(env[name]).mkdir()

        config = work / "sway.conf"
        config_text = (
            f"output HEADLESS-1 mode {width}x{height}\n"
            "output * scale 1\n"
            "output * bg #070e28 solid_color\n"
            "seat seat0 fallback true\n"
            "default_border none\n"
            "default_floating_border none\n"
            "gaps inner 0\n"
            "gaps outer 0\n"
        )
        config.write_text(config_text, encoding="utf-8")
        Path(f"{prefix}-sway.conf").write_text(config_text, encoding="utf-8")
        probe_config = work / "probe"
        probe_config.mkdir()
        (probe_config / "shell.qml").write_text(PROBE_QML, encoding="utf-8")

        def launch(name, arguments, critical=True):
            log_path = Path(f"{prefix}-{name}.log")
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(arguments, env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(process)
            if critical:
                critical_processes.append((name, process, log_path))
            return process

        def run(arguments, check=True):
            result = subprocess.run(arguments, env=env, capture_output=True,
                                    text=True, timeout=10, check=False)
            if check and result.returncode:
                raise RuntimeError(f"Command failed: {arguments!r}\n{result.stdout}{result.stderr}")
            return result

        def wait_for(predicate, description, timeout=15):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                for name, process, log_path in critical_processes:
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited with {process.returncode}; see {log_path}")
                value = predicate()
                if value:
                    return value
                time.sleep(0.1)
            raise TimeoutError(f"Timed out waiting for {description}")

        def probe_rect():
            tree = json.loads(run([tools["swaymsg"], "-t", "get_tree", "-r"]).stdout)
            probe = next((node for node in tree_nodes(tree)
                          if node.get("name") == PROBE_TITLE), None)
            return probe["rect"] if probe else None

        def record_geometry(action):
            # Check several frames after compositor layout has settled.
            time.sleep(0.2)
            samples = []
            for _ in range(4):
                samples.append(probe_rect())
                time.sleep(0.1)
            report["checks"].append({"action": action, "samples": samples})
            if any(rect != report["expected"] for rect in samples):
                raise AssertionError(f"{width}x{height} {action}: expected {report['expected']}, got {samples}")
            print(json.dumps({"size": [width, height], "action": action,
                              "rect": samples[-1]}), flush=True)

        try:
            launch("sway", [tools["sway"], "-c", str(config), "-d"])
            socket = wait_for(lambda: next(runtime.glob("sway-ipc.*.sock"), None), "Sway IPC socket")
            display = wait_for(lambda: next((path for path in runtime.glob("wayland-*")
                                             if path.is_socket()), None), "Wayland socket")
            env.update({"SWAYSOCK": str(socket), "WAYLAND_DISPLAY": display.name})

            def output_ready():
                result = run([tools["swaymsg"], "-t", "get_outputs", "-r"], check=False)
                if result.returncode:
                    return False
                outputs = json.loads(result.stdout)
                return any(output.get("active") and output.get("rect", {}).get("width") == width
                           and output.get("rect", {}).get("height") == height for output in outputs)

            wait_for(output_ready, f"{width}x{height} headless output")
            shell_args = [tools["quickshell"], "-p", str(REPO_ROOT / "quickshell")]
            launch("shell", [*shell_args, "--no-duplicate", "--no-color"])
            wait_for(lambda: run([*shell_args, "ipc", "show"], check=False).returncode == 0,
                     "Quickshell IPC")
            launch("probe", [tools["quickshell"], "-p", str(probe_config), "--no-color"])
            wait_for(probe_rect, "probe window")
            result = run([tools["swaymsg"], f'[title="{PROBE_TITLE}"] floating disable, border none'])
            if not all(reply.get("success") for reply in json.loads(result.stdout)):
                raise RuntimeError(f"Sway could not tile probe: {result.stdout}")
            wait_for(lambda: probe_rect() == report["expected"], "reserved workarea geometry")
            record_geometry("initial")

            for action in ("open", "close", "toggle", "toggle", "open", "controls", "controls"):
                run([*shell_args, "ipc", "call", "dashboard", action])
                record_geometry(action)

            duplicate = launch("duplicate", [*shell_args, "--no-duplicate", "--no-color"], critical=False)
            try:
                code = duplicate.wait(timeout=5)
            except subprocess.TimeoutExpired as error:
                raise AssertionError("--no-duplicate did not exit within five seconds") from error
            if code != 0:
                raise AssertionError(f"--no-duplicate exited with {code}; see {prefix}-duplicate.log")
            record_geometry("no-duplicate")
            run([tools["grim"], str(prefix.with_suffix(".png"))])
            report["passed"] = True
        except Exception as error:
            report["passed"] = False
            report["error"] = str(error)
            # Retain the failed composition as evidence when Sway is still alive.
            if env.get("WAYLAND_DISPLAY"):
                try:
                    run([tools["grim"], str(prefix.with_suffix(".png"))], check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            raise
        finally:
            geometry_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            for process in reversed(processes):
                stop(process)


def main():
    requested_root = os.environ.get("ARTIFACT_ROOT")
    artifact_root = Path(requested_root).expanduser().resolve() if requested_root else Path(
        tempfile.mkdtemp(prefix="spidey-workarea-artifacts-"))
    artifact_root.mkdir(parents=True, exist_ok=True)
    print(f"Workarea artifacts: {artifact_root}", flush=True)
    try:
        quickshell = os.environ.get("QS_BINARY") or shutil.which("qs") or "quickshell"
        tools = {name: binary(name) for name in ("sway", "swaymsg", "grim")}
        tools["quickshell"] = binary(quickshell)
        for width, height in SIZES:
            check_size(width, height, tools, artifact_root)
    except (AssertionError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Workarea regression failed: {error}\nArtifacts: {artifact_root}", file=sys.stderr)
        return 1
    print("Headless Wayland workarea, popup IPC, and duplicate-launch checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
