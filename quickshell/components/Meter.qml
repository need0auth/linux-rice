import QtQuick
import "../services"

Column {
    id: root
    property string label: "CPU"
    property real value: 0
    property bool available: true
    spacing: 9
    Row {
        width: parent.width
        Text { width: parent.width - reading.width; text: root.label; font.family: Theme.pixel; font.pixelSize: 10; color: Theme.muted }
        Text { id: reading; text: root.available ? Math.round(root.value) + "%" : "N/A"; font.family: Theme.mono; font.pixelSize: 11; color: Theme.text }
    }
    Row {
        width: parent.width
        spacing: 3
        Repeater {
            model: 18
            Rectangle {
                required property int index
                width: (root.width - 51) / 18
                height: 7
                color: root.available && index < Math.round(root.value * 18 / 100) ? Theme.red : "#29242b"
            }
        }
    }
}
