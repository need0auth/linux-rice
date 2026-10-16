pragma Singleton
import QtQuick
import Quickshell

Singleton {
    readonly property color ink: "#122743"
    readonly property color navy: "#192450"
    readonly property color map: "#16265e"
    readonly property color cyan: "#49c7f4"
    readonly property color cyanLight: "#8ceaff"
    readonly property color blue: "#348cd5"
    readonly property color purple: "#7888dc"
    readonly property color coral: "#ff958d"
    readonly property color peach: "#ffd39a"
    readonly property color mint: "#78ecb6"
    readonly property color green: "#34cf8b"
    readonly property color paper: "#fff0cc"
    readonly property color text: "#132946"
    readonly property color muted: "#59759b"
    readonly property string mono: "DejaVu Sans Mono"
    readonly property string pixel: pixelFont.name
    readonly property int barHeight: 76
    readonly property int railWidth: 70
    readonly property int railMargin: 18
    readonly property int railReserve: railMargin + railWidth + 12
    readonly property int dockHeight: 78
    readonly property int dockMargin: 20
    readonly property int dockReserve: dockHeight + dockMargin
    FontLoader { id: pixelFont; source: "../assets/fonts/Silkscreen-Regular.ttf" }
}
