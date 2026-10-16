import QtQuick

Item {
    id: root
    property string text: ""
    property color tone: GreeterConfig.peach
    signal clicked()
    implicitWidth: 160; implicitHeight: 48
    activeFocusOnTab: enabled
    opacity: enabled ? 1 : 0.48
    GreeterFrame {
        anchors.fill: parent; anchors.topMargin: mouse.pressed ? 2 : 0; anchors.leftMargin: mouse.pressed ? 2 : 0
        pixel: 2; inset: 6; shadow: !mouse.pressed
        fill: mouse.containsMouse ? Qt.lighter(root.tone, 1.1) : root.tone
        borderColor: root.activeFocus ? GreeterConfig.paper : GreeterConfig.ink
        Text { anchors.centerIn: parent; text: root.text; color: GreeterConfig.ink; font.family: GreeterConfig.pixel; font.pixelSize: 13 }
    }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
    Keys.onReturnPressed: root.clicked()
    Keys.onEnterPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: if (enabled) clicked()
}
