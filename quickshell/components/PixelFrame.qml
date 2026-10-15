import QtQuick
import "../services"

Item {
    id: root
    default property alias contentData: content.data
    property color fill: Theme.cyan
    property color borderColor: Theme.ink
    property int pixel: 3
    property int inset: 10
    property bool shadow: true
    implicitWidth: 320
    implicitHeight: 200
    onFillChanged: frame.requestPaint()
    onBorderColorChanged: frame.requestPaint()
    onPixelChanged: frame.requestPaint()
    onShadowChanged: frame.requestPaint()
    data: [
        Canvas {
            id: frame
            anchors.fill: parent
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const c = getContext("2d"); c.reset();
                const p = root.pixel;
                const w = width - (root.shadow ? p : 0), h = height - (root.shadow ? p : 0);
                function shape(x, y, sw, sh, cut, color) {
                    c.fillStyle = color; c.beginPath();
                    c.moveTo(x + cut, y); c.lineTo(x + sw - cut, y);
                    c.lineTo(x + sw - cut, y + cut); c.lineTo(x + sw, y + cut);
                    c.lineTo(x + sw, y + sh - cut); c.lineTo(x + sw - cut, y + sh - cut);
                    c.lineTo(x + sw - cut, y + sh); c.lineTo(x + cut, y + sh);
                    c.lineTo(x + cut, y + sh - cut); c.lineTo(x, y + sh - cut);
                    c.lineTo(x, y + cut); c.lineTo(x + cut, y + cut); c.closePath(); c.fill();
                }
                if (root.shadow) shape(p, p, w, h, p * 2, "#091b35");
                shape(0, 0, w, h, p * 2, root.borderColor);
                shape(p, p, w - p * 2, h - p * 2, p, root.fill);
                c.fillStyle = Qt.lighter(root.fill, 1.32);
                c.fillRect(p * 2, p, w - p * 4, p);
                c.fillRect(p, p * 2, p, h - p * 4);
                c.fillStyle = Qt.darker(root.fill, 1.35);
                c.fillRect(p * 2, h - p * 2, w - p * 4, p);
                c.fillRect(w - p * 2, p * 2, p, h - p * 4);
            }
        },
        Item {
            id: content
            anchors.fill: parent
            anchors.leftMargin: root.inset
            anchors.topMargin: root.inset
            anchors.rightMargin: root.inset + (root.shadow ? root.pixel : 0)
            anchors.bottomMargin: root.inset + (root.shadow ? root.pixel : 0)
        }
    ]
}
