"""Select and control the same MPRIS session, including Chromium/Brave instances.

The caller supplies the bounded command runner used by the desktop bridge. No
browser names are hardcoded: Brave can export either a brave or chromium player.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence


Output = Callable[[Sequence[str]], str]
Clean = Callable[[str], str]
PLAYER_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,254}\Z")
MEDIA_COMMANDS = {
    "media-play-pause": "play-pause",
    "media-next": "next",
    "media-previous": "previous",
}


def players(output: Output) -> list[str]:
    """Keep full instance names; do not collapse every browser into chromium."""
    names = {
        name.strip()
        for name in output(["playerctl", "--list-all"]).splitlines()
        if PLAYER_NAME.fullmatch(name.strip())
    }
    return sorted(names, key=lambda name: (name.casefold(), name))


def select_player(output: Output) -> tuple[str, str]:
    """Prefer playing media over an earlier, paused playerctl default session."""
    priority = {"playing": 0, "paused": 1, "stopped": 2}
    candidates = []
    for name in players(output):
        status = output(["playerctl", "--player", name, "status"]).strip().lower()
        if status in priority:
            candidates.append((priority[status], name.casefold(), name, status))
    if not candidates:
        return "", ""
    _, _, name, status = min(candidates)
    return name, status


def snapshot(output: Output, clean: Clean) -> dict:
    name, status = select_player(output)
    if not name:
        return {
            "available": False, "playing": False, "player": "",
            "title": "NO ACTIVE TRANSMISSION", "artist": "",
        }
    # Separate fields avoid treating separators/newlines in video metadata as
    # structural data. The UI also explicitly renders these strings as plain text.
    title = output(["playerctl", "--player", name, "metadata", "--format", "{{title}}"])
    artist = output(["playerctl", "--player", name, "metadata", "--format", "{{artist}}"])
    return {
        "available": True, "playing": status == "playing", "player": name,
        "title": clean(title) or "UNTITLED TRANSMISSION", "artist": clean(artist),
    }


def command(name: str, requested_player: str | None, output: Output, error: type[Exception]) -> list[str]:
    """Return argv targeting the displayed instance, never playerctl's default."""
    operation = MEDIA_COMMANDS.get(name)
    if operation is None:
        raise error("Unknown media action.")
    if requested_player:
        if not PLAYER_NAME.fullmatch(requested_player):
            raise error("Invalid media player name.")
        if requested_player not in players(output):
            raise error("That media session has closed. Wait for the player to refresh.")
        selected = requested_player
    else:
        selected, _ = select_player(output)
        if not selected:
            raise error("No MPRIS media session is available. Start playback in your browser or media player.")
    return ["playerctl", "--player", selected, operation]
