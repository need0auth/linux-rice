import QtQuick
import Quickshell

ShellRoot {
    id: root
    readonly property bool preview: Quickshell.env("SPIDEY_GREETER_PREVIEW") === "1"
    LazyLoader { id: auth; active: true; source: root.preview ? "PreviewController.qml" : "GreetdController.qml" }
    LazyLoader {
        active: auth.item !== null
        source: root.preview ? "Preview.qml" : "Desktop.qml"
        onItemChanged: if (item) item.controller = auth.item
    }
}
