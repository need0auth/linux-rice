import QtQuick
import Quickshell
import "services"
import "components"

FloatingWindow {
    title: "SPIDEY TRACKER / Desktop preview"
    implicitWidth: 1600
    implicitHeight: 1000
    color: Theme.background
    PreviewDesktop { anchors.fill: parent }
}
