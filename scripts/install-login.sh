#!/usr/bin/env bash
# Optional system login screen. The ordinary desktop installer never calls this.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if ! command -v python3 >/dev/null 2>&1; then
    printf 'Python 3 is required. On Arch: sudo pacman -S --needed python\n' >&2
    exit 1
fi
exec python3 "$repo_root/scripts/install-login.py" "$@"
