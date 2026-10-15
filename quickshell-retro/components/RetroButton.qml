import QtQuick
import QtQuick.Controls
import "../services"

Item {
    id: root
    property string label: ""
    property string icon: ""
    property string hint: label
    property color tone: Theme.peach
    property bool selected: false
    property bool available: true
    property bool compact: false
    property int iconSize: 24
    signal clicked()
    implicitWidth: Math.max(compact ? 38 : 44, contents.implicitWidth + 26)
    implicitHeight: compact ? 36 : 44
    activeFocusOnTab: available
    opacity: available ? 1 : .45
    PixelFrame {
        anchors.fill: parent
        anchors.topMargin: mouse.pressed ? 2 : 0
        anchors.leftMargin: mouse.pressed ? 2 : 0
        fill: selected ? Theme.mint : (mouse.containsMouse ? Qt.lighter(root.tone, 1.10) : root.tone)
        borderColor: root.activeFocus ? Theme.paper : Theme.ink
        pixel: 2
        inset: 6
        shadow: !mouse.pressed
        Row {
            id: contents
            anchors.centerIn: parent
            spacing: 6
            PixelIcon { visible: root.icon !== ""; name: root.icon; width: root.iconSize; height: root.iconSize; anchors.verticalCenter: parent.verticalCenter }
            Text { visible: root.label !== ""; text: root.label; font.family: Theme.pixel; font.pixelSize: root.compact ? 10 : 11; color: Theme.ink; anchors.verticalCenter: parent.verticalCenter }
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: available ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (root.available) root.clicked()
    }
    ToolTip {
        visible: mouse.containsMouse && root.hint !== ""
        delay: 650
        text: root.hint
        font.family: Theme.pixel
        font.pixelSize: 10
        contentItem: Text { text: root.hint; color: Theme.ink; font.family: Theme.pixel; font.pixelSize: 10 }
        background: Rectangle { color: Theme.paper; border.color: Theme.ink; border.width: 2 }
    }
    Keys.onReturnPressed: if (available) root.clicked()
    Keys.onEnterPressed: if (available) root.clicked()
    Keys.onSpacePressed: if (available) root.clicked()
    Accessible.name: hint || label || icon
    Accessible.role: Accessible.Button
    Accessible.onPressAction: if (available) root.clicked()
}
