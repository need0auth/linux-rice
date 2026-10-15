pragma Singleton
import QtQuick
import Quickshell

Singleton {
    readonly property color background: "#090c10"
    readonly property color panel: "#101317"
    readonly property color raised: "#181d22"
    readonly property color line: "#303239"
    readonly property color red: "#ff454b"
    readonly property color redDark: "#411c22"
    readonly property color text: "#ece7df"
    readonly property color muted: "#92949b"
    readonly property color dim: "#575d66"
    readonly property string mono: "DejaVu Sans Mono"
    readonly property string pixel: pixelFont.name
    readonly property int barHeight: 52
    FontLoader { id: pixelFont; source: "../assets/fonts/Silkscreen-Regular.ttf" }
}
