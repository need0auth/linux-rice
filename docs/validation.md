# Validation

## Checks completed in the cloud

- **116 Python and installer tests passed.** Includes migration from both earlier layouts, personal-file/link preservation, dry runs, repeated installation, backups, parsing, missing tools, timeouts, action validation, app preferences, MPRIS session selection, provider-specific workspace dispatch, user-reference upgrades, session-scoped restarts, child-scoped lock assets, staged greeter updates and login service rollback.
- Actual UI rendering, layer-shell panels under headless Sway and dashboard/settings IPC passed with **Quickshell 0.2.1** and current stable **0.3.2**, built from official sources against the cloud machine's **Qt 6.8.2**.
- Demo data and real Linux telemetry were exercised. The decorative tracker collects no location data.
- Layout checks include 1600×1000 and 1366×768; the smaller viewport scrolls to lower controls without reducing their size.
- New spider SVGs were visually inspected; icons parse as XML and regenerate deterministically.
- Bash syntax and Lua API/loading checks passed. Lua bindings match Hyprland 0.56.2 upstream APIs. Actual Hyprland config verification is included in Arch CI.

Screenshots show the 0.3.2 runtime with demo telemetry. Offscreen-mask warnings and an absent Hyprland socket under Sway are expected.

## App actions and browser media

App configuration tests verify Brave preference, direct file-manager launches that avoid folder MIME handlers, personal JSON overrides, literal argument handling, Rofi terminal selection and useful errors for missing network tools. Defaults are Kitty, Brave and Nemo. The provided Hyprland app shortcuts share the same configuration.

An actual Rofi 1.7.5 window rendered the bundled theme under an isolated Xvfb server in the cloud. The public `system.py action launcher` path opened a temporary `Terminal=true` desktop entry in the configured terminal, including an executable path with a space and custom arguments. The portable `tests/integration/rofi.py` retains this check and runs in native Arch CI; it requires `rofi` and `xorg-server-xvfb` when run on Arch. The test isolates display sockets, desktop entries and all config directories. It also checks theme parsing through `-dump-theme`: Rofi 2.0's standalone `-rasi-validate` calls display cleanup before backend initialization and crashes even after the real launcher checks pass.

The portable MPRIS integration test starts its own D-Bus session and exports a playing Brave-style `chromium.instance4242` session beside a paused desktop player. Real `playerctl` commands verify selected browser metadata, transport routing even after the other player starts, title changes, pause state, and disappeared-player handling. This tests actual MPRIS IPC; it does not start a real browser or establish whether your Brave build exports a session.

```sh
sudo pacman -Syu --needed playerctl dbus python-gobject
python3 tests/integration/mpris.py
```

Workspace tests cover Lua and legacy Hyprlang providers, empty numbered workspaces, dispatcher errors and rejected arguments. Actual Quickshell 0.2.1 and 0.3.2 component checks verified readable uptime boundaries and workspace names independent of opaque internal IDs. The retained `tests/integration/topbar.py` checks real component bindings, numbered/selected states, workspace click handlers and the network readout's click handler under an isolated demo runtime. Arch CI runs it. Live workspace changes still need a running Hyprland desktop.

## Window workarea regression

The original left rail and dock used non-exclusive overlay surfaces. An actual tiled test window under Sway occupied `(0, 76, 1600, 924)` on a 1600×1000 display and extended behind both bars.

The corrected layer-shell surfaces reserve 100px on the left and 98px at the bottom. The same test window occupies `(100, 76, 1500, 826)`. At 1366×768 it occupies `(100, 76, 1266, 594)`. Dashboard/settings toggles leave the workarea unchanged; another launch with `--no-duplicate` exits without adding reserved space. A real virtual-pointer check also verified that empty regions around the left rail and bottom dock pass clicks to a floating test window behind them.

The portable regression test starts its own headless Sway server, opens a real tiled Qt window, measures compositor-reported geometry at both resolutions, and checks popup/duplicate behavior. It isolates compositor sockets and stops only its own processes. Arch CI runs it and saves screenshots and geometry JSON:

```sh
sudo pacman -Syu --needed sway grim
python3 tests/integration/wayland_workarea.py
```

## Installing over an older rice

