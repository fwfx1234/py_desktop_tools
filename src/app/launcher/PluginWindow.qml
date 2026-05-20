import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../ui"
import "../theme"

Window {
    id: pluginWin

    property string pluginId: ""
    property string pluginName: ""
    property string qmlPage: ""
    property var pluginData: ({})
    property int initialWidth: 800
    property int initialHeight: 600
    property bool alwaysOnTop: false
    property bool isMacos: typeof app !== "undefined" && app ? app.isMacos : false
    property bool retainOnClose: true
    signal retainedCloseRequested(string pluginId)

    width: 800
    height: 600
    minimumWidth: 800
    minimumHeight: 480
    title: pluginName || "插件"
    color: Theme.token("color-bg-page", dark)
    flags: ((isMacos && alwaysOnTop) ? Qt.Tool : Qt.Window) | (alwaysOnTop ? Qt.WindowStaysOnTopHint : 0)

    readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false
    readonly property bool pluginPageReady: pageLoader.status === Loader.Ready
    readonly property int pluginPageStatus: pageLoader.status

    // 加载插件页面
    function pluginPageUrl(page) {
        if (!page || page.length === 0) return ""
        if (
            page.indexOf("file:///") === 0
            || page.indexOf("qrc:/") === 0
            || page.indexOf("http://") === 0
            || page.indexOf("https://") === 0
        ) {
            return page
        }
        return Qt.resolvedUrl("../../" + page)
    }

    function applyInitialSize(windowWidth, windowHeight) {
        initialWidth = Math.max(480, windowWidth || 800)
        initialHeight = Math.max(360, windowHeight || 600)
        width = initialWidth
        height = initialHeight
    }

    Component.onCompleted: applyInitialSize(initialWidth, initialHeight)

    onClosing: function(close) {
        // The runtime now keeps sessions warm for a short retention window.
        // When retainOnClose is enabled we intercept the native window close,
        // hide the surface, and let Python move the session into retained state.
        if (!retainOnClose)
            return
        close.accepted = false
        pluginWin.hide()
        pluginWin.retainedCloseRequested(pluginWin.pluginId)
    }

    FocusScope {
        anchors.fill: parent
        focus: true
        Keys.priority: Keys.AfterItem

        Loader {
            id: pageLoader
            anchors.fill: parent
            anchors.margins: 4
            active: qmlPage.length > 0
            asynchronous: true
            source: pluginWin.pluginPageUrl(qmlPage)
        }
    }

    // Ctrl+W / Esc 关闭
    Shortcut {
        sequence: "Ctrl+W"
        onActivated: pluginWin.close()
    }

    Shortcut {
        sequence: "Esc"
        onActivated: pluginWin.close()
    }
}
