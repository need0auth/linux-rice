"""Fixture-driven checks for the desktop bridge; no real desktop is needed."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "quickshell" / "scripts" / "system.py"
SPEC = importlib.util.spec_from_file_location("spidey_system", SCRIPT)
system = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(system)


class TelemetryTests(unittest.TestCase):
    def test_cpu_delta_excludes_double_counted_guest_time(self):
        first = "cpu  100 0 50 800 20 10 10 10 30 0\ncpu0 0 0"
        second = "cpu  120 0 60 850 30 15 15 10 40 0\ncpu0 0 0"
        self.assertEqual(system.cpu_percent(first, second), 40.0)

    def test_cpu_handles_unreadable_or_reset_counters(self):
        self.assertEqual(system.cpu_percent("", "cpu 1 1 1 1"), 0.0)
        self.assertEqual(system.cpu_percent("cpu 100 0 0 100", "cpu 1 0 0 1"), 0.0)

    def test_memory_uses_available_including_reclaimable_cache(self):
        self.assertEqual(system.memory_percent("MemTotal: 1000 kB\nMemAvailable: 600 kB\nMemFree: 20 kB"), 40.0)
        self.assertEqual(system.memory_percent("MemTotal: 1000 kB\nMemFree: 200 kB\nBuffers: 100 kB\nCached: 100 kB"), 60.0)
        self.assertEqual(system.memory_percent("MemTotal: bad kB"), 0.0)

    def test_battery_ignores_ac_and_absent_batteries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, files in {
                "AC": {"type": "Mains", "online": "1"},
                "BAT0": {"type": "Battery", "capacity": "72", "status": "Charging"},
                "BAT1": {"type": "Battery", "present": "0", "capacity": "5"},
            }.items():
                device = root / name
                device.mkdir()
                for key, value in files.items():
                    (device / key).write_text(value)
            self.assertEqual(system.battery_status(root), {"present": True, "percent": 72.0, "charging": True})

    def test_battery_supports_energy_counters(self):
        with tempfile.TemporaryDirectory() as folder:
            device = Path(folder) / "BAT0"
            device.mkdir()
            for name, value in {"type": "Battery", "energy_now": "25000", "energy_full": "50000"}.items():
                (device / name).write_text(value)
            self.assertEqual(system.battery_status(Path(folder))["percent"], 50.0)

    def test_network_handles_colons_in_connection_labels(self):
        with patch.object(system, "optional_output", return_value="lo:connected (externally):lo\nwlan0:connected:SPIDEY: NET"):
            self.assertEqual(system.network_status(), {"connected": True, "interface": "wlan0", "name": "SPIDEY: NET"})

    def test_network_falls_back_to_carrier_without_networkmanager(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(system, "optional_output", return_value=""):
            root = Path(folder)
            for name, state, carrier in [("lo", "up", "1"), ("eth0", "up", "0"), ("wlan0", "up", "1")]:
                interface = root / name
                interface.mkdir()
                (interface / "operstate").write_text(state)
                (interface / "carrier").write_text(carrier)
            self.assertEqual(system.network_status(root)["interface"], "wlan0")

    def test_wpctl_volume_is_bounded_and_reports_mute(self):
        with patch.object(system, "optional_output", return_value="Volume: 1.25 [MUTED]"):
            self.assertEqual(system.volume_status(), {"available": True, "percent": 100.0, "muted": True})
        with patch.object(system, "optional_output", return_value=""):
            self.assertFalse(system.volume_status()["available"])

    def test_brightness_uses_machine_readable_output(self):
        with patch.object(system, "optional_output", return_value="intel_backlight,backlight,96,40%,240"):
            self.assertEqual(system.brightness_status(), {"available": True, "percent": 40.0})

    def test_media_preserves_title_and_strips_controls(self):
        with patch.object(system, "optional_output", return_value="Playing\x1fCITY\nSWING\x1fQUEENS\x1b RADIO"):
            self.assertEqual(system.media_status(), {"available": True, "playing": True, "title": "CITY SWING", "artist": "QUEENS RADIO"})

    def test_demo_is_deterministic_and_does_not_probe_machine(self):
        with patch.object(system, "run_command", side_effect=AssertionError("must not probe")):
            self.assertEqual(system.snapshot(demo=True), system.snapshot(demo=True))
            self.assertTrue(system.snapshot(demo=True)["demo"])


class ActionTests(unittest.TestCase):
    def test_action_passes_arguments_without_a_shell(self):
        with patch.object(system.shutil, "which", return_value="/usr/bin/wpctl"), patch.object(system.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            self.assertEqual(system.action("volume-up"), {"success": True})
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"])
            self.assertNotIn("shell", kwargs)
            self.assertEqual(kwargs["timeout"], system.COMMAND_TIMEOUT)

    def test_arbitrary_actions_and_injected_values_are_rejected(self):
        with patch.object(system, "run_command") as run:
            for name, value in [("shutdown", None), ("volume-set", "50; touch /tmp/nope"), ("volume-set", "nan"), ("brightness-set", "101"), ("volume-up", "7")]:
                with self.subTest(name=name, value=value), self.assertRaises(system.ActionError):
                    system.action(name, value)
            run.assert_not_called()

    def test_absolute_volume_is_validated_and_capped(self):
        with patch.object(system, "run_command") as run:
            self.assertEqual(system.action("volume-set", "42.5"), {"success": True})
            self.assertEqual(run.call_args.args[0][-1], "42.5%")
            self.assertIn("1.0", run.call_args.args[0])

    def test_missing_tool_returns_json_failure_and_nonzero(self):
        stream = io.StringIO()
        with patch.object(system.shutil, "which", return_value=None), contextlib.redirect_stdout(stream):
            code = system.main(["action", "volume-mute"])
        self.assertEqual(code, 1)
        payload = json.loads(stream.getvalue())
        self.assertFalse(payload["success"])
        self.assertIn("wpctl", payload["error"])

    def test_timeout_is_handled_as_a_desktop_error(self):
        with patch.object(system.shutil, "which", return_value="/usr/bin/wpctl"), patch.object(system.subprocess, "run", side_effect=subprocess.TimeoutExpired("wpctl", 1.5)):
            with self.assertRaisesRegex(system.ActionError, "timed out"):
                system.action("volume-down")

    def test_gui_launch_uses_detached_process_and_whitelisted_program(self):
        def lookup(name):
            return "/usr/bin/foot" if name == "foot" else None

        with patch.object(system.shutil, "which", side_effect=lookup), patch.object(system.subprocess, "Popen") as popen:
            self.assertEqual(system.action("terminal"), {"success": True, "program": "foot"})
            self.assertEqual(popen.call_args.args[0], ["/usr/bin/foot"])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_terminal_and_lock_use_installed_configs_under_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(system.os.environ, {"XDG_CONFIG_HOME": folder}):
            for name, program, relative in [("terminal", "kitty", "kitty-spidey/kitty.conf"), ("lock", "hyprlock", "hypr-spidey/hyprlock.conf")]:
                with self.subTest(action=name):
                    config = Path(folder) / relative
                    config.parent.mkdir()
                    config.write_text("# fixture")
                    with patch.object(system.shutil, "which", side_effect=lambda candidate: f"/usr/bin/{program}" if candidate == program else None), patch.object(system.subprocess, "Popen") as popen:
                        system.action(name)
                        self.assertEqual(popen.call_args.args[0], [f"/usr/bin/{program}", "--config", str(config)])

    def test_missing_themed_config_preserves_program_default(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(system.os.environ, {"XDG_CONFIG_HOME": folder}):
            self.assertEqual(system.themed_command("kitty", "kitty-spidey/kitty.conf"), ["kitty"])
            self.assertEqual(system.themed_command("hyprlock", "hypr-spidey/hyprlock.conf"), ["hyprlock"])

    def test_empty_xdg_config_home_uses_home_dot_config(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(system.os.environ, {"XDG_CONFIG_HOME": ""}), patch.object(system.Path, "home", return_value=Path(folder)):
            config = Path(folder) / ".config" / "kitty-spidey" / "kitty.conf"
            config.parent.mkdir(parents=True)
            config.write_text("# fixture")
            self.assertEqual(system.themed_command("kitty", "kitty-spidey/kitty.conf"), ["kitty", "--config", str(config)])

    def test_screenshot_rejects_untrusted_selection_before_running_grim(self):
        with patch.object(system.shutil, "which", return_value="/usr/bin/tool"), patch.object(system, "run_command", return_value="0,0 100x100; touch /tmp/nope") as run:
            with self.assertRaises(system.ActionError):
                system.action("screenshot")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0], ["slurp"])

    def test_demo_actions_are_disabled(self):
        stream = io.StringIO()
        with patch.object(system, "action") as action, contextlib.redirect_stdout(stream):
            self.assertEqual(system.main(["--demo", "action", "terminal"]), 1)
            action.assert_not_called()
            self.assertFalse(json.loads(stream.getvalue())["success"])

    def test_demo_flag_is_supported_before_or_after_snapshot(self):
        for arguments in (["--demo", "snapshot"], ["snapshot", "--demo"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(system.main(arguments), 0)
                self.assertTrue(json.loads(stream.getvalue())["demo"])


if __name__ == "__main__":
    unittest.main()
