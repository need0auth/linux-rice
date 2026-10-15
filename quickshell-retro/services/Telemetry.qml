pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property var data: ({
        cpu: 0, memory: 0, disk: 0, uptime: 0,
        battery: {present: false, percent: 0, charging: false},
        network: {connected: false, interface: "", name: "CONNECTING"},
        volume: {available: false, percent: 0, muted: false},
        brightness: {available: false, percent: 0},
        media: {available: false, playing: false, title: "No active transmission", artist: "Open a media player"}
    })
    property bool healthy: false
    property string error: "Waiting for telemetry"
    readonly property string script: Quickshell.shellDir + "/scripts/system.py"
    function refresh() { if (!sampler.running) sampler.running = true; }
    function act(name, value) {
        if (TrackerState.demo) { TrackerState.notify("DEMO MODE / actions disabled"); return; }
        if (action.running) return;
        action.command = ["python3", script, "action", name].concat(value === undefined ? [] : [String(value)]);
        action.running = true;
    }
    Process {
        id: sampler
        command: ["python3", root.script].concat(TrackerState.demo ? ["--demo", "snapshot"] : ["snapshot"])
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.data = JSON.parse(text); root.healthy = true; root.error = ""; }
                catch (e) { root.healthy = false; root.error = "Telemetry unavailable: " + e; }
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0) { root.healthy = false; root.error = "Telemetry process failed (" + exitCode + ")"; }
        }
    }
    Process {
        id: action
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!result.success) TrackerState.notify(result.error || "Action unavailable");
                    else root.refresh();
                } catch (e) { TrackerState.notify("Could not read the action result"); }
            }
        }
    }
    Timer { interval: 3000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
}
