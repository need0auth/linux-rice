"""Application preferences apply to buttons and shortcuts without shell parsing."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "quickshell" / "scripts" / "system.py"
SPEC = importlib.util.spec_from_file_location("spidey_app_actions", SCRIPT)
system = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(system)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config_root = Path(self.folder.name)
        environment = patch.dict(system.os.environ, {"XDG_CONFIG_HOME": self.folder.name})
        environment.start()
        self.addCleanup(environment.stop)

    def override(self, config):
        path = self.config_root / "spidey" / "apps.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_brave_variants_win_over_installed_firefox(self):
        for executable in ("brave", "brave-browser", "brave-bin"):
            with self.subTest(executable=executable), patch.object(system.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in {executable, "firefox"} else None), patch.object(system.subprocess, "Popen") as process:
                self.assertEqual(system.action("browser")["program"], executable)
                self.assertEqual(process.call_args.args[0], [f"/usr/bin/{executable}"])

    def test_files_use_filemanager_instead_of_home_mime_association(self):
        with patch.object(system.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in {"xdg-open", "codium", "dolphin"} else None), patch.object(system.subprocess, "Popen") as process:
            self.assertEqual(system.action("files")["program"], "dolphin")
            self.assertEqual(process.call_args.args[0], ["/usr/bin/dolphin", str(Path.home())])

    def test_launcher_prefers_rofi_with_the_rice_theme(self):
        with patch.object(system.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in {"rofi", "fuzzel"} else None), patch.object(system.subprocess, "Popen") as process:
            self.assertEqual(system.action("launcher")["program"], "rofi")
            self.assertEqual(process.call_args.args[0], ["/usr/bin/rofi", "-show", "drun", "-theme", str(system.SHELL_ROOT / "assets" / "rofi.rasi"), "-terminal", "kitty"])

    def test_rofi_terminal_entries_use_available_configured_terminal_with_args(self):
        terminal = ["my-terminal", "--profile", "Daily coding", "--title", "$(touch /tmp/nope)"]
        self.override({"terminal": [["not-installed"], terminal]})
        with patch.object(system.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in {"rofi", "my-terminal"} else None), patch.object(system.subprocess, "Popen") as process:
            system.action("launcher")
        argv = process.call_args.args[0]
        self.assertEqual(shlex.split(argv[argv.index("-terminal") + 1]), terminal)
        self.assertNotIn("shell", process.call_args.kwargs)

    def test_explicit_rofi_terminal_setting_is_preserved(self):
        self.override({"launcher": [["rofi", "-show", "drun", "-terminal", "custom-terminal --profile work"]]})
        with patch.object(system.shutil, "which", return_value="/usr/bin/rofi"), patch.object(system.subprocess, "Popen") as process:
            system.action("launcher")
        self.assertEqual(process.call_args.args[0], ["/usr/bin/rofi", "-show", "drun", "-terminal", "custom-terminal --profile work"])

    def test_override_merges_actions_and_preserves_literal_arguments(self):
        self.override({"browser": [["custom-browser", "--profile-directory=Main Profile", "https://example.test/?q=$(touch /tmp/nope)"]]})
        self.assertEqual(system.app_candidates("files")[0][0], "nemo")
        with patch.object(system.shutil, "which", return_value="/opt/custom-browser"), patch.object(system.subprocess, "Popen") as process:
            system.action("browser")
            self.assertEqual(process.call_args.args[0], ["/opt/custom-browser", "--profile-directory=Main Profile", "https://example.test/?q=$(touch /tmp/nope)"])
            self.assertNotIn("shell", process.call_args.kwargs)
            self.assertTrue(process.call_args.kwargs["start_new_session"])

    def test_override_path_tokens_expand_without_shell_execution(self):
        self.override({"terminal": [["{home}/bin/my-terminal", "--config", "{config}/terminal/settings", "{shell}/assets/palette.json"]]})
        self.assertEqual(system.app_candidates("terminal"), [[str(Path.home() / "bin/my-terminal"), "--config", str(self.config_root / "terminal/settings"), str(system.SHELL_ROOT / "assets/palette.json")]])

    def test_invalid_override_does_not_silently_launch_another_program(self):
        invalid = [[], {"browser": "brave"}, {"browser": []}, {"browser": ["brave"]}, {"browser": [["brave", 1]]}, {"browser": [["brave", "bad\u0000arg"]]}, {"browesr": [["brave"]]}]
        for config in invalid:
            with self.subTest(config=config):
                self.override(config)
                with patch.object(system.subprocess, "Popen") as process, self.assertRaises(system.ActionError):
                    system.action("browser")
                process.assert_not_called()

    def test_bad_json_is_reported_through_normal_action_error(self):
        path = self.override({})
        path.write_text("{broken", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(system.main(["action", "launcher"]), 1)
        self.assertIn(str(path), json.loads(output.getvalue())["error"])

    def test_non_utf8_override_has_a_readable_action_error(self):
        path = self.override({})
        path.write_bytes(b"\xff")
        with self.assertRaisesRegex(system.ActionError, "UTF-8"):
            system.action("files")

    def test_home_mime_opener_is_never_used_as_filemanager_fallback(self):
        with patch.object(system.shutil, "which", side_effect=lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None), patch.object(system.subprocess, "Popen") as process:
            with self.assertRaisesRegex(system.ActionError, "thunar"):
                system.action("files")
            process.assert_not_called()

    def test_missing_network_tool_reports_what_to_install(self):
        with patch.object(system.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(system.main(["action", "network"]), 1)
        self.assertIn("nm-connection-editor", json.loads(output.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
