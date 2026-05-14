import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../ui"
import "../theme"

Window {
    id: launcher
    objectName: "launcherWindow"

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"

    readonly property int defaultWindowWidth: 800
    readonly property int defaultWindowHeight: 600
    readonly property int inputHeight: 44
    readonly property int rowHeight: 56
    readonly property int rowSpacing: 2
    readonly property int maxListRows: 8
    readonly property int pluginListCount: (
        typeof launcherBridge !== "undefined"
        && launcherBridge
        && launcherBridge.pluginListItems
    ) ? launcherBridge.pluginListItems.length : 0
    readonly property int pluginListRows: Math.max(1, Math.min(pluginListCount, maxListRows))
    readonly property int pluginListContentHeight: (
        pluginListRows * rowHeight
        + Math.max(0, pluginListRows - 1) * rowSpacing
    )
    readonly property int pluginListWindowHeight: (
        8 + inputHeight + 4 + pluginListContentHeight + 8
    )

    width: defaultWindowWidth
    height: (mixedMode && mixedPluginMode === "list")
        ? pluginListWindowHeight
        : defaultWindowHeight

    readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false
    readonly property bool hasBridge: typeof launcherBridge !== "undefined" && launcherBridge
    readonly property var safeSearchResults: hasBridge ? launcherBridge.searchResults : []
    readonly property var safePluginListItems: hasBridge ? launcherBridge.pluginListItems : []
    readonly property var safeAllPlugins: hasBridge ? launcherBridge.allPlugins : []

    // retainedInlineHosts caches QML host objects by plugin id. A host may be
    // hidden for minutes and then shown again without destroying the page Loader.
    property var retainedInlineHosts: ({})
    property bool mixedMode: false
    property string mixedPluginId: ""
    property string mixedPluginMode: ""
    property bool suppressPluginInputEdit: false

    Item {
        focus: true
        Keys.onEscapePressed: {
            if (launcher.mixedMode) {
                launcher.exitMixedMode()
            } else {
                launcher.hide()
            }
        }
    }

    onActiveChanged: {
        if (!active && !mixedMode) {
            hideTimer.start()
        }
    }

    Timer {
        id: hideTimer
        interval: 150
        onTriggered: launcher.hide()
    }

    onVisibleChanged: {
        if (visible) {
            searchInput.clear()
            searchInput.forceActiveFocus()
            if (hasBridge) launcherBridge.performSearch("")
            exitMixedMode(false)
        } else if (mixedMode) {
            exitMixedMode(true)
        }
    }

    Connections {
        target: hasBridge ? launcherBridge : null

        function onRetainedPluginExpired(pluginId) {
            launcher.destroyInlineHost(pluginId)
        }
    }

    Component {
        id: retainedInlineHostComponent

        FocusScope {
            property string pluginId: ""
            property string pageUrl: ""

            anchors.fill: parent
            visible: false
            focus: visible
            Keys.priority: Keys.AfterItem
            Keys.onEscapePressed: function(event) {
                launcher.exitMixedMode(true)
                event.accepted = true
            }

            Loader {
                id: retainedLoader
                anchors.fill: parent
                active: true
                visible: active
                clip: true
                asynchronous: true
                source: pageUrl
            }
        }
    }

    function activateItem(itemData) {
        var src = itemData.source || "plugin"
        var id = itemData.id || ""
        if (!hasBridge) return
        if (src === "plugin") {
            launcherBridge.launchItemWithInput(id, src, searchInput.text)
        } else if (src === "system" || src === "app") {
            launcherBridge.launchItem(id, src)
            launcher.hide()
        }
    }

    function openPluginFromHotkey(pluginId) {
        if (!hasBridge) return
        if (mixedMode) {
            exitMixedMode(true)
        }
        searchInput.clear()
        searchInput.forceActiveFocus()
        launcherBridge.launchPlugin(pluginId)
    }

    function enterMixedMode(pluginId) {
        enterPluginMode(pluginId, "inline_view", "", false, "")
    }

    function findPluginPage(pluginId) {
        var plugins = safeSearchResults
        for (var i = 0; i < plugins.length; i++) {
            if (plugins[i].id === pluginId || plugins[i].pluginId === pluginId) {
                return plugins[i].qmlPage || ""
            }
        }
        var allPlugins = safeAllPlugins || []
        for (var j = 0; j < allPlugins.length; j++) {
            if (allPlugins[j].id === pluginId || allPlugins[j].pluginId === pluginId) {
                return allPlugins[j].qmlPage || ""
            }
        }
        return ""
    }

    function ensureInlineHost(pluginId, qmlPage) {
        var host = retainedInlineHosts[pluginId]
        if (host)
            return host
        host = retainedInlineHostComponent.createObject(inlineHostStack, {
            "pluginId": pluginId,
            "pageUrl": pluginPageUrl(qmlPage)
        })
        retainedInlineHosts[pluginId] = host
        return host
    }

    function hideAllInlineHosts() {
        for (var key in retainedInlineHosts) {
            if (!retainedInlineHosts.hasOwnProperty(key))
                continue
            var host = retainedInlineHosts[key]
            if (host)
                host.visible = false
        }
    }

    function showInlineHost(pluginId, qmlPage) {
        var page = qmlPage || findPluginPage(pluginId)
        if (!page || page.length === 0)
            return
        var host = ensureInlineHost(pluginId, page)
        hideAllInlineHosts()
        host.visible = true
        host.forceActiveFocus()
    }

    function retainInlineHost(pluginId) {
        var host = retainedInlineHosts[pluginId]
        if (host)
            host.visible = false
    }

    function destroyInlineHost(pluginId) {
        var host = retainedInlineHosts[pluginId]
        if (!host)
            return
        host.destroy()
        delete retainedInlineHosts[pluginId]
    }

    function detachInlinePlugin(pluginId) {
        retainInlineHost(pluginId)
        mixedMode = false
        mixedPluginId = ""
        mixedPluginMode = ""
        pluginListView.visible = false
        resultsList.visible = true
        searchInput.forceActiveFocus()
        if (hasBridge) launcherBridge.performSearch(searchInput.text)
    }

    function enterPluginMode(pluginId, pluginMode, pluginInputText, clearInputAfterEnter, explicitQmlPage) {
        mixedMode = true
        mixedPluginId = pluginId
        mixedPluginMode = pluginMode || "inline_view"

        var nextInputText = pluginInputText || ""
        if (clearInputAfterEnter === true) {
            setSearchInputSilently("")
        } else if (nextInputText.length > 0 && searchInput.text !== nextInputText) {
            searchInput.text = nextInputText
        }

        resultsList.visible = false
        pluginListView.visible = mixedPluginMode === "list"
        hideAllInlineHosts()

        if (mixedPluginMode === "inline_view") {
            showInlineHost(pluginId, explicitQmlPage)
        }
    }

    function setSearchInputSilently(text) {
        suppressPluginInputEdit = true
        searchInput.text = text || ""
        suppressPluginInputEdit = false
    }

    function invokeInlinePluginAction(action, value) {
        var host = retainedInlineHosts[mixedPluginId]
        if (!host || !host.children || host.children.length === 0)
            return false
        var loader = host.children[0]
        if (!loader || !loader.item)
            return false
        if (action === "activate" && typeof loader.item.activateSelection === "function") {
            return !!loader.item.activateSelection()
        }
        if (action === "move" && typeof loader.item.moveSelection === "function") {
            return !!loader.item.moveSelection(value)
        }
        return false
    }

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

    function exitMixedMode(shouldSuspend) {
        var closingPluginId = mixedPluginId
        var closingPluginMode = mixedPluginMode

        if (closingPluginMode === "inline_view" && closingPluginId.length > 0) {
            retainInlineHost(closingPluginId)
        }

        mixedMode = false
        mixedPluginId = ""
        mixedPluginMode = ""
        pluginListView.visible = false
        resultsList.visible = true
        searchInput.forceActiveFocus()

        if (closingPluginId.length > 0 && hasBridge && shouldSuspend !== false) {
            if (closingPluginMode === "list") {
                launcherBridge.suspendPlugin(closingPluginId, "list")
            } else if (closingPluginMode === "inline_view") {
                launcherBridge.suspendPlugin(closingPluginId, "inline")
            }
        }
        if (hasBridge) launcherBridge.performSearch(searchInput.text)
    }

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: Theme.token("color-bg-surface", dark)
        border.color: Theme.token("color-border-default", dark)
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 4

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: launcher.inputHeight
                radius: 8
                color: Theme.token("color-bg-subtle", dark)

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    UiIcon {
                        Layout.preferredWidth: 18
                        Layout.preferredHeight: 18
                        Layout.alignment: Qt.AlignVCenter
                        name: "qta:fa5s.search"
                        color: Theme.token("color-text-regular", dark)
                        iconSize: 18
                    }

                    TextField {
                        id: searchInput
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        placeholderText: "搜索功能..."
                        font.pixelSize: 16
                        font.family: "IBM Plex Sans"
                        color: Theme.token("color-text-primary", dark)
                        placeholderTextColor: Theme.token("color-text-regular", dark)
                        background: null
                        verticalAlignment: TextInput.AlignVCenter

                        onTextChanged: {
                            if (suppressPluginInputEdit) return
                            if (!hasBridge) return
                            if (mixedMode && mixedPluginId) {
                                launcherBridge.setPluginInput(mixedPluginId, text)
                            } else {
                                launcherBridge.performSearch(text)
                            }
                        }

                        Keys.onReturnPressed: {
                            if (mixedMode && mixedPluginMode === "list") {
                                var pluginItem = pluginListView.currentItem
                                if (pluginItem) pluginItem.activated()
                                return
                            }
                            if (mixedMode && mixedPluginMode === "inline_view") {
                                launcher.invokeInlinePluginAction("activate", 0)
                                return
                            }
                            if (mixedMode) return
                            var item = resultsList.currentItem
                            if (item) item.activated()
                        }
                        Keys.onUpPressed: {
                            if (mixedMode && mixedPluginMode === "list") {
                                if (pluginListView.currentIndex > 0) pluginListView.decrementCurrentIndex()
                                return
                            }
                            if (mixedMode && mixedPluginMode === "inline_view") {
                                launcher.invokeInlinePluginAction("move", -1)
                                return
                            }
                            if (mixedMode) return
                            if (resultsList.currentIndex > 0) {
                                resultsList.decrementCurrentIndex()
                            }
                        }
                        Keys.onDownPressed: {
                            if (mixedMode && mixedPluginMode === "list") {
                                if (pluginListView.currentIndex < pluginListView.count - 1) pluginListView.incrementCurrentIndex()
                                return
                            }
                            if (mixedMode && mixedPluginMode === "inline_view") {
                                launcher.invokeInlinePluginAction("move", 1)
                                return
                            }
                            if (mixedMode) return
                            if (resultsList.currentIndex < resultsList.count - 1) {
                                resultsList.incrementCurrentIndex()
                            }
                        }
                        Keys.onEscapePressed: {
                            if (mixedMode) {
                                exitMixedMode(true)
                            } else {
                                launcher.hide()
                            }
                        }
                    }

                    Button {
                        id: detachButton
                        visible: mixedMode && mixedPluginMode === "inline_view"
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        padding: 0
                        hoverEnabled: true

                        ToolTip.visible: hovered
                        ToolTip.delay: 250
                        ToolTip.text: "在独立窗口打开"

                        background: Rectangle {
                            radius: 6
                            color: detachButton.down
                                ? Theme.token("color-border-default", launcher.dark)
                                : (detachButton.hovered
                                    ? Theme.token("color-bg-subtle-2", launcher.dark)
                                    : "transparent")
                        }

                        contentItem: Item {
                            UiIcon {
                                anchors.centerIn: parent
                                width: 16
                                height: 16
                                name: "mdi6.open-in-new"
                                color: Theme.token("color-text-regular", launcher.dark)
                                iconSize: 16
                            }
                        }

                        onClicked: {
                            if (hasBridge && mixedPluginId.length > 0) {
                                launcherBridge.detachPluginToWindow(mixedPluginId)
                            }
                        }
                    }
                }
            }

            Rectangle {
                visible: !mixedMode
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.token("color-border-default", dark)
            }

            ListView {
                id: resultsList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 2
                model: launcher.safeSearchResults
                currentIndex: 0

                delegate: SearchResultItem {
                    width: ListView.view.width
                    dark: launcher.dark
                    pluginName: modelData.name
                    pluginDescription: modelData.description
                    pluginIcon: modelData.icon
                    pluginMode: modelData.mode || "independent"
                    source: modelData.source || "plugin"
                    highlightStart: modelData.highlightStart
                    highlightLen: modelData.highlightLen
                    isSelected: index === resultsList.currentIndex
                    onActivated: launcher.activateItem(modelData)
                }

                Label {
                    anchors.centerIn: parent
                    visible: resultsList.count === 0 && searchInput.text.length > 0
                    text: "未找到匹配的功能"
                    color: Theme.token("color-text-regular", dark)
                    font.pixelSize: 14
                    font.family: "IBM Plex Sans"
                }
            }

            FocusScope {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: mixedMode && mixedPluginMode === "inline_view"
                clip: true
                focus: visible
                Keys.priority: Keys.AfterItem
                Keys.onEscapePressed: function(event) {
                    launcher.exitMixedMode(true)
                    event.accepted = true
                }

                Item {
                    id: inlineHostStack
                    anchors.fill: parent
                    clip: true
                }
            }

            ListView {
                id: pluginListView
                Layout.fillWidth: true
                Layout.preferredHeight: launcher.pluginListContentHeight
                visible: false
                clip: true
                spacing: launcher.rowSpacing
                model: launcher.safePluginListItems
                currentIndex: count > 0 ? 0 : -1

                delegate: Rectangle {
                    id: pluginRow

                    width: ListView.view.width
                    height: launcher.rowHeight
                    radius: 6
                    color: index === pluginListView.currentIndex
                        ? Theme.token("color-bg-subtle", launcher.dark)
                        : "transparent"

                    property var rowData: modelData
                    property string rowId: String(rowData.id || "")
                    readonly property string rawIcon: rowData.icon || ""
                    readonly property bool useQta: rawIcon.indexOf("qta:") === 0
                    readonly property bool useFile: rawIcon.indexOf("file:///") === 0
                    readonly property string qtaName: useQta ? rawIcon.slice(4) : ""

                    function activated() {
                        launcherBridge.activatePluginListItem(launcher.mixedPluginId, pluginRow.rowId)
                        launcher.hide()
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 8
                        spacing: 10

                        Item {
                            id: pluginRowMain
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            RowLayout {
                                anchors.fill: parent
                                spacing: 12

                                Rectangle {
                                    Layout.preferredWidth: 36
                                    Layout.preferredHeight: 36
                                    Layout.alignment: Qt.AlignVCenter
                                    radius: 8
                                    color: index === pluginListView.currentIndex
                                        ? Theme.token("color-primary-bg", launcher.dark)
                                        : Theme.token("color-bg-subtle", launcher.dark)

                                    Image {
                                        visible: pluginRow.useQta
                                        anchors.centerIn: parent
                                        width: 22
                                        height: 22
                                        source: pluginRow.useQta
                                            ? ("image://qta/" + pluginRow.qtaName + ";color="
                                                + ("" + Theme.token("color-primary", launcher.dark)).replace("#", "")
                                                + ";size=22")
                                            : ""
                                        sourceSize.width: 22
                                        sourceSize.height: 22
                                        fillMode: Image.PreserveAspectFit
                                        smooth: true
                                    }

                                    Image {
                                        visible: pluginRow.useFile
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        source: pluginRow.useFile ? pluginRow.rawIcon : ""
                                        sourceSize.width: 28
                                        sourceSize.height: 28
                                        fillMode: Image.PreserveAspectFit
                                        smooth: true
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 2

                                    Label {
                                        Layout.fillWidth: true
                                        text: pluginRow.rowData.title || pluginRow.rowData.name || ""
                                        font.pixelSize: 14
                                        font.family: "IBM Plex Sans"
                                        color: Theme.token("color-text-primary", launcher.dark)
                                        elide: Text.ElideRight
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: pluginRow.rowData.subtitle || pluginRow.rowData.description || ""
                                        font.pixelSize: 11
                                        font.family: "JetBrains Mono"
                                        color: Theme.token("color-text-regular", launcher.dark)
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: pluginListView.currentIndex = index
                                onClicked: pluginRow.activated()
                            }
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 4
                            visible: (pluginRow.rowData.actions || []).length > 0

                            Repeater {
                                model: pluginRow.rowData.actions || []

                                delegate: Button {
                                    id: actionButton
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    padding: 0
                                    enabled: modelData.enabled !== false
                                    hoverEnabled: true

                                    readonly property string actionIcon: modelData.icon || "qta:mdi6.dots-horizontal"
                                    readonly property bool actionUseQta: actionIcon.indexOf("qta:") === 0
                                    readonly property string actionQtaName: actionUseQta ? actionIcon.slice(4) : actionIcon
                                    readonly property bool danger: !!modelData.danger

                                    ToolTip.visible: hovered
                                    ToolTip.delay: 300
                                    ToolTip.text: modelData.label || modelData.id || ""

                                    background: Rectangle {
                                        radius: 6
                                        color: actionButton.down
                                            ? Theme.token(actionButton.danger ? "color-danger" : "color-border-default", launcher.dark) + "33"
                                            : (actionButton.hovered
                                                ? Theme.token(actionButton.danger ? "color-danger" : "color-bg-subtle", launcher.dark) + "22"
                                                : "transparent")
                                    }

                                    contentItem: Item {
                                        UiIcon {
                                            anchors.centerIn: parent
                                            width: 16
                                            height: 16
                                            name: actionButton.actionQtaName
                                            color: actionButton.danger
                                                ? Theme.token("color-danger", launcher.dark)
                                                : Theme.token("color-text-regular", launcher.dark)
                                            iconSize: 16
                                        }
                                    }

                                    onClicked: {
                                        launcherBridge.activatePluginListItemAction(
                                            launcher.mixedPluginId,
                                            pluginRow.rowId,
                                            String(modelData.id || "")
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: pluginListView.count === 0
                    text: "暂无匹配结果"
                    color: Theme.token("color-text-regular", dark)
                    font.pixelSize: 14
                    font.family: "IBM Plex Sans"
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        onClicked: { }
    }
}
