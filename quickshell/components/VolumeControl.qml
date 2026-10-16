import QtQuick
import Quickshell
import "../services"

Item {
    id: root
    objectName: "topbar-volume"
    implicitWidth: 118
    implicitHeight: 36
    property alias popup: volumePopup
    Row {
        anchors.fill: parent
        spacing: 4
        RetroButton {
            objectName: "volume-mute"
            compact: true; width: 86
            icon: Telemetry.data.volume.muted ? "muted" : "volume"
            label: Telemetry.data.volume.available ? Math.round(Telemetry.data.volume.percent) + "%" : "--"
            tone: Theme.peach
            available: Telemetry.data.volume.available
            hint: "Mute / unmute audio"
            onClicked: Telemetry.act("volume-mute")
        }
        RetroButton {
            objectName: "volume-toggle"
            compact: true; width: 28
            label: "v"; tone: Theme.peach
            selected: volumePopup.visible
            hint: "Open volume slider"
            onClicked: volumePopup.visible = !volumePopup.visible
        }
    }
    PopupWindow {
        id: volumePopup
        objectName: "volume-popup"
        property alias panel: volumePanel
        anchor.item: root
        anchor.rect.x: root.width
        anchor.rect.y: root.height + 16
        anchor.rect.width: 1
        anchor.rect.height: 1
        anchor.edges: Edges.Bottom | Edges.Right
        anchor.gravity: Edges.Bottom | Edges.Left
        implicitWidth: 300
        implicitHeight: 156
        color: "transparent"
        // Current Arch supports native outside-click dismissal. Keep the
        // explicit close button usable with the older 0.2.1 comparison build.
        Component.onCompleted: if ("grabFocus" in volumePopup) volumePopup.grabFocus = true
        onVisibleChanged: if (visible) {
            volumePanel.synchronize();
            Qt.callLater(() => volumePanel.slider.forceActiveFocus());
        }
        VolumePanel {
            id: volumePanel
            anchors.fill: parent
            onCloseRequested: volumePopup.visible = false
        }
    }
}
