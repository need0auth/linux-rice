#!/usr/bin/env bash
# Install only this rice's symlinks. Never replace a user's existing configuration silently.
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: scripts/install.sh [--dry-run] [--backup] [--config-root PATH]

Links Quickshell, Hyprland snippets and Kitty theme into the config directory.
Existing files are refused unless --backup is explicitly supplied. Your main
Hyprland and Kitty configurations are never edited. No packages are installed.

  --dry-run           Show actions without creating directories or files.
  --backup            Move conflicts to unique .spidey-backup.* paths first.
  --config-root PATH  Override ${XDG_CONFIG_HOME:-$HOME/.config}.
USAGE
}

dry_run=false
backup=false
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
while (($#)); do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --backup) backup=true; shift ;;
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
config_root=$(realpath -m -- "$config_root")
if [[ "$config_root" == / || "$config_root" == *$'\n'* || "$config_root" == *$'\r'* ]]; then
    printf 'Choose a normal config directory, not / or a path with newlines.\n' >&2
    exit 2
fi

sources=("$repo_root/quickshell" "$repo_root/config/hypr" "$repo_root/config/kitty")
destinations=("$config_root/quickshell/spidey" "$config_root/hypr-spidey" "$config_root/kitty-spidey")
conflicts=false
for i in "${!sources[@]}"; do
    source_path=${sources[$i]}
    destination=${destinations[$i]}
    if [[ ! -d "$source_path" ]]; then
        printf 'Missing repository directory: %s\n' "$source_path" >&2
        exit 1
    fi
    if [[ -L "$destination" ]] && [[ $(readlink -- "$destination") == "$source_path" ]]; then
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

backup_suffix="spidey-backup.$(date -u +%Y%m%dT%H%M%SZ).$$"
for i in "${!sources[@]}"; do
    source_path=${sources[$i]}
    destination=${destinations[$i]}
    if [[ -L "$destination" ]] && [[ $(readlink -- "$destination") == "$source_path" ]]; then
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

printf '\nNo main configuration was changed.\n'
printf 'Hyprland 0.55+: load %s/hypr-spidey/rice.lua from your existing Lua config.\n' "$config_root"
printf 'Hyprland 0.48–0.54: source %s/hypr-spidey/rice.conf after defining $spideyConfigRoot.\n' "$config_root"
printf 'See README.md for startup, dependencies and the complete starter configs.\n'
