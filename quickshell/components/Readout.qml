import QtQuick
import "../services"

PixelFrame {
    id: root
    property string label: "STATUS"
    property string value: "00"
    property string icon: ""
    property color tone: Theme.mint
    fill: tone
    pixel: 2
    inset: 6
    implicitWidth: 112
    implicitHeight: 44
    Row {
        anchors.centerIn: parent
        spacing: 6
        PixelIcon { visible: root.icon !== ""; name: root.icon; anchors.verticalCenter: parent.verticalCenter }
        Column {
            spacing: 1
            Text { text: root.label; color: Theme.ink; opacity: .7; font.family: Theme.pixel; font.pixelSize: 8 }
            Text { text: root.value; color: Theme.ink; font.family: Theme.pixel; font.pixelSize: 11 }
        }
    }
}
