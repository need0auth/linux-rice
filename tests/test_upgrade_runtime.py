"""Runtime upgrades target this checkout and this Wayland session exclusively."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "upgrade-runtime.py"
SPEC = importlib.util.spec_from_file_location("spidey_upgrade_runtime", SCRIPT)
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


class RuntimeUpgradeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spidey-runtime-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / "checkout with spaces"
        (self.repo / "quickshell").mkdir(parents=True)
        (self.repo / "quickshell" / "shell.qml").write_text("// current shell\n")
        self.config = self.base / "config"
        self.directory = self.base / "runtime"
        self.directory.mkdir(mode=0o700)
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.directory / "wayland-test"))
        self.addCleanup(self.socket.close)
        self.environment = {"WAYLAND_DISPLAY": "wayland-test", "XDG_RUNTIME_DIR": str(self.directory),
                            "SPIDEY_PREVIEW": "1", "SPIDEY_DEMO": "1", "SPIDEY_SCREENSHOT": "/tmp/test.png",
                            "QS_MANIFEST": "/foreign/manifest.conf", "QS_CONFIG_PATH": "/foreign/shell.qml"}
        self.instances = []
        self.processes = {}
        self.commands = []
        self.messages = []
        self.state_file = self.base / "state.json"
        self.upgrade = runtime.RuntimeUpgrade(
            self.repo, self.config, self.state_file, environment=self.environment,
            runner=self.run_command, process_reader=self.processes.get,
            output=self.messages.append, binary="/usr/bin/qs-fake")

    def add_instance(self, identifier, pid, path, environment=None, uid=None):
        self.instances.append({"id": identifier, "pid": pid, "config_path": str(path)})
        self.processes[pid] = runtime.ProcessInfo(
            os.getuid() if uid is None else uid,
            dict(self.environment if environment is None else environment), f"start-{pid}")

    def run_command(self, arguments, **options):
        self.commands.append((arguments, options))
        if arguments[1:] == ["list", "--all", "--json"]:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(self.instances), "")
        if arguments[1:3] == ["kill", "--id"]:
            # State is durable before the first stop, including partial failures.
            self.assertTrue(json.loads(self.state_file.read_text())["was_running"])
            identifier = arguments[3]
            pid = next(item["pid"] for item in self.instances if item["id"] == identifier)
            self.processes.pop(pid, None)
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[1:] == ["-p", str(self.config / "quickshell" / "spidey"), "--no-duplicate", "--daemonize"]:
            return subprocess.CompletedProcess(arguments, 0, "", "")
        self.fail(f"Unexpected command: {arguments}")

    def link(self, name, source):
        link = self.config / "quickshell" / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source, target_is_directory=True)
        return link / "shell.qml"

    def stopped_ids(self):
        return [arguments[3] for arguments, _ in self.commands if arguments[1:3] == ["kill", "--id"]]

    def test_stops_old_and_current_instances_and_resumes_one_canonical_shell(self):
        canonical = self.link("spidey", self.repo / "quickshell")
        retired = self.link("spidey-retro", self.repo / "quickshell-retro")
        self.add_instance("canonical-full-id", 101, canonical)
        self.add_instance("retired-full-id", 102, retired)
        self.add_instance("removed-source-id", 103, self.repo / "quickshell-retro" / "shell.qml")
        self.upgrade.stop()
        self.assertEqual(self.stopped_ids(), ["canonical-full-id", "retired-full-id", "removed-source-id"])
        self.assertEqual(self.state_file.stat().st_mode & 0o777, 0o600)
        self.upgrade.resume()
        self.assertEqual(self.commands[-1][0], ["/usr/bin/qs-fake", "-p", str(self.config / "quickshell" / "spidey"), "--no-duplicate", "--daemonize"])
        launch_environment = self.commands[-1][1]["env"]
        self.assertEqual(launch_environment["XDG_CONFIG_HOME"], str(self.config))
        self.assertNotIn("SPIDEY_PREVIEW", launch_environment)
        self.assertNotIn("SPIDEY_DEMO", launch_environment)
        self.assertNotIn("SPIDEY_SCREENSHOT", launch_environment)
        self.assertNotIn("QS_MANIFEST", launch_environment)
        self.assertNotIn("QS_CONFIG_PATH", launch_environment)
        self.assertFalse(json.loads(self.state_file.read_text())["was_running"])
        count = len(self.commands)
        self.upgrade.resume()
        self.assertEqual(len(self.commands), count)

    def test_preserves_foreign_shells_other_checkout_other_display_and_other_user(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        self.add_instance("foreign-shell", 102, self.base / "other" / "shell.qml")
        foreign_link = self.link("spidey-retro", self.base / "other")
        self.add_instance("foreign-link", 103, foreign_link)
        self.add_instance("other-checkout", 104, self.base / "another-checkout" / "quickshell" / "shell.qml")
        self.add_instance("other-display", 105, self.repo / "quickshell" / "shell.qml",
                          dict(self.environment, WAYLAND_DISPLAY="wayland-other"))
        self.add_instance("other-user", 106, self.repo / "quickshell" / "shell.qml", uid=os.getuid() + 1)
        self.add_instance("other-runtime", 107, self.repo / "quickshell" / "shell.qml",
                          dict(self.environment, XDG_RUNTIME_DIR=str(self.base / "other-runtime")))
        self.upgrade.stop()
        self.assertEqual(self.stopped_ids(), ["ours"])
        self.assertEqual(set(self.processes), {102, 103, 104, 105, 106, 107})

    def test_owned_relative_symlink_and_absolute_display_are_recognized(self):
        linked = self.link("spidey", Path("../../checkout with spaces/quickshell"))
        self.add_instance("relative-link", 101, linked,
                          dict(self.environment, WAYLAND_DISPLAY=str(self.directory / "wayland-test")))
        self.upgrade.stop()
        self.assertEqual(self.stopped_ids(), ["relative-link"])
        self.assertEqual(self.commands[-1][1]["env"]["WAYLAND_DISPLAY"], str(self.directory / "wayland-test"))

    def test_first_install_does_not_start_an_unrequested_shell(self):
        self.upgrade.stop()
        self.upgrade.resume()
        self.assertEqual(len(self.commands), 1)
        self.assertFalse(json.loads(self.state_file.read_text())["was_running"])

    def test_real_no_instances_text_and_empty_successful_output_are_supported(self):
        for output in ("No running instances.\n", ""):
            self.upgrade.runner = lambda arguments, **options: subprocess.CompletedProcess(arguments, 0, output, "")
            self.upgrade.stop()
            self.assertFalse(json.loads(self.state_file.read_text())["was_running"])

    def test_no_wayland_or_no_binary_skips_runtime_changes(self):
        self.upgrade.environment = {}
        self.upgrade.stop()
        self.assertFalse(self.commands)
        self.upgrade.environment = self.environment
        self.upgrade.binary = None
        self.upgrade.stop()
        self.assertFalse(self.commands)

    def test_missing_socket_is_not_a_live_session(self):
        self.upgrade.environment["WAYLAND_DISPLAY"] = "missing-socket"
        self.upgrade.stop()
        self.assertFalse(self.commands)

    def test_dry_run_plans_stop_and_one_restart_without_state_or_process_mutation(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        self.upgrade.dry_run = True
        self.upgrade.stop()
        self.assertFalse(self.state_file.exists())
        self.assertEqual(set(self.processes), {101})
        self.assertEqual(len(self.commands), 1)
        self.assertTrue(any("Would stop" in message for message in self.messages))
        self.assertEqual(sum("Would start one" in message for message in self.messages), 1)
        self.state_file.write_text("leave this exact content unchanged")
        self.upgrade.stop()
        self.assertEqual(self.state_file.read_text(), "leave this exact content unchanged")

    def test_capture_failures_prevent_all_stops_and_state_mutation(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        for result in (subprocess.CompletedProcess([], 1, "", "failed"),
                       subprocess.CompletedProcess([], 0, "broken json", ""),
                       subprocess.CompletedProcess([], 0, '{"unexpected":"object"}', ""),
                       subprocess.CompletedProcess([], 0, json.dumps([self.instances[0], {"pid": 102}]), "")):
            with self.subTest(result=result):
                self.upgrade.runner = lambda *args, **kwargs: result
                with self.assertRaises(runtime.UpgradeError):
                    self.upgrade.stop()
                self.assertFalse(self.state_file.exists())
                self.assertIn(101, self.processes)

    def test_timeout_prevents_stops(self):
        self.upgrade.runner = lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("qs", 15))
        with self.assertRaises(runtime.UpgradeError):
            self.upgrade.stop()
        self.assertFalse(self.state_file.exists())

    def test_unreadable_process_environment_is_left_untouched(self):
        self.add_instance("cannot-verify", 101, self.repo / "quickshell" / "shell.qml")
        self.upgrade.process_reader = lambda pid: (_ for _ in ()).throw(PermissionError())
        self.upgrade.stop()
        self.assertEqual(self.stopped_ids(), [])
        self.assertFalse(json.loads(self.state_file.read_text())["was_running"])

    def test_pid_reuse_does_not_kill_replacement_process(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        original = self.processes[101]
        replacement = runtime.ProcessInfo(os.getuid(), self.environment, "different-start-time")
        with patch.object(self.upgrade, "process_reader", side_effect=[original, replacement]):
            self.upgrade.stop()
        self.assertEqual(self.stopped_ids(), [])

    def test_failed_first_stop_leaves_old_shell_running_without_extra_restart(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        original_runner = self.upgrade.runner
        def fail_kill(arguments, **options):
            if arguments[1:3] == ["kill", "--id"]:
                return subprocess.CompletedProcess(arguments, 1, "", "failed")
            return original_runner(arguments, **options)
        self.upgrade.runner = fail_kill
        with self.assertRaises(runtime.UpgradeError):
            self.upgrade.stop()
        self.assertFalse(json.loads(self.state_file.read_text())["was_running"])
        self.assertIn(101, self.processes)

    def test_partial_stop_failure_retains_recovery_intent(self):
        self.add_instance("first", 101, self.repo / "quickshell" / "shell.qml")
        self.add_instance("second", 102, self.repo / "quickshell-retro" / "shell.qml")
        original_runner = self.upgrade.runner
        def fail_second_kill(arguments, **options):
            if arguments[1:] == ["kill", "--id", "second"]:
                return subprocess.CompletedProcess(arguments, 1, "", "failed")
            return original_runner(arguments, **options)
        self.upgrade.runner = fail_second_kill
        with self.assertRaises(runtime.UpgradeError):
            self.upgrade.stop()
        self.assertTrue(json.loads(self.state_file.read_text())["was_running"])
        self.assertEqual(set(self.processes), {102})

    def test_exit_wait_is_bounded_and_does_not_send_broad_signals(self):
        self.add_instance("ours", 101, self.repo / "quickshell" / "shell.qml")
        with patch.object(runtime.time, "monotonic", side_effect=[10, 16]):
            with self.assertRaises(runtime.UpgradeError):
                self.upgrade.wait_for_exit(self.instances[0], self.processes[101])
        self.assertFalse(self.commands)

    def test_resume_handles_missing_empty_state_and_other_session_without_launch(self):
        self.upgrade.resume()
        self.state_file.touch(mode=0o600)
        self.upgrade.resume()
        self.upgrade.write_state(self.upgrade.state(True, {"runtime": "/different", "socket": "/different/socket"}))
        self.upgrade.resume()
        self.assertFalse(self.commands)

    def test_resume_rejects_foreign_state_and_unsafe_permissions(self):
        state = self.upgrade.state(True, self.upgrade.live_session())
        state["repo_root"] = "/another-checkout"
        self.upgrade.write_state(state)
        with self.assertRaises(runtime.UpgradeError):
            self.upgrade.resume()
        self.upgrade.write_state(self.upgrade.state(True, self.upgrade.live_session()))
        self.state_file.chmod(0o644)
        with self.assertRaises(runtime.UpgradeError):
            self.upgrade.resume()
        self.assertFalse(self.commands)

    def test_state_symlink_is_not_followed(self):
        target = self.base / "personal-file"
        target.write_text("personal content")
        self.state_file.symlink_to(target)
        with self.assertRaises(OSError):
            self.upgrade.write_state(self.upgrade.state(False, None))
        self.assertEqual(target.read_text(), "personal content")

    def test_process_inspection_keeps_only_session_environment(self):
        process = runtime.read_process(os.getpid())
        self.assertEqual(process.uid, os.getuid())
        self.assertTrue(process.active)
        self.assertTrue(process.token.isdigit())
        self.assertTrue(set(process.environment) <= {"XDG_RUNTIME_DIR", "WAYLAND_DISPLAY"})


if __name__ == "__main__":
    unittest.main()
