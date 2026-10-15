import QtQuick
import Quickshell
import "services"
import "components"

FloatingWindow {
    title: "SPIDEY TRACKER / Retro UI"
    readonly property int requestedWidth: parseInt(Quickshell.env("SPIDEY_PREVIEW_WIDTH"), 10) || 1600
    readonly property int requestedHeight: parseInt(Quickshell.env("SPIDEY_PREVIEW_HEIGHT"), 10) || 1000
    implicitWidth: requestedWidth > 0 ? requestedWidth : 1600
    implicitHeight: requestedHeight > 0 ? requestedHeight : 1000
    color: "#172942"
    PreviewDesktop { anchors.fill: parent }
}
