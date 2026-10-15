import QtQuick
import "../services"

Item {
    id: root
    implicitHeight: 322
    clip: true
    property bool terrain: true
    property bool traces: true
    property bool labels: false
    readonly property var signals: [
        {x: .45, y: .35, tone: "#ff958d"}, {x: .54, y: .31, tone: "#ff958d"},
        {x: .58, y: .39, tone: "#ff958d"}, {x: .48, y: .45, tone: "#ff958d"},
        {x: .41, y: .51, tone: "#78ecb6"}, {x: .61, y: .49, tone: "#78ecb6"},
        {x: .53, y: .58, tone: "#ff958d"}, {x: .39, y: .63, tone: "#ff958d"},
        {x: .49, y: .71, tone: "#78ecb6"}, {x: .34, y: .80, tone: "#78ecb6"},
        {x: .57, y: .83, tone: "#78ecb6"}, {x: .73, y: .23, tone: "#b7dce8"},
        {x: .21, y: .66, tone: "#b7dce8"}, {x: .83, y: .75, tone: "#b7dce8"}
    ]
    onTerrainChanged: streets.requestPaint()
    onTracesChanged: streets.requestPaint()
    Canvas {
        id: streets
        anchors.fill: parent
        antialiasing: false
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const c = getContext("2d");
            c.reset();
            const w = width, h = height;
            function line(points, color, size) {
                c.strokeStyle = color; c.lineWidth = size;
                c.beginPath(); c.moveTo(points[0][0] * w, points[0][1] * h);
                for (let i = 1; i < points.length; ++i) c.lineTo(points[i][0] * w, points[i][1] * h);
                c.stroke();
            }
            function land(points, color) {
                c.fillStyle = color;
                c.beginPath(); c.moveTo(points[0][0] * w, points[0][1] * h);
                for (let i = 1; i < points.length; ++i) c.lineTo(points[i][0] * w, points[i][1] * h);
                c.closePath(); c.fill(); c.strokeStyle = "#7888dc"; c.lineWidth = 2; c.stroke();
            }
            c.fillStyle = "#16265e"; c.fillRect(0, 0, w, h);
            // An original, fictional borough schematic. No location is collected.
            land([[.02,0],[.29,0],[.31,.09],[.25,.19],[.22,.31],[.15,.43],[.11,.58],[0,.74],[0,0]], root.terrain ? "#345f9d" : "#2e457e");
            land([[.43,0],[.69,0],[.66,.13],[.74,.22],[.70,.34],[.81,.41],[.80,.52],[1,.62],[1,1],[.12,1],[.20,.86],[.29,.70],[.29,.57],[.37,.43],[.34,.31],[.42,.17]], root.terrain ? "#3265a0" : "#2e457e");
            land([[.75,0],[1,0],[1,.45],[.90,.42],[.85,.30],[.77,.25],[.73,.14]], root.terrain ? "#4075af" : "#2e457e");

            c.save();
            c.beginPath();
            c.moveTo(.43*w,0); c.lineTo(.69*w,0); c.lineTo(.66*w,.13*h); c.lineTo(.74*w,.22*h);
            c.lineTo(.70*w,.34*h); c.lineTo(.81*w,.41*h); c.lineTo(.80*w,.52*h); c.lineTo(w,.62*h);
            c.lineTo(w,h); c.lineTo(.12*w,h); c.lineTo(.20*w,.86*h); c.lineTo(.29*w,.70*h);
            c.lineTo(.29*w,.57*h); c.lineTo(.37*w,.43*h); c.lineTo(.34*w,.31*h); c.lineTo(.42*w,.17*h); c.closePath(); c.clip();
            c.translate(w*.49,h*.54); c.rotate(.36);
            for (let x = -w; x < w; x += 29) {
                for (let y = -h; y < h; y += 24) {
                    c.fillStyle = "#254d88"; c.fillRect(x+3,y+3,23,18);
                    c.strokeStyle = "#6e88bd"; c.lineWidth = 1; c.strokeRect(x+4,y+4,21,16);
                }
            }
            c.strokeStyle = "#142c5c"; c.lineWidth = 5;
            for (let x = -w; x < w; x += 29) { c.beginPath(); c.moveTo(x,-h); c.lineTo(x,h); c.stroke(); }
            for (let y = -h; y < h; y += 24) { c.beginPath(); c.moveTo(-w,y); c.lineTo(w,y); c.stroke(); }
            if (root.terrain) {
                c.strokeStyle = "#5898b2"; c.lineWidth = 2;
                c.strokeRect(45,-25,22,43); c.strokeRect(-36,70,20,44);
                c.fillStyle = "#477c9d"; c.fillRect(46,-24,20,41); c.fillRect(-35,71,18,42);
            }
            c.restore();

            // West-bank roads and two tiny bridge silhouettes.
            for (let i = 0; i < 7; ++i) line([[.01,.18+i*.085],[.18-i*.014,.20+i*.085]], "#657fb6", 2);
            line([[.20,0],[.22,.10],[.17,.27],[.11,.41],[.06,.58]], "#6d88c2", 2);
            line([[.18,.41],[.37,.48]], "#122743", 7);
            line([[.18,.41],[.37,.48]], "#78a6d1", 2);
            line([[.69,.14],[.85,.20]], "#122743", 7);
            line([[.69,.14],[.85,.20]], "#78a6d1", 2);
            if (root.traces) {
                line([[.07,.08],[.06,.25],[.12,.25]], "#7ba4cd", 1);
                line([[.92,.12],[.96,.12],[.96,.37],[.90,.37]], "#7ba4cd", 1);
                line([[.18,.92],[.18,.96],[.51,.96]], "#7ba4cd", 1);
                c.strokeStyle = "#203b76"; c.lineWidth = 1;
                for (let x = 0; x < w; x += 16) for (let y = 0; y < h; y += 16) c.strokeRect(x,y,1,1);
            }
            // Crisp, angular corner guides from a portable tracking screen.
            c.fillStyle = "#8ceaff";
            c.fillRect(7,7,20,2); c.fillRect(7,7,2,15);
            c.fillRect(w-27,7,20,2); c.fillRect(w-9,7,2,15);
            c.fillRect(7,h-9,20,2); c.fillRect(7,h-22,2,15);
            c.fillRect(w-27,h-9,20,2); c.fillRect(w-9,h-22,2,15);
        }
    }

    Repeater {
        model: root.signals
        Item {
            required property var modelData
            x: Math.round(root.width * modelData.x - width/2)
            y: Math.round(root.height * modelData.y - height/2)
            width: 32; height: 32
            PixelIcon {
                anchors.fill: parent
                name: modelData.tone === "#ff958d" ? "spider-coral" : (modelData.tone === "#78ecb6" ? "spider-mint" : "spider-gray")
            }
        }
    }

    // A fixed central target is decoration, rather than a claimed GPS fix.
    Item {
        x: root.width*.52-18; y: root.height*.49-18; width: 36; height: 36
        Rectangle { x: 6; y: 0; width: 24; height: 36; color: Theme.ink }
        Rectangle { x: 0; y: 6; width: 36; height: 24; color: Theme.ink }
        Rectangle { x: 7; y: 4; width: 22; height: 28; color: Theme.peach }
        Rectangle { x: 4; y: 7; width: 28; height: 22; color: Theme.peach }
        Rectangle { x: 12; y: 10; width: 12; height: 16; color: Theme.ink }
        Rectangle { x: 10; y: 12; width: 16; height: 12; color: Theme.ink }
        Rectangle { x: 14; y: 13; width: 8; height: 10; color: Theme.paper }
    }

    Text {
        x: 16; y: 14
        text: root.labels ? "FICTIONAL BOROUGH / NO GPS" : "SPT_1  //  SCHEMATIC"
        color: Theme.cyanLight; font.family: Theme.pixel; font.pixelSize: 8
    }
    Column {
        x: 10; y: 104; spacing: 7
        RetroButton { width: 29; height: 30; compact: true; label: "O"; tone: Theme.coral; selected: root.traces; hint: "Toggle scan overlay"; onClicked: root.traces = !root.traces }
        RetroButton { width: 29; height: 30; compact: true; label: "S"; tone: Theme.coral; selected: root.labels; hint: "Schematic information"; onClicked: root.labels = !root.labels }
        RetroButton { width: 29; height: 30; compact: true; label: "T"; tone: Theme.coral; selected: root.terrain; hint: "Toggle map terrain"; onClicked: root.terrain = !root.terrain }
    }

    PixelFrame {
        x: Math.round(parent.width*.29); y: 36; width: 202; height: 46
        fill: Theme.peach; pixel: 2; inset: 5; shadow: true
        Column {
            anchors.centerIn: parent; spacing: 2
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "SIGHTING IN YOUR"; font.family: Theme.pixel; font.pixelSize: 10; color: Theme.text }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "DIRECT VICINITY"; font.family: Theme.pixel; font.pixelSize: 10; color: Theme.text }
        }
    }
    PixelIcon { x: parent.width*.29+78; y: 14; width: 35; height: 35; name: "mask" }

    Item {
        anchors.right: parent.right; anchors.rightMargin: 12
        anchors.bottom: parent.bottom; anchors.bottomMargin: 22
        width: 74; height: 74
        Canvas {
            anchors.fill: parent
            onPaint: {
                const c = getContext("2d"); c.reset();
                c.fillStyle = "#102346"; c.beginPath(); c.arc(37,37,34,0,Math.PI*2); c.fill();
                c.strokeStyle = "#5c8ebd"; c.lineWidth=1;
                for(let r=12;r<=35;r+=11) { c.beginPath(); c.arc(37,37,r,0,Math.PI*2); c.stroke(); }
                for(let i=0;i<12;i++) { const a=i*Math.PI/6; c.beginPath(); c.moveTo(37,37); c.lineTo(37+35*Math.cos(a),37+35*Math.sin(a)); c.stroke(); }
                c.fillStyle="#78ecb6"; c.fillRect(48,21,4,4); c.fillRect(23,46,3,3);
            }
        }
        PixelIcon { anchors.centerIn: parent; name: "crosshair"; width: 22; height: 22 }
    }
    Text {
        x: 14; anchors.bottom: parent.bottom; anchors.bottomMargin: 12
        text: root.labels ? "ORIGINAL MAP ART / DECORATIVE SIGNALS" : "14 SIGNALS  /  VISUAL SCAN ONLY"
        color: Theme.cyanLight; font.family: Theme.pixel; font.pixelSize: 8
    }
}
