// Run with volume.py: all audio commands target its private fake wpctl.
import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import "components"
import "services"

ShellRoot {
    id: test
    property int phase: 0
    property int ticks: 0
    property var control: null
    property var slider: null
    property var events: null
    readonly property bool nativeFocus: control !== null && "grabFocus" in control.popup

    function verify(condition, message) {
        if (!condition) throw new Error(message);
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child, name);
            if (found) return found;
        }
        return null;
    }
    function click(item) {
        verify(item && item.visible, "Visible pointer target");
        const input = Qt.createQmlObject("import QtTest; TestEvent {}", item, "pointer-events");
        verify(input.mouseClick(item, item.width / 2, item.height / 2, Qt.LeftButton, Qt.NoModifier, 0), "Pointer click was delivered");
        input.destroy();
    }
    function drag(values) {
        const handle = slider.handle;
        const start = handle.mapToItem(slider, handle.width / 2, handle.height / 2);
        verify(events.mousePress(slider, start.x, start.y, Qt.LeftButton, Qt.NoModifier, 0), "Slider press was delivered");
        let x = start.x;
        for (const percent of values) {
            x = slider.leftPadding + handle.width / 2 + (slider.availableWidth - handle.width) * percent / 100;
            verify(events.mouseMove(slider, x, slider.height / 2, 0, Qt.LeftButton, Qt.NoModifier), "Slider drag was delivered");
        }
        verify(events.mouseRelease(slider, x, slider.height / 2, Qt.LeftButton, Qt.NoModifier, 0), "Slider release was delivered");
    }
    function key(code) {
        slider.forceActiveFocus();
        verify(events.keyClick(code, Qt.NoModifier, 0), "Keyboard event was delivered");
    }
    function closePopup() {
        // Quickshell 0.2.1 exposes only tooltip-style popups. Its explicit
        // pointer controls remain usable; current Arch supports popup focus.
        if (nativeFocus) key(Qt.Key_Escape);
        else click(find(control.popup.contentItem, "volume-close"));
    }
    function fixture(command) {
        verify(!fixtureAction.running, "Private fixture command is idle");
        fixtureAction.command = ["wpctl"].concat(command);
        fixtureAction.running = true;
    }
    function step() {
        ticks++;
        try {
            if (phase === 0 && Telemetry.data.volume.available) {
                verify(!TrackerState.demo, "Real action bridge is exercised against private fake audio");
                verify(Telemetry.data.volume.percent === 42, "Initial fake audio telemetry arrives");
                control = find(bar, "topbar-volume");
                verify(control, "Production top bar contains the volume control");
                verify(control.height <= bar.height, "Opening the popup does not reserve a second bar");
                click(find(control, "volume-toggle"));
                phase = 1;
            } else if (phase === 1 && control.popup.visible) {
                slider = find(control.popup.contentItem, "volume-slider");
                verify(slider && slider.enabled, "Popup exposes an enabled slider");
                verify(slider.from === 0 && slider.to === 100 && slider.stepSize === 1, "Slider is bounded to integer percentages");
                verify(slider.value === 42, "Slider starts at the actual volume");
                events = Qt.createQmlObject("import QtTest; TestEvent {}", slider, "slider-events");
                const screenshot = Quickshell.env("SPIDEY_VOLUME_SCREENSHOT");
                if (screenshot) control.popup.panel.grabToImage(result => result.saveToFile(screenshot));
                drag([10, 94, 73]);
                phase = 2;
            } else if (phase === 2 && !Telemetry.actionBusy && Telemetry.data.volume.percent === 73) {
                verify(Math.round(slider.value) === 73, "The final drag value reaches actual audio telemetry");
                closePopup();
                phase = 20;
            } else if (phase === 20) {
                verify(!control.popup.visible, "Popup closes before using the top-bar mute button");
                click(find(control, "volume-mute"));
                phase = 21;
            } else if (phase === 21 && Telemetry.actionBusy) {
                click(find(control, "volume-toggle"));
                phase = 22;
            } else if (phase === 22 && control.popup.visible) {
                drag([88, 3, 27]);
                verify(Math.round(slider.value) === 27, "Drag remains interactive during a pending mute");
                phase = 3;
            } else if (phase === 3 && !Telemetry.actionBusy && Telemetry.data.volume.muted && Telemetry.data.volume.percent === 27) {
                verify(Math.round(slider.value) === 27, "Last drag survives another action and the subsequent telemetry refresh");
                if (nativeFocus) {
                    key(Qt.Key_Home);
                    key(Qt.Key_Left);
                } else drag([0]);
                verify(slider.value === 0, "Slider lower bound is zero");
                phase = 4;
            } else if (phase === 4 && !Telemetry.actionBusy && Telemetry.data.volume.percent === 0) {
                if (nativeFocus) {
                    key(Qt.Key_End);
                    key(Qt.Key_Right);
                } else drag([100]);
                verify(slider.value === 100, "Slider upper bound is 100");
                phase = 5;
            } else if (phase === 5 && !Telemetry.actionBusy && Telemetry.data.volume.percent === 100) {
                fixture(["fixture-external", "19"]);
                phase = 6;
            } else if (phase === 6 && !fixtureAction.running) {
                Telemetry.refresh();
                phase = 7;
            } else if (phase === 7 && Telemetry.data.volume.percent === 19) {
                verify(slider.value === 19, "Idle slider follows external volume changes");
                closePopup();
                phase = 8;
            } else if (phase === 8) {
                verify(!control.popup.visible, "Popup closes after external volume changes");
                click(find(control, "volume-toggle"));
                phase = 9;
            } else if (phase === 9 && control.popup.visible) {
                verify(slider.value === 19, "Reopening retains current audio telemetry");
                fixture(["fixture-unavailable"]);
                phase = 10;
            } else if (phase === 10 && !fixtureAction.running) {
                Telemetry.refresh();
                phase = 11;
            } else if (phase === 11 && !Telemetry.data.volume.available) {
                verify(!slider.enabled, "Missing audio device disables the slider");
                verify(!find(control, "volume-mute").available, "Missing audio device disables mute");
                click(slider);
                click(find(control.popup.contentItem, "volume-close"));
                phase = 12;
            } else if (phase === 12) {
                verify(!control.popup.visible, "Close button hides the popup");
                console.log("VOLUME_INTERACTIONS_PASSED", nativeFocus ? "native-focus" : "legacy-pointer");
                Qt.quit();
            }
            if (ticks > 400) throw new Error("Interaction fixture timed out");
        } catch (error) {
            console.error("VOLUME_INTERACTIONS_FAILED", "phase", phase, error.message);
            Qt.exit(1);
        }
    }

    Process { id: fixtureAction }
    FloatingWindow {
        id: window
        implicitWidth: 1600
        implicitHeight: 400
        TopBar { id: bar; width: 1600; monitor: ({activeWorkspace: {name: "1", id: 1}}) }
    }
    Timer { interval: 40; running: true; repeat: true; onTriggered: test.step() }
}
