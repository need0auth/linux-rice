pragma Singleton
import QtQuick
import Quickshell

Singleton {
    readonly property bool preview: Quickshell.env("SPIDEY_PREVIEW") === "1"
    readonly property bool demo: Quickshell.env("SPIDEY_DEMO") === "1"
    property bool dashboardOpen: true
    property string message: ""
    function toggle() { dashboardOpen = !dashboardOpen; }
    function notify(text) { message = text; dismiss.restart(); }
    Timer { id: dismiss; interval: 4200; onTriggered: TrackerState.message = "" }
}
