"""Multiple-player fixtures for Brave/YouTube detection and matching controls."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "quickshell" / "scripts" / "media.py"
SPEC = importlib.util.spec_from_file_location("spidey_media", SCRIPT)
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)


class MediaFixture:
    def __init__(self, sessions, listing=None):
        self.sessions = sessions
        self.listing = listing if listing is not None else "\n".join(sessions)
        self.commands = []

    def output(self, argv):
        self.commands.append(argv)
        if argv == ["playerctl", "--list-all"]:
            return self.listing
        if len(argv) >= 4 and argv[:2] == ["playerctl", "--player"]:
            session = self.sessions[argv[2]]
            if argv[3:] == ["status"]:
                return session.get("status", "")
            if argv[3:] == ["metadata", "--format", "{{title}}"]:
                return session.get("title", "")
            if argv[3:] == ["metadata", "--format", "{{artist}}"]:
                return session.get("artist", "")
        raise AssertionError(f"Unexpected command: {argv}")


class MediaTests(unittest.TestCase):
    def test_playing_youtube_in_brave_wins_over_default_paused_player(self):
        fixture = MediaFixture({
            "spotify": {"status": "Paused", "title": "Old song"},
            "chromium.instance2354": {"status": "Playing", "title": "My YouTube video", "artist": "The channel"},
        })
        self.assertEqual(media.snapshot(fixture.output, str.strip), {
            "available": True, "playing": True, "player": "chromium.instance2354",
            "title": "My YouTube video", "artist": "The channel",
        })

    def test_selection_is_stable_when_player_enumeration_order_changes(self):
        sessions = {
            "brave.instance2": {"status": "Playing", "title": "Second browser"},
            "brave.instance1": {"status": "Playing", "title": "First browser"},
        }
        forward = MediaFixture(sessions)
        reverse = MediaFixture(sessions, "\n".join(reversed(sessions)))
        self.assertEqual(media.snapshot(forward.output, str.strip), media.snapshot(reverse.output, str.strip))

    def test_paused_session_remains_available_for_resume(self):
        fixture = MediaFixture({"brave.instance99": {"status": "Paused", "title": "Paused video"}})
        snapshot = media.snapshot(fixture.output, str.strip)
        self.assertTrue(snapshot["available"])
        self.assertFalse(snapshot["playing"])
        self.assertEqual(snapshot["player"], "brave.instance99")

    def test_player_disappearing_during_status_probe_is_skipped(self):
        fixture = MediaFixture({"chromium.instance1": {}, "vlc": {"status": "Paused", "title": "Film"}})
        self.assertEqual(media.snapshot(fixture.output, str.strip)["player"], "vlc")

    def test_no_mpris_session_has_an_explicit_empty_player(self):
        self.assertEqual(media.snapshot(MediaFixture({}).output, str.strip), {
            "available": False, "playing": False, "player": "",
            "title": "NO ACTIVE TRANSMISSION", "artist": "",
        })

    def test_missing_metadata_has_a_readable_fallback(self):
        fixture = MediaFixture({"vlc": {"status": "Stopped"}})
        self.assertEqual(media.snapshot(fixture.output, str.strip)["title"], "UNTITLED TRANSMISSION")

    def test_controls_target_displayed_browser_even_when_another_player_starts(self):
        fixture = MediaFixture({"brave.instance2": {"status": "Paused"}, "spotify": {"status": "Playing"}})
        for name, operation in media.MEDIA_COMMANDS.items():
            with self.subTest(action=name):
                self.assertEqual(media.command(name, "brave.instance2", fixture.output, ValueError),
                                 ["playerctl", "--player", "brave.instance2", operation])

    def test_control_without_explicit_player_selects_playing_browser(self):
        fixture = MediaFixture({"spotify": {"status": "Paused"}, "chromium.instance11": {"status": "Playing"}})
        self.assertEqual(media.command("media-play-pause", None, fixture.output, ValueError),
                         ["playerctl", "--player", "chromium.instance11", "play-pause"])

    def test_closed_displayed_session_does_not_control_an_unrelated_player(self):
        fixture = MediaFixture({"spotify": {"status": "Playing"}})
        with self.assertRaisesRegex(ValueError, "closed"):
            media.command("media-next", "brave.instance2", fixture.output, ValueError)

    def test_control_without_any_session_has_a_useful_error(self):
        with self.assertRaisesRegex(ValueError, "No MPRIS"):
            media.command("media-play-pause", None, MediaFixture({}).output, ValueError)

    def test_player_selector_cannot_expand_to_all_players_or_inject_options(self):
        fixture = MediaFixture({"brave": {"status": "Playing"}})
        for name in ("brave,*", "--all-players", "brave\nspotify", "brave; next", "*", "b" * 256):
            with self.subTest(player=name), self.assertRaisesRegex(ValueError, "Invalid"):
                media.command("media-next", name, fixture.output, ValueError)
        self.assertEqual(fixture.commands, [])


if __name__ == "__main__":
    unittest.main()
