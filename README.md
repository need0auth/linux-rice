# Spidey Tracker // Arch Linux rice

[![Arch Linux checks](https://github.com/need0auth/linux-rice/actions/workflows/arch.yml/badge.svg)](https://github.com/need0auth/linux-rice/actions/workflows/arch.yml)

A Hyprland + Quickshell desktop based on the supplied tracker reference: chunky cyan frames, navy panels, coral and mint buttons, peach keys, and illustrated pixel icons. This is the default rice on `main`. The previous black/red variant has been removed from the working tree.

![Tracker desktop panels](docs/desktop.png)

The shell provides workspace profiles, an app rail, media dock, quick settings and a tracker dashboard. CPU, memory, storage, network, battery and media readings come from your machine. The map is decorative and collects no location data. Your wallpaper is left alone.

## Install on Arch Linux

Use an up-to-date Arch installation and an existing working Hyprland session. Install the shell requirements with a full system upgrade:

```sh
sudo pacman -Syu --needed hyprland quickshell qt6-svg python ttf-dejavu
git clone https://github.com/need0auth/linux-rice.git
cd linux-rice
bash scripts/install.sh --dry-run
bash scripts/install.sh
bash scripts/check-arch.sh
```

The stable `quickshell` package is in Arch's official repositories; no AUR helper is required. Its Qt dependencies are resolved by pacman. Keep Quickshell and Qt upgraded together. The bundled Silkscreen font is loaded directly by the shell.

Installation creates only these links, so keep this checkout in place:

| Installed path | Repository directory |
| --- | --- |
| `~/.config/quickshell/spidey` | `quickshell/` |
| `~/.config/hypr-spidey` | `config/hypr/` |

The installer does not edit your existing Hyprland config, run a package manager, enable services or replace your wallpaper. Conflicting files stop the entire preflight. Use `--backup` to move conflicts to unique backup paths. `--config-root /absolute/path` selects a custom root; export `XDG_CONFIG_HOME` to that root when starting the shell.

### Connect it to Hyprland

Run `bash scripts/check-arch.sh` or `hyprctl version` to identify your installed Hyprland. Current **0.55+** uses Lua; add this to your existing Lua config:

```lua
local config_root = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
dofile(config_root .. "/hypr-spidey/rice.lua")({ config_root = config_root })
```

For **0.48–0.54**, add this to your existing `hyprland.conf`:

```ini
$spideyConfigRoot = ~/.config
source = $spideyConfigRoot/hypr-spidey/rice.conf
```

Keep your existing monitor definitions, keyboard layout and device settings. The snippet adds styling, bindings and new-session autostart. Reload, then launch the shell manually in an existing session:

```sh
hyprctl reload
qs -c spidey
```

Use `quickshell` in place of `qs` if that is your executable name. Complete starter configs are available: `Hyprland --config ~/.config/hypr-spidey/hyprland.lua` for 0.55+, or the `.conf` equivalent for older supported versions. The starter uses a US keyboard; change `kb_layout` to `br` if appropriate.

### Optional desktop controls

Install the tools for the controls you want:

```sh
sudo pacman -Syu --needed kitty fuzzel thunar xdg-utils firefox \
  wireplumber playerctl brightnessctl grim slurp wl-clipboard hyprlock \
  networkmanager nm-connection-editor
```

| Tool | Control |
| --- | --- |
| `kitty`, `firefox`, `xdg-open` and a file manager | Terminal, browser and files. Kitty keeps your normal configuration. |
| `fuzzel` | App launcher with the cyan/navy palette. |
| `wpctl` from `wireplumber` | Volume and mute, with an existing working PipeWire session. |
| `playerctl` | Playback and metadata from MPRIS players. |
| `brightnessctl` | Backlight controls, subject to hardware and user permissions. |
| `nmcli`, `nm-connection-editor` | Connection names and settings, with an existing NetworkManager service. |
| `grim`, `slurp`, `wl-copy` | Region screenshots and clipboard capture. |
| `hyprlock` | Locking with the bundled cyan/navy config and Arch's PAM setup. |

The rice does not change your network or audio service setup. Missing tools or devices disable the corresponding readings/controls or produce an action message. CPU, RAM, storage and uptime need only Python and Linux's system interfaces.

Run `bash scripts/check-arch.sh --all-tools --session` from your Arch Hyprland desktop to check installed controls and compositor monitor IPC. Audio routing, backlight access, MPRIS and locking still need a direct check on your machine.

## Updating either previous version

Before updating a running old installation, stop its shell while its config paths still exist:

```sh
qs -c spidey-retro kill   # If the separate retro config is running
qs -c spidey kill         # If the earlier default config is running
```

Then update your checkout to `main` and rerun `bash scripts/install.sh`. It reuses matching canonical links and removes only exact retired symlinks created by this checkout (`spidey-retro`, `hypr-spidey-retro` and `kitty-spidey`). Unknown files, replacement links and backups are preserved.

Replace old `hypr-spidey-retro/rice.*` source lines with the canonical snippet above. Keep one source/autostart entry. The old `install-retro.sh` and `quickshell-retro/` paths are retired.

## Controls

| Control | Action |
| --- | --- |
| Top-bar `PROF` buttons | Workspaces 1–5; fewer on narrow screens. |
| Left rail | Tracker, terminal, browser, files, screenshot and settings. |
| Gear button | Show/hide volume, brightness, network and lock controls. |
| Bottom dock | Media controls/title, launcher and lock. |
| Tracker `O`, `S`, `T` | Toggle local map overlays. |
| `Super + D` | Toggle tracker. |
| `Super + Enter`, `Super + Space`, `Super + E` | Terminal, launcher, files. |
| `Super + Q`, `Super + F`, `Super + V` | Close, fullscreen, floating. |
| `Super + arrows` | Focus; add Shift to move the window. |
| `Super + 1…0` | Workspace; add Shift to move the window there. |
| `Super + L`, `Print` | Lock; select and copy a screenshot. |

The dashboard screenshot button saves to `~/Pictures/SpideyTracker/`. Both popups start open and can be closed. Short displays scroll the tracker without shrinking controls. Terminal IPC:

```sh
qs -c spidey ipc call dashboard toggle
qs -c spidey ipc call dashboard controls
```

## Preview and customize

```sh
SPIDEY_PREVIEW=1 SPIDEY_DEMO=1 qs -p "$PWD/quickshell"
```

This opens the [windowed preview](docs/preview.png) over a neutral grid. Demo mode is labeled and disables desktop actions. Omit `SPIDEY_DEMO` for real measurements. `SPIDEY_PREVIEW_WIDTH` and `SPIDEY_PREVIEW_HEIGHT` set the window size. No wallpaper asset is installed.

- Colors/fonts: `quickshell/services/Theme.qml`.
- Frames/buttons: `quickshell/components/PixelFrame.qml` and `RetroButton.qml`.
- Icons: `quickshell/assets/icons/`; rebuild with `python3 tools/generate-icons.py`.
- Telemetry/actions: `quickshell/scripts/system.py`.
- Hyprland and lock screen: `config/hypr/`.

Spider badges now have a small head, narrow center, pointed abdomen and eight separated legs:

![Updated spider sprites](docs/spider-icons.png)

This is an unofficial fan interpretation. The bundled font retains its [SIL Open Font License](quickshell/assets/fonts/OFL.txt).

## Validation and removal

```sh
python3 -m unittest discover -s tests -v
bash scripts/check-arch.sh --session
```

The [Arch CI workflow](.github/workflows/arch.yml) installs official packages in an official Arch container, validates Hyprland config as a normal user, renders Quickshell, exercises IPC and saves logs/screenshots. Its badge reports CI status. See [validation details](docs/validation.md) for cloud checks and their limits.

To remove this checkout's links, run `bash scripts/uninstall.sh --dry-run`, then `bash scripts/uninstall.sh`. Remove the source/autostart lines you added. Backups and unrelated configuration stay intact.
