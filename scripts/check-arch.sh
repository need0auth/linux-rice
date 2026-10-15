#!/usr/bin/env bash
# Read-only checks for the Arch Linux target. Does not install packages or start a compositor.
set -uo pipefail

usage() {
    cat <<'USAGE'
Usage: scripts/check-arch.sh [--all-tools] [--session]

Check Arch Linux, required packages and executable versions. Optional desktop
controls are reported separately unless --all-tools makes them required.
--session additionally checks an active Wayland Hyprland session and monitors.
No packages, configuration files, services or desktop settings are changed.
USAGE
}
all_tools=false
session=false
while (($#)); do
    case "$1" in
        --all-tools) all_tools=true; shift ;;
        --session) session=true; shift ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

failures=0
optional_missing=0
pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }
optional() {
    if command -v "$1" >/dev/null 2>&1; then
        pass "$1 — $2"
    elif "$all_tools"; then
        fail "$1 — $2 (optional tool selected by --all-tools)"
    else
        printf 'OPTIONAL %s — %s\n' "$1" "$2"
        optional_missing=$((optional_missing + 1))
    fi
}
version_at_least() {
    python3 - "$1" "$2" <<'PY'
import re
import sys
match = re.search(r'(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?', sys.argv[1])
if not match:
    raise SystemExit(1)
actual = tuple(int(part or 0) for part in match.groups())
required = tuple(int(part) for part in sys.argv[2].split('.'))
required += (0,) * (3 - len(required))
raise SystemExit(0 if actual >= required else 1)
PY
}

if [[ $(uname -s) == Linux ]]; then
    pass 'Linux kernel'
else
    fail 'Linux kernel required'
fi
os_id=unknown
if [[ -r /etc/os-release ]]; then
    os_id=$(sed -n 's/^ID=//p' /etc/os-release)
    os_id=${os_id#\"}
    os_id=${os_id%\"}
fi
if [[ "$os_id" == arch ]]; then
    pass 'Arch Linux target'
else
    fail "Arch Linux target required; this machine reports ID=$os_id"
fi

for executable in bash realpath readlink ln mv mkdir rm date timeout; do
    if command -v "$executable" >/dev/null 2>&1; then
        pass "$executable"
    else
        fail "Missing required executable: $executable (bash/coreutils)"
    fi
done

if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    pass "$(python3 --version) (requires 3.10+)"
    have_python=true
else
    fail 'Python 3.10+ required'
    have_python=false
fi

if command -v pacman >/dev/null 2>&1; then
    for package in qt6-base qt6-declarative qt6-svg ttf-dejavu; do
        if package_version=$(pacman -Q "$package" 2>/dev/null); then
            pass "$package_version"
        else
            fail "Required Arch package missing: $package"
        fi
    done
else
    fail 'pacman unavailable; required Arch package checks could not run'
fi

if command -v Hyprland >/dev/null 2>&1; then
    if compositor_version=$(timeout 10 Hyprland --version 2>&1) && "$have_python" && version_at_least "$compositor_version" 0.48.0; then
        if version_at_least "$compositor_version" 0.55.0; then
            pass 'Hyprland 0.55+ — use hyprland.lua / rice.lua'
        else
            pass 'Hyprland 0.48–0.54 — use hyprland.conf / rice.conf'
        fi
        printf '%s\n' "$compositor_version" | sed -n '1p'
    else
        fail 'Hyprland 0.48+ required, or installed Hyprland could not report a valid version'
    fi
else
    fail 'Hyprland executable missing'
fi

shell_binary=
if command -v qs >/dev/null 2>&1; then
    shell_binary=qs
elif command -v quickshell >/dev/null 2>&1; then
    shell_binary=quickshell
fi
if [[ -n "$shell_binary" ]]; then
    if shell_version=$(QT_QPA_PLATFORM=offscreen timeout 10 "$shell_binary" --version 2>&1) && "$have_python" && version_at_least "$shell_version" 0.2.1; then
        pass "$shell_binary 0.2.1+"
        printf '%s\n' "$shell_version" | sed -n '1p'
    else
        fail 'Quickshell 0.2.1+ required, or installed Quickshell could not report a valid version'
    fi
else
    fail 'Quickshell executable missing (qs or quickshell)'
fi

optional kitty 'terminal and Super+Enter'
optional fuzzel 'APPS launcher and Super+Space'
optional xdg-open 'home-folder and browser fallback'
optional firefox 'browser shortcut'
optional wpctl 'PipeWire volume controls (wireplumber)'
optional brightnessctl 'hardware backlight controls'
optional playerctl 'MPRIS media controls'
optional nmcli 'NetworkManager connection names'
optional nm-connection-editor 'NetworkManager connection settings'
optional grim 'screenshot capture'
optional slurp 'screenshot region selection'
optional wl-copy 'screenshot clipboard (wl-clipboard)'
optional hyprlock 'screen locking with the bundled configuration'

if "$session"; then
    if [[ ${XDG_SESSION_TYPE:-} == wayland ]]; then
        pass 'Wayland session'
    else
        fail 'Run --session from your Wayland desktop (XDG_SESSION_TYPE=wayland)'
    fi
    if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] && command -v hyprctl >/dev/null 2>&1 && "$have_python"; then
        if monitors=$(timeout 10 hyprctl -j monitors 2>/dev/null) && printf '%s' "$monitors" | python3 -c 'import json,sys; data=json.load(sys.stdin); raise SystemExit(0 if isinstance(data,list) and data and all(isinstance(m,dict) and m.get("name") for m in data) else 1)' 2>/dev/null; then
            pass 'Hyprland IPC returned active monitors'
        else
            fail 'Hyprland monitor IPC unavailable or returned no active monitors'
        fi
    else
        fail 'Active Hyprland session, hyprctl and Python are required for monitor checks'
    fi
fi

printf '\n%d required check(s) failed; %d optional tool(s) unavailable.\n' "$failures" "$optional_missing"
if ((failures)); then
    exit 1
fi
printf 'Required Arch installation checks passed.\n'
if ! "$session"; then
    printf 'Run --session inside Hyprland to check compositor IPC.\n'
fi
printf 'Actual audio, backlight, media and screen-lock actions need testing on your desktop.\n'
