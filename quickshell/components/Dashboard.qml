import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../services"

Rectangle {
    id: root
    color: Theme.panel
    border.width: 1
    border.color: Theme.line
    implicitWidth: 408
    implicitHeight: 790
    Rectangle { x: 0; y: 0; width: 58; height: 3; color: Theme.red }
    Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: 58; height: 3; color: Theme.red }
    Flickable {
        anchors.fill: parent; anchors.margins: 22
        contentWidth: width
        contentHeight: body.height
        clip: true; boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        Column {
            id: body
            width: parent.width
            spacing: 18
            Row {
                width: parent.width
                Column {
                    width: parent.width - 34; spacing: 6
                    Text { text: "SPIDER TRACKER"; font.family: Theme.pixel; font.pixelSize: 18; color: Theme.text }
                    Text { text: "PERSONAL TERMINAL  /  MK.01"; font.family: Theme.mono; font.pixelSize: 8; font.letterSpacing: 1; color: Theme.dim }
                }
                PixelButton { compact: true; icon: "close"; hint: "Close tracker"; onClicked: TrackerState.toggle() }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            Row {
                width: parent.width
                Row {
                    width: parent.width - status.width; spacing: 7
                    Rectangle { width: 5; height: 5; color: Telemetry.healthy ? Theme.red : Theme.dim; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: TrackerState.demo ? "DEMO SIGNAL" : (Telemetry.healthy ? "SYSTEM CONNECTED" : "CONNECTING"); font.family: Theme.pixel; font.pixelSize: 9; color: Theme.red }
                }
                Text { id: status; text: "CH_001"; font.family: Theme.mono; font.pixelSize: 9; color: Theme.dim }
            }
            Radar { width: parent.width; height: 218 }
            Row {
                width: parent.width
                Column {
                    width: parent.width * .60; spacing: 5
                    Text { text: "NETWORK UPLINK"; font.family: Theme.mono; font.pixelSize: 8; font.letterSpacing: .8; color: Theme.dim }
                    Text { width: parent.width - 10; elide: Text.ElideRight; text: Telemetry.data.network.connected ? (Telemetry.data.network.name || Telemetry.data.network.interface || "CONNECTED") : "NO CONNECTION"; font.family: Theme.pixel; font.pixelSize: 11; color: Theme.text }
                }
                Column {
                    width: parent.width * .40; spacing: 5
                    Text { text: "UPTIME"; font.family: Theme.mono; font.pixelSize: 8; font.letterSpacing: .8; color: Theme.dim }
                    Text { text: Math.floor(Telemetry.data.uptime / 3600) + "H " + Math.floor((Telemetry.data.uptime % 3600) / 60) + "M"; font.family: Theme.pixel; font.pixelSize: 11; color: Theme.text }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            Column {
                width: parent.width; spacing: 14
                SectionLabel { number: "01"; text: "SYSTEM VITALS" }
                Row {
                    width: parent.width; spacing: 18
                    Meter { width: (parent.width - 18) / 2; label: "CPU"; value: Telemetry.data.cpu; available: Telemetry.healthy }
                    Meter { width: (parent.width - 18) / 2; label: "RAM"; value: Telemetry.data.memory; available: Telemetry.healthy }
                }
                Row {
                    width: parent.width; spacing: 18
                    Meter { width: (parent.width - 18) / 2; label: "STORAGE"; value: Telemetry.data.disk; available: Telemetry.healthy }
                    Meter { width: (parent.width - 18) / 2; label: "BATTERY"; value: Telemetry.data.battery.percent; available: Telemetry.data.battery.present }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            Column {
                width: parent.width; spacing: 12
                SectionLabel { number: "02"; text: "TRANSMISSION" }
                Row {
                    width: parent.width; spacing: 10
                    Rectangle {
                        width: 42; height: 42; color: Theme.redDark; border.color: "#633038"
                        Row {
                            anchors.centerIn: parent; spacing: 3
                            Repeater {
                                model: [9, 19, 28, 14, 22]
                                Rectangle { required property var modelData; width: 3; height: modelData; color: Theme.red; anchors.verticalCenter: parent.verticalCenter; opacity: Telemetry.data.media.playing ? 1 : .35 }
                            }
                        }
                    }
                    Column {
                        width: parent.width - 52; spacing: 6; anchors.verticalCenter: parent.verticalCenter
                        Text { width: parent.width; elide: Text.ElideRight; text: Telemetry.data.media.title || "No active transmission"; color: Theme.text; font.family: Theme.mono; font.pixelSize: 11 }
                        Text { width: parent.width; elide: Text.ElideRight; text: Telemetry.data.media.artist || "Open an MPRIS media player"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 9 }
                    }
                }
                Row {
                    width: parent.width; spacing: 7
                    PixelButton { compact: true; icon: "previous"; hint: "Previous track"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-previous") }
                    PixelButton { compact: true; icon: Telemetry.data.media.playing ? "pause" : "play"; hint: "Play / pause"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-play-pause") }
                    PixelButton { compact: true; icon: "next"; hint: "Next track"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-next") }
                    Item { width: Math.max(0, parent.width - 243); height: 1 }
                    PixelButton { compact: true; icon: "minus"; hint: "Volume down"; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-down") }
                    PixelButton { compact: true; icon: Telemetry.data.volume.muted ? "muted" : "volume"; hint: "Mute / unmute"; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-mute") }
                    PixelButton { compact: true; icon: "plus"; hint: "Volume up"; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-up") }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            Column {
                width: parent.width; spacing: 12
                SectionLabel { number: "03"; text: "QUICK DISPATCH" }
                Row {
                    spacing: 7; width: parent.width
                    PixelButton { width: (parent.width - 14) / 3; icon: "terminal"; label: "TERM"; hint: "Open terminal"; onClicked: Telemetry.act("terminal") }
                    PixelButton { width: (parent.width - 14) / 3; icon: "browser"; label: "WEB"; hint: "Open browser"; onClicked: Telemetry.act("browser") }
                    PixelButton { width: (parent.width - 14) / 3; icon: "files"; label: "FILES"; hint: "Open home folder"; onClicked: Telemetry.act("files") }
                }
                Row {
                    spacing: 7; width: parent.width
                    PixelButton { width: (parent.width - 21) / 4; icon: "screenshot"; hint: "Capture selection (grim + slurp)"; onClicked: Telemetry.act("screenshot") }
                    PixelButton { width: (parent.width - 21) / 4; icon: "wifi"; hint: "Network settings"; onClicked: Telemetry.act("network") }
                    PixelButton { width: (parent.width - 21) / 4; icon: "brightness"; hint: "Brightness +5% (right click decreases)"; available: Telemetry.data.brightness.available; onClicked: Telemetry.act("brightness-up"); MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: Telemetry.act("brightness-down") } }
                    PixelButton { width: (parent.width - 21) / 4; icon: "lock"; hint: "Lock session (hyprlock or swaylock)"; onClicked: Telemetry.act("lock") }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            Row {
                width: parent.width
                Text { width: parent.width - 80; text: "WITH GREAT POWER_"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.dim }
                Text { text: "SP//DR 01"; font.family: Theme.mono; font.pixelSize: 8; color: Theme.red }
            }
        }
    }
}
