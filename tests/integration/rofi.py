#!/usr/bin/env python3
"""Render the real launcher and exercise a terminal desktop entry under Xvfb.

Requires rofi and Xvfb (xorg-server-xvfb on Arch). Every config, desktop entry,
and display belongs to this test; it never uses the live desktop. ARTIFACT_ROOT
selects retained logs/report files, otherwise a temporary artifact directory is
printed. ImageMagick's import optionally saves a launcher screenshot.
"""

import json
import os
from pathlib import Path
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def exercise(artifacts):
    report = {"passed": False, "checks": []}
    terminal_log = artifacts / "rofi-terminal.log"
    xvfb = rofi = None
    read_fd = None
    try:
        for program in ("Xvfb", "rofi"):
            if not shutil.which(program):
                raise RuntimeError(f"Integration check requires {program}")
        report["rofi_version"] = subprocess.run(
            ["rofi", "-version"], check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="spidey-rofi-") as temporary:
            work = Path(temporary)
            env = dict(os.environ)
            for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY",
                         "DBUS_SESSION_BUS_ADDRESS", "HYPRLAND_INSTANCE_SIGNATURE", "SWAYSOCK"):
                env.pop(name, None)
            for key, folder in {
                "HOME": "home", "XDG_CONFIG_HOME": "config", "XDG_CONFIG_DIRS": "system-config",
                "XDG_DATA_HOME": "data", "XDG_DATA_DIRS": "data", "XDG_CACHE_HOME": "cache",
                "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "runtime",
            }.items():
                directory = work / folder
                directory.mkdir(mode=0o700, exist_ok=True)
                env[key] = str(directory)
            apps = work / "data" / "applications"
            apps.mkdir()
            for name in ("Brave", "Discord", "Nemo", "Obsidian", "Spotify", "Vim"):
                entry = "Exec=/bin/true --fixture-argument\nTerminal=true\n" if name == "Vim" else "Exec=/bin/true\nTerminal=false\n"
                (apps / f"{name.lower()}.desktop").write_text(
                    "[Desktop Entry]\nType=Application\n"
                    f"Name={name}\n{entry}", encoding="utf-8",
                )

            read_fd, write_fd = os.pipe()
            try:
                with (artifacts / "xvfb.log").open("w", encoding="utf-8") as log:
                    xvfb = subprocess.Popen(
                        ["Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1200x800x24", "-nolisten", "tcp"],
                        env=env, pass_fds=(write_fd,), stdout=log, stderr=subprocess.STDOUT,
                    )
            finally:
                os.close(write_fd)
            assert select.select([read_fd], [], [], 10)[0], "Xvfb did not start within ten seconds"
            display = os.read(read_fd, 32).decode().strip()
            os.close(read_fd)
            read_fd = None
            assert display.isdecimal(), "Xvfb did not return a display number; see xvfb.log"
            env["DISPLAY"] = f":{display}"

            args = ["rofi", "-show", "drun", "-theme", str(ROOT / "quickshell/assets/rofi.rasi")]
            with (artifacts / "rofi.log").open("w", encoding="utf-8") as log:
                rofi = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
            time.sleep(1)
            assert rofi.poll() is None, f"The themed launcher exited: {(artifacts / 'rofi.log').read_text()}"
            report["checks"].append("Real themed application launcher stays open on an isolated display")
            if shutil.which("import"):
                try:
                    screenshot = artifacts / "launcher.png"
                    subprocess.run(
                        ["import", "-display", env["DISPLAY"], "-window", "root", str(screenshot)],
                        env=env, check=True, capture_output=True, timeout=10,
                    )
                    report["screenshot"] = str(screenshot)
                except (OSError, subprocess.SubprocessError) as exc:
                    report["screenshot_skipped"] = str(exc)
            stop(rofi)
            rofi = None

            capture = work / "terminal-argv.json"
            terminal = work / "kitty fixture"
            terminal.write_text(
                f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                f"capture = Path({str(capture)!r})\n"
                "temporary = capture.with_suffix('.tmp')\n"
                "temporary.write_text(json.dumps(sys.argv[1:]))\ntemporary.replace(capture)\n",
                encoding="utf-8",
            )
            terminal.chmod(0o755)
            error_callback = work / "capture-rofi-error.py"
            error_callback.write_text(
                "import json, sys\nfrom pathlib import Path\n"
                "Path(sys.argv[1]).write_text(json.dumps({'error': ' '.join(sys.argv[2:])}))\n",
                encoding="utf-8",
            )
            callback = shlex.join([sys.executable, str(error_callback), str(artifacts / "rofi-error.json")]) + ' "{error}"'
            settings = work / "config" / "spidey"
            settings.mkdir()
            (settings / "apps.json").write_text(json.dumps({
                "terminal": [[str(terminal), "--configured-arg", "Daily coding"]],
                "launcher": [[*args, "-auto-select", "-filter", "Vim", "-log", str(terminal_log),
                              "-on-menu-error", callback]],
            }), encoding="utf-8")
            (artifacts / "apps.json").write_text((settings / "apps.json").read_text(encoding="utf-8"), encoding="utf-8")
            resolved = subprocess.run(
                [sys.executable, "-c",
                 "import json, runpy, sys\n"
                 "module = runpy.run_path(sys.argv[1])\n"
                 "print(json.dumps(module['app_candidates']('launcher')))\n",
                 str(ROOT / "quickshell/scripts/system.py")],
                env=env, check=True, capture_output=True, text=True, timeout=10,
            )
            report["resolved_launcher_argv"] = json.loads(resolved.stdout)[0]
            result = subprocess.run(
                [sys.executable, str(ROOT / "quickshell/scripts/system.py"), "action", "launcher"],
                env=env, check=True, text=True, capture_output=True, timeout=10,
            )
            payload = json.loads(result.stdout)
            assert payload == {"success": True, "program": "rofi"}, payload
            deadline = time.monotonic() + 8
            while not capture.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert capture.exists(), "Rofi did not execute the configured terminal for the Vim fixture"
            argv = json.loads(capture.read_text(encoding="utf-8"))
            assert argv[:2] == ["--configured-arg", "Daily coding"], argv
            assert "/bin/true" in argv and "--fixture-argument" in argv, argv
            report["terminal_argv"] = argv
            report["checks"].append("Public APPS action executes Terminal=true entries using configured terminal path and arguments")
            report["passed"] = True
    except Exception as exc:
        report["error"] = str(exc)
        if terminal_log.exists():
            lines = terminal_log.read_text(encoding="utf-8", errors="replace").splitlines()
            useful = [line for line in lines if not line.startswith(("[Theme]", "[Widgets.", "[Timings]"))
                      or any(word in line.lower() for word in ("error", "fail", "warning"))]
            report["terminal_log_tail"] = "\n".join(useful)[-6000:]
        raise
    finally:
        if read_fd is not None:
            os.close(read_fd)
        stop(rofi)
        stop(xvfb)
        (artifacts / "rofi.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    artifacts = Path(os.environ.get("ARTIFACT_ROOT") or tempfile.mkdtemp(prefix="spidey-rofi-artifacts-"))
    artifacts.mkdir(parents=True, exist_ok=True)
    print(f"Rofi integration artifacts: {artifacts}", flush=True)
    exercise(artifacts)
