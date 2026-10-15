import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import "services"
import "components"

ShellRoot {
    IpcHandler {
        target: "dashboard"
        function toggle(): void { TrackerState.toggle(); }
        function open(): void { TrackerState.dashboardOpen = true; }
        function close(): void { TrackerState.dashboardOpen = false; }
    }
    LazyLoader {
        active: true
        source: TrackerState.preview ? "Preview.qml" : "Desktop.qml"
    }
}
