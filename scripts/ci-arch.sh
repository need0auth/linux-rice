#!/usr/bin/env bash
# Reproduce the native Arch CI checks without touching a user's live config.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd -- "$repo_root"
if (( EUID == 0 )); then
    printf 'Run this check as an ordinary user; Hyprland rejects root.\n' >&2
    exit 1
fi
test_root=$(mktemp -d "${TMPDIR:-/tmp}/spidey-arch.XXXXXXXX")
shell_pid=''
cleanup() {
    if [[ -n "$shell_pid" ]]; then
        kill "$shell_pid" 2>/dev/null || true
        wait "$shell_pid" 2>/dev/null || true
    fi
    rm -rf -- "$test_root"
}
trap cleanup EXIT
export XDG_CONFIG_HOME="$test_root/config"
export XDG_RUNTIME_DIR="$test_root/runtime"
mkdir -m 700 -- "$XDG_CONFIG_HOME" "$XDG_RUNTIME_DIR"
artifact_root=${SPIDEY_ARTIFACT_DIR:-"$test_root/artifacts"}
mkdir -p -- "$artifact_root"

bash scripts/check-arch.sh | tee "$artifact_root/requirements.log"
pacman -Q hyprland quickshell qt6-base qt6-declarative qt6-svg python > "$artifact_root/versions.txt"
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh scripts/uninstall.sh scripts/check-arch.sh scripts/ci-arch.sh
bash scripts/install.sh

compositor_version=$(Hyprland --version)
config_format=$(python3 - "$compositor_version" <<'PY'
import re
import sys
match = re.search(r'(\d+)\.(\d+)\.(\d+)', sys.argv[1])
if match is None:
    raise SystemExit('Cannot identify the installed Hyprland version')
version = tuple(map(int, match.groups()))
print('lua' if version >= (0, 55, 0) else 'conf')
PY
)
Hyprland --verify-config --config "$XDG_CONFIG_HOME/hypr-spidey/hyprland.$config_format" 2>&1 | tee "$artifact_root/hyprland-config.log"

if command -v qs >/dev/null 2>&1; then
    shell_binary=qs
else
    shell_binary=quickshell
fi
export QT_QPA_PLATFORM=offscreen
export QT_QUICK_BACKEND=software
export SPIDEY_PREVIEW=1
export SPIDEY_DEMO=1
export SPIDEY_PREVIEW_WIDTH=1600
export SPIDEY_PREVIEW_HEIGHT=1000
export QT_SCALE_FACTOR=1
SPIDEY_SCREENSHOT="$artifact_root/preview.png" \
    timeout 45 "$shell_binary" -c spidey --no-color 2>&1 | tee "$artifact_root/preview.log"
grep -Fq 'SPIDEY_SCREENSHOT_SAVED' "$artifact_root/preview.log"
python3 - "$artifact_root/preview.png" <<'PY'
import struct
import sys
from pathlib import Path
image = Path(sys.argv[1]).read_bytes()
if image[:8] != b'\x89PNG\r\n\x1a\n' or image[12:16] != b'IHDR':
    raise SystemExit('Preview is not a PNG')
if struct.unpack('>II', image[16:24]) != (1600, 1000) or len(image) < 4096:
    raise SystemExit('Preview dimensions or contents are unexpected')
print('Rendered a 1600x1000 desktop preview')
PY

SPIDEY_SCREENSHOT='' "$shell_binary" -c spidey --no-color > "$artifact_root/ipc.log" 2>&1 &
shell_pid=$!
ready=false
for attempt in {1..30}; do
    if ! kill -0 "$shell_pid" 2>/dev/null; then
        cat "$artifact_root/ipc.log" >&2
        exit 1
    fi
    if timeout 5 "$shell_binary" -c spidey ipc show > "$artifact_root/ipc-schema.txt" 2>/dev/null; then
        ready=true
        break
    fi
    sleep 1
done
if ! "$ready"; then
    printf 'Quickshell IPC did not become ready.\n' >&2
    exit 1
fi
for method in close open toggle controls; do
    timeout 10 "$shell_binary" -c spidey ipc call dashboard "$method"
done
python3 quickshell/scripts/system.py snapshot > "$artifact_root/telemetry.json"
python3 - "$artifact_root/telemetry.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    data = json.load(stream)
assert data['demo'] is False
assert all(0 <= data[key] <= 100 for key in ('cpu', 'memory', 'disk'))
assert data['uptime'] > 0
print('Live Linux telemetry and dashboard IPC passed')
PY
ARTIFACT_ROOT="$artifact_root/topbar" python3 tests/integration/topbar.py
ARTIFACT_ROOT="$artifact_root/workarea" python3 tests/integration/wayland_workarea.py
ARTIFACT_ROOT="$artifact_root/mpris" python3 tests/integration/mpris.py
ARTIFACT_ROOT="$artifact_root/rofi" python3 tests/integration/rofi.py
ARTIFACT_ROOT="$artifact_root/upgrade" python3 tests/integration/upgrade.py
bash scripts/uninstall.sh
printf 'Native Arch package, installer, config, QML and IPC checks passed.\n'
