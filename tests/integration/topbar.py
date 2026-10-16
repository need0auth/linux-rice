#!/usr/bin/env python3
"""Run real top-bar QML bindings and click handlers in an isolated preview.

Requires Quickshell on PATH, or QS_BINARY. Uses Qt's offscreen backend and demo
actions, so no compositor or applications are launched. ARTIFACT_ROOT optionally
retains logs for both preview and desktop workspace bindings.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[2]


def main():
    executable = os.environ.get("QS_BINARY") or shutil.which("qs") or shutil.which("quickshell")
    if not executable:
        raise SystemExit("Quickshell is required; set QS_BINARY or add qs to PATH")
    artifact = os.environ.get("ARTIFACT_ROOT")
    artifact_root = Path(artifact) if artifact else None
    if artifact_root:
        artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spidey-topbar-") as temporary:
        work = Path(temporary)
        # Quickshell's QML scanner skips directory symlinks. Copy this small
        # config so the test exercises its normal component/import discovery.
        shutil.copytree(REPO_ROOT / "quickshell", work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(Path(__file__).with_suffix(".qml"), work / "shell.qml")
        runtime = work / "runtime"
        runtime.mkdir(mode=0o700)
        env = dict(os.environ)
        for name in ("HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY", "DISPLAY", "SPIDEY_SCREENSHOT", "QT_SCREEN_SCALE_FACTORS"):
            env.pop(name, None)
        env.update({
            "XDG_RUNTIME_DIR": str(runtime), "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_CACHE_HOME": str(work / "cache"), "XDG_STATE_HOME": str(work / "state"),
            "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
            "QT_SCALE_FACTOR": "1", "QT_AUTO_SCREEN_SCALE_FACTOR": "0", "SPIDEY_DEMO": "1",
        })
        for preview in ("0", "1"):
            env["SPIDEY_PREVIEW"] = preview
            try:
                result = subprocess.run(
                    [executable, "-p", str(work / "shell.qml"), "--no-color"],
                    env=env, capture_output=True, text=True, timeout=15, check=False,
                )
            except subprocess.TimeoutExpired as error:
                output = (error.stdout or b"") + (error.stderr or b"")
                raise SystemExit(output.decode(errors="replace") or "Top-bar interaction test timed out") from error
            output = result.stdout + result.stderr
            if artifact_root:
                (artifact_root / f"topbar-preview-{preview}.log").write_text(output)
            if result.returncode or "TOPBAR_INTERACTIONS_PASSED" not in output:
                raise SystemExit(output or "Top-bar interaction test exited without a result")
        print("Top-bar uptime, workspace bindings, and click handlers passed")


if __name__ == "__main__":
    main()
