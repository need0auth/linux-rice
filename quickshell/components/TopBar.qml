import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import "../services"

Rectangle {
    id: root
    height: Theme.barHeight
    color: Theme.panel
    property var monitor: null
    property int demoWorkspace: 1
    readonly property int workspace: TrackerState.preview ? demoWorkspace : (monitor && monitor.activeWorkspace ? monitor.activeWorkspace.id : (Hyprland.focusedMonitor && Hyprland.focusedMonitor.activeWorkspace ? Hyprland.focusedMonitor.activeWorkspace.id : 1))
    SystemClock { id: clock; precision: SystemClock.Minutes }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
    Row {
        id: left
        x: 18; height: parent.height; spacing: 18
        Item {
            width: logo.width + 2; height: parent.height
            Row {
                id: logo
                spacing: 10; anchors.verticalCenter: parent.verticalCenter
                PixelIcon { name: "spider"; width: 26; height: 26; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    spacing: 2; anchors.verticalCenter: parent.verticalCenter
                    Text { text: "SPIDEY"; font.family: Theme.pixel; font.pixelSize: 13; color: Theme.text }
                    Text { text: "TRACKER_OS"; font.family: Theme.mono; font.pixelSize: 8; font.letterSpacing: 2; color: Theme.red }
                }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: TrackerState.toggle() }
        }
        Rectangle { width: 1; height: 24; color: Theme.line; anchors.verticalCenter: parent.verticalCenter }
        Row {
            spacing: 5; anchors.verticalCenter: parent.verticalCenter
            Repeater {
                model: 5
                PixelButton {
                    required property int index
                    compact: true
                    label: "0" + (index + 1)
                    hint: "Workspace " + (index + 1)
                    selected: root.workspace === index + 1
                    onClicked: {
                        if (TrackerState.preview) root.demoWorkspace = index + 1;
                        else Hyprland.dispatch("workspace " + (index + 1));
                    }
                }
            }
        }
        Text {
            visible: root.width > 1250
            anchors.verticalCenter: parent.verticalCenter
            text: TrackerState.demo ? "FIELD TEST / DEMO" : "LOCAL SYSTEM / LIVE"
            color: Theme.dim; font.family: Theme.mono; font.pixelSize: 9
        }
    }
    Row {
        visible: root.width > 1480
        anchors.centerIn: parent
        spacing: 7
        Rectangle { width: 4; height: 4; color: Telemetry.healthy ? Theme.red : Theme.dim; anchors.verticalCenter: parent.verticalCenter }
        Text { text: "FRIENDLY NEIGHBORHOOD NETWORK"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 9; font.letterSpacing: 1 }
    }
    Row {
        anchors.right: parent.right; anchors.rightMargin: 16
        height: parent.height; spacing: 14
        Row {
            visible: root.width > 1080
            spacing: 6; anchors.verticalCenter: parent.verticalCenter
            PixelIcon { name: "cpu"; width: 13; height: 13; opacity: .6 }
            Text { text: Math.round(Telemetry.data.cpu) + "%"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10 }
        }
        Item {
            width: networkRow.width; height: parent.height
            Row {
                id: networkRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
                PixelIcon { name: Telemetry.data.network.connected ? "wifi" : "offline"; width: 14; height: 14 }
                Text { visible: root.width > 920; text: Telemetry.data.network.connected ? "LINKED" : "OFFLINE"; color: Theme.muted; font.family: Theme.pixel; font.pixelSize: 10 }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Telemetry.act("network") }
        }
        Item {
            width: audioRow.width; height: parent.height
            Row {
                id: audioRow; spacing: 6; anchors.verticalCenter: parent.verticalCenter
                PixelIcon { name: Telemetry.data.volume.muted ? "muted" : "volume"; width: 14; height: 14 }
                Text { visible: root.width > 820; text: Telemetry.data.volume.available ? Math.round(Telemetry.data.volume.percent) + "%" : "--"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10 }
            }
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: Telemetry.act("volume-mute")
                onWheel: wheel => Telemetry.act(wheel.angleDelta.y > 0 ? "volume-up" : "volume-down")
            }
        }
        Row {
            visible: Telemetry.data.battery.present
            spacing: 6; anchors.verticalCenter: parent.verticalCenter
            PixelIcon { name: Telemetry.data.battery.charging ? "plug" : "battery"; width: 14; height: 14 }
            Text { text: Math.round(Telemetry.data.battery.percent) + "%"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10 }
        }
        Rectangle { width: 1; height: 20; color: Theme.line; anchors.verticalCenter: parent.verticalCenter }
        Column {
            spacing: 1; anchors.verticalCenter: parent.verticalCenter
            Text { text: Qt.formatDateTime(clock.date, "hh:mm"); font.family: Theme.pixel; font.pixelSize: 12; color: Theme.text }
            Text { text: Qt.formatDateTime(clock.date, "ddd dd MMM").toUpperCase(); font.family: Theme.mono; font.pixelSize: 8; color: Theme.dim }
        }
        PixelButton { compact: true; icon: "radar"; hint: "Toggle tracker / Super+D"; selected: TrackerState.dashboardOpen; anchors.verticalCenter: parent.verticalCenter; onClicked: TrackerState.toggle() }
    }
}
