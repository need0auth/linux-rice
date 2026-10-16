import QtQuick

// This component never imports or contacts Greetd, including when GREETD_SOCK is set.
QtObject {
    property bool available: true
    property bool activeSession: false
    property bool waitingForResponse: false
    property bool echoResponse: false
    property bool busy: false
    property bool failed: false
    property string stage: "username"
    property string username: ""
    property string prompt: ""
    property string message: "Preview only. Authentication is disconnected."
    signal clearResponse()
    function begin(name) { message = "Preview only. Boot login is handled by greetd."; }
    function respond(response) { clearResponse(); }
    function reset() { clearResponse(); message = "Preview only. Authentication is disconnected."; }
}
