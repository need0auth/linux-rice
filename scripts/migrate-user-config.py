#!/usr/bin/env python3
"""Back up and migrate only recognizable references to retired Spidey installs.

This deliberately does not parse arbitrary Lua or shell programs. Unrecognized
references are reported for review instead of guessing at the user's intent.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile


@dataclass(frozen=True)
class Change:
    path: Path
    before: bytes
    after: bytes
    mode: int


RETIRED = re.compile(r"hypr-spidey-retro|spidey-retro|kitty-spidey|hypr-spidey/wallpaper\.sh")
START_OPTIONS = {"--no-duplicate", "--daemonize", "-d"}
SOURCE = re.compile(r"^(\s*source\s*=\s*)(.+?)(\s*)$")
LUA_SOURCE = re.compile(
    r"(\b(?:dofile|loadfile)\(\s*(?:[A-Za-z_]\w*\s*\.\.\s*)?)"
    r"([\"'])([^\"'\r\n]*/hypr-spidey-retro/rice\.lua)\2(?=\s*\))"
)
LONG_OPEN = re.compile(r"\[(=*)\[")


def split_comment(line, marker):
    """Split a single line outside ordinary quoted strings, preserving bytes."""
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and quote:
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif line.startswith(marker, index):
            return line[:index], line[index:]
    return line, ""


def migrate_command(command, migrate_retired=True):
    """Migrate a plain argv command; never inject startup flags into IPC."""
    try:
        words = shlex.split(command)
    except ValueError:
        return command
    if not words or words[0] not in {"qs", "quickshell"}:
        return command
    # Operators, substitutions and unknown options need a human's shell context.
    if re.search(r"[;&|`$<>\\\n]", command):
        return command
    config = re.search(r"(?<!\S)(?:-c|--config)\s+([\"']?)(spidey(?:-retro)?)\1(?=\s|$)", command)
    if not config:
        return command
    if config.group(2) == "spidey-retro" and not migrate_retired:
        return command
    if words.count("-c") + words.count("--config") != 1:
        return command
    config_index = words.index("-c") if "-c" in words else words.index("--config")
    remainder = words[1:config_index] + words[config_index + 2:]
    if any(word in {"-c", "--config"} for word in remainder):
        return command
    result = command[:config.start(2)] + "spidey" + command[config.end(2):]
    if all(word in START_OPTIONS for word in remainder) and "--no-duplicate" not in remainder:
        result = result.rstrip() + " --no-duplicate" + result[len(result.rstrip()):]
    return result


def transform(text, path, config_root, allowed=None):
    """Return migrated text and line-numbered review notices."""
    allowed = allowed if allowed is not None else {"hypr": True, "kitty": True, "quickshell": True}
    output = []
    notices = []
    block_end = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        body = line[:-len(ending)] if ending else line
        if path.suffix == ".lua":
            # Avoid multiline strings/comments, including arbitrary [=[ brackets.
            if block_end:
                if block_end in body:
                    block_end = None
                output.append(line)
                continue
            code, comment = split_comment(body, "--")
            opening = LONG_OPEN.search(code) or LONG_OPEN.search(comment)
            if opening:
                closer = "]" + opening.group(1) + "]"
                source = code if LONG_OPEN.search(code) else comment
                if closer not in source[opening.end():]:
                    block_end = closer
                if RETIRED.search(code):
                    notices.append(f"Review complex reference: {path}:{number}")
                output.append(line)
                continue
        else:
            code, comment = split_comment(body, "#")

        if not code.strip():
            output.append(line)
            continue

        migrated = code
        if path.parent.name == "kitty" and path.name == "kitty.conf":
            include = re.fullmatch(r"\s*include\s+(.+?)\s*", code)
            if include:
                target = include.group(1).strip("\"'")
                known = {"../kitty-spidey/kitty.conf", "~/.config/kitty-spidey/kitty.conf",
                         "$XDG_CONFIG_HOME/kitty-spidey/kitty.conf", "${XDG_CONFIG_HOME}/kitty-spidey/kitty.conf",
                         str(config_root / "kitty-spidey/kitty.conf")}
                if target in known and allowed["kitty"]:
                    output.append("# Spidey upgrade: retired theme: " + body + ending)
                    continue
        elif path.suffix == ".lua":
            migrated = LUA_SOURCE.sub(lambda match: match.group(1) + match.group(2)
                                     + match.group(3).replace("/hypr-spidey-retro/", "/hypr-spidey/")
                                     + match.group(2), code) if allowed["hypr"] else code
            # These are whole standalone calls. Concatenated shell expressions
            # remain visible as review notices rather than being reconstructed.
            call = re.fullmatch(r"(\s*hl\.exec_cmd\(\s*)([\"'])(.*)\2(\s*\)\s*;?\s*)", migrated)
            if call and not re.search(r"[\\\"']", call.group(3)):
                command = call.group(3)
                if re.fullmatch(r"bash\s+\S*/hypr-spidey/wallpaper\.sh(?:\s+\S+)?", command):
                    output.append("-- Spidey upgrade: retired wallpaper: " + body + ending)
                    continue
                migrated = call.group(1) + call.group(2) + migrate_command(command, allowed["quickshell"]) + call.group(2) + call.group(4)
            elif re.fullmatch(
                    r'\s*hl\.exec_cmd\("bash "\s*\.\.\s*quote\((root|config_root)\s*\.\.\s*'
                    r'"/hypr-spidey/wallpaper\.sh"\)\s*\.\.\s*" "\s*\.\.\s*quote\(\1\)\)\s*;?\s*', migrated):
                output.append("-- Spidey upgrade: retired wallpaper: " + body + ending)
                continue
        else:
            source = SOURCE.fullmatch(migrated)
            if source:
                value = source.group(2)
                unquoted = value.strip("\"'")
                if (allowed["hypr"] and unquoted.endswith("/hypr-spidey-retro/rice.conf")
                        and not re.search(r"[;&|`\r\n]", unquoted)):
                    root = unquoted[:-len("/hypr-spidey-retro/rice.conf")]
                    if root not in {"$spideyRetroConfigRoot", "$spideyConfigRoot", "~/.config", str(config_root)}:
                        notices.append(f"Review complex reference: {path}:{number}")
                        output.append(line)
                        continue
                    if root != "$spideyConfigRoot":
                        indent = re.match(r"\s*", migrated).group(0)
                        output.append(indent + "$spideyConfigRoot = " + root + (ending or "\n"))
                    migrated = source.group(1) + value.replace("/hypr-spidey-retro/rice.conf", "/hypr-spidey/rice.conf") + source.group(3)
            startup = re.fullmatch(r"(\s*exec(?:-once)?\s*=\s*)(.*)", migrated)
            if startup:
                command = startup.group(2)
                try:
                    words = shlex.split(command)
                except ValueError:
                    words = []
                if (len(words) in {2, 3} and words[0] == "bash"
                        and re.fullmatch(r".*/hypr-spidey/wallpaper\.sh", words[1])):
                    output.append("# Spidey upgrade: retired wallpaper: " + body + ending)
                    continue
                migrated = startup.group(1) + migrate_command(command, allowed["quickshell"])
            # IPC keybindings also use the retired config argument; only plain
            # commands at the end of a bind are safe to change automatically.
            binding = re.fullmatch(r"(\s*bind\w*\s*=.*?,\s*exec\s*,\s*)(qs\s+.*|quickshell\s+.*)", migrated)
            if binding:
                migrated = binding.group(1) + migrate_command(binding.group(2), allowed["quickshell"])

        if RETIRED.search(migrated):
            notices.append(f"Review complex reference: {path}:{number}")
        output.append(migrated + comment + ending)
    return "".join(output), notices


def candidate_files(config_root):
    paths, notices = [], []
    hypr = config_root / "hypr"
    if hypr.is_symlink():
        notices.append(f"Leave symlink unchanged: {hypr}")
    elif hypr.is_dir():
        def walk_error(error):
            raise error
        for directory, dirs, files in os.walk(hypr, followlinks=False, onerror=walk_error):
            for name in list(dirs):
                target = Path(directory) / name
                if target.is_symlink():
                    notices.append(f"Leave symlink unchanged: {target}")
                    dirs.remove(name)
            for name in sorted(files):
                target = Path(directory) / name
                if target.suffix in {".lua", ".conf"}:
                    if target.is_symlink():
                        notices.append(f"Leave symlink unchanged: {target}")
                    elif stat.S_ISREG(target.stat().st_mode):
                        paths.append(target)
    kitty = config_root / "kitty" / "kitty.conf"
    if kitty.parent.is_symlink() or kitty.is_symlink():
        notices.append(f"Leave symlink unchanged: {kitty}")
    elif kitty.is_file():
        paths.append(kitty)
    return sorted(paths), notices


def retired_policy(config_root, repo_root):
    allowed, notices = {}, []
    for key, destination, source in (("hypr", "hypr-spidey-retro", "config/hypr-retro"),
                                      ("kitty", "kitty-spidey", "config/kitty"),
                                      ("quickshell", "quickshell/spidey-retro", "quickshell-retro")):
        target = config_root / destination
        ours = target.is_symlink() and target.resolve(strict=False) == (repo_root / source).resolve(strict=False)
        allowed[key] = not os.path.lexists(target) or ours
        if not allowed[key]:
            notices.append(f"Leave references to unrelated retired path unchanged: {target}")
    return allowed, notices


def plan_migration(config_root, repo_root=None):
    config_root = Path(config_root)
    paths, notices = candidate_files(config_root)
    allowed, ownership_notices = retired_policy(config_root, Path(repo_root) if repo_root else Path(__file__).resolve().parents[1])
    notices.extend(ownership_notices)
    changes = []
    for path in paths:
        before = path.read_bytes()
        # surrogateescape makes unrelated non-UTF-8 bytes round-trip unchanged.
        after, reviews = transform(before.decode("utf-8", errors="surrogateescape"), path, config_root, allowed)
        notices.extend(reviews)
        after = after.encode("utf-8", errors="surrogateescape")
        if before != after:
            changes.append(Change(path, before, after, stat.S_IMODE(path.stat().st_mode)))
    return changes, notices


def backup_path(change, suffix):
    return change.path.with_name(change.path.name + ".spidey-backup." + suffix)


def preflight(changes, suffix):
    if not suffix or suffix in {".", ".."} or re.search(r"[/\\\r\n]", suffix):
        raise ValueError("Backup suffix must be a plain nonempty filename suffix")
    for change in changes:
        if (change.path.is_symlink() or change.path.read_bytes() != change.before
                or stat.S_IMODE(change.path.stat().st_mode) != change.mode):
            raise RuntimeError(f"Configuration changed during migration: {change.path}")
        backup = backup_path(change, suffix)
        if os.path.lexists(backup):
            raise FileExistsError(f"Backup destination already exists: {backup}")
        if not os.access(change.path, os.R_OK) or not os.access(change.path.parent, os.W_OK | os.X_OK):
            raise PermissionError(f"Cannot back up and replace: {change.path}")


def apply_migration(changes, suffix, dry_run=False, check=False):
    preflight(changes, suffix)
    if check:
        return
    if dry_run:
        for change in changes:
            print(f"Would back up {change.path} -> {backup_path(change, suffix)}")
            print(f"Would migrate references: {change.path}")
        return
    # Prepare every backup and replacement before replacing the first file.
    # A full disk or unreadable file cannot leave only half the files migrated.
    prepared = []
    created_backups = []
    try:
        for change in changes:
            backup = backup_path(change, suffix)
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, change.mode)
            created_backups.append(backup)
            with os.fdopen(descriptor, "wb") as stream:
                os.fchmod(stream.fileno(), change.mode)
                stream.write(change.before)
            descriptor, temporary = tempfile.mkstemp(prefix=".spidey-upgrade-", dir=change.path.parent)
            prepared.append((change, Path(temporary)))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(change.after)
            os.chmod(temporary, change.mode)
        preflight_without_backups(changes)
    except BaseException:
        for _, temporary in prepared:
            temporary.unlink(missing_ok=True)
        for backup in created_backups:
            backup.unlink(missing_ok=True)
        raise
    try:
        for change, temporary in prepared:
            os.replace(temporary, change.path)
            print(f"Back up {change.path} -> {backup_path(change, suffix)}")
            print(f"Migrate references: {change.path}")
    finally:
        for _, temporary in prepared:
            temporary.unlink(missing_ok=True)


def preflight_without_backups(changes):
    for change in changes:
        if (change.path.is_symlink() or change.path.read_bytes() != change.before
                or stat.S_IMODE(change.path.stat().st_mode) != change.mode):
            raise RuntimeError(f"Configuration changed during migration: {change.path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-root", type=Path, required=True)
    parser.add_argument("--backup-suffix", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f".{os.getpid()}")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validate all planned edits and backup destinations without writing")
    args = parser.parse_args(argv)
    try:
        changes, notices = plan_migration(args.config_root)
        for notice in notices:
            print(notice)
        apply_migration(changes, args.backup_suffix, dry_run=args.dry_run, check=args.check)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Reference migration stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