Installer fixtures cover both historical layouts, relative links, canonical aliases to retired sources, foreign replacements, original config backups, dry runs, and repeated upgrades. Reference migration preserves file permissions, CRLF and unrelated bytes; skips external symlinks and complex expressions; and leaves personal app preferences intact. Runtime fixtures verify exact instance IDs, current display and user ownership, deleted source paths, failure recovery and process reuse protection.

The real `tests/integration/upgrade.py` starts its own Sway desktop and both old/current named shells beside an unrelated Quickshell window. It deletes the legacy source directories first to reproduce updating the checkout before running the installer. A dry run leaves the files and instances unchanged. Installation migrates the references, retires old links, preserves backups and preferences, and leaves one current bar plus the original unrelated window. Repeating installation keeps the same configuration and does not create additional backups. Arch CI runs this check and retains command logs and instance IDs.

```sh
python3 tests/integration/upgrade.py
```

## Native Arch Linux

The login checks exercise the real `Quickshell.Services.Greetd` module against a private fake greetd socket. They drive the production inputs through authentication failure, retry, cancel, secret and visible prompts, informational messages and session launch. Responses stay out of logs and files. A separate production preview never connects to the available fake socket. Current Quickshell 0.3.2 passed these checks locally; the real full-screen login surface also rendered under isolated headless Sway. These checks do not authenticate a real PAM account or switch a machine's login manager.

The native workflow additionally runs the actual Hyprlock configuration on a private Sway compositor at 1600×1000 and 1366×768. The test checks the session-lock protocol, artwork placement and wallpaper pixels, without entering a password. To repeat these appearance checks on Arch:

```sh
sudo pacman -Syu --needed hyprlock mesa sway grim
python3 tests/integration/greeter.py
python3 tests/integration/lockscreen.py
```

**Native Arch CI passed** for the workarea fix at commit `af00a3a`: [Arch Linux run #5](https://github.com/need0auth/linux-rice/actions/runs/38863480122). The job installed signed official Arch packages, ran all 35 tests, installed the dotfiles into a temporary config root, verified the Hyprland config as an ordinary user, rendered a 1600×1000 Quickshell preview, exercised dashboard/settings IPC and read live telemetry. It also verified actual tiled-window geometry, popup stability and duplicate-launch behavior at both 1600×1000 and 1366×768. Package versions, logs, screenshots and geometry JSON are recorded in the run's `arch-validation` artifact.

The isolated CI container removes Sway's executable capabilities before running the headless pixman test as an ordinary user. This avoids Docker rejecting execution when the package requests a scheduling capability outside the container's bounding set. It does not change the installed rice or require changes to your Arch desktop.

An official Arch container started from digest `sha256:3c64b538588416593f69a1aebd2f2ec0f2541b29159f32556fa7def2167147a0`, image version `20261011.0.609700`. The target checker identifies Arch and reports missing desktop packages in that minimal image.

The cloud proxy returns HTTP 403 for Arch's package mirrors. Native Arch Qt/Hyprland installation and execution have **not been completed in this cloud instance**. Current-stable Quickshell tests on Debian are recorded separately above; they do not establish native Arch package compatibility. The required official domains were saved in the environment's network draft; saving does not apply it.

The [Arch workflow](../.github/workflows/arch.yml) repeats native package/runtime checks on pushes to `main`, pull requests and manual dispatch. Inspect its current status and `arch-validation` artifact for package versions, config logs and the UI screenshot.

Stable `quickshell` is an official Arch package, as documented in [Quickshell's installation guide](https://quickshell.org/docs/guide/install-setup/). AUR `quickshell-git` is for unreleased builds. Use a full `pacman -Syu` to keep Qt private-ABI dependencies aligned. Pacman resolves the Qt dependencies; no separate mandatory `qt6-wayland` package is assumed for Qt 6.10+.

## Reproduce

Install the README requirements plus the integration-test tools, then run as a normal user:

```sh
sudo pacman -Syu --needed sway grim rofi xorg-server-xvfb playerctl dbus python-gobject hyprlock mesa
bash scripts/check-arch.sh
bash scripts/ci-arch.sh
```

CI uses temporary config/runtime directories and never modifies your live Hyprland configuration. To keep logs/screenshots, set `SPIDEY_ARTIFACT_DIR` to a writable directory.

Inside a real Hyprland session also run `bash scripts/check-arch.sh --all-tools --session` and exercise audio, backlight, media, locking and screenshots directly. A container cannot validate GPU/display behavior or your desktop permissions and services.
