"""Install a root-owned greetd snapshot without touching a running session."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]


def parse_args(arguments=None):
    parser = argparse.ArgumentParser(
        description="Preview or install the optional Spidey greetd login screen. "
                    "Without --install or --enable, this is a dry run. Packages are never installed.",
        epilog="Arch packages: greetd sway quickshell qt6-svg ttf-dejavu dbus python. "
               "--enable changes next boot only; it never stops Ly or your desktop.")
    parser.add_argument("--dry-run", action="store_true", help="show the plan without writing files or changing services")
    parser.add_argument("--install", action="store_true", help="copy the login screen and greetd config; keep existing services")
    parser.add_argument("--enable", action="store_true", help="enable greetd for next boot and disable enabled Ly units, without --now")
    parser.add_argument("--backup", action="store_true", help="allow replacing unrelated existing paths after backing them up")
    parser.add_argument("--root", default="/", metavar="PATH", help="stage files under PATH; service changes are forbidden there")
    return parser.parse_args(arguments)


def fail(message):
    raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def present(path):
    return path.exists() or path.is_symlink()


def safe_path(path, root):
    """Do not traverse pre-existing destination symlinks when running as root."""
    if path != root and root not in path.parents:
        fail(f"Destination escapes installation root: {path}")
    for component in (path, *path.parents):
        if component.is_symlink():
            fail(f"Refusing destination symlink: {component}")
        if component == root:
            break


def run(command):
    return subprocess.run(command, text=True, capture_output=True, check=True).stdout.strip()


def ly_units_from_output(output):
    """Pick actual enabled instances, including Arch's ly@tty2.service."""
    units = []
    for line in output.splitlines():
        unit = line.split()[0] if line.split() else ""
        if unit == "ly.service" or re.fullmatch(r"ly@[^/]+\.service", unit):
            if unit not in units:
                units.append(unit)
    return units


def switch_next_boot(ly_units, greetd_enabled, runner=run):
    """Change enablement only; restore Ly if any systemctl step fails."""
    attempted = []
    try:
        for unit in ly_units:
            # Even an unsuccessful disable may have removed some links.
            attempted.append(unit)
            runner(["systemctl", "disable", unit])
        runner(["systemctl", "enable", "greetd.service"])
    except subprocess.CalledProcessError:
        rollback = ([] if greetd_enabled else [["systemctl", "disable", "greetd.service"]])
        rollback += [["systemctl", "enable", unit] for unit in attempted]
        for command in rollback:
            try:
                runner(command)
            except subprocess.CalledProcessError as error:
                print(f"Rollback needs attention: {' '.join(command)} ({error})", file=sys.stderr)
        raise


