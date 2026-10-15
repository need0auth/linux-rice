import QtQuick
import Quickshell
import "../services"

Item {
    id: root
    Rectangle { anchors.fill: parent; color: Theme.background }
    Image { anchors.fill: parent; source: "../assets/wallpaper.png"; fillMode: Image.PreserveAspectCrop }
    Rectangle { anchors.fill: parent; color: "#20000000" }
    // A desktop-only concept presentation; live mode draws panels over your apps.
    Column {
        x: 62; y: parent.height * .23; spacing: 20
        Text { text: "EST. QUEENS, NY  /  40.7282 N"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 2 }
        Text { text: "YOUR FRIENDLY\nNEIGHBORHOOD\nDESKTOP."; color: Theme.text; font.family: Theme.pixel; font.pixelSize: Math.min(37, root.width / 41); lineHeight: 1.18 }
        Row {
            spacing: 10
            Rectangle { width: 25; height: 2; color: Theme.red; anchors.verticalCenter: parent.verticalCenter }
            Text { text: "A LITTLE MORE AMAZING."; color: Theme.red; font.family: Theme.mono; font.pixelSize: 11; font.letterSpacing: 2 }
        }
        Text { text: "HYPRLAND + QUICKSHELL\nPIXEL BY PIXEL. BLOCK BY BLOCK."; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10; lineHeight: 1.8 }
        Row {
            spacing: 8
            PixelButton { icon: "radar"; label: "TRACKER"; selected: TrackerState.dashboardOpen; onClicked: TrackerState.toggle() }
            PixelButton { icon: "grid"; label: "APPS"; onClicked: Telemetry.act("launcher") }
        }
    }
    Column {
        x: 62; anchors.bottom: parent.bottom; anchors.bottomMargin: 58; spacing: 10
        Text { text: "[ 01 ]   LOCAL SYSTEM"; font.family: Theme.pixel; font.pixelSize: 10; color: Theme.text }
        Text { text: "NO SUPERPOWERS REQUIRED."; font.family: Theme.mono; font.pixelSize: 9; color: Theme.dim; font.letterSpacing: 1 }
    }
    TopBar { width: parent.width }
    Dashboard { visible: TrackerState.dashboardOpen; anchors.right: parent.right; anchors.top: parent.top; anchors.rightMargin: 24; anchors.topMargin: 76; width: 408; height: Math.min(850, root.height - 104) }
    Toast { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 20 }
    Timer {
        interval: 2200; running: (Quickshell.env("SPIDEY_SCREENSHOT") || "") !== ""; repeat: false
        onTriggered: root.grabToImage(function(result) {
            const ok = result.saveToFile(Quickshell.env("SPIDEY_SCREENSHOT"));
            console.log(ok ? "SPIDEY_SCREENSHOT_SAVED" : "SPIDEY_SCREENSHOT_FAILED");
            Qt.quit();
        })
    }
}
