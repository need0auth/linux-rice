pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    readonly property color ink: "#122743"
    readonly property color navy: "#192450"
    readonly property color cyan: "#49c7f4"
    readonly property color cyanLight: "#8ceaff"
    readonly property color coral: "#ff958d"
    readonly property color peach: "#ffd39a"
    readonly property color mint: "#78ecb6"
    readonly property color paper: "#fff0cc"
    readonly property string assetsRoot: Quickshell.env("SPIDEY_GREETER_ASSETS") || (Quickshell.shellDir + "/../quickshell/assets")
    readonly property string wallpaper: Quickshell.env("SPIDEY_GREETER_WALLPAPER") || (Quickshell.shellDir + "/../assets/wallpapers/spidey-city.png")
    readonly property string pixel: pixelFont.name
    readonly property var settings: {
        try { return JSON.parse(sessionFile.text()); }
        catch (_) { return null; }
    }
    readonly property var sessionCommand: settings && validStrings(settings.command, false) ? settings.command : []
    readonly property var sessionEnvironment: settings && validStrings(settings.environment, true) ? settings.environment : []
    readonly property string defaultUser: settings && typeof settings.defaultUser === "string" ? settings.defaultUser.trim() : ""
    readonly property bool valid: sessionCommand.length > 0 && settings && validStrings(settings.environment, true)
    function validStrings(values, allowEmpty) {
        return Array.isArray(values) && (allowEmpty || values.length > 0)
            && values.every(value => typeof value === "string" && value.length > 0 && !/[\u0000\r\n]/.test(value));
    }
    FontLoader { id: pixelFont; source: root.assetsRoot + "/fonts/Silkscreen-Regular.ttf" }
    // Root-owned session preferences only. Credentials never enter this file.
    FileView { id: sessionFile; path: Qt.resolvedUrl("session.json"); blockLoading: true; watchChanges: false }
}
