# Artwork and typography

- `wallpaper.png` is original AI-generated artwork made for this project: a charcoal city-grid map, burgundy streets, and a signal-red tracker. It is a fictional graphic, not live geolocation or a map service. The generated original is included without image-processing changes.
- `icons/*.svg` are 23 original 16×16 pixel icons, drawn on an integer grid. Rebuild them with `python3 tools/generate-icons.py` from the repository root. SVG sources have explicit colors and do not require a desktop icon theme.
- `fonts/Silkscreen-Regular.ttf` is Silkscreen by Jason Kottke, distributed under the SIL Open Font License in `fonts/OFL.txt`. Download source: [Google Fonts](https://github.com/google/fonts/tree/main/ofl/silkscreen). The shell loads this bundled font directly; no system font installation is required. Body text uses DejaVu Sans Mono.

This is an unofficial, movie-inspired fan rice. It does not include extracted film or website assets. The reference site could not be fetched from the development environment, so the visual design is an original interpretation.

The animated dashboard map is drawn in `../components/Radar.qml`; it is intentionally labeled **signal visualization**. Live measurements come from the local Linux system and are separate from this decorative map.

| Role | Color |
| --- | --- |
| Desktop | `#090c10` |
| Panel | `#101317` |
| Raised control | `#181d22` |
| Border | `#303239` |
| Signal | `#ff454b` |
| Text | `#ece7df` |
| Muted text | `#92949b` |

Adjust the shell palette in `../services/Theme.qml`. Hyprland, Hyprlock, and Kitty have matching colors in their own configuration files.