def main(arguments=None):
    args = parse_args(arguments)
    dry = args.dry_run or not (args.install or args.enable)
    install_requested = args.install or not args.enable
    if any(c in args.root for c in "\r\n"):
        fail("Choose a root path without newlines.")
    raw_root = Path(os.path.abspath(args.root))
    # Check the original spelling before resolving so --root cannot hide a symlink.
    for component in (raw_root, *raw_root.parents):
        if component.is_symlink():
            fail(f"Refusing symlink in installation root: {component}")
    root = raw_root.resolve()
    real_root = root == Path("/")
    if args.enable and not real_root:
        fail("--enable cannot be used with a staging --root.")
    if not dry and real_root and os.geteuid() != 0:
        fail("Use sudo for a real system install, or use --root PATH to stage files.")

    share = root / "usr/local/share/spidey-greeter"
    config = root / "etc/greetd/config.toml"
    for path in (share, config):
        safe_path(path, root)
    marker = share / ".spidey-managed.json"
    metadata = {}
    if marker.is_file() and not marker.is_symlink():
        try:
            metadata = json.loads(marker.read_text())
        except (ValueError, OSError):
            pass
    if not isinstance(metadata, dict) or not isinstance(metadata.get("hashes", {}), dict):
        metadata = {}
    managed_share = metadata.get("owner") == "spidey-greeter" and metadata.get("format") == 1
    if present(share) and not share.is_dir():
        fail(f"Expected a directory at {share}; move it before installing.")
    managed_config = config.is_file() and config.read_bytes().startswith(
        b"# Managed by Spidey Tracker login installer (format 1).")
    if present(config) and not config.is_file():
        fail(f"Expected a regular file at {config}; move it before installing.")
    conflicts = [path for path, managed in ((share, managed_share), (config, managed_config))
                 if present(path) and not managed]
    if install_requested and conflicts and not args.backup:
        for path in conflicts:
            print(f"Existing unrelated path: {path}")
        fail("Nothing changed. Review these paths, then rerun with --backup to preserve them and install.")

    # Service preflight happens before the first write, including combined install/enable.
    ly_units = []
    prior_dm = ""
    greetd_enabled = False
    if args.enable:
        for executable in ("systemctl", "sway", "dbus-run-session", "Hyprland"):
            if not shutil.which(executable):
                fail(f"Missing {executable}; install the required Arch packages first.")
        if not (shutil.which("qs") or shutil.which("quickshell")):
            fail("Missing Quickshell; install the Arch quickshell package first.")
        import pwd
        try:
            pwd.getpwnam("greeter")
        except KeyError:
            fail("The greetd package's greeter account is missing; install greetd first.")
        if run(["systemctl", "show", "greetd.service", "--property=LoadState", "--value"]) != "loaded":
            fail("greetd.service is not installed; install greetd first.")
        dm_link = root / "etc/systemd/system/display-manager.service"
        if dm_link.is_symlink():
            prior_dm = dm_link.resolve().name
            if prior_dm not in ("ly.service", "greetd.service") and not re.fullmatch(r"ly@[^/]+\.service", prior_dm):
                fail(f"Another display manager is configured ({prior_dm}); disable it yourself before opting in.")
        enabled = run(["systemctl", "list-unit-files", "--state=enabled,enabled-runtime", "--no-legend", "--no-pager"])
        ly_units = ly_units_from_output(enabled)
        greetd_enabled = any(line.split() and line.split()[0] == "greetd.service"
                             for line in enabled.splitlines())
        if not install_requested and not (managed_share and managed_config):
            fail("Install the managed login files with --install before using --enable.")

    if install_requested:
        sources = {}
        for source_dir, prefix in ((REPO / "greeter", Path("greeter")),
                                   (REPO / "quickshell/assets", Path("assets"))):
            if not source_dir.is_dir():
                fail(f"Missing source directory: {source_dir}")
            for source in sorted(source_dir.rglob("*")):
                if source.is_symlink():
                    fail(f"Login snapshots cannot include source symlinks: {source}")
                if source.is_file():
                    sources[prefix / source.relative_to(source_dir)] = source
        for name in ("sway.conf", "start-greeter"):
            sources[Path(name)] = REPO / "config/greetd" / name
        sources[Path("assets/wallpaper.png")] = REPO / "assets/wallpapers/spidey-city.png"
        config_source = REPO / "config/greetd/config.toml"
        for source in (*sources.values(), config_source):
            if not source.is_file() or source.is_symlink():
                fail(f"Missing regular source file: {source}")
        if Path("greeter/shell.qml") not in sources:
            fail("The login snapshot is missing greeter/shell.qml.")

        preserved = {}
        previous_hashes = metadata.get("hashes", {}) if managed_share else {}
        for relative in (Path("greeter/session.json"), Path("sway.conf")):
            installed = share / relative
            safe_path(installed, root)
            if installed.is_file() and managed_share and digest(installed) != previous_hashes.get(str(relative)):
                preserved[relative] = installed.read_bytes()
                print(f"Preserve customized login setting: {installed}")
        # Keep the original service choice when updating an already enabled login.
        # This is installation state, not a theme asset with a repository default.
        service_state = share / "service-before-enable.json"
        safe_path(service_state, root)
        if managed_share and present(service_state):
            if not service_state.is_file():
                fail(f"Expected a regular service rollback record: {service_state}")
            preserved[Path("service-before-enable.json")] = service_state.read_bytes()
        preserve_config = (managed_config and
                           digest(config) != metadata.get("config_hash", digest(config_source)))
        if preserve_config:
            print(f"Preserve customized greetd config: {config}")
        new_metadata = {
            "owner": "spidey-greeter", "format": 1,
            "hashes": {str(rel): digest(source) for rel, source in sources.items()},
            "config_hash": digest(config_source),
        }
        print(f"Snapshot {len(sources)} files -> {share} (directories 0755, files 0644, root ownership on the real system)")
        print(f"Install greetd configuration -> {config}")
        if not dry:
            suffix = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + f".{os.getpid()}"
            share.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            config.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with tempfile.TemporaryDirectory(prefix=".spidey-login-", dir=share.parent) as temporary:
                staged = Path(temporary) / "snapshot"
                staged.mkdir(mode=0o755)
                for relative, source in sources.items():
                    target = staged / relative
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                    target.write_bytes(preserved.get(relative, source.read_bytes()))
                    target.chmod(0o755 if relative == Path("start-greeter") else 0o644)
                for relative, content in preserved.items():
                    if relative not in sources:
                        (staged / relative).write_bytes(content)
                (staged / ".spidey-managed.json").write_text(json.dumps(new_metadata, indent=2) + "\n")
                for path in (staged, *staged.rglob("*")):
                    path.chmod(0o755 if path.is_dir() or path.name == "start-greeter" else 0o644)
                    if real_root:
                        os.chown(path, 0, 0)
                if present(share):
                    backup_path = share.with_name(share.name + ".spidey-backup." + suffix)
                    share.rename(backup_path)
                    print(f"Backup: {backup_path}")
                staged.rename(share)
            if not preserve_config:
                if present(config):
                    backup_path = config.with_name(config.name + ".spidey-backup." + suffix)
                    config.rename(backup_path)
                    print(f"Backup: {backup_path}")
                # Atomic replacement prevents greetd observing a partly written config.
                handle, temporary = tempfile.mkstemp(prefix=".spidey-config-", dir=config.parent)
                try:
                    with os.fdopen(handle, "wb") as stream:
                        stream.write(config_source.read_bytes())
                    os.chmod(temporary, 0o644)
                    if real_root:
                        os.chown(temporary, 0, 0)
                    os.replace(temporary, config)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)

    if args.enable:
        print("Next boot: disable " + (", ".join(ly_units) or "no enabled Ly units") + "; enable greetd.service.")
        print("The current login manager and desktop remain running.")
        if not dry:
            state = share / "service-before-enable.json"
            safe_path(state, root)
            if present(state) and not state.is_file():
                fail(f"Expected a regular service rollback record: {state}")
            if not state.exists():
                state.write_text(json.dumps({"ly_units": ly_units, "display_manager": prior_dm}, indent=2) + "\n")
                state.chmod(0o644)
            switch_next_boot(ly_units, greetd_enabled)
        rollback_units = ly_units or ([prior_dm] if prior_dm.startswith("ly") else [])
        if rollback_units:
            print("Rollback for the next boot (from a TTY):")
            print("  sudo systemctl disable greetd.service")
            print("  sudo systemctl enable " + " ".join(rollback_units))
    if dry:
        print("Dry run complete. No files or services changed.")
    elif not args.enable:
        print("Installed. Ly remains your login manager. Review the snapshot before opting in with --enable.")
    else:
        print("Enabled for the next boot. Reboot when you are ready; keep your Ly package installed for rollback.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        message = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f"Login setup: {message}", file=sys.stderr)
        sys.exit(1)
