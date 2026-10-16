"""Compatibility checks for numbered workspace switching through Hyprland IPC."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "quickshell" / "scripts" / "workspace.py"
SPEC = importlib.util.spec_from_file_location("spidey_workspace", SCRIPT)
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)
SYSTEM_SPEC = importlib.util.spec_from_file_location("spidey_workspace_system", SCRIPT.with_name("system.py"))
system = importlib.util.module_from_spec(SYSTEM_SPEC)
SYSTEM_SPEC.loader.exec_module(system)


class WorkspaceError(Exception):
    pass


class WorkspaceTests(unittest.TestCase):
    def test_public_action_routes_numbered_workspace_to_compatible_dispatcher(self):
        with patch.object(system, "run_command", side_effect=['{"configProvider":"lua"}', "ok"]) as run:
            self.assertEqual(system.action("workspace", "4"), {"success": True})
            self.assertEqual(run.call_args.args[0], ["hyprctl", "dispatch", 'hl.dsp.focus({ workspace = "4" })'])

    def test_lua_provider_accepts_uncreated_numbered_workspace(self):
        run = Mock(side_effect=['{"configProvider":"lua","backend":"drm"}', "ok"])
        workspace.activate("5", run, WorkspaceError)
        self.assertEqual(run.call_args.args[0], ["hyprctl", "dispatch", 'hl.dsp.focus({ workspace = "5" })'])

    def test_hyprlang_and_old_unknown_status_use_legacy_syntax(self):
        for status in ['{"configProvider":"hyprlang"}', "unknown request\n"]:
            with self.subTest(status=status):
                run = Mock(side_effect=[status, "ok"])
                workspace.activate("2", run, WorkspaceError)
                self.assertEqual(run.call_args.args[0], ["hyprctl", "dispatch", "workspace", "2"])

    def test_invalid_target_never_probes_or_dispatches(self):
        run = Mock()
        for value in [None, "", "0", "-1", "1.5", "01", "1;exec kitty", "2147483648", 1, True]:
            with self.subTest(value=value), self.assertRaises(WorkspaceError):
                workspace.activate(value, run, WorkspaceError)
        run.assert_not_called()

    def test_unknown_or_malformed_provider_never_dispatches(self):
        for status in ["broken", "[]", "{}", '{"configProvider":"future"}']:
            with self.subTest(status=status):
                run = Mock(return_value=status)
                with self.assertRaises(WorkspaceError):
                    workspace.activate("1", run, WorkspaceError)
                run.assert_called_once_with(["hyprctl", "-j", "status"])

    def test_dispatcher_error_with_successful_process_status_is_reported(self):
        run = Mock(side_effect=['{"configProvider":"lua"}', "error: invalid workspace"])
        with self.assertRaisesRegex(WorkspaceError, "invalid workspace"):
            workspace.activate("3", run, WorkspaceError)


if __name__ == "__main__":
    unittest.main()
