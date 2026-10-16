import QtQuick
import Quickshell.Services.Greetd

QtObject {
    id: root
    property bool available: Greetd.available && GreeterConfig.valid
    property bool activeSession: false
    property bool waitingForResponse: false
    property bool echoResponse: false
    property bool busy: false
    property bool failed: false
    property string stage: "username"
    property string username: ""
    property string prompt: ""
    property string message: !GreeterConfig.valid ? "Session configuration needs attention."
        : (Greetd.available ? "Your neighborhood is waiting." : "Login service unavailable.")
    signal clearResponse()

    function begin(name) {
        name = name.trim();
        if (!available || busy || activeSession || !name) return;
        username = name;
        failed = false;
        busy = true;
        activeSession = true;
        waitingForResponse = false;
        stage = "waiting";
        message = "Connecting to your session...";
        Greetd.createSession(name);
    }
    function respond(response) {
        if (!waitingForResponse || !activeSession || busy) return;
        waitingForResponse = false;
        busy = true;
        stage = "waiting";
        message = "Checking credentials...";
        Greetd.respond(response);
    }
    function reset() {
        clearResponse();
        waitingForResponse = false;
        busy = false;
        failed = false;
        activeSession = false;
        stage = "username";
        prompt = "";
        message = available ? "Your neighborhood is waiting." : "Login service unavailable.";
        if (Greetd.state !== GreetdState.Inactive) Greetd.cancelSession();
    }
    function fail(message) {
        clearResponse();
        waitingForResponse = false;
        busy = false;
        activeSession = false;
        stage = "username";
        failed = true;
        prompt = "";
        root.message = message || "Authentication failed. Please try again.";
    }
    property Connections transport: Connections {
        target: Greetd
        function onAuthMessage(message, error, responseRequired, echoResponse) {
            if (!root.activeSession) return;
            root.clearResponse();
            root.waitingForResponse = responseRequired;
            root.echoResponse = echoResponse;
            root.failed = error;
            root.busy = !responseRequired;
            root.prompt = responseRequired ? message : "";
            root.message = responseRequired ? "Complete the prompt to continue." : message;
            root.stage = responseRequired ? "challenge" : "waiting";
        }
        function onAuthFailure(message) { root.fail(message || "Authentication failed. Please try again."); }
        function onError(error) { root.fail(error || "Login service error. Please try again."); }
        function onReadyToLaunch() {
            // A cancelled conversation must never turn a late PAM success into a login.
            if (!root.activeSession) {
                Greetd.cancelSession();
                return;
            }
            root.clearResponse();
            root.waitingForResponse = false;
            root.busy = true;
            root.stage = "starting";
            root.message = "Welcome back. Opening Hyprland...";
            Greetd.launch(GreeterConfig.sessionCommand, GreeterConfig.sessionEnvironment);
        }
    }
    property Timer healthCheck: Timer {
        interval: 1000; running: true; repeat: true
        onTriggered: {
            const usable = Greetd.available && GreeterConfig.valid;
            if (root.available && !usable) root.fail("Login service disconnected.");
            root.available = usable;
        }
    }
}
