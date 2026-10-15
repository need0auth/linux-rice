import QtQuick
import "../services"

Rectangle {
    visible: TrackerState.message !== "" || !Telemetry.healthy
    color: Theme.panel; border.color: Theme.red; border.width: 1
    implicitWidth: Math.min(600, note.implicitWidth + 36)
    implicitHeight: note.height + 24
    Text {
        id: note
        anchors.centerIn: parent
        width: Math.min(560, implicitWidth)
        text: TrackerState.message || Telemetry.error
        wrapMode: Text.WordWrap
        color: Theme.text; font.family: Theme.mono; font.pixelSize: 11
    }
}
