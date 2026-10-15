import QtQuick

Item {
    id: root
    property string name: "mask"
    implicitWidth: 24
    implicitHeight: 24
    Image {
        anchors.fill: parent
        source: root.name ? "../assets/icons/" + root.name + ".svg" : ""
        sourceSize.width: 96
        sourceSize.height: 96
        smooth: false
        fillMode: Image.PreserveAspectFit
    }
}
