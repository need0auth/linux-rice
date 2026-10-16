import QtQuick
import QtQuick.Controls
import "../services"

PixelFrame {
    id: root
    property string label: "STATUS"
    property string value: "00"
    property string icon: ""
    property color tone: Theme.mint
    property bool interactive: false
    property string hint: ""
    signal clicked()
    activeFocusOnTab: interactive
    fill: interactive && mouse.containsMouse ? Qt.lighter(tone, 1.10) : tone
    borderColor: activeFocus ? Theme.paper : Theme.ink
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
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.interactive
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    ToolTip {
        visible: root.interactive && mouse.containsMouse && root.hint !== ""
        delay: 650
        text: root.hint
        contentItem: Text { text: root.hint; color: Theme.ink; font.family: Theme.pixel; font.pixelSize: 10 }
        background: Rectangle { color: Theme.paper; border.color: Theme.ink; border.width: 2 }
    }
    Keys.onReturnPressed: if (interactive) root.clicked()
    Keys.onEnterPressed: if (interactive) root.clicked()
    Keys.onSpacePressed: if (interactive) root.clicked()
    Accessible.name: hint || (label + " " + value)
    Accessible.role: interactive ? Accessible.Button : Accessible.StaticText
    Accessible.onPressAction: if (interactive) root.clicked()
}
