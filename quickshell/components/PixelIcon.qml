import QtQuick

Item {
    id: root
    property string name: "radar"
    implicitWidth: 16
    implicitHeight: 16
    Image {
        anchors.fill: parent
        source: root.name ? "../assets/icons/" + root.name + ".svg" : ""
        sourceSize.width: 32
        sourceSize.height: 32
        smooth: false
        fillMode: Image.PreserveAspectFit
    }
}
