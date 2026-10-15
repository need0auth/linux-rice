"""Exercise the real installer against isolated config roots, never the user config."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="spidey installer ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.config_root = self.base / "config with spaces"

    def run_script(self, script, *arguments, expected_code=0):
        result = subprocess.run(
            [
                "bash", str(REPO_ROOT / "scripts" / script),
                "--config-root", str(self.config_root), *arguments,
            ],
            cwd=self.base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode, expected_code,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def assert_installed(self):
        for relative, source in (
            ("quickshell/spidey", "quickshell"),
            ("hypr-spidey", "config/hypr"),
            ("kitty-spidey", "config/kitty"),
        ):
            destination = self.config_root / relative
            self.assertTrue(destination.is_symlink(), str(destination))
            self.assertEqual(destination.resolve(), REPO_ROOT / source)

    def test_dry_run_does_not_create_directories(self):
        result = self.run_script("install.sh", "--dry-run")
        self.assertIn("Link ", result.stdout)
        self.assertFalse(self.config_root.exists())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_install_can_be_repeated_and_uninstall_dry_run_preserves_links(self):
        self.run_script("install.sh")
        self.assert_installed()
        result = self.run_script("install.sh")
        self.assertEqual(result.stdout.count("Already linked:"), 3)
        self.assert_installed()
        self.run_script("uninstall.sh", "--dry-run")
        self.assert_installed()
        self.run_script("uninstall.sh")
        for relative in ("quickshell/spidey", "hypr-spidey", "kitty-spidey"):
            destination = self.config_root / relative
            self.assertFalse(destination.exists())
            self.assertFalse(destination.is_symlink())

    def test_conflict_preserves_content_and_prevents_partial_installation(self):
        existing = self.config_root / "hypr-spidey"
        existing.mkdir(parents=True)
        personal_file = existing / "personal.conf"
        personal_file.write_text("my original settings\n", encoding="utf-8")
        result = self.run_script("install.sh", expected_code=1)
        self.assertIn("Nothing changed", result.stderr)
        self.assertEqual(personal_file.read_text(encoding="utf-8"), "my original settings\n")
        self.assertEqual(list(self.config_root.iterdir()), [existing])
        self.assertFalse((self.config_root / "quickshell").exists())

    def test_backup_keeps_original_content_through_install_and_uninstall(self):
        existing = self.config_root / "hypr-spidey"
        existing.mkdir(parents=True)
        (existing / "personal.conf").write_text("preserve me\n", encoding="utf-8")
        self.run_script("install.sh", "--backup")
        self.assert_installed()
        backups = list(self.config_root.glob("hypr-spidey.spidey-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "personal.conf").read_text(encoding="utf-8"), "preserve me\n")
        self.run_script("install.sh", "--backup")
        self.assertEqual(list(self.config_root.glob("hypr-spidey.spidey-backup.*")), backups)
        self.run_script("uninstall.sh")
        self.assertEqual((backups[0] / "personal.conf").read_text(encoding="utf-8"), "preserve me\n")

    def test_uninstall_preserves_foreign_files_and_symlinks(self):
        self.run_script("install.sh")
        foreign_file = self.config_root / "hypr-spidey"
        foreign_file.unlink()
        foreign_file.write_text("user replacement\n", encoding="utf-8")
        outside = self.base / "unrelated directory"
        outside.mkdir()
        marker = outside / "important.txt"
        marker.write_text("still here\n", encoding="utf-8")
        foreign_link = self.config_root / "kitty-spidey"
        foreign_link.unlink()
        foreign_link.symlink_to(outside, target_is_directory=True)
        self.run_script("uninstall.sh")
        self.assertEqual(foreign_file.read_text(encoding="utf-8"), "user replacement\n")
        self.assertTrue(foreign_link.is_symlink())
        self.assertEqual(foreign_link.resolve(), outside)
        self.assertEqual(marker.read_text(encoding="utf-8"), "still here\n")
        self.assertFalse((self.config_root / "quickshell/spidey").is_symlink())


if __name__ == "__main__":
    unittest.main()
