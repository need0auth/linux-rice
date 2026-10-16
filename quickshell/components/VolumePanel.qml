import QtQuick
import QtQuick.Controls
import "../services"

PixelFrame {
    id: root
    implicitWidth: 300; implicitHeight: 156
    fill: Theme.cyan; inset: 14
    property int level: Math.round(Telemetry.data.volume.percent)
    property int requestedVolume: -1
    property alias slider: levelSlider
    signal closeRequested()

    function synchronize() {
        if (!levelSlider.pressed && requestedVolume < 0 && !Telemetry.actionBusy)
            level = Math.round(Telemetry.data.volume.percent);
    }
    function requestVolume(value) {
        if (!Telemetry.data.volume.available) return;
        level = Math.max(0, Math.min(100, Math.round(value)));
        requestedVolume = level;
        commit.restart();
    }
    // Coalesce pointer motion and retain the final value while another action
    // is running. Telemetry's shared action process must not drop the release.
    Timer {
        id: commit
        interval: 120
        onTriggered: {
            if (!Telemetry.data.volume.available) {
                root.requestedVolume = -1;
                root.synchronize();
            } else if (Telemetry.actionBusy) restart();
            else {
                Telemetry.act("volume-set", root.requestedVolume);
                root.requestedVolume = -1;
            }
        }
    }
    Connections {
        target: Telemetry
        function onDataChanged() { root.synchronize(); }
    }
    Keys.onEscapePressed: root.closeRequested()
    Column {
        anchors.fill: parent
        spacing: 10
        Row {
            width: parent.width; height: 30
            Text {
                width: parent.width - 38
                anchors.verticalCenter: parent.verticalCenter
                text: !Telemetry.data.volume.available ? "AUDIO / UNAVAILABLE"
                    : (Telemetry.data.volume.muted ? "MUTED / " : "VOLUME / ") + root.level + "%"
                font.family: Theme.pixel; font.pixelSize: 11; color: Theme.ink
            }
            RetroButton {
                objectName: "volume-close"
                compact: true; width: 30; height: 30
                icon: "close"; iconSize: 18; tone: Theme.coral
                hint: "Close volume slider / Escape"
                onClicked: root.closeRequested()
                KeyNavigation.tab: levelSlider
            }
        }
        Slider {
            id: levelSlider
            objectName: "volume-slider"
            width: parent.width; height: 44
            from: 0; to: 100; stepSize: 1
            snapMode: Slider.SnapAlways
            value: root.level
            enabled: Telemetry.data.volume.available
            opacity: enabled ? 1 : .45
            padding: 10
            wheelEnabled: true
            onMoved: root.requestVolume(value)
            Keys.onPressed: event => {
                if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
                    root.requestVolume(event.key === Qt.Key_Home ? 0 : 100);
                    event.accepted = true;
                }
            }
            Accessible.name: "Output volume"
            Accessible.description: "Adjust volume from 0 to 100 percent"
            background: Rectangle {
                x: levelSlider.leftPadding
                y: levelSlider.topPadding + (levelSlider.availableHeight - height) / 2
                width: levelSlider.availableWidth; height: 12
                color: Theme.navy; border.width: 2; border.color: Theme.ink
                Rectangle {
                    x: 2; y: 2; height: parent.height - 4
                    width: (parent.width - 4) * levelSlider.visualPosition
                    color: Telemetry.data.volume.muted ? Theme.muted : Theme.mint
                }
                Repeater {
                    model: 11
                    Rectangle {
                        required property int index
                        x: 2 + (parent.width - 6) * index / 10
                        y: 2; width: 2; height: parent.height - 4
                        color: Theme.ink; opacity: .45
                    }
                }
            }
            handle: PixelFrame {
                x: levelSlider.leftPadding + levelSlider.visualPosition * (levelSlider.availableWidth - width)
                y: levelSlider.topPadding + (levelSlider.availableHeight - height) / 2
                width: 20; height: 28
                fill: levelSlider.pressed ? Theme.mint : Theme.peach
                borderColor: levelSlider.activeFocus ? Theme.paper : Theme.ink
                pixel: 2; inset: 3
            }
        }
        Row {
            width: parent.width
            Text { width: 30; text: "0"; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink }
            Text { width: parent.width - 72; text: "DRAG / ARROWS"; horizontalAlignment: Text.AlignHCenter; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink }
            Text { width: 42; text: "100%"; horizontalAlignment: Text.AlignRight; font.family: Theme.pixel; font.pixelSize: 8; color: Theme.ink }
        }
    }
}
