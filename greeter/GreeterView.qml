import QtQuick
import QtQuick.Controls
import Quickshell

Item {
    id: root
    required property var controller
    property bool preview: false
    property bool capsKeySeen: false
    readonly property bool challenge: controller && controller.stage === "challenge"
    onControllerChanged: Qt.callLater(focusInput)
    function focusInput() {
        if (challenge) response.forceActiveFocus();
        else if (controller && !controller.busy) username.forceActiveFocus();
    }
    function submit() {
        if (!controller || controller.busy || !controller.available) return;
        if (challenge) {
            const answer = response.text;
            response.clear();
            controller.respond(answer);
        } else controller.begin(username.text);
    }
    function reset() {
        response.clear();
        capsKeySeen = false;
        controller.reset();
        username.forceActiveFocus();
    }
    Image { anchors.fill: parent; source: GreeterConfig.wallpaper; fillMode: Image.PreserveAspectCrop; smooth: false }
    Rectangle { anchors.fill: parent; color: "#96122443" }
    Canvas {
        anchors.fill: parent; opacity: 0.13
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const c = getContext("2d"); c.reset(); c.strokeStyle = "#8ceaff"; c.lineWidth = 1;
            for (let x = 0; x < width; x += 64) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, height); c.stroke(); }
            for (let y = 0; y < height; y += 64) { c.beginPath(); c.moveTo(0, y); c.lineTo(width, y); c.stroke(); }
        }
    }
    SystemClock { id: clock; precision: SystemClock.Minutes }
    Column {
        x: 32; y: 28; spacing: 8
        Text { text: "SPIDEY TRACKER"; font.family: GreeterConfig.pixel; font.pixelSize: 17; color: GreeterConfig.cyanLight }
        Text { text: "NEIGHBORHOOD ACCESS TERMINAL"; font.family: GreeterConfig.pixel; font.pixelSize: 10; color: GreeterConfig.paper }
    }
    Column {
        anchors.right: parent.right; anchors.rightMargin: 32; y: 26; spacing: 6
        Text { anchors.right: parent.right; text: Qt.formatDateTime(clock.date, "HH:mm"); font.family: GreeterConfig.pixel; font.pixelSize: 28; color: GreeterConfig.paper }
        Text { anchors.right: parent.right; text: Qt.formatDateTime(clock.date, "ddd, dd MMM").toUpperCase(); font.family: GreeterConfig.pixel; font.pixelSize: 10; color: GreeterConfig.cyanLight }
    }
    GreeterFrame {
        id: card
        objectName: "spidey-login-card"
        anchors.centerIn: parent
        width: 560; height: 584; inset: 18; pixel: 4
        scale: Math.min(1, (root.width - 40) / width, (root.height - 150) / height)
        fill: GreeterConfig.cyan
        Column {
            anchors.fill: parent; spacing: 14
            Row {
                width: parent.width; spacing: 14
                Image { source: GreeterConfig.assetsRoot + "/icons/spider.svg"; width: 72; height: 72; smooth: false; sourceSize.width: 72; sourceSize.height: 72 }
                Column {
                    anchors.verticalCenter: parent.verticalCenter; spacing: 9
                    Text { text: "WELCOME BACK,"; color: GreeterConfig.ink; font.family: GreeterConfig.pixel; font.pixelSize: 19 }
                    Text { text: "NEIGHBOR."; color: GreeterConfig.ink; font.family: GreeterConfig.pixel; font.pixelSize: 27 }
                }
            }
            GreeterFrame {
                width: parent.width; height: 42; fill: GreeterConfig.peach; pixel: 2; inset: 8
                Text { anchors.centerIn: parent; text: root.preview ? "DESIGN PREVIEW / LOGIN DISCONNECTED" : "IDENTIFY YOURSELF TO ENTER THE CITY"; font.family: GreeterConfig.pixel; font.pixelSize: 11; color: GreeterConfig.ink }
            }
            GreeterFrame {
                width: parent.width; height: 274; fill: GreeterConfig.navy; pixel: 3; inset: 18
                Column {
                    anchors.fill: parent; spacing: 10
                    Text { text: "01 / USERNAME"; font.family: GreeterConfig.pixel; font.pixelSize: 11; color: GreeterConfig.cyanLight }
                    TextField {
                        id: username
                        objectName: "spidey-username"
                        width: parent.width; height: 48
                        text: GreeterConfig.defaultUser
                        placeholderText: "your username"
                        enabled: !!root.controller && !root.controller.activeSession && !root.controller.busy
                        font.family: GreeterConfig.pixel; font.pixelSize: 17
                        color: GreeterConfig.ink; placeholderTextColor: "#59759b"; selectionColor: GreeterConfig.cyan
                        leftPadding: 12; rightPadding: 12; maximumLength: 128
                        selectByMouse: true; persistentSelection: false
                        inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                        background: Rectangle { color: GreeterConfig.paper; border.width: 3; border.color: username.activeFocus ? GreeterConfig.cyanLight : GreeterConfig.ink }
                        onAccepted: root.submit()
                        KeyNavigation.tab: root.challenge ? response : connectButton
                        Accessible.name: "Username"
                    }
                    Text {
                        text: root.challenge ? (root.controller.echoResponse ? "02 / RESPONSE" : "02 / SECRET RESPONSE") : "02 / AUTHENTICATION"
                        font.family: GreeterConfig.pixel; font.pixelSize: 11; color: GreeterConfig.cyanLight
                    }
                    TextField {
                        id: response
                        objectName: "spidey-response"
                        width: parent.width; height: 48
                        enabled: root.challenge && !root.controller.busy
                        echoMode: root.challenge && root.controller.echoResponse ? TextInput.Normal : TextInput.Password
                        passwordCharacter: "●"; passwordMaskDelay: 0
                        placeholderText: root.challenge ? root.controller.prompt.replace(/\s+/g, " ").trim() : "Enter username to continue"
                        font.family: "DejaVu Sans Mono"; font.pixelSize: 16
                        color: GreeterConfig.ink; placeholderTextColor: "#59759b"; selectionColor: GreeterConfig.cyan
                        leftPadding: 12; rightPadding: 12; maximumLength: 4096
                        selectByMouse: false; persistentSelection: false
                        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                            | (root.challenge && root.controller.echoResponse ? Qt.ImhNone : Qt.ImhHiddenText)
                        background: Rectangle { color: enabled ? GreeterConfig.paper : "#a9becb"; border.width: 3; border.color: response.activeFocus ? GreeterConfig.cyanLight : GreeterConfig.ink }
                        onAccepted: root.submit()
                        KeyNavigation.tab: connectButton
                        Accessible.name: root.challenge && root.controller.echoResponse ? "Authentication response" : "Secret authentication response"
                    }
                    Text {
                        objectName: "spidey-login-status"
                        width: parent.width; height: 50
                        text: root.capsKeySeen ? "CAPS LOCK CHANGED. CHECK LETTER CASE." : (root.controller ? root.controller.message : "Connecting...")
                        wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
                        font.family: GreeterConfig.pixel; font.pixelSize: 10
                        color: root.controller && root.controller.failed ? GreeterConfig.coral : GreeterConfig.paper
                    }
                }
            }
            Row {
                width: parent.width; spacing: 10
                GreeterButton {
                    id: connectButton
                    objectName: "spidey-login-submit"
                    width: parent.width - resetButton.width - parent.spacing; height: 50
                    tone: GreeterConfig.mint
                    text: root.controller && root.controller.busy ? "CONNECTING..." : (root.challenge ? "AUTHENTICATE >" : "CONNECT >")
                    enabled: !!root.controller && root.controller.available && !root.controller.busy && (root.challenge || username.text.trim() !== "")
                    onClicked: root.submit()
                    KeyNavigation.tab: resetButton
                }
                GreeterButton {
                    id: resetButton
                    objectName: "spidey-login-reset"
                    width: 132; height: 50; text: "RESET"; tone: GreeterConfig.coral
                    enabled: !!root.controller && root.controller.stage !== "starting"
                    onClicked: root.reset()
                    KeyNavigation.tab: root.challenge ? response : username
                }
            }
            Row {
                width: parent.width
                Text { width: parent.width / 2; text: "SESSION / HYPRLAND"; font.family: GreeterConfig.pixel; font.pixelSize: 10; color: GreeterConfig.ink }
                Text { width: parent.width / 2; horizontalAlignment: Text.AlignRight; text: "ENTER > CONNECT"; font.family: GreeterConfig.pixel; font.pixelSize: 10; color: GreeterConfig.ink }
            }
        }
    }
    Text {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 26; anchors.horizontalCenter: parent.horizontalCenter
        text: root.preview ? "PREVIEW ONLY / NO PASSWORDS ARE AUTHENTICATED" : "FRIENDLY NEIGHBORHOOD SECURITY / ESC TO RESET"
        font.family: GreeterConfig.pixel; font.pixelSize: 10; color: GreeterConfig.cyanLight
    }
    Connections {
        target: root.controller
        function onClearResponse() { response.clear(); root.capsKeySeen = false; }
        function onStageChanged() { Qt.callLater(root.focusInput); }
    }
    Keys.onEscapePressed: root.reset()
    Keys.onPressed: event => {
        if (event.key === Qt.Key_CapsLock) root.capsKeySeen = true;
    }
    Component.onCompleted: Qt.callLater(root.focusInput)
}
