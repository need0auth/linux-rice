import QtQuick
import "../services"

Item {
    id: root
    property string label: "CPU"
    property real value: 0
    property color tone: Theme.mint
    property bool available: true
    implicitWidth: 100
    implicitHeight: 43
    Column {
        anchors.fill: parent
        spacing: 6
        Row {
            width: parent.width
            Text { width: parent.width - reading.width; text: root.label; color: Theme.ink; font.family: Theme.pixel; font.pixelSize: 10 }
            Text { id: reading; text: root.available ? Math.round(root.value) + "%" : "--"; color: Theme.ink; font.family: Theme.pixel; font.pixelSize: 10 }
        }
        Rectangle {
            width: parent.width; height: 21; color: Theme.navy; border.width: 2; border.color: Theme.ink
            Row {
                anchors.fill: parent; anchors.margins: 4; spacing: 3
                Repeater {
                    model: 12
                    Rectangle {
                        required property int index
                        width: (root.width - 8 - 33) / 12; height: 13
                        color: root.available && index < Math.ceil(root.value * .12) ? root.tone : "#334675"
                        Rectangle { width: parent.width; height: 2; color: Qt.lighter(parent.color, 1.35) }
                    }
                }
            }
        }
    }
}
