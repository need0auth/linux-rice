import QtQuick
import QtQuick.Layouts
import "../services"

PixelFrame {
    id: root
    implicitWidth: 348
    implicitHeight: 388
    fill: Theme.cyan; inset: 15
    Column {
        anchors.fill: parent
        spacing: 14
        Row {
            width: parent.width
            PixelIcon { name: "settings"; width: 24; height: 24 }
            Text { width: parent.width - 60; text: "  QUICK CONTROLS"; font.family: Theme.pixel; font.pixelSize: 12; color: Theme.ink; anchors.verticalCenter: parent.verticalCenter }
            RetroButton { compact: true; width: 32; height: 30; icon: "close"; iconSize: 18; tone: Theme.coral; hint: "Close quick controls"; onClicked: TrackerState.controlsOpen = false }
        }
        PixelFrame {
            width: parent.width; height: 42; fill: Theme.mint; pixel: 2; inset: 7; shadow: false
            Row {
                anchors.centerIn: parent; spacing: 8
                PixelIcon { name: Telemetry.data.network.connected ? "wifi" : "offline" }
                Text { text: Telemetry.data.network.connected ? "SIGNAL ACQUIRED" : "NO SIGNAL"; font.family: Theme.pixel; font.pixelSize: 11; color: Theme.ink; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        Column {
            width: parent.width; spacing: 7
            Text { text: "AUDIO / " + (Telemetry.data.volume.available ? Math.round(Telemetry.data.volume.percent) + "%" : "UNAVAILABLE"); font.family: Theme.pixel; font.pixelSize: 10; color: Theme.ink }
            Row {
                width: parent.width; spacing: 8
                RetroButton { width: (parent.width - 16) / 3; icon: "minus"; label: "5"; hint: "Volume -5%"; tone: Theme.peach; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-down") }
                RetroButton { width: (parent.width - 16) / 3; icon: Telemetry.data.volume.muted ? "muted" : "volume"; hint: "Mute / unmute"; tone: Theme.coral; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-mute") }
                RetroButton { width: (parent.width - 16) / 3; icon: "plus"; label: "5"; hint: "Volume +5%"; tone: Theme.peach; available: Telemetry.data.volume.available; onClicked: Telemetry.act("volume-up") }
            }
        }
        Column {
            width: parent.width; spacing: 7
            Text { text: "BACKLIGHT / " + (Telemetry.data.brightness.available ? Math.round(Telemetry.data.brightness.percent) + "%" : "UNAVAILABLE"); font.family: Theme.pixel; font.pixelSize: 10; color: Theme.ink }
            Row {
                width: parent.width; spacing: 8
                RetroButton { width: (parent.width - 8) / 2; icon: "brightness"; label: "DIM -"; tone: Theme.mint; available: Telemetry.data.brightness.available; onClicked: Telemetry.act("brightness-down") }
                RetroButton { width: (parent.width - 8) / 2; icon: "brightness"; label: "BRIGHT +"; tone: Theme.mint; available: Telemetry.data.brightness.available; onClicked: Telemetry.act("brightness-up") }
            }
        }
        Row {
            width: parent.width; spacing: 8
            RetroButton { width: (parent.width - 8) / 2; label: "NETWORK"; icon: "wifi"; tone: Theme.peach; onClicked: Telemetry.act("network") }
            RetroButton { width: (parent.width - 8) / 2; label: "LOCK"; icon: "lock"; tone: Theme.coral; onClicked: Telemetry.act("lock") }
        }
        Text { text: TrackerState.demo ? "DEMO SIGNAL / ACTIONS DISABLED" : "LOCAL HARDWARE / LIVE SIGNAL"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink; opacity: .7 }
    }
}
