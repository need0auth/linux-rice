# Development validation

The following checks completed in the development cloud environment:

| Check | Result |
| --- | --- |
| Python bridge and safe-installer integration suite | **28 tests passed**. Covers telemetry parsers, missing tools, timeouts, allowed actions, rejected values, screenshot selection validation, themed config paths, dry runs, repeated installation, conflicts, backups, and preservation of unrelated files. |
| Bash syntax | `install.sh`, `uninstall.sh`, and `wallpaper.sh` passed `bash -n`. |
| Hyprland Lua | Parsed with Lua 5.4. API/schema compared with the official Hyprland v0.56.2 sources. Startup/IPC argument quoting exercised with a mock runner using config paths containing spaces and apostrophes. |
| Quickshell | Official **v0.2.1**, built against **Qt 6.8.2**. Real QML loaded and rendered; bundled SVG icons and font loaded. |
| Preview mode | Offscreen software-rendered 1600×1000 window using demo telemetry and separately using real Linux telemetry. Screenshot output verified. The only remaining offscreen warning concerns unsupported window masks. |
| Dashboard IPC | `open`, `close`, and `toggle` succeeded against the running shell; rendered open/closed output differed as expected. |
| Production panels | `Desktop.qml` bar and dashboard rendered under **Sway 1.10.1** with a headless Wayland backend and pixman. No QML errors. Missing Hyprland socket warning was expected. |
| Artwork | Wallpaper PNG and both screenshots decoded successfully. All **23 SVG icons** parsed as XML. |
| Hyprpaper launcher | Generated the appropriate 0.7 and 0.8 formats against mocked versioned executables; paths containing spaces and temporary-file cleanup checked. |

`desktop.png` shows the real layer-shell layout with demo telemetry. `preview.png` shows the optional windowed presentation. Sample network/media/battery values in those images are labeled **DEMO** in the interface.

The cloud machine does not provide a running Hyprland desktop or laptop hardware. Native Hyprland workspace dispatch, GPU-specific effects, audio routing, backlight permissions, MPRIS player interoperability, actual screenshots and PAM-backed screen locking remain checks for the target machine. Successful headless rendering does not verify those capabilities.

## Reproduce

From the repository root:

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh scripts/uninstall.sh config/hypr/wallpaper.sh
SPIDEY_PREVIEW=1 SPIDEY_DEMO=1 qs -p "$PWD/quickshell"
```

To save a preview on a machine with Quickshell and its Qt dependencies:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  SPIDEY_PREVIEW=1 SPIDEY_DEMO=1 \
  SPIDEY_SCREENSHOT="$PWD/docs/preview.png" qs -p "$PWD/quickshell"
```

The screenshot command exits after capture. To exercise a running instance's IPC, omit `SPIDEY_SCREENSHOT`, leave that instance running, and use another terminal:

```sh
qs -p "$PWD/quickshell" ipc call dashboard close
qs -p "$PWD/quickshell" ipc call dashboard open
qs -p "$PWD/quickshell" ipc call dashboard toggle
```

When installed as the named config, replace `-p "$PWD/quickshell"` with `-c spidey`. The shell defaults to real measurements; only `SPIDEY_DEMO=1` enables sample data and disables desktop actions.

Hyprland API references: [official v0.56.2 example](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua), [configuration bindings](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsConfigRules.cpp), and [dispatch bindings](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp).
