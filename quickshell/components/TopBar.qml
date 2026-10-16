import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import "../services"

Item {
    id: root
    implicitHeight: Theme.barHeight
    property var monitor: null
    readonly property var activeWorkspace: monitor && monitor.activeWorkspace ? monitor.activeWorkspace : (Hyprland.focusedMonitor ? Hyprland.focusedMonitor.activeWorkspace : null)
    // Workspace names remain stable across Hyprland versions; recent versions use
    // the object's id for an internal address instead of its numbered name.
    readonly property string workspace: TrackerState.preview ? String(TrackerState.previewWorkspace) : (activeWorkspace ? activeWorkspace.name : "1")
    function formatUptime(seconds) {
        const elapsed = Math.max(0, Math.floor(Number(seconds) || 0));
        const days = Math.floor(elapsed / 86400);
        const hours = String(Math.floor(elapsed / 3600) % 24).padStart(2, "0");
        const minutes = String(Math.floor(elapsed / 60) % 60).padStart(2, "0");
        const remainder = String(elapsed % 60).padStart(2, "0");
        return days > 0 ? days + "d " + hours + ":" + minutes : hours + ":" + minutes + ":" + remainder;
    }
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
                        width: 44
                        label: String(index + 1)
                        tone: Theme.coral
                        selected: root.workspace === String(index + 1)
                        hint: "Workspace " + (index + 1)
                        onClicked: {
                            if (TrackerState.preview) TrackerState.previewWorkspace = index + 1;
                            else Telemetry.act("workspace", index + 1);
                        }
                    }
                }
            }
            Item { Layout.fillWidth: true }
            Readout { visible: root.width > 1240; label: "UPTIME"; value: root.formatUptime(Telemetry.data.uptime); implicitWidth: 128; tone: Theme.mint }
            Readout { visible: root.width > 1160; label: "NETWORK"; value: Telemetry.data.network.connected ? "LINKED" : "OFFLINE"; icon: Telemetry.data.network.connected ? "wifi" : "offline"; implicitWidth: 114; interactive: true; hint: "Open network settings"; onClicked: Telemetry.act("network") }
            RetroButton { compact: true; width: 86; icon: Telemetry.data.volume.muted ? "muted" : "volume"; label: Telemetry.data.volume.available ? Math.round(Telemetry.data.volume.percent) + "%" : "--"; tone: Theme.peach; hint: "Mute audio / adjust in controls"; onClicked: Telemetry.act("volume-mute") }
            Readout { visible: Telemetry.data.battery.present && root.width > 1000; label: "POWER"; value: Math.round(Telemetry.data.battery.percent) + "%"; icon: Telemetry.data.battery.charging ? "plug" : "battery"; implicitWidth: 100; tone: Theme.mint }
            Readout { label: Qt.formatDateTime(clock.date, "ddd dd").toUpperCase(); value: Qt.formatDateTime(clock.date, "hh:mm"); implicitWidth: 88; tone: Theme.peach }
            RetroButton { icon: "mask"; hint: "Toggle tracker / Super+D"; width: 48; tone: Theme.coral; selected: TrackerState.dashboardOpen; onClicked: TrackerState.toggle() }
        }
    }
}
