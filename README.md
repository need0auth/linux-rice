# Spidey Tracker // Arch Linux rice

[![Arch Linux checks](https://github.com/need0auth/linux-rice/actions/workflows/arch.yml/badge.svg)](https://github.com/need0auth/linux-rice/actions/workflows/arch.yml)

A Hyprland + Quickshell desktop based on the supplied tracker reference: chunky cyan frames, navy panels, coral and mint buttons, peach keys, and illustrated pixel icons. This is the default rice on `main`. The previous black/red variant has been removed from the working tree.

![Tracker desktop panels](docs/preview.png)

The shell provides numbered workspace buttons, an app rail, media dock, quick settings and a tracker dashboard. CPU, memory, storage, network, battery and media readings come from your machine. The map is decorative and collects no location data. Your wallpaper is left alone.

The top bar, left rail and bottom dock reserve compositor space, so tiled windows stay clear of them. The tracker and quick settings are popups. Transparent areas around the bars pass clicks through.

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

The installer migrates recognizable old Spidey startup/source references in your Hyprland files and backs up every changed file. Other settings and personal app preferences are preserved. It does not run a package manager or enable services. Unrelated conflicting files stop the preflight; use `--backup` to preserve and replace those conflicts. `--config-root /absolute/path` selects a custom root; export `XDG_CONFIG_HOME` to that root when starting the shell.

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
qs -c spidey --no-duplicate --daemonize
```

Use `quickshell` in place of `qs` if that is your executable name. Complete starter configs are available: `Hyprland --config ~/.config/hypr-spidey/hyprland.lua` for 0.55+, or the `.conf` equivalent for older supported versions. The starter uses a US keyboard; change `kb_layout` to `br` if appropriate.

`rice.lua` already autostarts the shell, using `--no-duplicate`. If you prefer launching it from your own `autostart.lua`, pass `autostart = false` in the existing `rice.lua` options and use `hl.exec_cmd("qs -c spidey --no-duplicate")` in your startup handler. Keep one startup entry.

### Optional desktop controls

Install the tools for the controls you want:

```sh
sudo pacman -Syu --needed kitty rofi nemo \
  wireplumber playerctl brightnessctl grim slurp wl-clipboard hyprlock \
  networkmanager nm-connection-editor
```

| Tool | Control |
| --- | --- |
| `kitty`, your existing Brave installation, `nemo` | Default terminal, browser and files. Kitty keeps your normal configuration. |
| `rofi` | APPS launcher with the cyan/navy/pastel theme; Fuzzel and Wofi are fallbacks. |
| `wpctl` from `wireplumber` | Volume and mute, with an existing working PipeWire session. |
| `playerctl` | Playback and metadata from MPRIS players. |
| `brightnessctl` | Backlight controls, subject to hardware and user permissions. |
| `nmcli`, `nm-connection-editor` | Connection names and settings, with an existing NetworkManager service. |
| `grim`, `slurp`, `wl-copy` | Region screenshots and clipboard capture. |
| `hyprlock` | Locking with the bundled cyan/navy config and Arch's PAM setup. |

The rice does not change your network or audio service setup. Missing tools or devices disable the corresponding readings/controls or produce an action message. CPU, RAM, storage and uptime need only Python and Linux's system interfaces.

Run `bash scripts/check-arch.sh --all-tools --session` from your Arch Hyprland desktop to check installed controls and compositor monitor IPC. Audio routing, backlight access, MPRIS and locking still need a direct check on your machine.

## Preferred applications

Edit [quickshell/config/apps.json](quickshell/config/apps.json) to change what the buttons launch. Defaults prefer **Kitty, Brave and Nemo**. Each action contains an ordered list of argument arrays; the first installed executable wins. Files launches a real file manager directly, so your folder MIME association cannot send it to an editor. The top-bar NETWORK button opens your configured network settings app.

For preferences that survive `git pull`, create `~/.config/spidey/apps.json` (or `$XDG_CONFIG_HOME/spidey/apps.json`). Include only the actions you want to replace:

```json
{
  "terminal": [["kitty"]],
  "browser": [["brave"]],
  "files": [["nemo", "{home}"]]
}
```

Available keys are `terminal`, `browser`, `files`, `network`, `launcher` and `lock`. Arguments support `{home}`, `{config}` and `{shell}` path tokens. Keep each argument separate; these commands do not run through a shell. Changes apply on the next click. The provided Hyprland terminal/files/launcher shortcuts use the same preferences after `hyprctl reload`.

APPS opens the bundled [Rofi theme](quickshell/assets/rofi.rasi). Installed desktop entries such as Discord, Obsidian, Spotify and Brave appear in its searchable list. Rofi uses your configured terminal for terminal entries such as Vim. You can replace `launcher` with your own Rofi command or another launcher.

## Brave, YouTube and Spotify media

The dock reads MPRIS sessions through `playerctl`, including Brave sessions named `chromium.instance…`. Playing sessions take priority over paused players. The transport buttons address the exact session displayed in the dock. If several players are playing, selection is stable by player name.

While a YouTube video is playing in Brave, check:

```sh
playerctl --list-all
playerctl --all-players status
playerctl --all-players metadata --format '{{playerName}}: {{title}}'
```

If Brave is absent, the browser is not exporting a media session to your desktop bus. Check its launch arguments and media controls settings for disabled MPRIS/media integration, then restart Brave. Browser flags vary by version; no browser extension is required when MPRIS is available. The bar cannot read video metadata from audio alone. Spotify desktop also works when it exports MPRIS.

## Updating either previous version

Update from this checkout and run the installer; you do not need to stop the old bar yourself:

```sh
git switch main
git pull --ff-only
bash scripts/install.sh --dry-run
bash scripts/install.sh
```

The installer recognizes both previous layouts. It reuses canonical links (including equivalent relative links), backs up aliases to the retired source, and removes only this checkout's retired `spidey-retro`, `hypr-spidey-retro` and `kitty-spidey` links. Unknown files, foreign links and earlier backups stay intact. If you moved to another checkout, use `--backup` for conflicting canonical links rather than deleting your old files.

Recognized `dofile`/`source` lines and plain Quickshell startup/IPC commands are migrated to the current names. Startup commands gain `--no-duplicate`. The former rice's wallpaper startup and Kitty theme include are commented out, leaving other wallpaper and terminal settings alone. Each changed file gets an adjacent `.spidey-backup.<timestamp>.<pid>` copy. External symlinks and complex expressions are left unchanged with a review notice.

On an active Wayland desktop, it stops only verified Spidey instances belonging to this checkout on the current display, reloads Hyprland when available, and starts one current bar if one was already running. Other Quickshell configs and sessions remain running. `--no-restart` updates files without touching live processes or reloading Hyprland. Offline installs update files for your next login. Personal `~/.config/spidey/apps.json` overrides are never replaced.

The old `install-retro.sh` and `quickshell-retro/` paths are retired.

## Controls

| Control | Action |
| --- | --- |
| Top-bar numbered buttons | Switch to workspaces 1–5, including empty workspaces; fewer on narrow screens. |
| Top-bar NETWORK | Open configured network settings. |
| Top-bar UPTIME | Elapsed time as `HH:MM:SS`, or `Nd HH:MM` after a day. |
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
- Reserved edge sizes: `barHeight`, `railReserve` and `dockReserve` in the same theme file (76px top, 100px left and 98px bottom by default).
- Frames/buttons: `quickshell/components/PixelFrame.qml` and `RetroButton.qml`.
- Icons: `quickshell/assets/icons/`; rebuild with `python3 tools/generate-icons.py`.
- Preferred apps: `quickshell/config/apps.json`, or your personal `~/.config/spidey/apps.json` override.
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
