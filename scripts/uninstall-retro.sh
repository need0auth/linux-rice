#!/usr/bin/env bash
# Remove only symlinks created by this checkout. Existing files are left alone.
set -euo pipefail
dry_run=false
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
while (($#)); do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --config-root)
            if (($# < 2)) || [[ -z "$2" ]]; then
                printf 'Missing path after --config-root.\n' >&2
                exit 2
            fi
            config_root=$2
            shift 2
            ;;
        --help|-h)
            printf 'Usage: scripts/uninstall-retro.sh [--dry-run] [--config-root PATH]\n'
            exit 0
            ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
config_root=$(realpath -m -- "$config_root")
sources=("$repo_root/quickshell-retro" "$repo_root/config/hypr-retro")
destinations=("$config_root/quickshell/spidey-retro" "$config_root/hypr-spidey-retro")
for i in "${!sources[@]}"; do
    destination=${destinations[$i]}
    if [[ -L "$destination" ]] && [[ $(readlink -- "$destination") == "${sources[$i]}" ]]; then
        printf 'Remove link: %s\n' "$destination"
        if ! "$dry_run"; then
            rm -- "$destination"
        fi
    elif [[ -e "$destination" || -L "$destination" ]]; then
        printf 'Leave unrelated path unchanged: %s\n' "$destination"
    fi
done
printf 'Remove your retro source/autostart lines manually; backups are never deleted or restored automatically.\n'
