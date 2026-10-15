import QtQuick
import Quickshell
import Quickshell.Hyprland
import "services"
import "components"

Scope {
    Variants {
        model: Quickshell.screens
        Scope {
            id: display
            required property var modelData
            PanelWindow {
                screen: display.modelData
                anchors { top: true; left: true; right: true }
                implicitHeight: Theme.barHeight
                color: "transparent"
                TopBar { anchors.fill: parent; monitor: Hyprland.monitorFor(display.modelData) }
            }
            PanelWindow {
                screen: display.modelData
                anchors { left: true; top: true }
                margins { left: 18; top: 168 }
                implicitWidth: 70; implicitHeight: 388
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                SideBar { anchors.fill: parent }
            }
            PanelWindow {
                screen: display.modelData
                visible: TrackerState.controlsOpen
                anchors { left: true; top: true }
                margins { left: 108; top: 168 }
                implicitWidth: Math.min(348, display.modelData.width - 130)
                implicitHeight: Math.min(388, display.modelData.height - 200)
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                QuickControls { anchors.fill: parent }
            }
            PanelWindow {
                screen: display.modelData
                visible: TrackerState.dashboardOpen
                anchors { right: true; top: true }
                margins { right: 20; top: 98 }
                implicitWidth: Math.min(470, display.modelData.width - 40)
                implicitHeight: Math.min(860, display.modelData.height - (display.modelData.height < 900 ? 118 : 200))
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                TrackerConsole { anchors.fill: parent }
            }
            PanelWindow {
                screen: display.modelData
                anchors { left: true; bottom: true }
                margins { left: 108; bottom: 20 }
                implicitWidth: Math.max(480, Math.min(710, display.modelData.width - 650))
                implicitHeight: 78
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                BottomBar { anchors.fill: parent }
            }
            PanelWindow {
                screen: display.modelData
                visible: TrackerState.message !== "" || !Telemetry.healthy
                anchors.bottom: true
                margins.bottom: 110
                implicitWidth: Math.min(620, display.modelData.width - 40)
                implicitHeight: 70
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                Toast { anchors.centerIn: parent }
            }
        }
    }
}
