import QtQuick
import Quickshell

FloatingWindow {
    id: root
    property var controller: null
    title: "SPIDEY TRACKER / Login preview"
    implicitWidth: parseInt(Quickshell.env("SPIDEY_PREVIEW_WIDTH"), 10) || 1600
    implicitHeight: parseInt(Quickshell.env("SPIDEY_PREVIEW_HEIGHT"), 10) || 1000
    color: GreeterConfig.navy
    GreeterView { id: previewView; anchors.fill: parent; controller: root.controller; preview: true }
    Timer {
        interval: 1800; running: Quickshell.env("SPIDEY_SCREENSHOT") !== ""
        onTriggered: previewView.grabToImage(result => { result.saveToFile(Quickshell.env("SPIDEY_SCREENSHOT")); Qt.quit(); })
    }
}
