#!/usr/bin/env python3
"""Upgrade real running shells without touching another configuration or desktop.

Requires Python, Sway and Quickshell. QS_BINARY selects a Quickshell executable;
ARTIFACT_ROOT selects retained logs and JSON evidence. All configuration, sockets,
processes and installed links belong to a temporary private desktop.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from wayland_workarea import PROBE_QML, binary, stop


ROOT = Path(__file__).resolve().parents[2]


def snapshot(directory):
    return {str(path.relative_to(directory)): (
        ["link", os.readlink(path)] if path.is_symlink() else
        ["directory"] if path.is_dir() else ["file", path.read_bytes().hex()]
    ) for path in sorted(directory.rglob("*"))}


def check_upgrade(artifacts):
    qs = binary(os.environ.get("QS_BINARY") or shutil.which("qs") or "quickshell")
    sway = binary("sway")
    report = {"checks": []}
    processes = []
    with tempfile.TemporaryDirectory(prefix="spidey-upgrade-") as temporary:
        work = Path(temporary)
        checkout, config, runtime = work / "checkout", work / "config", work / "run"
        shutil.copytree(ROOT, checkout, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        shutil.copytree(checkout / "quickshell", checkout / "quickshell-retro")
        shutil.copytree(checkout / "config/hypr", checkout / "config/hypr-retro")
        (checkout / "config/kitty").mkdir()
        runtime.mkdir(mode=0o700)
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SWAYSOCK", "HYPRLAND_INSTANCE_SIGNATURE",
                     "SPIDEY_PREVIEW", "SPIDEY_SCREENSHOT", "QS_CONFIG_NAME", "QS_CONFIG_PATH",
                     "QS_MANIFEST", "QT_SCREEN_SCALE_FACTORS"):
            env.pop(name, None)
        env.update({"XDG_RUNTIME_DIR": str(runtime), "XDG_CONFIG_HOME": str(config),
                    "HOME": str(work / "home"), "XDG_CACHE_HOME": str(work / "cache"),
                    "XDG_DATA_HOME": str(work / "data"), "XDG_STATE_HOME": str(work / "state"),
                    "QML_DISK_CACHE_PATH": str(work / "cache/qml"),
                    "WLR_BACKENDS": "headless", "WLR_HEADLESS_OUTPUTS": "1",
                    "WLR_RENDERER": "pixman", "WLR_LIBINPUT_NO_DEVICES": "1",
                    "QT_QPA_PLATFORM": "wayland", "QT_QUICK_BACKEND": "software",
                    "QT_SCALE_FACTOR": "1", "QT_AUTO_SCREEN_SCALE_FACTOR": "0", "SPIDEY_DEMO": "1"})
        for key in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            Path(env[key]).mkdir()
        (work / "bin").mkdir()
        (work / "bin/qs").symlink_to(qs)
        env["PATH"] = str(work / "bin") + os.pathsep + env["PATH"]
        links = {"quickshell/spidey": "quickshell", "quickshell/spidey-retro": "quickshell-retro",
                 "hypr-spidey": "config/hypr", "hypr-spidey-retro": "config/hypr-retro",
                 "kitty-spidey": "config/kitty"}
        for destination, source in links.items():
            path = config / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(checkout / source)
        originals = {
            "hypr/autostart.lua": 'dofile(config_root .. "/hypr-spidey-retro/rice.lua")\n'
                                  'hl.exec_cmd("qs -c spidey-retro")\nhl.exec_cmd("discord")\n',
            "kitty/kitty.conf": "font_size 13\ninclude ../kitty-spidey/kitty.conf\n",
            "spidey/apps.json": '{"files": [["nemo", "{home}"]]}\n',
        }
        for relative, text in originals.items():
            path = config / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text(text)
        probe = config / "quickshell/unrelated"
        probe.mkdir()
        (probe / "shell.qml").write_text(PROBE_QML)
        sway_config = work / "sway.conf"
        sway_config.write_text("output HEADLESS-1 mode 1600x1000\noutput * scale 1\nseat seat0 fallback true\n")

        def run(arguments, check=True):
            result = subprocess.run(arguments, env=env, capture_output=True, text=True,
                                    timeout=45, check=False)
            with (artifacts / "upgrade-commands.log").open("a") as log:
                log.write(f"{arguments!r}\nexit={result.returncode}\n{result.stdout}{result.stderr}\n")
            if check and result.returncode:
                raise RuntimeError(f"Command failed: {arguments!r}; see upgrade-commands.log")
            return result

        def launch(name, arguments):
            with (artifacts / f"upgrade-{name}.log").open("w") as log:
                process = subprocess.Popen(arguments, env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(process)

        def wait_for(predicate, description):
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                value = predicate()
                if value:
                    return value
                time.sleep(0.1)
            raise TimeoutError(f"Timed out waiting for {description}; see upgrade logs")

        def instances():
            result = run([qs, "list", "--all", "--json"])
            return [] if result.stdout.strip() in ("", "No running instances.") else json.loads(result.stdout)

        def record(label, values):
            report["checks"].append({"action": label, "instances": values})
            print(json.dumps({"action": label, "instances": len(values)}), flush=True)

        try:
            launch("sway", [sway, "-c", str(sway_config)])
            env["SWAYSOCK"] = str(wait_for(lambda: next(runtime.glob("sway-ipc.*.sock"), None), "Sway IPC"))
            env["WAYLAND_DISPLAY"] = wait_for(
                lambda: next((path.name for path in runtime.glob("wayland-*") if path.is_socket()), None),
                "Wayland socket")
            for name in ("spidey", "spidey-retro", "unrelated"):
                launch(name, [qs, "-c", name, "--no-color"])
            initial = wait_for(lambda: (items if len(items := instances()) == 3 else None), "three old shells")
            # Quickshell 0.2 resolves config symlinks; 0.3 retains their paths.
            canonical_paths = {str(config / "quickshell/spidey/shell.qml"),
                               str(checkout / "quickshell/shell.qml")}
            retired_paths = {str(config / "quickshell/spidey-retro/shell.qml"),
                             str(checkout / "quickshell-retro/shell.qml")}
            unrelated_path = str(probe / "shell.qml")
            old = {item["id"] for item in initial if item["config_path"] in canonical_paths | retired_paths}
            unrelated = next(item["id"] for item in initial if item["config_path"] == unrelated_path)
            assert len(old) == 2, initial
            # A git pull can remove retired source directories before the
            # installer runs. Surviving processes must be stopped by ID.
            for relative in ("quickshell-retro", "config/hypr-retro", "config/kitty"):
                shutil.rmtree(checkout / relative)
            remaining = instances()
            assert unrelated in {item["id"] for item in remaining}
            before = snapshot(config)
            installer = ["bash", str(checkout / "scripts/install.sh"), "--config-root", str(config)]
            run([*installer, "--dry-run"])
            assert snapshot(config) == before, "Dry run changed configuration"
            assert {item["id"] for item in instances()} == {item["id"] for item in remaining}, "Dry run restarted a shell"
            record("dry-run-after-source-removal", remaining)
            run(installer)

            def installed():
                items = instances()
                if (len(items) != 2 or sum(item["config_path"] in canonical_paths for item in items) != 1
                        or not any(item["config_path"] == unrelated_path for item in items)):
                    return None
                identifiers = {item["id"] for item in items}
                return items if unrelated in identifiers and not old & identifiers else None

            upgraded = wait_for(installed, "one updated shell and the untouched unrelated shell")
            for relative in ("quickshell/spidey-retro", "hypr-spidey-retro", "kitty-spidey"):
                assert not os.path.lexists(config / relative), f"Retired link remains: {relative}"
            startup = (config / "hypr/autostart.lua").read_text()
            assert '"/hypr-spidey/rice.lua"' in startup and '"qs -c spidey --no-duplicate"' in startup
            assert 'hl.exec_cmd("discord")' in startup
            assert (config / "kitty/kitty.conf").read_text().splitlines()[1].startswith("#")
            for relative in ("hypr/autostart.lua", "kitty/kitty.conf"):
                path = config / relative
                backups = list(path.parent.glob(path.name + ".spidey-backup.*"))
                assert len(backups) == 1 and backups[0].read_text() == originals[relative]
            assert (config / "spidey/apps.json").read_text() == originals["spidey/apps.json"]
            record("upgrade", upgraded)
            after = snapshot(config)
            run(installer)
            repeated = wait_for(installed, "one shell after repeated installation")
            assert snapshot(config) == after, "Repeated installation changed files or created extra backups"
            record("repeat-install", repeated)
            report["passed"] = True
        except Exception as error:
            report.update(passed=False, error=str(error))
            raise
        finally:
            (artifacts / "upgrade.json").write_text(json.dumps(report, indent=2) + "\n")
            # Inventory and IDs are scoped to this test's private runtime/display.
            if env.get("WAYLAND_DISPLAY"):
                try:
                    for item in instances():
                        run([qs, "kill", "--id", item["id"]], check=False)
                except (OSError, ValueError, subprocess.SubprocessError, RuntimeError):
                    pass
            for process in reversed(processes):
                stop(process)


def main():
    requested = os.environ.get("ARTIFACT_ROOT")
    artifacts = Path(requested).expanduser().resolve() if requested else Path(
        tempfile.mkdtemp(prefix="spidey-upgrade-artifacts-"))
    artifacts.mkdir(parents=True, exist_ok=True)
    print(f"Upgrade artifacts: {artifacts}", flush=True)
    try:
        check_upgrade(artifacts)
    except (AssertionError, OSError, RuntimeError, subprocess.SubprocessError, StopIteration) as error:
        print(f"Live upgrade regression failed: {error}\nArtifacts: {artifacts}", file=sys.stderr)
        return 1
    print("Live upgrade, dry-run, preferences, backups, and unrelated-shell preservation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
