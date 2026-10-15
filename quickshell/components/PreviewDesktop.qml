import QtQuick
import Quickshell
import "../services"

Item {
    id: root
    Rectangle { anchors.fill: parent; color: "#172942" }
    // A neutral work surface while the wallpaper is deliberately left undecided.
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const c = getContext("2d"); c.reset(); c.fillStyle = "#263b54";
            for (let x = 12; x < width; x += 24)
                for (let y = 12; y < height; y += 24) c.fillRect(x, y, 1, 1);
        }
    }
    TopBar { anchors.top: parent.top; width: parent.width }
    SideBar { x: 18; y: 168 }
    QuickControls { visible: TrackerState.controlsOpen; x: 108; y: 168 }
    TrackerConsole {
        visible: TrackerState.dashboardOpen
        anchors.right: parent.right; anchors.rightMargin: 20
        y: 98; width: 470; height: Math.min(860, root.height - (root.height < 900 ? 118 : 200))
    }
    BottomBar { x: 108; anchors.bottom: parent.bottom; anchors.bottomMargin: 20; width: Math.min(710, root.width - 650) }
    Text { x: 112; y: 112; text: "SPT / PERSONAL TRACKING DEVICE"; color: "#65869f"; font.family: Theme.pixel; font.pixelSize: 10 }
    Text { x: 112; anchors.bottom: parent.bottom; anchors.bottomMargin: 116; text: "UI PREVIEW  //  WALLPAPER NOT SET"; color: "#65869f"; font.family: Theme.pixel; font.pixelSize: 8 }
    Toast { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 110 }
    Timer {
        interval: 2200; running: (Quickshell.env("SPIDEY_SCREENSHOT") || "") !== ""; repeat: false
        onTriggered: root.grabToImage(function(result) {
            const ok = result.saveToFile(Quickshell.env("SPIDEY_SCREENSHOT"));
            console.log(ok ? "SPIDEY_SCREENSHOT_SAVED" : "SPIDEY_SCREENSHOT_FAILED");
            Qt.quit();
        })
    }
}
