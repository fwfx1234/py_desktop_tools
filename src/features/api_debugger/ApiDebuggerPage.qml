import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"
import "components"
import "api_utils.js" as ApiUtils

Item {
    id: root

    // ---- UI-only properties (layout, theme) ----
    property int currentTab: 0
    property real sidebarWidth: 260
    property real responsePanelRatio: 0.44
    property real responsePanelWidth: 0
    property int activeBodyRow: -1
    property bool showMagicPanel: false
    property bool applyingTabToActionBar: false
    readonly property var vm: apiDebuggerVm
    readonly property var appVm: app

    enabled: !!apiDebuggerVm

    readonly property bool dark: appVm ? appVm.theme === "dark" : false
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    readonly property color sidebarBg: Theme.token("color-bg-subtle-2", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color tableHeaderBg: Theme.token("color-table-header", dark)
    readonly property color softBorder: Qt.rgba(panelBorder.r, panelBorder.g, panelBorder.b, 0.55)
    readonly property var emptyRows: []
    readonly property var endpointTabsModel: vm ? vm.endpointTabs : emptyRows
    readonly property int currentEndpointTabIndex: vm ? vm.currentEndpointTab : -1
    readonly property var environmentsModel: vm ? vm.environments : emptyRows
    readonly property int currentEnvironmentIndex: vm ? vm.currentEnvIndex : 0
    readonly property var collectionTreeModel: vm ? vm.collectionTree : emptyRows
    readonly property bool requestSendingValue: vm ? vm.requestSending : false
    readonly property string wsStatusValue: vm ? vm.wsStatus : "idle"
    readonly property string wsStatusTextValue: vm ? vm.wsStatusText : "未连接"
    readonly property string wsEncodingValue: vm ? vm.wsEncoding : "text"
    readonly property bool mockModeValue: vm ? vm.mockMode : false
    readonly property bool assertionsEnabledValue: vm ? vm.assertionsEnabled : true
    readonly property string responseTitleValue: vm ? vm.responseTitle : "返回响应"
    readonly property string responseStatusCodeValue: vm ? vm.responseStatusCode : ""
    readonly property string responseElapsedMsValue: vm ? vm.responseElapsedMs : ""
    readonly property string responseFinalUrlValue: vm ? vm.responseFinalUrl : ""
    readonly property string responseOutcomeValue: vm ? vm.responseOutcome : "idle"
    readonly property string responseBodyValue: vm ? vm.responseBody : ""
    readonly property string responseBodyHtmlValue: vm ? vm.responseBodyHtml : ""
    readonly property string responseHeadersValue: vm ? vm.responseHeaders : ""
    readonly property string responseRequestValue: vm ? vm.responseRequest : ""
    readonly property string responseCurlValue: vm ? vm.responseCurl : ""
    readonly property string responseLogValue: vm ? vm.responseLog : ""
    readonly property var responseLogsModel: vm ? vm.responseLogs : emptyRows

    // ---- helpers that need QML element access ----
    function currentTabId() {
        var tabs = root.endpointTabsModel
        var idx = root.currentEndpointTabIndex
        return (idx >= 0 && idx < tabs.length) ? tabs[idx].id : ""
    }
    function endpointKey() {
        return ApiUtils.normalizeMethod(requestActionBar.getMethodText()) + " " + root.currentRequestUrl()
    }
    function currentEnvBaseUrl() {
        var envs = root.environmentsModel
        var idx = root.currentEnvironmentIndex
        return (idx >= 0 && idx < envs.length) ? (envs[idx].baseUrl || "") : ""
    }
    function currentRequestUrl() {
        var tab = root.endpointTabsModel[root.currentEndpointTabIndex] || {}
        return tab.url || "/"
    }
    function methodColor(method) {
        var m = {"GET": Theme.token("color-method-get", dark), "POST": Theme.token("color-method-post", dark),
                 "PUT": Theme.token("color-method-put", dark), "DEL": Theme.token("color-method-del", dark),
                 "DELETE": Theme.token("color-method-del", dark), "PATCH": Theme.token("color-method-patch", dark)}
        return m[method] || textMain
    }
    function envTagColor(name) {
        if (!name) return Theme.token("color-primary-active", dark)
        if (name.indexOf("正式") !== -1) return Theme.token("color-primary-active", dark)
        if (name.indexOf("本地") !== -1) return Theme.token("color-success", dark)
        if (name.indexOf("云") !== -1) return Theme.token("color-danger", dark)
        return Theme.token("color-primary-active", dark)
    }
    function qta(name, colorValue, iconSize) {
        return "image://qta/" + name + ";color=" + ("" + colorValue).replace("#", "") + ";size=" + iconSize
    }

    // ---- actions that assemble QML data → ViewModel ----
    function sendCurrent() {
        if (!apiDebuggerVm || root.requestSendingValue) return
        apiDebuggerVm.persistCurrentTabDraft()
        apiDebuggerVm.sendRequest({
            method: requestActionBar.getMethodText(),
            url: root.currentRequestUrl(),
            paramsText: ApiUtils.buildKvText(vm.pathParams) + "\n" + ApiUtils.buildKvText(vm.queryParams),
            headersText: ApiUtils.buildHeaderText(vm.headersRows),
            bodyText: bodyTextForRequest(),
            envBaseUrl: currentEnvBaseUrl(),
            authType: vm.authTypeValue,
            authValue: vm.authValueText,
            requestMode: vm.mockMode ? "mock" : ApiUtils.requestModeForMethod(requestActionBar.getMethodText()),
            wsEncoding: vm.wsEncoding,
            preOpsText: vm.assertionsEnabled ? vm.preOpsText : "",
            postOpsText: vm.assertionsEnabled ? vm.postOpsText : "",
            mockMode: vm.mockMode,
            tabId: currentTabId(),
            filePath: vm.bodyFilePath,
            fileParamName: vm.bodyFileParamName,
            bodyFormRows: vm.bodyFormRows,
            cookiesText: ApiUtils.buildCookieText(vm.cookieRows),
            currentBodyMode: vm.currentBodyMode,
        })
    }
    function bodyTextForRequest() {
        if (vm.currentBodyMode === 1 || vm.currentBodyMode === 5) return ""
        return vm.bodyText
    }
    function saveCurrentAsDebugCase() {
        if (!apiDebuggerVm) return
        var tab = root.endpointTabsModel[root.currentEndpointTabIndex] || {}
        apiDebuggerVm.saveDebugCaseData({
            endpointKey: endpointKey(), caseId: "",
            name: "调试用例 " + (vm.debugCases.length + 1),
            method: requestActionBar.getMethodText(), url: root.currentRequestUrl(),
            requestMode: vm.mockMode ? "mock" : ApiUtils.requestModeForMethod(requestActionBar.getMethodText()),
            bodyMode: currentBodyModeName(),
            authType: vm.authTypeValue, authValue: vm.authValueText,
            headersText: ApiUtils.buildHeaderText(vm.headersRows),
            cookiesText: ApiUtils.buildCookieText(vm.cookieRows),
            bodyText: bodyTextForRequest(),
            paramsText: ApiUtils.buildKvText(vm.queryParams),
            pathParamsText: ApiUtils.buildKvText(vm.pathParams),
            envBaseUrl: currentEnvBaseUrl(),
            preOpsText: vm.preOpsText, postOpsText: vm.postOpsText,
            mockMode: vm.mockMode,
        })
        apiDebuggerVm.loadDebugCases(endpointKey())
        apiDebuggerVm.loadWsTimeline(currentTabId())
    }
    function currentBodyModeName() {
        var modes = vm.bodyModes, idx = vm.currentBodyMode
        return (idx >= 0 && idx < modes.length) ? modes[idx] : "none"
    }
    function syncRequestActionBarFromCurrentTab() {
        var idx = root.currentEndpointTabIndex
        if (idx < 0 || idx >= root.endpointTabsModel.length) return
        var tab = root.endpointTabsModel[idx] || {}
        root.applyingTabToActionBar = true
        requestActionBar.setMethodText(tab.method || "GET")
        requestActionBar.setPathText(tab.url || "/")
        var savedTab = parseInt(tab.activeRequestTab || 0, 10)
        if (!isNaN(savedTab) && savedTab >= 0)
            root.currentTab = savedTab
        root.applyingTabToActionBar = false
    }
    function updateCurrentTreeEndpoint(methodText, pathText) {
        if (root.applyingTabToActionBar || !apiDebuggerVm) return
        var tab = root.endpointTabsModel[root.currentEndpointTabIndex]
        if (!tab) return
        apiDebuggerVm.updateCurrentTabRequest(methodText || "GET", pathText || "/")
        if (tab.kind === "case") {
            apiDebuggerVm.persistCurrentTabDraft()
            return
        }
        apiDebuggerVm.updateCollectionEndpoint(tab.nodeId || "", methodText || "GET", pathText || "/")
        apiDebuggerVm.persistCurrentTabDraft()
        apiDebuggerVm.loadCollectionTree()
    }
    function connectWs() {
        if (!apiDebuggerVm) return
        apiDebuggerVm.wsConnect(currentTabId(), root.currentRequestUrl(),
            ApiUtils.buildKvText(vm.queryParams), ApiUtils.buildHeaderText(vm.headersRows),
            ApiUtils.buildCookieText(vm.cookieRows), currentEnvBaseUrl())
    }
    function disconnectWs() { if (apiDebuggerVm) apiDebuggerVm.wsDisconnect(currentTabId()) }
    function receiveWs() { if (apiDebuggerVm) apiDebuggerVm.wsReceive(currentTabId()) }
    function restoreHistoryRequest(methodText, urlText) {
        if (!apiDebuggerVm) return
        apiDebuggerVm.updateCurrentTabRequest(methodText || "GET", urlText || "/")
        requestActionBar.setMethodText(methodText || "GET")
        requestActionBar.setPathText(urlText || "/")
        apiDebuggerVm.persistCurrentTabDraft()
    }
    function wsActionText() {
        if (root.wsStatusValue === "connecting")
            return "连接中"
        if (root.wsStatusValue === "connected")
            return "已连接"
        if (root.wsStatusValue === "receiving")
            return "接收中"
        if (root.wsStatusValue === "disconnecting")
            return "断开中"
        if (root.wsStatusValue === "error")
            return "连接失败"
        return "就绪"
    }
    function wsStatusColor() {
        if (root.wsStatusValue === "connected")
            return Theme.token("color-success", root.dark)
        if (root.wsStatusValue === "error")
            return Theme.token("color-danger", root.dark)
        if (root.wsStatusValue === "connecting" || root.wsStatusValue === "receiving" || root.wsStatusValue === "disconnecting")
            return Theme.token("color-info", root.dark)
        return root.textMuted
    }
    function wsDetailText() {
        if (root.wsStatusValue === "idle" || root.wsStatusValue === "disconnected")
            return ""
        return root.wsStatusTextValue
    }

    // ---- background ----
    Rectangle { anchors.fill: parent; color: root.panelBg }

    Component.onCompleted: {
        if (!apiDebuggerVm) return
        apiDebuggerVm.loadInitialData()
    }

    onCurrentTabChanged: { root.showMagicPanel = false }

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Item {
                Layout.preferredWidth: root.sidebarWidth; Layout.fillHeight: true
                Layout.minimumWidth: 180; Layout.maximumWidth: 500
                ApiCollectionSidebar {
                    id: collectionSidebar; anchors.fill: parent
                    dark: root.dark; panelBorder: root.panelBorder
                    textMain: root.textMain; textMuted: root.textMuted
                    collectionTree: root.collectionTreeModel
                    qtaFn: root.qta; methodColorFn: root.methodColor
                    onImportRequested: openApiDialog.open()
                    onNodeCreated: function(parentId, kind, name, methodText, pathText) {
                        var persistedId = apiDebuggerVm.createCollectionNode(parentId || "", kind || "folder", name || "未命名", methodText || "GET", pathText || "/new-endpoint")
                        apiDebuggerVm.loadCollectionTree()
                        if (persistedId.length > 0 && kind === "endpoint") {
                            apiDebuggerVm.openEndpointTab(name || "未命名", methodText || "GET", pathText || "/", persistedId || "")
                            root.syncRequestActionBarFromCurrentTab()
                        } else if (persistedId.length > 0 && kind === "case") {
                            apiDebuggerVm.openCaseTab(name || "未命名", methodText || "GET", pathText || "/", persistedId || "", {})
                            root.syncRequestActionBarFromCurrentTab()
                        }
                    }
                    onNodeRenamed: function(nodeId, name) { apiDebuggerVm.renameCollectionNode(nodeId || "", name || ""); apiDebuggerVm.loadCollectionTree() }
                    onNodeDeleted: function(nodeId) { apiDebuggerVm.deleteCollectionNode(nodeId || ""); apiDebuggerVm.loadCollectionTree() }
                    onNodeDuplicated: function(nodeId) { apiDebuggerVm.duplicateCollectionNode(nodeId || ""); apiDebuggerVm.loadCollectionTree() }
                    onNodeMoved: function(nodeId, targetParentId) { apiDebuggerVm.moveCollectionNode(nodeId || "", targetParentId || ""); apiDebuggerVm.loadCollectionTree() }
                    onNodeReordered: function(nodeId, delta) { apiDebuggerVm.reorderCollectionNode(nodeId || "", delta); apiDebuggerVm.loadCollectionTree() }
                    onNodeExpandedChanged: function(nodeId, expanded) { apiDebuggerVm.setCollectionNodeExpanded(nodeId || "", expanded); apiDebuggerVm.loadCollectionTree() }
                    onAllNodesExpandedChanged: function(expanded) { apiDebuggerVm.setAllCollectionNodesExpanded(expanded); apiDebuggerVm.loadCollectionTree() }
                    onEndpointSelected: function(name, methodText, pathText, nodeId) {
                        apiDebuggerVm.persistCurrentTabDraft()
                        apiDebuggerVm.openEndpointTab(name, methodText, pathText || "/", nodeId || "")
                        root.syncRequestActionBarFromCurrentTab()
                    }
                    onCaseSelected: function(name, methodText, pathText, nodeId, requestSnapshot) {
                        apiDebuggerVm.persistCurrentTabDraft()
                        apiDebuggerVm.openCaseTab(name, methodText, pathText || "/", nodeId || "", requestSnapshot || {})
                        root.syncRequestActionBarFromCurrentTab()
                    }
                }
            }
            Rectangle {
                Layout.preferredWidth: 4; Layout.fillHeight: true; color: root.panelBorder
                MouseArea {
                    anchors.fill: parent; anchors.leftMargin: -4; anchors.rightMargin: -4
                    cursorShape: Qt.SplitHCursor
                    property real _startX: 0; property real _startW: 0
                    onPressed: { _startX = mapToItem(parent.parent, mouseX, mouseY).x; _startW = root.sidebarWidth }
                    onPositionChanged: {
                        var p = mapToItem(parent.parent, mouseX, mouseY)
                        root.sidebarWidth = Math.round(Math.max(180, Math.min(500, _startW + (p.x - _startX))))
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0

                ApiEndpointTabsBar {
                    id: endpointTabsBar
                    endpointTabs: root.endpointTabsModel
                    currentEndpointTab: root.currentEndpointTabIndex
                    environments: root.environmentsModel
                    currentEnvIndex: root.currentEnvironmentIndex
                    dark: root.dark; panelBg: root.panelBg
                    textMain: root.textMain; textMuted: root.textMuted
                    methodColorFn: root.methodColor
                    envTagFn: ApiUtils.envTag; envTagColorFn: root.envTagColor
                    onTabClicked: function(index) {
                        apiDebuggerVm.persistCurrentTabDraft()
                        apiDebuggerVm.currentEndpointTab = index
                        root.syncRequestActionBarFromCurrentTab()
                    }
                    onTabCloseClicked: function(index) { apiDebuggerVm.closeCurrentTab(); root.syncRequestActionBarFromCurrentTab() }
                    onTabMoreClicked: function(buttonItem) {
                        var p = buttonItem.mapToItem(root, 0, buttonItem.height + 4)
                        tabActionsMenu.x = p.x; tabActionsMenu.y = p.y; tabActionsMenu.open()
                    }
                    onEnvironmentSelected: function(buttonItem) {
                        var p = buttonItem.mapToItem(root, 0, buttonItem.height + 4)
                        envPopup.x = p.x; envPopup.y = p.y; envPopup.open()
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

                ApiRequestActionBar {
                    id: requestActionBar
                    Layout.fillWidth: true; Layout.preferredHeight: 40
                    dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
                    textMuted: root.textMuted; sending: root.requestSendingValue
                    baseUrlText: root.currentEnvBaseUrl()
                    pathText: root.currentRequestUrl()
                    methodColorFn: root.methodColor
                    onMethodTextChanged: function(value) { updateCurrentTreeEndpoint(value, requestActionBar.getPathText()) }
                    onRequestPathEdited: function(value) { updateCurrentTreeEndpoint(requestActionBar.getMethodText(), value) }
                    onSendClicked: sendCurrent()
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 36
                    visible: ApiUtils.requestModeForMethod(requestActionBar.getMethodText()) === "websocket"
                    color: root.panelBg
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.space["2.5"]; anchors.rightMargin: Theme.space["2.5"]
                        UiButton { text: "连接"; dark: root.dark; variant: "primary"; onClicked: connectWs() }
                        UiButton { text: "接收"; dark: root.dark; variant: "secondary"; onClicked: receiveWs() }
                        UiButton { text: "断开"; dark: root.dark; variant: "secondary"; onClicked: disconnectWs() }
                        Label {
                            text: root.wsActionText()
                            color: root.wsStatusColor()
                            elide: Text.ElideRight
                            Layout.maximumWidth: 82
                        }
                        Label {
                            text: root.wsDetailText()
                            visible: text.length > 0
                            color: root.textSubtle
                            elide: Text.ElideMiddle
                            Layout.maximumWidth: 240
                        }
                        Label { text: "编码"; color: root.textMuted }
                        UiComboBox {
                            dark: root.dark; Layout.preferredWidth: 100; Layout.preferredHeight: 28
                            model: [{ text: "text", value: "text" }, { text: "binary", value: "binary" }]
                            textRole: "text"; valueRole: "value"
                            currentValue: root.wsEncodingValue
                            onCurrentValueChanged: if (apiDebuggerVm) apiDebuggerVm.wsEncoding = currentValue
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true

                    ApiRequestEditorPanel {
                        id: requestPanel
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: Math.max(parent.width < 820 ? 320 : 420, parent.width - responsePanel.width - verticalSplitter.width)
                        backend: apiDebuggerVm
                        vm: root.vm
                        dark: root.dark
                        panelBg: root.panelBg
                        panelBorder: root.panelBorder
                        textMain: root.textMain
                        textMuted: root.textMuted
                        textSubtle: root.textSubtle
                        tableHeaderBg: root.tableHeaderBg
                        currentTab: root.currentTab
                        activeBodyRow: root.activeBodyRow
                        showMagicPanel: root.showMagicPanel
                        currentMethod: requestActionBar.getMethodText()
                        methodColorFn: root.methodColor
                        onTabSelected: function(index) {
                            root.currentTab = index
                            if (apiDebuggerVm && !root.applyingTabToActionBar)
                                apiDebuggerVm.updateCurrentTabActiveRequestTab(index)
                        }
                        onFileBrowseClicked: fileDialog.open()
                        onSaveAsCaseClicked: saveCurrentAsDebugCase()
                        onBatchRunClicked: {
                            if (apiDebuggerVm && vm.selectedDebugCaseIds.length > 0)
                                apiDebuggerVm.runDebugCases(endpointKey(), apiDebuggerVm.selectedDebugCaseIds)
                        }
                        onCaseSelectionToggled: function(caseId, checked) { apiDebuggerVm.toggleCaseSelectionById(caseId || "") }
                        onHistoryRestoreRequested: function(methodText, urlText) { restoreHistoryRequest(methodText, urlText) }
                        onBodyRowFocused: function(index) { root.activeBodyRow = index }
                        onMagicPanelToggleRequested: root.showMagicPanel = !root.showMagicPanel
                        onMagicValueInsertRequested: function(value) { if (apiDebuggerVm) apiDebuggerVm.bodyText = vm.bodyText + value }
                        onMagicPanelCloseRequested: root.showMagicPanel = false
                    }

                    Rectangle {
                        id: verticalSplitter
                        width: 4
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.right: responsePanel.left
                        color: root.panelBorder
                        MouseArea {
                            anchors.fill: parent
                            anchors.leftMargin: -4
                            anchors.rightMargin: -4
                            cursorShape: Qt.SplitHCursor
                            property real _startX: 0
                            property real _startWidth: 0
                            onPressed: {
                                var p = mapToItem(parent.parent, mouseX, mouseY)
                                _startX = p.x
                                _startWidth = responsePanel.width
                            }
                            onPositionChanged: {
                                var p = mapToItem(parent.parent, mouseX, mouseY)
                                var total = parent.parent.width
                                if (total > 0) {
                                    root.responsePanelWidth = Math.round(Math.max(360, Math.min(total * 0.62, _startWidth - (p.x - _startX))))
                                    root.responsePanelRatio = root.responsePanelWidth / total
                                }
                            }
                        }
                    }

                    ApiResponsePanel {
                        id: responsePanel
                        width: {
                            var total = parent ? parent.width : 0
                            var minRequest = total < 820 ? 320 : 420
                            var minResponse = total < 820 ? 300 : 360
                            var desired = root.responsePanelWidth > 0 ? root.responsePanelWidth : Math.round(total * root.responsePanelRatio)
                            var maxResponse = Math.max(minResponse, total - minRequest - verticalSplitter.width)
                            return Math.max(minResponse, Math.min(desired, maxResponse))
                        }
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
                        textMain: root.textMain; textMuted: root.textMuted; textSubtle: root.textSubtle
                        softBorder: root.softBorder
                        mockMode: root.mockModeValue; assertionsEnabled: root.assertionsEnabledValue
                        titleText: root.responseTitleValue
                        statusCode: root.responseStatusCodeValue
                        elapsedMs: root.responseElapsedMsValue
                        finalUrl: root.responseFinalUrlValue
                        outcome: root.responseOutcomeValue
                        bodyText: root.responseBodyValue
                        bodyHtml: root.responseBodyHtmlValue
                        headersText: root.responseHeadersValue
                        requestText: root.responseRequestValue
                        curlText: root.responseCurlValue
                        requestLogText: root.responseLogValue
                        logEntries: root.responseLogsModel
                        onMockModeToggled: function(checked) { if (apiDebuggerVm) apiDebuggerVm.mockMode = checked }
                        onAssertionsToggled: function(checked) { if (apiDebuggerVm) apiDebuggerVm.assertionsEnabled = checked }
                    }
                }
            }
        }
    }

    // ---- Overlays ----
    ApiEnvPopup {
        id: envPopup; dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
        environments: root.environmentsModel; currentEnvIndex: root.currentEnvironmentIndex
        envTagFn: ApiUtils.envTag; envTagColorFn: root.envTagColor
        onEnvironmentSelected: function(index) { if (apiDebuggerVm) apiDebuggerVm.currentEnvIndex = index }
        onManageRequested: envDialog.open()
    }
    ApiTabActionsPopup {
        id: tabActionsMenu; dark: root.dark; panelBg: root.panelBg
        onCloseAllRequested: if (apiDebuggerVm) { apiDebuggerVm.endpointTabs = []; apiDebuggerVm.currentEndpointTab = -1 }
        onCloseCurrentRequested: if (apiDebuggerVm) { apiDebuggerVm.closeCurrentTab(); root.syncRequestActionBarFromCurrentTab() }
        onCloseOthersRequested: {
            if (!apiDebuggerVm || root.currentEndpointTabIndex < 0 || root.currentEndpointTabIndex >= root.endpointTabsModel.length) return
            var keep = root.endpointTabsModel[root.currentEndpointTabIndex]
            apiDebuggerVm.endpointTabs = [keep]
            apiDebuggerVm.currentEndpointTab = 0
            root.syncRequestActionBarFromCurrentTab()
        }
    }
    EnvManagerDialog {
        id: envDialog; anchors.centerIn: Overlay.overlay
        dark: root.dark; environments: root.environmentsModel; currentEnvIndex: root.currentEnvironmentIndex
        autoSaveEnabled: true
        onEnvironmentsSaved: function(envs, selectedIndex) {
            if (!apiDebuggerVm) return
            apiDebuggerVm.currentEnvIndex = selectedIndex
            apiDebuggerVm.saveEnvironments(envs)
        }
    }
    FileDialog {
        id: openApiDialog; fileMode: FileDialog.OpenFile; nameFilters: ["OpenAPI (*.json *.yaml *.yml)"]
        onAccepted: {
            if (!apiDebuggerVm) return
            var filePath = decodeURIComponent(selectedFile.toString()).replace("file:///", "")
            apiDebuggerVm.importOpenApi(filePath)
        }
    }
    FileDialog {
        id: fileDialog; fileMode: FileDialog.OpenFile; title: "选择上传文件"
        onAccepted: {
            if (!apiDebuggerVm) return
            var path = decodeURIComponent(selectedFile.toString()).replace("file:///", "")
            apiDebuggerVm.bodyFilePath = path
        }
    }

    // ---- Connections ----
    Connections {
        target: apiDebuggerVm
        function onApiImported(items) {
            apiDebuggerVm.replaceCollectionTree(items, true)
            apiDebuggerVm.loadCollectionTree()
        }
        function onApiEnvironmentsImported(items) {
            if (items.length > 0) {
                apiDebuggerVm.currentEnvIndex = 0
                apiDebuggerVm.saveEnvironments(items)
            }
        }
        function onEnvironmentsLoaded(items) { apiDebuggerVm.environments = items }
        function onCollectionTreeLoaded(items) { apiDebuggerVm.collectionTree = items }
        function onTabsLoaded(items) {
            if (items.length > 0) {
                apiDebuggerVm.endpointTabs = items
                apiDebuggerVm.currentEndpointTab = 0
                root.syncRequestActionBarFromCurrentTab()
            }
        }
        function onApiResponseReady(title, bodyText, details) {
            responsePanel.detailTab = 0
        }
        function onApiSendingChanged(sending) { apiDebuggerVm.requestSending = sending }
        function onApiHistoryUpdated(items) { apiDebuggerVm.apiHistory = items }
        function onWsTimelineLoaded(items) { apiDebuggerVm.wsTimeline = items }
        function onDebugCasesLoaded(items) { apiDebuggerVm.debugCases = items; apiDebuggerVm.selectedDebugCaseIds = [] }
        function onDebugCasesRunCompleted(items) {
            if (items.length === 0) return
            var lines = []
            for (var i = 0; i < items.length; i++)
                lines.push("[" + items[i].name + "] " + items[i].title)
            apiDebuggerVm.applyResponseDetails("批量运行结果", lines.join("\n"), {})
        }
    }
}
