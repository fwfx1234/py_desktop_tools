import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../ui"
import "../theme"

Window {
    id: launcher
    objectName: "launcherWindow"

    readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false
    readonly property bool isMacos: typeof app !== "undefined" && app ? app.isMacos : false
    readonly property int panelMargin: 0
    readonly property int contentPadding: isMacos ? 14 : 12
    readonly property color panelColor: dark ? "#111827" : "#FBFCFE"
    readonly property color panelBorderColor: dark ? "#2F3A4D" : "#D7DEE8"
    readonly property color fieldColor: dark ? "#172033" : "#FFFFFF"
    readonly property color rowSelectedColor: dark ? "#18243A" : "#EFF6FF"
    readonly property color iconSurfaceColor: dark ? "#202B3F" : "#EEF2F7"
    readonly property color accentColor: dark ? "#38BDF8" : "#2563EB"

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"

    readonly property int defaultWindowWidth: isMacos ? 760 : 800
    readonly property int defaultWindowHeight: isMacos ? 560 : 600
    readonly property int inputHeight: isMacos ? 52 : 48
    readonly property int rowHeight: isMacos ? 62 : 58
    readonly property int rowSpacing: 4
    readonly property int maxListRows: 8
    readonly property int pluginListCount: (typeof launcherBridge !== "undefined" && launcherBridge && launcherBridge.pluginListItems) ? launcherBridge.pluginListItems.length : 0
    readonly property int pluginListRows: Math.max(1, Math.min(pluginListCount, maxListRows))
    readonly property int pluginListContentHeight: (pluginListRows * rowHeight + Math.max(0, pluginListRows - 1) * rowSpacing)
    readonly property int pluginListWindowHeight: (contentPadding * 2 + inputHeight + 8 + pluginListContentHeight)

    width: defaultWindowWidth
    height: (mixedMode && mixedPluginMode === "list") ? pluginListWindowHeight : defaultWindowHeight

    readonly property bool hasBridge: typeof launcherBridge !== "undefined" && launcherBridge
    readonly property var safeSearchResults: hasBridge ? launcherBridge.searchResults : []
    readonly property var safePluginListItems: hasBridge ? launcherBridge.pluginListItems : []
    readonly property var safeAllPlugins: hasBridge ? launcherBridge.allPlugins : []

    property var retainedInlineHosts: ({})
    property bool mixedMode: false
    property string mixedPluginId: ""
    property string mixedPluginMode: ""
    property bool suppressPluginInputEdit: false
    property bool prewarming: false
    property bool showGraceActive: false

    Item {
        focus: true
        Keys.onEscapePressed: {
            if (launcher.mixedMode) {
                launcher.exitMixedMode();
            } else {
                launcher.hide();
            }
        }
    }

    onActiveChanged: {
        if (prewarming)
            return;
        if (active) {
            hideTimer.stop();
            return;
        }
        if (visible && !mixedMode && !showGraceActive) {
            hideTimer.start();
        }
    }

    Timer {
        id: hideTimer
        interval: 150
        onTriggered: launcher.hide()
    }

    Timer {
        id: showGraceTimer
        interval: 600
        onTriggered: launcher.showGraceActive = false
    }

    onVisibleChanged: {
        if (prewarming)
            return;
        hideTimer.stop();
        if (visible) {
            showGraceActive = true;
            showGraceTimer.restart();
            setSearchInputSilently("");
            searchInput.forceActiveFocus();
            exitMixedMode(false);
        } else if (mixedMode) {
            showGraceActive = false;
            showGraceTimer.stop();
            exitMixedMode(true);
        } else {
            showGraceActive = false;
            showGraceTimer.stop();
        }
    }

    Connections {
        target: hasBridge ? launcherBridge : null

        function onRetainedPluginExpired(pluginId) {
            launcher.destroyInlineHost(pluginId);
        }

        function onPluginClosed(pluginId) {
            if (hasBridge)
                launcherBridge.setPluginListItems([]);
            if (launcher.mixedPluginId === pluginId) {
                launcher.exitMixedMode(false);
                return;
            }
            launcher.destroyInlineHost(pluginId);
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
            onVisibleChanged: retainedLoader.active = visible && pageUrl.length > 0
            onPageUrlChanged: retainedLoader.active = visible && pageUrl.length > 0
            Keys.priority: Keys.AfterItem
            Keys.onEscapePressed: function (event) {
                launcher.exitMixedMode(true);
                event.accepted = true;
            }

            Loader {
                id: retainedLoader
                anchors.fill: parent
                active: visible && pageUrl.length > 0
                visible: active
                clip: true
                asynchronous: true
                source: pageUrl
            }
        }
    }

    function activateItem(itemData) {
        var src = itemData.source || "plugin";
        var id = itemData.id || "";
        if (!hasBridge)
            return;
        if (src === "plugin") {
            launcherBridge.launchItemWithInput(id, src, searchInput.text);
        } else if (src === "system" || src === "app") {
            launcherBridge.launchItem(id, src);
            launcher.hide();
        }
    }

    function openPluginFromHotkey(pluginId) {
        if (!hasBridge)
            return;
        if (mixedMode) {
            exitMixedMode(true);
        }
        searchInput.clear();
        searchInput.forceActiveFocus();
        launcherBridge.launchPlugin(pluginId);
    }

    function enterMixedMode(pluginId) {
        enterPluginMode(pluginId, "inline_view", "", false, "");
    }

    function findPluginPage(pluginId) {
        var plugins = safeSearchResults;
        for (var i = 0; i < plugins.length; i++) {
            if (plugins[i].id === pluginId || plugins[i].pluginId === pluginId) {
                return plugins[i].qmlPage || "";
            }
        }
        var allPlugins = safeAllPlugins || [];
        for (var j = 0; j < allPlugins.length; j++) {
            if (allPlugins[j].id === pluginId || allPlugins[j].pluginId === pluginId) {
                return allPlugins[j].qmlPage || "";
            }
        }
        return "";
    }

    function ensureInlineHost(pluginId, qmlPage) {
        var host = retainedInlineHosts[pluginId];
        var pageUrl = pluginPageUrl(qmlPage);
        if (host) {
            if (host.pageUrl !== pageUrl)
                host.pageUrl = pageUrl;
            return host;
        }
        host = retainedInlineHostComponent.createObject(inlineHostStack, {
            "pluginId": pluginId,
            "pageUrl": pageUrl
        });
        retainedInlineHosts[pluginId] = host;
        return host;
    }

    function hideAllInlineHosts(exceptPluginId) {
        var keys = Object.keys(retainedInlineHosts);
        for (var i = 0; i < keys.length; i++) {
            if (exceptPluginId && keys[i] === exceptPluginId)
                continue;
            destroyInlineHost(keys[i]);
        }
    }

    function showInlineHost(pluginId, qmlPage) {
        var page = qmlPage || findPluginPage(pluginId);
        if (!page || page.length === 0)
            return;
        var host = ensureInlineHost(pluginId, page);
        hideAllInlineHosts(pluginId);
        host.visible = true;
        searchInput.forceActiveFocus();
    }

    function retainInlineHost(pluginId) {
        destroyInlineHost(pluginId);
    }

    function destroyInlineHost(pluginId) {
        var host = retainedInlineHosts[pluginId];
        if (!host)
            return;
        host.destroy();
        delete retainedInlineHosts[pluginId];
    }

    function detachInlinePlugin(pluginId) {
        retainInlineHost(pluginId);
        mixedMode = false;
        mixedPluginId = "";
        mixedPluginMode = "";
        pluginListView.visible = false;
        resultsList.visible = true;
        searchInput.forceActiveFocus();
        if (hasBridge)
            launcherBridge.performSearch(searchInput.text);
    }

    function enterPluginMode(pluginId, pluginMode, pluginInputText, clearInputAfterEnter, explicitQmlPage) {
        mixedMode = true;
        mixedPluginId = pluginId;
        mixedPluginMode = pluginMode || "inline_view";

        var nextInputText = pluginInputText || "";
        if (clearInputAfterEnter === true) {
            setSearchInputSilently("");
        } else if (nextInputText.length > 0 && searchInput.text !== nextInputText) {
            searchInput.text = nextInputText;
        }

        resultsList.visible = false;
        pluginListView.visible = mixedPluginMode === "list";
        hideAllInlineHosts();

        if (mixedPluginMode === "inline_view") {
            showInlineHost(pluginId, explicitQmlPage);
        }
    }

    function setSearchInputSilently(text) {
        suppressPluginInputEdit = true;
        searchInput.text = text || "";
        suppressPluginInputEdit = false;
    }

    function invokeInlinePluginAction(action, value) {
        var host = retainedInlineHosts[mixedPluginId];
        if (!host || !host.children || host.children.length === 0)
            return false;
        var loader = host.children[0];
        if (!loader || !loader.item)
            return false;
        if (action === "activate" && typeof loader.item.activateSelection === "function") {
            return !!loader.item.activateSelection();
        }
        if (action === "move" && typeof loader.item.moveSelection === "function") {
            return !!loader.item.moveSelection(value);
        }
        return false;
    }

    function normalizeListSelection(view, resetToTop) {
        if (!view)
            return false;
        if (view.count <= 0) {
            view.currentIndex = -1;
            view.contentY = 0;
            return false;
        }
        if (resetToTop) {
            view.currentIndex = 0;
            view.positionViewAtIndex(0, ListView.Beginning);
            return true;
        }
        if (view.currentIndex < 0) {
            view.currentIndex = 0;
        } else if (view.currentIndex >= view.count) {
            view.currentIndex = view.count - 1;
        }
        view.positionViewAtIndex(view.currentIndex, ListView.Contain);
        return true;
    }

    function moveListSelection(view, delta) {
        if (!view || view.count <= 0)
            return false;
        var current = view.currentIndex;
        if (current < 0)
            current = delta < 0 ? view.count - 1 : 0;
        var next = Math.max(0, Math.min(view.count - 1, current + delta));
        view.currentIndex = next;
        view.positionViewAtIndex(next, ListView.Contain);
        return true;
    }

    function pageListSelection(view, direction) {
        if (!view || view.count <= 0)
            return false;
        var rowExtent = Math.max(1, launcher.rowHeight + launcher.rowSpacing);
        var rows = Math.max(1, Math.floor(view.height / rowExtent));
        return moveListSelection(view, direction * rows);
    }

    function activeListView() {
        if (mixedMode && mixedPluginMode === "list")
            return pluginListView;
        if (!mixedMode)
            return resultsList;
        return null;
    }

    function openSettings() {
        if (!hasBridge)
            return;
        if (mixedMode) {
            exitMixedMode(true);
        }
        setSearchInputSilently("");
        launcherBridge.launchPlugin("system-settings");
    }

    function pluginPageUrl(page) {
        if (!page || page.length === 0)
            return "";
        if (page.indexOf("file:///") === 0 || page.indexOf("qrc:/") === 0 || page.indexOf("http://") === 0 || page.indexOf("https://") === 0) {
            return page;
        }
        return Qt.resolvedUrl("../../" + page);
    }

    function exitMixedMode(shouldSuspend) {
        var closingPluginId = mixedPluginId;
        var closingPluginMode = mixedPluginMode;

        if (closingPluginMode === "inline_view" && closingPluginId.length > 0) {
            retainInlineHost(closingPluginId);
        }

        mixedMode = false;
        mixedPluginId = "";
        mixedPluginMode = "";
        pluginListView.visible = false;
        resultsList.visible = true;
        searchInput.forceActiveFocus();

        if (closingPluginId.length > 0 && hasBridge && shouldSuspend !== false) {
            if (closingPluginMode === "list") {
                launcherBridge.suspendPlugin(closingPluginId, "list");
            } else if (closingPluginMode === "inline_view") {
                launcherBridge.suspendPlugin(closingPluginId, "inline");
            }
        }
        if (hasBridge)
            launcherBridge.performSearch(searchInput.text);
    }

    Item {
        anchors.fill: parent

        Rectangle {
            id: panel
            anchors.fill: parent
            anchors.margins: launcher.panelMargin
            radius: launcher.isMacos ? 18 : 12
            color: launcher.panelColor
            border.color: launcher.panelBorderColor
            border.width: 1
            z: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: launcher.contentPadding
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: launcher.inputHeight
                    radius: launcher.isMacos ? 12 : 8
                    color: launcher.fieldColor
                    border.width: 1
                    border.color: launcher.dark ? "#2B3850" : "#E1E8F0"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 0
                        anchors.rightMargin: launcher.isMacos ? 14 : 12
                        spacing: 10

                        TextField {
                            id: searchInput
                            objectName: "launcherSearchInput"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            placeholderText: "搜索功能或打开应用..."
                            font.pixelSize: 16
                            font.family: Theme.fontFamily.ui
                            color: Theme.token("color-text-primary", dark)
                            placeholderTextColor: Theme.token("color-text-secondary", dark)
                            background: null
                            verticalAlignment: TextInput.AlignVCenter
                            leftPadding: 30
                            rightPadding: 0

                            onTextChanged: {
                                if (suppressPluginInputEdit)
                                    return;
                                if (!hasBridge)
                                    return;
                                if (mixedMode && mixedPluginId) {
                                    launcherBridge.setPluginInput(mixedPluginId, text);
                                } else {
                                    launcherBridge.performSearch(text);
                                }
                            }

                            Keys.onReturnPressed: function (event) {
                                if (mixedMode && mixedPluginMode === "list") {
                                    var pluginItem = pluginListView.currentItem;
                                    if (pluginItem)
                                        pluginItem.activated();
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode && mixedPluginMode === "inline_view") {
                                    launcher.invokeInlinePluginAction("activate", 0);
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode) {
                                    event.accepted = true;
                                    return;
                                }
                                var item = resultsList.currentItem;
                                if (item)
                                    item.activated();
                                event.accepted = true;
                            }
                            Keys.onUpPressed: function (event) {
                                if (mixedMode && mixedPluginMode === "list") {
                                    launcher.moveListSelection(pluginListView, -1);
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode && mixedPluginMode === "inline_view") {
                                    launcher.invokeInlinePluginAction("move", -1);
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode) {
                                    event.accepted = true;
                                    return;
                                }
                                launcher.moveListSelection(resultsList, -1);
                                event.accepted = true;
                            }
                            Keys.onDownPressed: function (event) {
                                if (mixedMode && mixedPluginMode === "list") {
                                    launcher.moveListSelection(pluginListView, 1);
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode && mixedPluginMode === "inline_view") {
                                    launcher.invokeInlinePluginAction("move", 1);
                                    event.accepted = true;
                                    return;
                                }
                                if (mixedMode) {
                                    event.accepted = true;
                                    return;
                                }
                                launcher.moveListSelection(resultsList, 1);
                                event.accepted = true;
                            }
                            Keys.onPressed: function (event) {
                                var listView = launcher.activeListView();
                                if (!listView)
                                    return;
                                if (event.key === Qt.Key_PageDown) {
                                    launcher.pageListSelection(listView, 1);
                                    event.accepted = true;
                                } else if (event.key === Qt.Key_PageUp) {
                                    launcher.pageListSelection(listView, -1);
                                    event.accepted = true;
                                }
                            }
                            Keys.onEscapePressed: {
                                if (mixedMode) {
                                    exitMixedMode(true);
                                } else {
                                    launcher.hide();
                                }
                            }
                        }

                        Button {
                            id: settingsButton
                            visible: !mixedMode
                            Layout.preferredWidth: 34
                            Layout.preferredHeight: 34
                            padding: 0
                            hoverEnabled: true

                            ToolTip.visible: hovered
                            ToolTip.delay: 250
                            ToolTip.text: "设置"

                            background: Rectangle {
                                radius: 7
                                color: settingsButton.down ? Theme.token("color-border-default", launcher.dark) : (settingsButton.hovered ? Theme.token("color-bg-subtle", launcher.dark) : "transparent")
                            }

                            contentItem: Item {
                                UiIcon {
                                    anchors.centerIn: parent
                                    width: 18
                                    height: 18
                                    name: "mdi6.cog-outline"
                                    color: Theme.token("color-text-regular", launcher.dark)
                                    iconSize: 18
                                }
                            }

                            onClicked: launcher.openSettings()
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
                                color: detachButton.down ? Theme.token("color-border-default", launcher.dark) : (detachButton.hovered ? Theme.token("color-bg-subtle-2", launcher.dark) : "transparent")
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
                                    launcherBridge.detachPluginToWindow(mixedPluginId);
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: !mixedMode
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: launcher.panelBorderColor
                }

                ListView {
                    id: resultsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: launcher.rowSpacing
                    model: launcher.safeSearchResults
                    currentIndex: count > 0 ? 0 : -1
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    onCountChanged: launcher.normalizeListSelection(resultsList, true)
                    onCurrentIndexChanged: launcher.normalizeListSelection(resultsList, false)

                    delegate: SearchResultItem {
                        width: ListView.view.width
                        dark: launcher.dark
                        pluginName: modelData.name
                        pluginDescription: modelData.description
                        pluginIcon: modelData.icon
                        pluginMode: modelData.mode || "independent"
                        source: modelData.source || "plugin"
                        accentColor: launcher.accentColor
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
                        font.family: Theme.fontFamily.ui
                    }
                }

                FocusScope {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: mixedMode && mixedPluginMode === "inline_view"
                    clip: true
                    focus: visible
                    Keys.priority: Keys.AfterItem
                    Keys.onEscapePressed: function (event) {
                        launcher.exitMixedMode(true);
                        event.accepted = true;
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
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    onCountChanged: launcher.normalizeListSelection(pluginListView, true)
                    onCurrentIndexChanged: launcher.normalizeListSelection(pluginListView, false)

                    delegate: Rectangle {
                        id: pluginRow

                        width: ListView.view.width
                        height: launcher.rowHeight
                        radius: launcher.isMacos ? 10 : 8
                        color: index === pluginListView.currentIndex ? launcher.rowSelectedColor : "transparent"

                        property var rowData: modelData
                        property string rowId: String(rowData.id || "")
                        readonly property string rawIcon: rowData.icon || ""
                        readonly property bool useQta: rawIcon.indexOf("qta:") === 0
                        readonly property bool useFile: rawIcon.indexOf("file:///") === 0
                        readonly property string qtaName: useQta ? rawIcon.slice(4) : ""
                        readonly property bool rowEnabled: rowData.enabled !== false

                        function activated() {
                            if (!rowEnabled)
                                return;
                            launcherBridge.activatePluginListItem(launcher.mixedPluginId, pluginRow.rowId);
                            launcher.hide();
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 10
                            spacing: 12

                            Item {
                                id: pluginRowMain
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 12

                                    Rectangle {
                                        Layout.preferredWidth: 40
                                        Layout.preferredHeight: 40
                                        Layout.alignment: Qt.AlignVCenter
                                        radius: 8
                                        color: index === pluginListView.currentIndex ? (launcher.dark ? "#123044" : "#DBEAFE") : launcher.iconSurfaceColor

                                        Image {
                                            visible: pluginRow.useQta
                                            anchors.centerIn: parent
                                            width: 22
                                            height: 22
                                            source: pluginRow.useQta ? ("image://qta/" + pluginRow.qtaName + ";color=" + ("" + launcher.accentColor).replace("#", "") + ";size=22") : ""
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
                                            sourceSize.width: 32
                                            sourceSize.height: 32
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            asynchronous: true
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
                                            font.family: Theme.fontFamily.ui
                                            color: pluginRow.rowEnabled ? Theme.token("color-text-primary", launcher.dark) : Theme.token("color-text-secondary", launcher.dark)
                                            elide: Text.ElideRight
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: pluginRow.rowData.subtitle || pluginRow.rowData.description || ""
                                            font.pixelSize: 11
                                            font.family: Theme.fontFamily.mono
                                            color: Theme.token("color-text-regular", launcher.dark)
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: pluginRow.rowEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    scrollGestureEnabled: false
                                    onEntered: pluginListView.currentIndex = index
                                    onClicked: pluginRow.activated()
                                    onWheel: function (wheel) {
                                        wheel.accepted = false;
                                    }
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
                                            color: actionButton.down ? Theme.token(actionButton.danger ? "color-danger" : "color-border-default", launcher.dark) + "33" : (actionButton.hovered ? Theme.token(actionButton.danger ? "color-danger" : "color-bg-subtle", launcher.dark) + "22" : "transparent")
                                        }

                                        contentItem: Item {
                                            UiIcon {
                                                anchors.centerIn: parent
                                                width: 16
                                                height: 16
                                                name: actionButton.actionQtaName
                                                color: actionButton.danger ? Theme.token("color-danger", launcher.dark) : Theme.token("color-text-regular", launcher.dark)
                                                iconSize: 16
                                            }
                                        }

                                        onClicked: {
                                            launcherBridge.activatePluginListItemAction(launcher.mixedPluginId, pluginRow.rowId, String(modelData.id || ""));
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
                        font.family: Theme.fontFamily.ui
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        onClicked: {}
    }
}
