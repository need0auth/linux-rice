import QtQuick
import Quickshell
import Quickshell.Hyprland
import "services"
import "components"

Scope {
    Variants {
        model: Quickshell.screens
        PanelWindow {
            required property var modelData
            screen: modelData
            anchors { top: true; left: true; right: true }
            implicitHeight: Theme.barHeight
            color: "transparent"
            TopBar { anchors.fill: parent; monitor: Hyprland.monitorFor(modelData) }
        }
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            required property var modelData
            screen: modelData
            visible: TrackerState.dashboardOpen
            anchors { top: true; right: true }
            margins { top: 20; right: 20 }
            implicitWidth: Math.min(408, modelData.width - 40)
            implicitHeight: Math.min(850, modelData.height - 104)
            exclusiveZone: 0
            color: "transparent"
            Dashboard { anchors.fill: parent }
        }
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            required property var modelData
            screen: modelData
            anchors { bottom: true }
            margins.bottom: 24
            visible: TrackerState.message !== "" || !Telemetry.healthy
            implicitWidth: Math.min(600, modelData.width - 40)
            implicitHeight: 64
            exclusiveZone: 0
            color: "transparent"
            Toast { anchors.centerIn: parent }
        }
    }
}
