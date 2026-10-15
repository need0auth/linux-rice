import QtQuick
import "../services"

Item {
    id: root
    clip: true
    property real phase: 0
    property bool animated: true
    NumberAnimation on phase { from: 0; to: 360; duration: 9000; loops: Animation.Infinite; running: root.animated }
    Canvas {
        id: grid
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            c.fillStyle = "#0b0e12"; c.fillRect(0, 0, width, height);
            // Stylized city blocks are an original schematic, not a location feed.
            c.save(); c.translate(width / 2, height / 2); c.rotate(-0.33);
            for (let x = -400; x < 400; x += 27) {
                for (let y = -400; y < 400; y += 19) {
                    const channel = x > -27 && x < 20 + y * 0.12;
                    if (!channel) {
                        c.fillStyle = ((x + y) % 3 === 0) ? "#252229" : "#1a1d24";
                        c.fillRect(x + 3, y + 3, 20, 12);
                    }
                }
            }
            c.restore();
            c.strokeStyle = "#252831"; c.lineWidth = 1;
            for (let x = 0; x < width; x += 24) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, height); c.stroke(); }
            for (let y = 0; y < height; y += 24) { c.beginPath(); c.moveTo(0, y); c.lineTo(width, y); c.stroke(); }
            const cx = width * .5, cy = height * .5;
            c.strokeStyle = "#613039";
            for (let r = 33; r < width * .6; r += 33) { c.beginPath(); c.arc(cx, cy, r, 0, Math.PI * 2); c.stroke(); }
            c.strokeStyle = "#ad434a";
            c.beginPath(); c.moveTo(cx - 8, cy); c.lineTo(cx + 8, cy); c.moveTo(cx, cy - 8); c.lineTo(cx, cy + 8); c.stroke();
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }
    Item {
        width: parent.width; height: parent.height
        rotation: root.phase
        Rectangle {
            x: parent.width / 2; y: parent.height / 2
            width: parent.width * .47; height: 1
            color: Theme.red; opacity: .65
            transformOrigin: Item.Left
        }
    }
    Repeater {
        model: [{x:.31,y:.32}, {x:.72,y:.61}, {x:.62,y:.22}]
        Rectangle {
            required property var modelData
            x: root.width * modelData.x; y: root.height * modelData.y
            width: 4; height: 4; color: Theme.red
            Rectangle { anchors.centerIn: parent; width: 12; height: 12; color: "transparent"; border.color: "#803239" }
        }
    }
    Text { x: 10; y: 9; text: "LOCAL SCAN // 01"; font.family: Theme.mono; font.pixelSize: 9; color: Theme.muted }
    Text { x: 10; anchors.bottom: parent.bottom; anchors.bottomMargin: 9; text: "SIGNAL VISUALIZATION"; font.family: Theme.mono; font.pixelSize: 8; color: Theme.dim }
    Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 9; text: "+ SYSTEM"; font.family: Theme.mono; font.pixelSize: 8; color: Theme.red }
    Rectangle { anchors.fill: parent; color: "transparent"; border.width: 1; border.color: Theme.line }
}
