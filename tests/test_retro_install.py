"""Exercise coexistence and conflict handling using real, isolated installers."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_LINKS = (
    ("quickshell/spidey", "quickshell"),
    ("hypr-spidey", "config/hypr"),
    ("kitty-spidey", "config/kitty"),
)
RETRO_LINKS = (
    ("quickshell/spidey-retro", "quickshell-retro"),
    ("hypr-spidey-retro", "config/hypr-retro"),
)


class RetroInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="spidey retro installer ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.config_root = self.base / "config with spaces and ' apostrophe"

    def run_script(self, name, *arguments, expected_code=0):
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / name), "--config-root", str(self.config_root), *arguments],
            cwd=self.base, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, expected_code, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def assert_links(self, links):
        for relative, source in links:
            target = self.config_root / relative
            self.assertTrue(target.is_symlink(), str(target))
            self.assertEqual(target.resolve(), REPO_ROOT / source)

    def assert_absent(self, links):
        for relative, _ in links:
            target = self.config_root / relative
            self.assertFalse(target.exists(), str(target))
            self.assertFalse(target.is_symlink(), str(target))

    def test_retro_dry_run_creates_nothing(self):
        output = self.run_script("install-retro.sh", "--dry-run").stdout
        self.assertEqual(output.count("Link "), 2)
        self.assertFalse(self.config_root.exists())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_original_then_retro_coexist_and_retro_removal_preserves_original(self):
        self.run_script("install.sh")
        self.run_script("install-retro.sh")
        self.assert_links(ORIGINAL_LINKS + RETRO_LINKS)
        self.assertEqual(self.run_script("install-retro.sh").stdout.count("Already linked:"), 2)
        self.run_script("uninstall-retro.sh", "--dry-run")
        self.assert_links(ORIGINAL_LINKS + RETRO_LINKS)
        self.run_script("uninstall-retro.sh")
        self.assert_links(ORIGINAL_LINKS)
        self.assert_absent(RETRO_LINKS)

    def test_retro_then_original_coexist_and_original_removal_preserves_retro(self):
        self.run_script("install-retro.sh")
        self.run_script("install.sh")
        self.assert_links(ORIGINAL_LINKS + RETRO_LINKS)
        self.run_script("uninstall.sh")
        self.assert_links(RETRO_LINKS)
        self.assert_absent(ORIGINAL_LINKS)

    def test_conflict_preflight_preserves_original_and_avoids_partial_install(self):
        self.run_script("install.sh")
        existing = self.config_root / "hypr-spidey-retro"
        existing.mkdir()
        marker = existing / "personal.conf"
        marker.write_text("keep personal configuration\n", encoding="utf-8")
        for arguments in ((), ("--dry-run",)):
            output = self.run_script("install-retro.sh", *arguments, expected_code=1)
            self.assertIn("Nothing changed", output.stderr)
            self.assertFalse((self.config_root / "quickshell/spidey-retro").is_symlink())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep personal configuration\n")
            self.assert_links(ORIGINAL_LINKS)

    def test_backup_dry_run_and_real_backup_preserve_content_and_original(self):
        self.run_script("install.sh")
        existing = self.config_root / "hypr-spidey-retro"
        existing.write_text("personal configuration\n", encoding="utf-8")
        self.run_script("install-retro.sh", "--backup", "--dry-run")
        self.assertEqual(existing.read_text(encoding="utf-8"), "personal configuration\n")
        self.assertFalse(list(self.config_root.glob("hypr-spidey-retro.spidey-retro-backup.*")))
        self.run_script("install-retro.sh", "--backup")
        self.assert_links(ORIGINAL_LINKS + RETRO_LINKS)
        backups = list(self.config_root.glob("hypr-spidey-retro.spidey-retro-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "personal configuration\n")
        self.run_script("install-retro.sh", "--backup")
        self.assertEqual(list(self.config_root.glob("hypr-spidey-retro.spidey-retro-backup.*")), backups)
        self.run_script("uninstall-retro.sh")
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "personal configuration\n")
        self.assert_links(ORIGINAL_LINKS)

    def test_retro_uninstall_preserves_replacement_files_and_foreign_symlinks(self):
        self.run_script("install.sh")
        self.run_script("install-retro.sh")
        replacement = self.config_root / "hypr-spidey-retro"
        replacement.unlink()
        replacement.write_text("user replacement\n", encoding="utf-8")
        external = self.base / "foreign shell"
        external.mkdir()
        marker = external / "important.qml"
        marker.write_text("leave me alone\n", encoding="utf-8")
        foreign_link = self.config_root / "quickshell/spidey-retro"
        foreign_link.unlink()
        foreign_link.symlink_to(external, target_is_directory=True)
        self.run_script("uninstall-retro.sh")
        self.assertEqual(replacement.read_text(encoding="utf-8"), "user replacement\n")
        self.assertEqual(foreign_link.resolve(), external)
        self.assertEqual(marker.read_text(encoding="utf-8"), "leave me alone\n")
        self.assert_links(ORIGINAL_LINKS)

    def test_broken_foreign_link_is_refused_until_backed_up(self):
        self.config_root.mkdir()
        destination = self.config_root / "hypr-spidey-retro"
        missing = self.base / "missing configuration"
        destination.symlink_to(missing, target_is_directory=True)
        self.run_script("install-retro.sh", expected_code=1)
        self.assertTrue(destination.is_symlink())
        self.run_script("install-retro.sh", "--backup")
        self.assert_links(RETRO_LINKS)
        backups = list(self.config_root.glob("hypr-spidey-retro.spidey-retro-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())
        self.assertEqual(backups[0].readlink(), missing)


if __name__ == "__main__":
    unittest.main()
