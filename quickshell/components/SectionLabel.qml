import QtQuick
import "../services"

Row {
    property string text: ""
    property string number: "01"
    spacing: 9
    Rectangle { width: 3; height: 12; color: Theme.red; anchors.verticalCenter: parent.verticalCenter }
    Text { text: parent.number; font.family: Theme.mono; font.pixelSize: 10; color: Theme.red; anchors.verticalCenter: parent.verticalCenter }
    Text { text: parent.text; font.family: Theme.pixel; font.pixelSize: 11; color: Theme.text; anchors.verticalCenter: parent.verticalCenter }
}
