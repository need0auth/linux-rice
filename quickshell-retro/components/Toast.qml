import QtQuick
import "../services"

PixelFrame {
    visible: TrackerState.message !== "" || !Telemetry.healthy
    fill: Theme.peach; pixel: 2; inset: 10
    implicitWidth: Math.min(620, note.implicitWidth + 38)
    implicitHeight: note.height + 25
    Text {
        id: note
        anchors.centerIn: parent
        width: Math.min(580, implicitWidth)
        text: TrackerState.message || Telemetry.error
        wrapMode: Text.WordWrap
        font.family: Theme.pixel; font.pixelSize: 10; color: Theme.ink
    }
}
