# Validation

## Checks completed in the cloud

- **35 Python and installer tests passed.** Includes migration from both earlier layouts, personal-file/link preservation, dry runs, repeated installation, backups, parsing, missing tools, timeouts, action validation and lock-config selection.
- Actual UI rendering, layer-shell panels under headless Sway and dashboard/settings IPC passed with **Quickshell 0.2.1** and current stable **0.3.2**, built from official sources against the cloud machine's **Qt 6.8.2**.
- Demo data and real Linux telemetry were exercised. The decorative tracker collects no location data.
- Layout checks include 1600×1000 and 1366×768; the smaller viewport scrolls to lower controls without reducing their size.
- New spider SVGs were visually inspected; icons parse as XML and regenerate deterministically.
- Bash syntax and Lua API/loading checks passed. Lua bindings match Hyprland 0.56.2 upstream APIs. Actual Hyprland config verification is included in Arch CI.

Screenshots show the 0.3.2 runtime with demo telemetry. Offscreen-mask warnings and an absent Hyprland socket under Sway are expected.

## Native Arch Linux

**Native Arch CI passed** for implementation commit `54d14d4`: [Arch Linux run #1](https://github.com/need0auth/linux-rice/actions/runs/38794450322). The job installed signed official Arch packages, ran all 35 tests, installed the dotfiles into a temporary config root, verified the Hyprland config as an ordinary user, rendered a 1600×1000 Quickshell preview, exercised dashboard/settings IPC and read live telemetry. Package versions, logs and the screenshot are recorded in the run's `arch-validation` artifact.

An official Arch container started from digest `sha256:3c64b538588416593f69a1aebd2f2ec0f2541b29159f32556fa7def2167147a0`, image version `20261011.0.609700`. The target checker identifies Arch and reports missing desktop packages in that minimal image.

The cloud proxy returns HTTP 403 for Arch's package mirrors. Native Arch Qt/Hyprland installation and execution have **not been completed in this cloud instance**. Current-stable Quickshell tests on Debian are recorded separately above; they do not establish native Arch package compatibility. The required official domains were saved in the environment's network draft; saving does not apply it.

The [Arch workflow](../.github/workflows/arch.yml) repeats native package/runtime checks on pushes to `main`, pull requests and manual dispatch. Inspect its current status and `arch-validation` artifact for package versions, config logs and the UI screenshot.

Stable `quickshell` is an official Arch package, as documented in [Quickshell's installation guide](https://quickshell.org/docs/guide/install-setup/). AUR `quickshell-git` is for unreleased builds. Use a full `pacman -Syu` to keep Qt private-ABI dependencies aligned. Pacman resolves the Qt dependencies; no separate mandatory `qt6-wayland` package is assumed for Qt 6.10+.

## Reproduce

Install the README requirements on Arch, then run as a normal user:

```sh
bash scripts/check-arch.sh
bash scripts/ci-arch.sh
```

CI uses temporary config/runtime directories and never modifies your live Hyprland configuration. To keep logs/screenshots, set `SPIDEY_ARTIFACT_DIR` to a writable directory.

Inside a real Hyprland session also run `bash scripts/check-arch.sh --all-tools --session` and exercise audio, backlight, media, locking and screenshots directly. A container cannot validate GPU/display behavior or your desktop permissions and services.
