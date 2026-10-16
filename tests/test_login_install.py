"""Stage the optional boot login safely; service tests use a fake runner only."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("spidey_login_install", REPO / "scripts/install-login.py")
login = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(login)


class LoginInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spidey login ")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "staged system with ' spaces"
        self.share = self.root / "usr/local/share/spidey-greeter"
        self.config = self.root / "etc/greetd/config.toml"

    def install(self, *arguments, expected_code=0, root=None):
        result = subprocess.run(
            ["bash", str(REPO / "scripts/install-login.sh"), "--root", str(root or self.root), *arguments],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, expected_code, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def test_default_and_explicit_dry_run_create_nothing(self):
        for arguments in ((), ("--install", "--dry-run")):
            with self.subTest(arguments=arguments):
                result = self.install(*arguments)
                self.assertIn("Dry run complete", result.stdout)
                self.assertFalse(self.root.exists())

    def test_staged_install_copies_assets_config_and_readable_modes(self):
        self.install("--install")
        expected = {
            "greeter/shell.qml": REPO / "greeter/shell.qml",
            "greeter/session.json": REPO / "greeter/session.json",
            "assets/fonts/Silkscreen-Regular.ttf": REPO / "quickshell/assets/fonts/Silkscreen-Regular.ttf",
            "assets/wallpaper.png": REPO / "assets/wallpapers/spidey-city.png",
            "start-greeter": REPO / "config/greetd/start-greeter",
            "sway.conf": REPO / "config/greetd/sway.conf",
        }
        for relative, source in expected.items():
            target = self.share / relative
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), source.read_bytes())
        self.assertEqual(self.config.read_bytes(), (REPO / "config/greetd/config.toml").read_bytes())
        for target in (self.config, self.share, *self.share.rglob("*")):
            mode = 0o755 if target.is_dir() or target.name == "start-greeter" else 0o644
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode, str(target))
        marker = json.loads((self.share / ".spidey-managed.json").read_text())
        self.assertEqual(marker["owner"], "spidey-greeter")
        self.assertIn("greeter/shell.qml", marker["hashes"])

    def test_conflict_at_either_destination_prevents_partial_install(self):
        for target in (self.share, self.config):
            with self.subTest(target=target):
                if target == self.share:
                    target.mkdir(parents=True)
                    content = target / "personal.qml"
                else:
                    target.parent.mkdir(parents=True)
                    content = target
                content.write_text("personal login\n")
                for arguments in (("--install",), ()):
                    result = self.install(*arguments, expected_code=1)
                    self.assertIn("Nothing changed", result.stderr)
                    self.assertEqual(content.read_text(), "personal login\n")
                    other = self.config if target == self.share else self.share
                    self.assertFalse(other.exists())
                content.unlink()
                if target == self.share:
                    target.rmdir()

    def test_backup_preserves_unrelated_settings_and_dry_run_does_not_move_them(self):
        self.share.mkdir(parents=True)
        (self.share / "personal.qml").write_text("previous renderer")
        self.config.parent.mkdir(parents=True)
        self.config.write_text("previous config")
        self.install("--install", "--backup", "--dry-run")
        self.assertFalse(list(self.share.parent.glob("spidey-greeter.spidey-backup.*")))
        self.assertEqual(self.config.read_text(), "previous config")
        self.install("--install", "--backup")
        share_backups = list(self.share.parent.glob("spidey-greeter.spidey-backup.*"))
        config_backups = list(self.config.parent.glob("config.toml.spidey-backup.*"))
        self.assertEqual(len(share_backups), 1)
        self.assertEqual(len(config_backups), 1)
        self.assertEqual((share_backups[0] / "personal.qml").read_text(), "previous renderer")
        self.assertEqual(config_backups[0].read_text(), "previous config")

    def test_upgrade_preserves_session_keyboard_config_and_original_ly_rollback(self):
        self.install("--install")
        custom = {
            self.share / "greeter/session.json": '{"command":["Hyprland"],"defaultUser":"agent"}\n',
            self.share / "sway.conf": "input type:keyboard xkb_layout br\n",
            self.share / "service-before-enable.json": '{"ly_units":["ly@tty2.service"],"display_manager":""}\n',
            self.config: self.config.read_text() + "# personal VT configuration\n",
        }
        for target, content in custom.items():
            target.write_text(content)
        (self.share / "greeter/shell.qml").write_text("old renderer")
        self.install("--install")
        for target, content in custom.items():
            self.assertEqual(target.read_text(), content)
        self.assertEqual((self.share / "greeter/shell.qml").read_bytes(), (REPO / "greeter/shell.qml").read_bytes())
        self.install("--install")
        for target, content in custom.items():
            self.assertEqual(target.read_text(), content)

    def test_malformed_management_metadata_is_an_unrelated_conflict(self):
        self.share.mkdir(parents=True)
        for value in ([], {"owner": "spidey-greeter", "format": 1, "hashes": []}):
            (self.share / ".spidey-managed.json").write_text(json.dumps(value))
            result = self.install("--install", expected_code=1)
            self.assertIn("Nothing changed", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(self.config.exists())

    def test_symlink_root_and_destination_parents_are_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        self.assertIn("symlink", self.install("--install", root=alias, expected_code=1).stderr)
        for relative in ("etc", "usr"):
            with self.subTest(relative=relative):
                self.root.mkdir(exist_ok=True)
                target = self.root / relative
                target.symlink_to(outside, target_is_directory=True)
                self.assertIn("symlink", self.install("--install", expected_code=1).stderr)
                target.unlink()
        self.assertEqual(list(outside.iterdir()), [])

    def test_managed_customization_and_service_record_symlinks_are_refused(self):
        self.install("--install")
        outside = self.base / "personal"
        outside.write_text("keep me")
        for relative in ("greeter/session.json", "service-before-enable.json"):
            with self.subTest(relative=relative):
                target = self.share / relative
                previous = target.read_bytes() if target.exists() else None
                target.unlink(missing_ok=True)
                target.symlink_to(outside)
                self.assertIn("symlink", self.install("--install", expected_code=1).stderr)
                self.assertEqual(outside.read_text(), "keep me")
                target.unlink()
                if previous is not None:
                    target.write_bytes(previous)

    def test_service_enable_is_rejected_for_every_staging_mode(self):
        for arguments in (("--enable",), ("--enable", "--install"), ("--enable", "--dry-run")):
            result = self.install(*arguments, expected_code=1)
            self.assertIn("cannot be used with a staging", result.stderr)
            self.assertFalse(self.root.exists())


class LoginServiceTests(unittest.TestCase):
    def test_enabled_ly_instances_are_selected_without_other_units(self):
        self.assertEqual(login.ly_units_from_output(
            "ly@tty2.service enabled enabled\nly.service enabled disabled\n"
            "ly@tty3.service enabled-runtime disabled\nly@tty2.service enabled enabled\n"
            "lyra.service enabled enabled\nsddm.service enabled enabled\nly@tty2.timer enabled enabled\n"),
            ["ly@tty2.service", "ly.service", "ly@tty3.service"])

    def test_success_changes_only_next_boot_service_enablement(self):
        commands = []
        login.switch_next_boot(["ly@tty2.service"], False, runner=commands.append)
        self.assertEqual(commands, [["systemctl", "disable", "ly@tty2.service"],
                                    ["systemctl", "enable", "greetd.service"]])

    def test_failed_greetd_enable_restores_original_ly_without_stopping_services(self):
        commands = []

        def runner(command):
            commands.append(command)
            if command == ["systemctl", "enable", "greetd.service"]:
                raise subprocess.CalledProcessError(1, command, stderr="simulated failure")

        with self.assertRaises(subprocess.CalledProcessError):
            login.switch_next_boot(["ly@tty2.service", "ly.service"], False, runner=runner)
        self.assertEqual(commands[-3:], [["systemctl", "disable", "greetd.service"],
                                         ["systemctl", "enable", "ly@tty2.service"],
                                         ["systemctl", "enable", "ly.service"]])
        self.assertFalse(any("--now" in command or "stop" in command for command in commands))

    def test_failure_keeps_a_previously_enabled_greetd_and_restores_partial_ly_disable(self):
        commands = []

        def runner(command):
            commands.append(command)
            if command == ["systemctl", "disable", "ly@tty2.service"]:
                raise subprocess.CalledProcessError(1, command)

        with self.assertRaises(subprocess.CalledProcessError):
            login.switch_next_boot(["ly@tty2.service"], True, runner=runner)
        self.assertEqual(commands, [["systemctl", "disable", "ly@tty2.service"],
                                    ["systemctl", "enable", "ly@tty2.service"]])


class GreeterProcessTests(unittest.TestCase):
    def test_renderer_exit_always_ends_owned_sway_compositor(self):
        bash_binary = shutil.which("bash")
        self.assertIsNotNone(bash_binary)
        with tempfile.TemporaryDirectory(prefix="spidey greeter wrapper ") as directory:
            base = Path(directory)
            for binary, returncode in (("qs", 0), ("quickshell", 7)):
                with self.subTest(binary=binary, returncode=returncode):
                    command_dir = base / binary
                    command_dir.mkdir()
                    log = command_dir / "commands.jsonl"
                    for command in (binary, "swaymsg"):
                        path = command_dir / command
                        path.write_text(
                            "#!/usr/bin/python3\nimport json,os,sys\n"
                            "with open(os.environ['MOCK_LOG'],'a') as stream:\n"
                            " stream.write(json.dumps([os.path.basename(sys.argv[0]),*sys.argv[1:]])+'\\n')\n"
                            f"sys.exit({returncode if command == binary else 0})\n")
                        path.chmod(0o755)
                    # A real installed qs must not shadow the fake quickshell
                    # fallback on Arch. The fake commands use absolute shebangs.
                    environment = dict(os.environ, PATH=str(command_dir),
                                       MOCK_LOG=str(log))
                    result = subprocess.run([bash_binary, str(REPO / "config/greetd/start-greeter")],
                                            env=environment, capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, returncode, result.stderr)
                    self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
                        [binary, "--path", "/usr/local/share/spidey-greeter/greeter", "--no-duplicate"],
                        ["swaymsg", "exit"],
                    ])


if __name__ == "__main__":
    unittest.main()
