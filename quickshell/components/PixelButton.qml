import QtQuick
import QtQuick.Controls
import "../services"

Rectangle {
    id: root
    property string icon: ""
    property string label: ""
    property string hint: label
    property bool selected: false
    property bool compact: false
    property bool available: true
    signal clicked()
    activeFocusOnTab: available
    implicitHeight: compact ? 30 : 38
    implicitWidth: Math.max(compact ? 30 : 38, content.width + (compact ? 16 : 24))
    color: selected ? Theme.red : (mouse.containsMouse ? "#29252a" : Theme.raised)
    border.width: 1
    border.color: selected || mouse.containsMouse || activeFocus ? Theme.red : Theme.line
    opacity: available ? 1 : 0.38
    Behavior on color { ColorAnimation { duration: 100 } }
    // Cut corners and a stepped inset give the controls their pixel silhouette.
    Rectangle { x: -1; y: -1; width: 3; height: 3; color: Theme.panel }
    Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: -1; anchors.bottomMargin: -1; width: 3; height: 3; color: Theme.panel }
    Row {
        id: content
        anchors.centerIn: parent
        spacing: 9
        PixelIcon { visible: root.icon !== ""; name: root.icon; anchors.verticalCenter: parent.verticalCenter; opacity: root.selected ? 0.95 : 0.85 }
        Text { visible: root.label !== ""; text: root.label; color: root.selected ? Theme.background : Theme.text; font.family: Theme.pixel; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.available ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (root.available) root.clicked()
    }
    ToolTip.visible: mouse.containsMouse && root.hint !== ""
    ToolTip.text: root.hint
    ToolTip.delay: 600
    Accessible.name: hint || label || icon
    Accessible.role: Accessible.Button
    Accessible.onPressAction: if (available) root.clicked()
    Keys.onReturnPressed: if (available) root.clicked()
    Keys.onEnterPressed: if (available) root.clicked()
    Keys.onSpacePressed: if (available) root.clicked()
}
