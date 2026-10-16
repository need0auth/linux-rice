#!/usr/bin/env bash
# Install this rice's symlinks and retire known links from older layouts. Never replace a user's existing configuration silently.
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: scripts/install.sh [--dry-run] [--backup] [--no-restart] [--config-root PATH]

Links Quickshell and Hyprland snippets into the config directory.
Existing unrelated files are refused unless --backup is explicitly supplied.
Known old Spidey references are migrated with backups. Only this checkout's old
links are retired. Running Spidey bars on this display are restarted once.
No packages are installed; personal app preferences are preserved.

  --dry-run           Show actions without creating directories or files.
  --backup            Move conflicts to unique .spidey-backup.* paths first.
  --no-restart        Update files without reloading Hyprland or restarting bars.
  --config-root PATH  Override ${XDG_CONFIG_HOME:-$HOME/.config}.
USAGE
}

dry_run=false
backup=false
restart=true
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
while (($#)); do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --backup) backup=true; shift ;;
        --no-restart) restart=false; shift ;;
        --config-root)
            if (($# < 2)) || [[ -z "$2" ]]; then
                printf 'Missing path after --config-root.\n' >&2
                exit 2
            fi
            config_root=$2
            shift 2
            ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if ! command -v python3 >/dev/null 2>&1; then
    printf 'Python 3 is required for safe upgrade checks. Install python on Arch first.\n' >&2
    exit 1
fi
config_root=$(realpath -m -- "$config_root")
if [[ "$config_root" == / || "$config_root" == *$'\n'* || "$config_root" == *$'\r'* ]]; then
    printf 'Choose a normal config directory, not / or a path with newlines.\n' >&2
    exit 2
fi

sources=("$repo_root/quickshell" "$repo_root/config/hypr")
destinations=("$config_root/quickshell/spidey" "$config_root/hypr-spidey")
old_sources=("$repo_root/quickshell-retro" "$repo_root/config/hypr-retro")
managed_link() {
    [[ -L "$1" ]] && [[ $(realpath -m -- "$1") == $(realpath -m -- "$2") ]]
}
conflicts=false
for i in "${!sources[@]}"; do
    source_path=${sources[$i]}
    destination=${destinations[$i]}
    if [[ ! -d "$source_path" ]]; then
        printf 'Missing repository directory: %s\n' "$source_path" >&2
        exit 1
    fi
    if managed_link "$destination" "$source_path" || managed_link "$destination" "${old_sources[$i]}"; then
        continue
    fi
    if [[ -e "$destination" || -L "$destination" ]] && ! "$backup"; then
        printf 'Conflict: %s\n' "$destination" >&2
        conflicts=true
    fi
done
if "$conflicts"; then
    printf 'Nothing changed. Move these paths yourself, or rerun with --backup.\n' >&2
    exit 1
fi

upgrade_suffix="$(date -u +%Y%m%dT%H%M%SZ).$$"
backup_suffix="spidey-backup.$upgrade_suffix"
migration=(python3 "$repo_root/scripts/migrate-user-config.py" --config-root "$config_root" --backup-suffix "$upgrade_suffix")
# Validate every reference migration before stopping an existing desktop.
"${migration[@]}" --check
runtime=(python3 "$repo_root/scripts/upgrade-runtime.py" --repo-root "$repo_root" --config-root "$config_root")
runtime_state=''
cleanup() {
    local exit_status=$?
    if [[ -n "$runtime_state" ]]; then
        if (( exit_status != 0 )); then
            "${runtime[@]}" --state-file "$runtime_state" resume || true
        fi
        rm -f -- "$runtime_state"
    fi
    return "$exit_status"
}
trap cleanup EXIT
if "$dry_run"; then
    "${migration[@]}" --dry-run
    if "$restart"; then
        "${runtime[@]}" --state-file /dev/null --dry-run stop
    fi
else
    if "$restart"; then
        runtime_state=$(mktemp "${TMPDIR:-/tmp}/spidey-upgrade.XXXXXXXX")
        "${runtime[@]}" --state-file "$runtime_state" stop
    fi
    "${migration[@]}"
fi
for i in "${!sources[@]}"; do
    source_path=${sources[$i]}
    destination=${destinations[$i]}
    if managed_link "$destination" "$source_path"; then
        printf 'Already linked: %s\n' "$destination"
        continue
    fi
    if [[ -e "$destination" || -L "$destination" ]]; then
        backup_path="$destination.$backup_suffix"
        if [[ -e "$backup_path" || -L "$backup_path" ]]; then
            printf 'Backup destination unexpectedly exists: %s\n' "$backup_path" >&2
            exit 1
        fi
        printf 'Back up %s -> %s\n' "$destination" "$backup_path"
        if ! "$dry_run"; then
            mv -- "$destination" "$backup_path"
        fi
    fi
    printf 'Link %s -> %s\n' "$destination" "$source_path"
    if ! "$dry_run"; then
        mkdir -p -- "$(dirname -- "$destination")"
        ln -s -- "$source_path" "$destination"
    fi
done

# Older installers used these exact source/destination pairs. Retire only those
# symlinks; never remove a real file, directory, or a foreign symlink.
retired_sources=("$repo_root/quickshell-retro" "$repo_root/config/hypr-retro" "$repo_root/config/kitty")
retired_destinations=("$config_root/quickshell/spidey-retro" "$config_root/hypr-spidey-retro" "$config_root/kitty-spidey")
for i in "${!retired_sources[@]}"; do
    destination=${retired_destinations[$i]}
    if managed_link "$destination" "${retired_sources[$i]}"; then
        printf 'Retire old link: %s\n' "$destination"
        if ! "$dry_run"; then
            rm -- "$destination"
        fi
    elif [[ -e "$destination" || -L "$destination" ]]; then
        printf 'Leave unrelated retired path unchanged: %s\n' "$destination"
    fi
done

wayland_socket=${WAYLAND_DISPLAY:-}
if [[ -n "$wayland_socket" && "$wayland_socket" != /* ]]; then
    wayland_socket="${XDG_RUNTIME_DIR:-}/$wayland_socket"
fi
if ! "$dry_run" && "$restart" && [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} && -S "$wayland_socket" ]] && command -v hyprctl >/dev/null 2>&1; then
    printf 'Reload the current Hyprland configuration.\n'
    timeout 10 hyprctl reload
fi
if [[ -n "$runtime_state" ]]; then
    "${runtime[@]}" --state-file "$runtime_state" resume
fi
if "$dry_run"; then
    printf '\nDry run complete. Nothing changed.\n'
else
    printf '\nUpgrade complete. Changed startup/config references have adjacent .spidey-backup.* backups.\n'
fi
printf 'Hyprland 0.55+: load %s/hypr-spidey/rice.lua from your existing Lua config.\n' "$config_root"
printf 'Hyprland 0.48–0.54: source %s/hypr-spidey/rice.conf after defining $spideyConfigRoot.\n' "$config_root"
printf 'See README.md for startup, dependencies and the complete starter configs.\n'
printf 'Any complex or externally linked references flagged above need manual review.\n'
