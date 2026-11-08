"""Run the read-only checker with representative distro and bundled-app fixtures."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CheckerTests(unittest.TestCase):
    def check(self, distro, launcher="noctalia", files="dolphin"):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            release = base / "os-release"
            release.write_text(f'ID="{distro}"\n')
            script = base / "check.sh"
            script.write_text((ROOT / "scripts/check-arch.sh").read_text().replace("/etc/os-release", str(release)))
            for name, output in {
                "Hyprland": "Hyprland 0.56.2", "qs": "quickshell 0.3.2",
                "pacman": "test-package 1.0", launcher: "", files: "",
                **dict.fromkeys(["kitty", "brave", "wpctl", "brightnessctl", "playerctl", "nmcli", "nm-connection-editor", "grim", "slurp", "wl-copy", "hyprlock"], ""),
            }.items():
                command = base / name
                command.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
                command.chmod(0o755)
            return subprocess.run(["bash", str(script), "--all-tools"], env={**os.environ, "PATH": f"{base}:{os.environ['PATH']}"}, capture_output=True, text=True)

    def test_cachyos_bundled_apps_satisfy_all_tools(self):
        result = self.check("cachyos")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS noctalia", result.stdout)
        self.assertIn("PASS dolphin", result.stdout)

    def test_arch_fallback_apps_satisfy_all_tools(self):
        result = self.check("arch", "rofi", "nemo")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsupported_distro_still_fails(self):
        result = self.check("debian")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ID=debian", result.stdout)
