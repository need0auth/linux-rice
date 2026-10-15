import QtQuick
import "../services"

PixelFrame {
    id: root
    implicitWidth: 70
    implicitHeight: 388
    fill: Theme.cyan
    inset: 9
    Column {
        anchors.centerIn: parent
        spacing: 9
        RetroButton { width: 48; height: 48; icon: "mask"; iconSize: 32; tone: Theme.coral; hint: "Tracker map"; selected: TrackerState.dashboardOpen; onClicked: TrackerState.toggle() }
        Rectangle { width: 44; height: 3; color: Theme.blue }
        RetroButton { width: 48; height: 44; icon: "terminal"; tone: Theme.coral; hint: "Terminal"; onClicked: Telemetry.act("terminal") }
        RetroButton { width: 48; height: 44; icon: "browser"; tone: Theme.peach; hint: "Browser"; onClicked: Telemetry.act("browser") }
        RetroButton { width: 48; height: 44; icon: "files"; tone: Theme.mint; hint: "Files"; onClicked: Telemetry.act("files") }
        RetroButton { width: 48; height: 44; icon: "screenshot"; tone: Theme.peach; hint: "Capture a region"; onClicked: Telemetry.act("screenshot") }
        Rectangle { width: 44; height: 3; color: Theme.blue }
        RetroButton { width: 48; height: 44; icon: "settings"; tone: Theme.coral; selected: TrackerState.controlsOpen; hint: "Quick controls"; onClicked: TrackerState.controlsOpen = !TrackerState.controlsOpen }
    }
}
