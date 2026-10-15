import QtQuick
import Quickshell
import Quickshell.Io
import "services"

ShellRoot {
    IpcHandler {
        target: "dashboard"
        function toggle(): void { TrackerState.toggle(); }
        function open(): void { TrackerState.dashboardOpen = true; }
        function close(): void { TrackerState.dashboardOpen = false; }
        function controls(): void { TrackerState.controlsOpen = !TrackerState.controlsOpen; }
    }
    LazyLoader {
        active: true
        source: TrackerState.preview ? "Preview.qml" : "Desktop.qml"
    }
}
