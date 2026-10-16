import QtQuick
import Quickshell
import Quickshell.Wayland

Scope {
    id: root
    property var controller: null
    Variants {
        model: root.controller ? Quickshell.screens : []
        PanelWindow {
            required property var modelData
            screen: modelData
            anchors { top: true; bottom: true; left: true; right: true }
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            WlrLayershell.namespace: "spidey-greeter"
            color: GreeterConfig.navy
            GreeterView { anchors.fill: parent; controller: root.controller }
        }
    }
}
