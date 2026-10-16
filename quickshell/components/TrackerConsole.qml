import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../services"

Item {
    id: root
    implicitWidth: 470
    implicitHeight: 810
    readonly property var stats: Telemetry.data
    readonly property string uptime: Math.floor(stats.uptime / 3600) + ":" + String(Math.floor((stats.uptime % 3600) / 60)).padStart(2, "0")
    PixelFrame {
        anchors.fill: parent
        fill: Theme.blue; pixel: 4; inset: 8
        PixelFrame {
            anchors.fill: parent
            fill: Theme.cyan; pixel: 3; inset: 12; shadow: false
            Flickable {
                id: viewport
                anchors.fill: parent
                contentWidth: width
                contentHeight: Math.max(744, height)
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    visible: viewport.contentHeight > viewport.height
                    width: 8
                    background: Rectangle { color: Theme.blue; border.color: Theme.ink; border.width: 1 }
                    contentItem: Rectangle { color: Theme.mint; border.color: Theme.ink; border.width: 1 }
                }
                ColumnLayout {
                width: viewport.width - 12
                height: viewport.contentHeight
                spacing: 9

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 39
                    spacing: 9
                    PixelFrame {
                        Layout.preferredWidth: 41; Layout.preferredHeight: 37
                        fill: Theme.peach; inset: 5; pixel: 2
                        PixelIcon { anchors.centerIn: parent; name: "spider"; width: 28; height: 28 }
                    }
                    Column {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: "SPIDEY TRACKER"; font.family: Theme.pixel; font.pixelSize: 17; color: Theme.text }
                        Text { text: "PERSONAL TRACKING DEVICE // MK.02"; font.family: Theme.pixel; font.pixelSize: 7; color: Theme.text }
                    }
                    RetroButton { Layout.preferredWidth: 31; compact: true; icon: "close"; tone: Theme.coral; hint: "Close tracker"; onClicked: TrackerState.toggle() }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 26
                    spacing: 6
                    PixelFrame {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        fill: Theme.mint; inset: 4; pixel: 2; shadow: false
                        Row {
                            anchors.centerIn: parent; spacing: 5
                            Rectangle { width: 5; height: 5; anchors.verticalCenter: parent.verticalCenter; color: Theme.ink }
                            Text { text: TrackerState.demo ? "DEMO SIGNAL" : (Telemetry.healthy ? "SYSTEM ONLINE" : "CONNECTING"); font.family: Theme.pixel; font.pixelSize: 9; color: Theme.ink }
                        }
                    }
                    PixelFrame {
                        Layout.preferredWidth: 135; Layout.fillHeight: true
                        fill: Theme.mint; inset: 4; pixel: 2; shadow: false
                        Text { anchors.centerIn: parent; text: "UP " + root.uptime + "  //  01"; font.family: Theme.pixel; font.pixelSize: 9; color: Theme.ink }
                    }
                }

                PixelFrame {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 334
                    fill: Theme.purple; inset: 5; pixel: 3; shadow: false
                    RadarMap { anchors.fill: parent }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 23
                    spacing: 7
                    PixelIcon { name: root.stats.network.connected ? "wifi" : "offline"; width: 21; height: 21 }
                    Text {
                        Layout.fillWidth: true
                        text: root.stats.network.connected ? (root.stats.network.name || root.stats.network.interface || "CONNECTED") : "NO UPLINK"
                        elide: Text.ElideRight; textFormat: Text.PlainText; color: Theme.text; font.family: Theme.pixel; font.pixelSize: 9
                    }
                    Text { text: "LOCAL SYSTEM FEED"; color: Theme.text; font.family: Theme.pixel; font.pixelSize: 7 }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 51
                    spacing: 8
                    RetroMeter { Layout.fillWidth: true; label: "CPU"; value: root.stats.cpu; available: Telemetry.healthy; tone: Theme.mint }
                    RetroMeter { Layout.fillWidth: true; label: "RAM"; value: root.stats.memory; available: Telemetry.healthy; tone: Theme.mint }
                    RetroMeter { Layout.fillWidth: true; label: root.stats.battery.present ? "BAT" : "DISK"; value: root.stats.battery.present ? root.stats.battery.percent : root.stats.disk; available: Telemetry.healthy; tone: Theme.peach }
                }

                PixelFrame {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 94
                    fill: Theme.blue; pixel: 2; inset: 7; shadow: false
                    ColumnLayout {
                        anchors.fill: parent; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            PixelIcon { name: "volume"; width: 25; height: 25 }
                            Column {
                                Layout.fillWidth: true; spacing: 2
                                Text { width: parent.width; elide: Text.ElideRight; textFormat: Text.PlainText; text: root.stats.media.title || "NO TRANSMISSION"; font.family: Theme.pixel; font.pixelSize: 9; color: Theme.ink }
                                Text { width: parent.width; elide: Text.ElideRight; textFormat: Text.PlainText; text: root.stats.media.artist || "Open an MPRIS media player"; font.family: Theme.mono; font.pixelSize: 9; color: Theme.ink }
                            }
                            Text { text: root.stats.volume.available ? Math.round(root.stats.volume.percent) + "%" : "--"; font.family: Theme.pixel; font.pixelSize: 11; color: Theme.ink }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 5
                            RetroButton { Layout.fillWidth: true; compact: true; icon: "previous"; tone: Theme.peach; available: root.stats.media.available; hint: "Previous track"; onClicked: Telemetry.act("media-previous", root.stats.media.player) }
                            RetroButton { Layout.fillWidth: true; compact: true; icon: root.stats.media.playing ? "pause" : "play"; tone: Theme.mint; available: root.stats.media.available; hint: "Play or pause"; onClicked: Telemetry.act("media-play-pause", root.stats.media.player) }
                            RetroButton { Layout.fillWidth: true; compact: true; icon: "next"; tone: Theme.peach; available: root.stats.media.available; hint: "Next track"; onClicked: Telemetry.act("media-next", root.stats.media.player) }
                            Item { Layout.preferredWidth: 5 }
                            RetroButton { Layout.fillWidth: true; compact: true; icon: "minus"; tone: Theme.coral; available: root.stats.volume.available; hint: "Volume down"; onClicked: Telemetry.act("volume-down") }
                            RetroButton { Layout.fillWidth: true; compact: true; icon: root.stats.volume.muted ? "muted" : "volume"; tone: Theme.coral; available: root.stats.volume.available; hint: "Toggle mute"; onClicked: Telemetry.act("volume-mute") }
                            RetroButton { Layout.fillWidth: true; compact: true; icon: "plus"; tone: Theme.coral; available: root.stats.volume.available; hint: "Volume up"; onClicked: Telemetry.act("volume-up") }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 13
                    spacing: 8
                    Text { text: "DISPATCH CONTROLS"; font.family: Theme.pixel; font.pixelSize: 9; color: Theme.ink }
                    Rectangle { Layout.fillWidth: true; height: 3; color: Theme.ink }
                    Text { text: "A.1"; font.family: Theme.pixel; font.pixelSize: 9; color: Theme.ink }
                }
                GridLayout {
                    columns: 3
                    Layout.fillWidth: true
                    Layout.preferredHeight: 87
                    rowSpacing: 7; columnSpacing: 7
                    RetroButton { Layout.fillWidth: true; icon: "terminal"; label: "TERM"; tone: Theme.mint; hint: "Open terminal"; onClicked: Telemetry.act("terminal") }
                    RetroButton { Layout.fillWidth: true; icon: "browser"; label: "WEB"; tone: Theme.peach; hint: "Open browser"; onClicked: Telemetry.act("browser") }
                    RetroButton { Layout.fillWidth: true; icon: "files"; label: "FILES"; tone: Theme.peach; hint: "Open file manager"; onClicked: Telemetry.act("files") }
                    RetroButton { Layout.fillWidth: true; icon: "wifi"; label: "LINK"; tone: Theme.mint; hint: "Network settings"; onClicked: Telemetry.act("network") }
                    RetroButton { Layout.fillWidth: true; icon: "screenshot"; label: "SNAP"; tone: Theme.peach; hint: "Capture a screen region"; onClicked: Telemetry.act("screenshot") }
                    RetroButton { Layout.fillWidth: true; icon: "lock"; label: "LOCK"; tone: Theme.coral; hint: "Lock session"; onClicked: Telemetry.act("lock") }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 10
                    Text { text: "GREAT POWER. GREAT RESPONSIBILITY."; font.family: Theme.pixel; font.pixelSize: 7; color: Theme.ink }
                    Item { Layout.fillWidth: true }
                    Text { text: "SP//02"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink }
                }
                }
            }
        }
    }
}
