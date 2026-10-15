import QtQuick
import QtQuick.Layouts
import "../services"

PixelFrame {
    id: root
    implicitWidth: 710
    implicitHeight: 78
    fill: Theme.cyan; inset: 11
    RowLayout {
        anchors.fill: parent
        spacing: 8
        RetroButton { width: 48; icon: "previous"; tone: Theme.peach; hint: "Previous track"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-previous") }
        RetroButton { width: 48; icon: Telemetry.data.media.playing ? "pause" : "play"; tone: Theme.coral; hint: "Play / pause"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-play-pause") }
        RetroButton { width: 48; icon: "next"; tone: Theme.peach; hint: "Next track"; available: Telemetry.data.media.available; onClicked: Telemetry.act("media-next") }
        PixelFrame {
            Layout.fillWidth: true; Layout.preferredHeight: 44
            fill: Theme.navy; pixel: 2; inset: 7; shadow: false
            Column {
                anchors.fill: parent; spacing: 2
                Text { width: parent.width; elide: Text.ElideRight; textFormat: Text.PlainText; text: Telemetry.data.media.title || "NO TRANSMISSION"; font.family: Theme.pixel; font.pixelSize: 10; color: Theme.mint }
                Text { width: parent.width; elide: Text.ElideRight; textFormat: Text.PlainText; text: Telemetry.data.media.artist || "OPEN A MEDIA PLAYER"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.cyan }
            }
        }
        RetroButton { label: "APPS"; icon: "grid"; tone: Theme.mint; hint: "Application launcher"; onClicked: Telemetry.act("launcher") }
        RetroButton { icon: "lock"; width: 48; tone: Theme.peach; hint: "Lock session"; onClicked: Telemetry.act("lock") }
    }
}
