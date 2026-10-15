"""Exercise real installation, safe migration and removal in isolated config roots."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
LINKS = (
    ("quickshell/spidey", "quickshell"),
    ("hypr-spidey", "config/hypr"),
)
RETIRED_LINKS = (
    ("quickshell/spidey-retro", "quickshell-retro"),
    ("hypr-spidey-retro", "config/hypr-retro"),
    ("kitty-spidey", "config/kitty"),
)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="spidey installer ")
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

    def create_links(self, links):
        for relative, source in links:
            target = self.config_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(REPO_ROOT / source, target_is_directory=True)

    def assert_links(self, links=LINKS):
        for relative, source in links:
            target = self.config_root / relative
            self.assertTrue(target.is_symlink(), str(target))
            self.assertEqual(target.readlink(), REPO_ROOT / source)

    def assert_absent(self, links):
        for relative, _ in links:
            target = self.config_root / relative
            self.assertFalse(target.exists(), str(target))
            self.assertFalse(target.is_symlink(), str(target))

    def test_dry_run_creates_nothing(self):
        output = self.run_script("install.sh", "--dry-run").stdout
        self.assertEqual(output.count("Link "), 2)
        self.assertFalse(self.config_root.exists())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_repeated_install_and_uninstall_dry_run(self):
        self.run_script("install.sh")
        self.assert_links()
        self.assertEqual(self.run_script("install.sh").stdout.count("Already linked:"), 2)
        self.run_script("uninstall.sh", "--dry-run")
        self.assert_links()
        self.run_script("uninstall.sh")
        self.assert_absent(LINKS)

    def test_conflicts_at_either_destination_prevent_partial_installation(self):
        for relative, _ in LINKS:
            with self.subTest(relative=relative):
                existing = self.config_root / relative
                existing.parent.mkdir(parents=True, exist_ok=True)
                existing.write_text("keep personal configuration\n", encoding="utf-8")
                for arguments in ((), ("--dry-run",)):
                    result = self.run_script("install.sh", *arguments, expected_code=1)
                    self.assertIn("Nothing changed", result.stderr)
                    self.assertEqual(existing.read_text(encoding="utf-8"), "keep personal configuration\n")
                    for other, _ in LINKS:
                        if other != relative:
                            self.assertFalse((self.config_root / other).is_symlink())
                existing.unlink()

    def test_backup_dry_run_and_actual_backup_preserve_user_content(self):
        existing = self.config_root / "hypr-spidey"
        existing.mkdir(parents=True)
        marker = existing / "personal.conf"
        marker.write_text("personal configuration\n", encoding="utf-8")
        self.run_script("install.sh", "--backup", "--dry-run")
        self.assertEqual(marker.read_text(encoding="utf-8"), "personal configuration\n")
        self.assertFalse(list(self.config_root.glob("hypr-spidey.spidey-backup.*")))
        self.run_script("install.sh", "--backup")
        self.assert_links()
        backups = list(self.config_root.glob("hypr-spidey.spidey-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "personal.conf").read_text(encoding="utf-8"), "personal configuration\n")
        self.run_script("install.sh", "--backup")
        self.assertEqual(list(self.config_root.glob("hypr-spidey.spidey-backup.*")), backups)
        self.run_script("uninstall.sh")
        self.assertEqual((backups[0] / "personal.conf").read_text(encoding="utf-8"), "personal configuration\n")

    def test_known_retired_symlinks_migrate_only_after_successful_install(self):
        self.create_links(RETIRED_LINKS)
        result = self.run_script("install.sh", "--dry-run")
        self.assertEqual(result.stdout.count("Retire old link:"), 3)
        self.assert_links(RETIRED_LINKS)
        self.assert_absent(LINKS)
        self.run_script("install.sh")
        self.assert_links()
        self.assert_absent(RETIRED_LINKS)
        self.assertFalse(list(self.config_root.glob("*.spidey-backup.*")))

    def test_conflict_preflight_preserves_retired_symlinks(self):
        self.create_links(RETIRED_LINKS)
        conflict = self.config_root / "hypr-spidey"
        conflict.write_text("personal configuration\n", encoding="utf-8")
        self.run_script("install.sh", expected_code=1)
        self.assert_links(RETIRED_LINKS)
        self.assertFalse((self.config_root / "quickshell/spidey").is_symlink())
        self.assertEqual(conflict.read_text(encoding="utf-8"), "personal configuration\n")

    def test_old_canonical_links_are_reused_while_retired_links_are_removed(self):
        # Earlier original installers already used these canonical targets.
        self.create_links(LINKS + RETIRED_LINKS)
        result = self.run_script("install.sh")
        self.assertEqual(result.stdout.count("Already linked:"), 2)
        self.assert_links()
        self.assert_absent(RETIRED_LINKS)

    def test_migration_and_uninstall_preserve_foreign_retired_paths(self):
        foreign_file = self.config_root / "hypr-spidey-retro"
        foreign_file.parent.mkdir(parents=True)
        foreign_file.write_text("user replacement\n", encoding="utf-8")
        external = self.base / "foreign shell"
        external.mkdir()
        marker = external / "important.qml"
        marker.write_text("leave me alone\n", encoding="utf-8")
        foreign_link = self.config_root / "quickshell/spidey-retro"
        foreign_link.parent.mkdir()
        foreign_link.symlink_to(external, target_is_directory=True)
        foreign_directory = self.config_root / "kitty-spidey"
        foreign_directory.mkdir()
        theme = foreign_directory / "personal.conf"
        theme.write_text("my terminal\n", encoding="utf-8")
        self.run_script("install.sh", "--backup")
        self.assert_links()
        self.run_script("uninstall.sh")
        self.assertEqual(foreign_file.read_text(encoding="utf-8"), "user replacement\n")
        self.assertEqual(foreign_link.resolve(), external)
        self.assertEqual(marker.read_text(encoding="utf-8"), "leave me alone\n")
        self.assertEqual(theme.read_text(encoding="utf-8"), "my terminal\n")

    def test_uninstall_preserves_foreign_canonical_files_and_symlinks(self):
        self.run_script("install.sh")
        replacement = self.config_root / "hypr-spidey"
        replacement.unlink()
        replacement.write_text("user replacement\n", encoding="utf-8")
        external = self.base / "foreign shell"
        external.mkdir()
        foreign_link = self.config_root / "quickshell/spidey"
        foreign_link.unlink()
        foreign_link.symlink_to(external, target_is_directory=True)
        self.run_script("uninstall.sh")
        self.assertEqual(replacement.read_text(encoding="utf-8"), "user replacement\n")
        self.assertEqual(foreign_link.resolve(), external)

    def test_broken_foreign_canonical_link_requires_explicit_backup(self):
        self.config_root.mkdir()
        destination = self.config_root / "hypr-spidey"
        missing = self.base / "missing configuration"
        destination.symlink_to(missing, target_is_directory=True)
        self.run_script("install.sh", expected_code=1)
        self.assertTrue(destination.is_symlink())
        self.run_script("install.sh", "--backup")
        self.assert_links()
        backups = list(self.config_root.glob("hypr-spidey.spidey-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())
        self.assertEqual(backups[0].readlink(), missing)

    def test_uninstall_can_remove_known_legacy_links_without_installing(self):
        self.create_links(RETIRED_LINKS)
        self.run_script("uninstall.sh", "--dry-run")
        self.assert_links(RETIRED_LINKS)
        self.run_script("uninstall.sh")
        self.assert_absent(RETIRED_LINKS)


if __name__ == "__main__":
    unittest.main()
