import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import "../services"

Item {
    id: root
    implicitHeight: Theme.barHeight
    property var monitor: null
    readonly property int workspace: TrackerState.preview ? TrackerState.previewWorkspace : (monitor && monitor.activeWorkspace ? monitor.activeWorkspace.id : (Hyprland.focusedMonitor && Hyprland.focusedMonitor.activeWorkspace ? Hyprland.focusedMonitor.activeWorkspace.id : 1))
    SystemClock { id: clock; precision: SystemClock.Minutes }
    PixelFrame {
        anchors.fill: parent
        anchors.topMargin: 8; anchors.leftMargin: 12; anchors.rightMargin: 12
        fill: Theme.cyan; inset: 11
        RowLayout {
            anchors.fill: parent
            spacing: 12
            Row {
                spacing: 8
                PixelIcon { name: "spider"; width: 40; height: 40; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    anchors.verticalCenter: parent.verticalCenter; spacing: 2
                    Text { text: "SPIDEY TRACKER"; font.family: Theme.pixel; font.pixelSize: 13; color: Theme.ink }
                    Text { text: TrackerState.demo ? "DEMO / RETRO EDITION" : "LOCAL / RETRO EDITION"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink; opacity: .75 }
                }
            }
            Rectangle { Layout.preferredWidth: 3; Layout.preferredHeight: 34; color: Theme.blue }
            Row {
                spacing: 5
                Repeater {
                    model: root.width < 1100 ? 3 : 5
                    RetroButton {
                        required property int index
                        width: root.width < 1250 ? 50 : 82
                        label: root.width < 1250 ? "0" + (index + 1) : "PROF " + (index + 1)
                        tone: Theme.coral
                        selected: root.workspace === index + 1
                        hint: "Workspace " + (index + 1)
                        onClicked: {
                            if (TrackerState.preview) TrackerState.previewWorkspace = index + 1;
                            else Hyprland.dispatch("workspace " + (index + 1));
                        }
                    }
                }
            }
            Item { Layout.fillWidth: true }
            Readout { visible: root.width > 1420; label: "UPTIME"; value: "0x" + Math.floor(Telemetry.data.uptime).toString(16).toUpperCase().padStart(6, "0"); implicitWidth: 128; tone: Theme.mint }
            Readout { visible: root.width > 1160; label: "NETWORK"; value: Telemetry.data.network.connected ? "LINKED" : "OFFLINE"; icon: Telemetry.data.network.connected ? "wifi" : "offline"; implicitWidth: 114 }
            RetroButton { compact: true; width: 86; icon: Telemetry.data.volume.muted ? "muted" : "volume"; label: Telemetry.data.volume.available ? Math.round(Telemetry.data.volume.percent) + "%" : "--"; tone: Theme.peach; hint: "Mute audio / adjust in controls"; onClicked: Telemetry.act("volume-mute") }
            Readout { visible: Telemetry.data.battery.present && root.width > 1000; label: "POWER"; value: Math.round(Telemetry.data.battery.percent) + "%"; icon: Telemetry.data.battery.charging ? "plug" : "battery"; implicitWidth: 100; tone: Theme.mint }
            Readout { label: Qt.formatDateTime(clock.date, "ddd dd").toUpperCase(); value: Qt.formatDateTime(clock.date, "hh:mm"); implicitWidth: 88; tone: Theme.peach }
            RetroButton { icon: "mask"; hint: "Toggle tracker / Super+D"; width: 48; tone: Theme.coral; selected: TrackerState.dashboardOpen; onClicked: TrackerState.toggle() }
        }
    }
}
