// Fake credentials arrive only through the private test process environment.
// This wrapper drives the production view and GreetdController unchanged.
import QtQuick
import Quickshell

ShellRoot {
    id: test
    property int phase: 0

    function verify(condition, message) {
        if (!condition) throw new Error(message);
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const result = find(child, name);
            if (result) return result;
        }
        return null;
    }
    function step() {
        try {
            const username = find(view, "spidey-username");
            const response = find(view, "spidey-response");
            verify(username && response, "Production authentication inputs exist");
            if (phase === 0 && controller.available) {
                verify(response.text === "", "Secret input starts empty");
                verify(response.echoMode === TextInput.Password, "Secret input masks characters");
                verify(response.passwordMaskDelay === 0, "Secret input never reveals the last character");
                username.text = "  " + Quickshell.env("SPIDEY_GREETER_TEST_USER") + "  ";
                view.submit();
                verify(controller.busy && controller.activeSession, "Username begins authentication");
                phase = 1;
            } else if (phase === 1 && controller.waitingForResponse) {
                verify(controller.prompt === "Fixture rejected password", "First secret prompt is displayed");
                verify(response.enabled && response.echoMode === TextInput.Password, "Secret challenge is masked and enabled");
                response.text = Quickshell.env("SPIDEY_GREETER_TEST_BAD_SECRET");
                verify(response.displayText !== response.text, "Secret challenge hides entered characters");
                view.submit();
                verify(response.text === "", "Secret response clears before transport waits");
                verify(controller.busy && !controller.waitingForResponse, "Duplicate submission is disabled");
                phase = 2;
            } else if (phase === 2 && controller.failed && controller.stage === "username") {
                verify(response.text === "", "Failed authentication clears the response");
                verify(!controller.activeSession && !controller.busy && !controller.waitingForResponse, "Failed authentication permits a fresh session");
                verify(controller.message !== "", "Failed authentication displays feedback");
                view.submit();
                phase = 3;
            } else if (phase === 3 && controller.waitingForResponse) {
                verify(controller.prompt === "Fixture cancel password", "Retry reaches a fresh challenge");
                response.text = Quickshell.env("SPIDEY_GREETER_TEST_CANCEL_SECRET");
                view.reset();
                verify(response.text === "", "Cancel clears the entered response");
                verify(!controller.busy && !controller.activeSession && !controller.waitingForResponse && !controller.failed, "Cancel resets authentication state");
                verify(controller.stage === "username", "Cancel returns to username entry");
                phase = 4;
            } else if (phase === 4) {
                view.submit();
                phase = 5;
            } else if (phase === 5 && controller.waitingForResponse) {
                verify(controller.prompt === "Fixture accepted password", "Final attempt reaches secret challenge");
                verify(response.echoMode === TextInput.Password, "Next attempt keeps password masking");
                response.text = Quickshell.env("SPIDEY_GREETER_TEST_GOOD_SECRET");
                view.submit();
                verify(response.text === "", "Accepted secret clears after submission");
                phase = 6;
            } else if (phase === 6 && controller.waitingForResponse) {
                verify(controller.prompt === "Fixture visible code", "Chained visible challenge is displayed");
                verify(controller.echoResponse && response.echoMode === TextInput.Normal, "Visible PAM challenge uses normal echo");
                verify(response.text === "", "Previous secret is absent from chained prompt");
                response.text = Quickshell.env("SPIDEY_GREETER_TEST_VISIBLE_RESPONSE");
                view.submit();
                verify(response.text === "", "Visible response clears after submission");
                phase = 7;
            } else if (phase === 7 && controller.message === "Fixture authentication information") {
                verify(response.text === "", "Informational prompt retains no response");
                verify(!controller.waitingForResponse && controller.busy, "Informational PAM messages require no user response");
                console.log("GREETER_AUTH_INTERACTIONS_PASSED");
                phase = 8;
            } else if (phase === 8 && controller.stage === "starting") {
                verify(response.text === "", "Session launch retains no response");
                verify(controller.busy && !controller.waitingForResponse, "Launch prevents further submissions");
                phase = 9;
            }
        } catch (error) {
            console.error("GREETER_AUTH_INTERACTIONS_FAILED", "phase", phase, error.message);
            Qt.exit(1);
        }
    }

    GreetdController { id: controller }
    FloatingWindow {
        implicitWidth: 1600
        implicitHeight: 1000
        GreeterView { id: view; anchors.fill: parent; controller: controller }
    }
    Timer { interval: 40; repeat: true; running: true; onTriggered: test.step() }
    Timer {
        interval: 12000; running: true
        onTriggered: {
            console.error("GREETER_AUTH_INTERACTIONS_FAILED", "Timed out at phase", test.phase);
            Qt.exit(1);
        }
    }
}
