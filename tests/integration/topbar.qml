// Run through topbar.py, which supplies the real shell's scripts and imports.
import QtQuick
import Quickshell
import "components"
import "services"

ShellRoot {
    id: test

    function verify(condition, message) {
        if (!condition) throw new Error(message);
    }

    function descendants(item) {
        let items = [item];
        for (const child of item.children) items = items.concat(descendants(child));
        return items;
    }

    function check() {
        try {
            verify(TrackerState.demo, "The interaction test must disable real desktop actions");
            const cases = [
                [0, "00:00:00"], [59, "00:00:59"], [3601, "01:00:01"],
                [86399, "23:59:59"], [86400, "1d 00:00"], [90061, "1d 01:01"],
                [-1, "00:00:00"]
            ];
            for (const pair of cases)
                verify(bar.formatUptime(pair[0]) === pair[1], "Readable uptime for " + pair[0]);

            const items = descendants(bar);
            const uptime = items.find(item => item.label === "UPTIME");
            const network = items.find(item => item.label === "NETWORK");
            const workspaces = items.filter(item => /^Workspace [1-5]$/.test(item.hint || ""));
            verify(uptime && uptime.visible, "Uptime is visible at desktop width");
            // Exercise the displayed telemetry binding, beyond the formatter alone.
            Telemetry.data = Object.assign({}, Telemetry.data, {uptime: 90061});
            verify(uptime.value === "1d 01:01", "Uptime readout follows telemetry");
            verify(workspaces.length === 5, "Five desktop workspace buttons");
            for (const button of workspaces)
                verify(button.label === String(button.index + 1), "Workspace label contains only its number");

            const target = workspaces.find(button => button.label === "4");
            if (TrackerState.preview) {
                TrackerState.previewWorkspace = 1;
                target.clicked();
                verify(TrackerState.previewWorkspace === 4, "Workspace click changes the preview workspace");
                verify(target.selected, "Clicked workspace is selected");
                verify(workspaces.every(button => button === target || !button.selected), "Only the current workspace is selected");
            } else {
                // New Hyprland releases expose an opaque address in id. The
                // visible numbered workspace and selected button must use name.
                verify(bar.workspace === "4" && target.selected, "Workspace name takes precedence over opaque id");
                TrackerState.message = "";
                target.clicked();
                verify(TrackerState.message === "DEMO MODE / actions disabled", "Workspace click reaches the desktop action bridge");
            }

            verify(network && network.visible && network.interactive, "Network readout is an interactive control");
            verify(network.activeFocusOnTab, "Network control supports keyboard focus");
            TrackerState.message = "";
            network.clicked();
            verify(TrackerState.message === "DEMO MODE / actions disabled", "Network click reaches the desktop action bridge");
            console.log("TOPBAR_INTERACTIONS_PASSED", TrackerState.preview ? "preview" : "desktop");
            Qt.quit();
        } catch (error) {
            console.error("TOPBAR_INTERACTIONS_FAILED", error.message);
            Qt.exit(1);
        }
    }

    FloatingWindow {
        implicitWidth: 1600
        implicitHeight: 76
        TopBar {
            id: bar
            width: 1600
            monitor: ({activeWorkspace: {name: "4", id: 987654321}})
        }
        Timer { interval: 200; running: true; onTriggered: test.check() }
    }
}
