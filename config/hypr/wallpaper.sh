#!/usr/bin/env bash
# Keep a generated Hyprpaper config outside the checkout. Supports custom roots.
set -euo pipefail
config_root=${1:-${XDG_CONFIG_HOME:-"$HOME/.config"}}
wallpaper="$config_root/quickshell/spidey/assets/wallpaper.png"
if ! command -v hyprpaper >/dev/null 2>&1; then
    printf 'Spidey: install hyprpaper to enable the wallpaper.\n' >&2
    exit 0
fi
if [[ ! -f "$wallpaper" ]]; then
    printf 'Spidey: wallpaper missing: %s\n' "$wallpaper" >&2
    exit 1
fi
if [[ "$wallpaper" == *$'\n'* || "$wallpaper" == *$'\r'* || "$wallpaper" == *'#'* || "$wallpaper" == *'$'* ]]; then
    printf 'Spidey: wallpaper path contains unsupported Hyprlang characters.\n' >&2
    exit 1
fi
runtime_dir=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/spidey-wallpaper.XXXXXXXX")
paper_pid=''
cleanup() {
    if [[ -n "$paper_pid" ]]; then
        kill "$paper_pid" 2>/dev/null || true
    fi
    rm -rf -- "$runtime_dir"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
version=$(hyprpaper --version 2>/dev/null || true)
if [[ "$version" =~ (^|[^0-9])0\.[0-7]\. ]]; then
    printf 'preload = %s\nwallpaper = ,%s\nsplash = false\nipc = on\n' "$wallpaper" "$wallpaper" > "$runtime_dir/hyprpaper.conf"
else
    printf 'wallpaper {\n    monitor =\n    path = %s\n    fit_mode = cover\n}\nsplash = false\nipc = on\n' "$wallpaper" > "$runtime_dir/hyprpaper.conf"
fi
hyprpaper --config "$runtime_dir/hyprpaper.conf" &
paper_pid=$!
wait "$paper_pid"
