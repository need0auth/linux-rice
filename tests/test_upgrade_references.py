"""Exercise upgrades against user-owned config fixtures, not the live desktop."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/migrate-user-config.py"
spec = importlib.util.spec_from_file_location("spidey_reference_migration", SCRIPT)
migration = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = migration
spec.loader.exec_module(migration)


class ReferenceMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="spidey upgrade '")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.config = self.base / "config with spaces"

    def write(self, relative, contents):
        path = self.config / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents.encode("utf-8") if isinstance(contents, str) else contents)
        return path

    def plan(self):
        return migration.plan_migration(self.config)

    def apply(self, suffix="fixture"):
        changes, notices = self.plan()
        with contextlib.redirect_stdout(io.StringIO()):
            migration.apply_migration(changes, suffix)
        return changes, notices

    def test_lua_sources_startup_and_personal_app_commands(self):
        path = self.write("hypr/autostart.lua", '''local config_root = os.getenv("XDG_CONFIG_HOME")
dofile(config_root .. "/hypr-spidey-retro/rice.lua")({config_root = config_root})
hl.exec_cmd("qs -c spidey-retro --daemonize")
hl.exec_cmd('quickshell --config spidey')
hl.exec_cmd("brave --profile-directory=Default")
hl.exec_cmd("nemo")
''')
        before = path.read_bytes()
        self.apply()
        updated = path.read_text()
        self.assertIn('/hypr-spidey/rice.lua', updated)
        self.assertIn('qs -c spidey --daemonize --no-duplicate', updated)
        self.assertIn("quickshell --config spidey --no-duplicate", updated)
        self.assertIn('hl.exec_cmd("brave --profile-directory=Default")', updated)
        self.assertIn('hl.exec_cmd("nemo")', updated)
        self.assertEqual(path.with_name(path.name + ".spidey-backup.fixture").read_bytes(), before)
        self.assertEqual(self.plan()[0], [])

    def test_ipc_kill_and_list_migrate_only_the_exact_config_argument(self):
        path = self.write("hypr/autostart.lua", '''hl.exec_cmd("qs -c spidey-retro ipc call dashboard toggle")
hl.exec_cmd("quickshell -c spidey-retro kill")
hl.exec_cmd("qs --config spidey-retro list")
hl.exec_cmd("echo spidey-retro")
''')
        self.apply()
        updated = path.read_text()
        self.assertIn('qs -c spidey ipc call dashboard toggle', updated)
        self.assertIn('quickshell -c spidey kill', updated)
        self.assertIn('qs --config spidey list', updated)
        self.assertNotIn('--no-duplicate', updated)
        self.assertIn('echo spidey-retro', updated)

    def test_legacy_variable_keeps_its_value_and_supplies_canonical_alias(self):
        path = self.write("hypr/hyprland.conf", '''$spideyRetroConfigRoot = /custom/config
source = $spideyRetroConfigRoot/hypr-spidey-retro/rice.conf
exec-once = qs -c spidey-retro --daemonize
bind = SUPER, D, exec, qs -c spidey-retro ipc call dashboard toggle
$terminal = kitty
''')
        self.apply()
        updated = path.read_text()
        self.assertIn('$spideyRetroConfigRoot = /custom/config\n', updated)
        self.assertIn('$spideyConfigRoot = $spideyRetroConfigRoot\nsource = $spideyRetroConfigRoot/hypr-spidey/rice.conf', updated)
        self.assertIn('exec-once = qs -c spidey --daemonize --no-duplicate', updated)
        self.assertIn('bind = SUPER, D, exec, qs -c spidey ipc call dashboard toggle', updated)
        self.assertIn('$terminal = kitty\n', updated)
        self.assertEqual(self.plan()[0], [])

    def test_unrecognized_expressions_comments_and_long_strings_are_unchanged(self):
        original = '''-- dofile(root .. "/hypr-spidey-retro/rice.lua")
--[[
hl.exec_cmd("qs -c spidey-retro")
]]
local docs = [=[
hl.exec_cmd("qs -c spidey-retro")
]=]
hl.exec_cmd("qs -c spidey-retro" .. options)
hl.exec_cmd("sh -c 'qs -c spidey-retro'")
print("/hypr-spidey-retro/rice.lua")
'''
        path = self.write("hypr/example.lua", original)
        changes, notices = self.plan()
        self.assertEqual(changes, [])
        self.assertEqual(path.read_text(), original)
        self.assertEqual(len(notices), 3)
        self.assertTrue(all("Review complex reference" in notice for notice in notices))

    def test_retire_only_known_wallpaper_exec_and_kitty_include(self):
        lua = self.write("hypr/autostart.lua", '''hl.exec_cmd("bash " .. quote(root .. "/hypr-spidey/wallpaper.sh") .. " " .. quote(root))
hl.exec_cmd("awww-daemon")
hl.exec_cmd("echo " .. quote(root .. "/hypr-spidey/wallpaper.sh"))
''')
        conf = self.write("hypr/theme.conf", '''exec-once = bash "$spideyConfigRoot/hypr-spidey/wallpaper.sh" "$spideyConfigRoot"
exec-once = bash /my/custom/wallpaper.sh
''')
        kitty = self.write("kitty/kitty.conf", '''include ~/.config/kitty-spidey/kitty.conf
include personal-theme.conf
font_family My Font
''')
        self.apply()
        self.assertTrue(lua.read_text().startswith('-- Spidey upgrade: retired wallpaper: hl.exec_cmd('))
        self.assertIn('hl.exec_cmd("awww-daemon")', lua.read_text())
        self.assertIn('hl.exec_cmd("echo " .. quote(root .. "/hypr-spidey/wallpaper.sh"))', lua.read_text())
        self.assertTrue(conf.read_text().startswith('# Spidey upgrade: retired wallpaper: exec-once'))
        self.assertIn('exec-once = bash /my/custom/wallpaper.sh', conf.read_text())
        self.assertTrue(kitty.read_text().startswith('# Spidey upgrade: retired theme: include'))
        self.assertIn('include personal-theme.conf\nfont_family My Font\n', kitty.read_text())

    def test_symlinked_files_and_directories_are_left_unchanged(self):
        outside = self.base / "outside"
        outside.mkdir()
        original = 'hl.exec_cmd("qs -c spidey-retro")\n'
        (outside / "startup.lua").write_text(original)
        hypr = self.config / "hypr"
        hypr.mkdir(parents=True)
        (hypr / "external.lua").symlink_to(outside / "startup.lua")
        (hypr / "snippets").symlink_to(outside, target_is_directory=True)
        changes, notices = self.plan()
        self.assertEqual(changes, [])
        self.assertEqual(len(notices), 2)
        self.assertEqual((outside / "startup.lua").read_text(), original)
        (hypr / "external.lua").unlink()
        (hypr / "snippets").unlink()
        hypr.rmdir()
        hypr.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.plan()[0], [])

    def test_foreign_retired_paths_keep_their_references(self):
        lua = self.write("hypr/startup.lua", '''dofile(root .. "/hypr-spidey-retro/rice.lua")({})
hl.exec_cmd("qs -c spidey-retro")
''')
        kitty = self.write("kitty/kitty.conf", 'include ~/.config/kitty-spidey/kitty.conf\n')
        originals = (lua.read_bytes(), kitty.read_bytes())
        (self.config / "hypr-spidey-retro").mkdir()
        (self.config / "kitty-spidey").write_text("personal file")
        (self.config / "quickshell").mkdir()
        (self.config / "quickshell/spidey-retro").symlink_to(self.base / "foreign-shell")
        changes, notices = self.plan()
        self.assertEqual(changes, [])
        self.assertEqual((lua.read_bytes(), kitty.read_bytes()), originals)
        self.assertEqual(sum("unrelated retired path" in notice for notice in notices), 3)

    def test_broken_relative_owned_links_still_allow_reference_migration(self):
        self.write("hypr/startup.lua", 'dofile(root .. "/hypr-spidey-retro/rice.lua")({})\n')
        old = self.config / "hypr-spidey-retro"
        old.symlink_to(os.path.relpath(REPO_ROOT / "config/hypr-retro", self.config), target_is_directory=True)
        changes, notices = self.plan()
        self.assertEqual(len(changes), 1)
        self.assertEqual(notices, [])

    def test_crlf_permissions_and_non_utf8_content_survive_upgrade_and_backup(self):
        original = b'# personal label \xff\r\nexec-once = qs -c spidey-retro\r\n'
        path = self.write("hypr/hyprland.conf", original)
        path.chmod(0o640)
        self.apply()
        backup = path.with_name(path.name + '.spidey-backup.fixture')
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(path.read_bytes(), b'# personal label \xff\r\nexec-once = qs -c spidey --no-duplicate\r\n')
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o640)

    def test_dry_run_and_check_create_nothing(self):
        path = self.write("hypr/startup.lua", 'hl.exec_cmd("qs -c spidey-retro")\n')
        before = path.read_bytes()
        for argument in ('--dry-run', '--check'):
            result = subprocess.run([sys.executable, str(SCRIPT), '--config-root', str(self.config), argument],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            if argument == '--check':
                self.assertEqual(result.stdout, '')
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_late_backup_collision_rejects_all_changes(self):
        first = self.write("hypr/a.conf", 'exec-once = qs -c spidey-retro\n')
        second = self.write("hypr/b.conf", 'exec-once = qs -c spidey-retro\n')
        originals = (first.read_bytes(), second.read_bytes())
        existing = second.with_name(second.name + '.spidey-backup.fixture')
        existing.write_text('important backup')
        changes, _ = self.plan()
        with self.assertRaises(FileExistsError):
            migration.apply_migration(changes, 'fixture')
        self.assertEqual((first.read_bytes(), second.read_bytes()), originals)
        self.assertFalse(first.with_name(first.name + '.spidey-backup.fixture').exists())
        self.assertEqual(existing.read_text(), 'important backup')

    def test_preparation_failure_leaves_all_originals_and_removes_partial_backups(self):
        first = self.write("hypr/a.conf", 'exec-once = qs -c spidey-retro\n')
        second = self.write("hypr/b.conf", 'exec-once = qs -c spidey-retro\n')
        changes, _ = self.plan()
        actual = migration.tempfile.mkstemp
        calls = 0

        def failing_temporary(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('fixture disk full')
            return actual(*args, **kwargs)

        with mock.patch.object(migration.tempfile, 'mkstemp', side_effect=failing_temporary):
            with self.assertRaisesRegex(OSError, 'disk full'):
                migration.apply_migration(changes, 'fixture')
        self.assertEqual(set(first.parent.iterdir()), {first, second})
        self.assertEqual(first.read_text(), 'exec-once = qs -c spidey-retro\n')
        self.assertEqual(second.read_text(), first.read_text())

    def test_edit_after_planning_is_preserved(self):
        path = self.write("hypr/startup.lua", 'hl.exec_cmd("qs -c spidey-retro")\n')
        changes, _ = self.plan()
        path.write_text('my new settings\n')
        with self.assertRaisesRegex(RuntimeError, 'changed during migration'):
            migration.apply_migration(changes, 'fixture')
        self.assertEqual(path.read_text(), 'my new settings\n')
        self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
