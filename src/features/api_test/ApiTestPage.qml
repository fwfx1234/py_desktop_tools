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
    property real requestPanelRatio: 0.40
    property real requestPanelHeight: 0
    property int activeBodyRow: -1
    property bool showMagicPanel: false
    property bool applyingTabToActionBar: false
    readonly property var vmFallback: ({
        endpointTabs: [],
        currentEndpointTab: -1,
        environments: [],
        currentEnvIndex: -1,
        requestSending: false,
        queryParams: [],
        pathParams: [],
        bodyModes: ["none", "x-www-form-urlencoded", "JSON", "XML", "Text", "file"],
        currentBodyMode: 0,
        bodyFormRows: [],
        bodyText: "",
        bodyFilePath: "",
        bodyFileParamName: "file",
        headersRows: [],
        cookieRows: [],
        authTypeValue: "none",
        authValueText: "",
        preOpsText: "",
        postOpsText: "",
        debugCases: [],
        selectedDebugCaseIds: [],
        apiHistory: [],
        wsTimeline: [],
        wsStatusText: "未连接",
        wsStatus: "idle",
        wsEncoding: "text",
        mockMode: false,
        assertionsEnabled: true,
        responseTitle: "返回响应",
        responseBody: "",
        responseHeaders: "",
        responseRequest: "",
        responseCurl: "",
        responseLog: "",
        responseLogs: [],
        collectionTree: []
    })
    readonly property var vm: apiTestVm || vmFallback
    readonly property var appVm: app || ({ theme: "light" })

    enabled: !!apiTestVm

    readonly property bool dark: appVm.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    readonly property color sidebarBg: Theme.token("color-bg-subtle-2", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color tableHeaderBg: Theme.token("color-table-header", dark)
    readonly property color softBorder: Qt.rgba(panelBorder.r, panelBorder.g, panelBorder.b, 0.55)

    // ---- helpers that need QML element access ----
    function currentTabId() {
        var tabs = vm.endpointTabs
        var idx = vm.currentEndpointTab
        return (idx >= 0 && idx < tabs.length) ? tabs[idx].id : ""
    }
    function endpointKey() {
        return ApiUtils.normalizeMethod(requestActionBar.getMethodText()) + " " + (requestActionBar.getUrlText() || "/")
    }
    function currentEnvBaseUrl() {
        var envs = vm.environments
        var idx = vm.currentEnvIndex
        return (idx >= 0 && idx < envs.length) ? (envs[idx].baseUrl || "") : ""
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
        if (!apiTestVm || vm.requestSending) return
        apiTestVm.persistCurrentTabDraft()
        apiTestVm.sendRequest({
            method: requestActionBar.getMethodText(),
            url: requestActionBar.getUrlText(),
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
        if (!apiTestVm) return
        var tab = vm.endpointTabs[vm.currentEndpointTab] || {}
        apiTestVm.saveDebugCaseData({
            endpointKey: endpointKey(), caseId: "",
            name: "调试用例 " + (vm.debugCases.length + 1),
            method: requestActionBar.getMethodText(), url: requestActionBar.getUrlText(),
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
        apiTestVm.loadDebugCases(endpointKey())
        apiTestVm.loadWsTimeline(currentTabId())
    }
    function currentBodyModeName() {
        var modes = vm.bodyModes, idx = vm.currentBodyMode
        return (idx >= 0 && idx < modes.length) ? modes[idx] : "none"
    }
    function syncRequestActionBarFromCurrentTab() {
        var idx = vm.currentEndpointTab
        if (idx < 0 || idx >= vm.endpointTabs.length) return
        var tab = vm.endpointTabs[idx] || {}
        root.applyingTabToActionBar = true
        requestActionBar.setMethodText(tab.method || "GET")
        requestActionBar.setUrlText(tab.url || "/")
        root.applyingTabToActionBar = false
    }
    function updateCurrentTreeEndpoint(methodText, pathText) {
        if (root.applyingTabToActionBar || !apiTestVm) return
        var tab = vm.endpointTabs[vm.currentEndpointTab]
        if (!tab) return
        apiTestVm.updateCurrentTabRequest(methodText || "GET", pathText || "/")
        if (tab.kind === "case") {
            apiTestVm.persistCurrentTabDraft()
            return
        }
        apiTestVm.updateCollectionEndpoint(tab.nodeId || "", methodText || "GET", pathText || "/")
        apiTestVm.persistCurrentTabDraft()
    }
    function autoParseUrlParams(urlText) {
        var q = (urlText || "").split("?")[1]
        if (!q || q.length === 0) return
        var rows = []
        var pairs = q.split("&")
        for (var i = 0; i < pairs.length; i++) {
            var eq = pairs[i].indexOf("=")
            var k = eq >= 0 ? decodeURIComponent(pairs[i].slice(0, eq)) : decodeURIComponent(pairs[i])
            var v = eq >= 0 ? decodeURIComponent(pairs[i].slice(eq + 1)) : ""
            if (k) rows.push({ enabled: true, key: k, value: v, type: "string", desc: "" })
        }
        if (apiTestVm && rows.length > 0) apiTestVm.queryParams = ApiUtils.normalizeQueryRows(rows)
    }
    function connectWs() {
        if (!apiTestVm) return
        apiTestVm.wsConnect(currentTabId(), requestActionBar.getUrlText(),
            ApiUtils.buildKvText(vm.queryParams), ApiUtils.buildHeaderText(vm.headersRows),
            ApiUtils.buildCookieText(vm.cookieRows), currentEnvBaseUrl())
    }
    function disconnectWs() { if (apiTestVm) apiTestVm.wsDisconnect(currentTabId()) }
    function receiveWs() { if (apiTestVm) apiTestVm.wsReceive(currentTabId()) }
    function restoreHistoryRequest(methodText, urlText) {
        if (!apiTestVm) return
        apiTestVm.updateCurrentTabRequest(methodText || "GET", urlText || "/")
        requestActionBar.setMethodText(methodText || "GET")
        requestActionBar.setUrlText(urlText || "/")
        apiTestVm.persistCurrentTabDraft()
    }

    // ---- background ----
    Rectangle { anchors.fill: parent; color: root.panelBg }

    Component.onCompleted: {
        if (!apiTestVm) return
        apiTestVm.loadEnvironments()
        apiTestVm.loadCollectionTree()
        apiTestVm.loadTabs()
        apiTestVm.loadApiHistory()
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
                    collectionTree: vm.collectionTree
                    qtaFn: root.qta; methodColorFn: root.methodColor
                    onImportRequested: openApiDialog.open()
                    onNodeCreated: function(parentId, kind, name, methodText, pathText) {
                        var persistedId = apiTestVm.createCollectionNode(parentId || "", kind || "folder", name || "未命名", methodText || "GET", pathText || "/new-endpoint")
                        apiTestVm.loadCollectionTree()
                        if (persistedId.length > 0 && kind === "endpoint") {
                            apiTestVm.openEndpointTab(name || "未命名", methodText || "GET", pathText || "/", persistedId || "")
                            root.syncRequestActionBarFromCurrentTab()
                        } else if (persistedId.length > 0 && kind === "case") {
                            apiTestVm.openCaseTab(name || "未命名", methodText || "GET", pathText || "/", persistedId || "", {})
                            root.syncRequestActionBarFromCurrentTab()
                        }
                    }
                    onNodeRenamed: function(nodeId, name) { apiTestVm.renameCollectionNode(nodeId || "", name || ""); apiTestVm.loadCollectionTree() }
                    onNodeDeleted: function(nodeId) { apiTestVm.deleteCollectionNode(nodeId || ""); apiTestVm.loadCollectionTree() }
                    onNodeDuplicated: function(nodeId) { apiTestVm.duplicateCollectionNode(nodeId || ""); apiTestVm.loadCollectionTree() }
                    onNodeMoved: function(nodeId, targetParentId) { apiTestVm.moveCollectionNode(nodeId || "", targetParentId || ""); apiTestVm.loadCollectionTree() }
                    onNodeReordered: function(nodeId, delta) { apiTestVm.reorderCollectionNode(nodeId || "", delta); apiTestVm.loadCollectionTree() }
                    onNodeExpandedChanged: function(nodeId, expanded) { apiTestVm.setCollectionNodeExpanded(nodeId || "", expanded); apiTestVm.loadCollectionTree() }
                    onAllNodesExpandedChanged: function(expanded) { apiTestVm.setAllCollectionNodesExpanded(expanded); apiTestVm.loadCollectionTree() }
                    onEndpointSelected: function(name, methodText, pathText, nodeId) {
                        apiTestVm.openEndpointTab(name, methodText, pathText || "/", nodeId || "")
                        root.syncRequestActionBarFromCurrentTab()
                    }
                    onCaseSelected: function(name, methodText, pathText, nodeId, requestSnapshot) {
                        apiTestVm.openCaseTab(name, methodText, pathText || "/", nodeId || "", requestSnapshot || {})
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
                    endpointTabs: vm.endpointTabs
                    currentEndpointTab: vm.currentEndpointTab
                    environments: vm.environments
                    currentEnvIndex: vm.currentEnvIndex
                    dark: root.dark; panelBg: root.panelBg
                    textMain: root.textMain; textMuted: root.textMuted
                    methodColorFn: root.methodColor
                    envTagFn: ApiUtils.envTag; envTagColorFn: root.envTagColor
                    onTabClicked: function(index) {
                        apiTestVm.currentEndpointTab = index
                        root.syncRequestActionBarFromCurrentTab()
                    }
                    onTabCloseClicked: function(index) { apiTestVm.closeCurrentTab(); root.syncRequestActionBarFromCurrentTab() }
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
                    textMuted: root.textMuted; sending: vm.requestSending
                    methodColorFn: root.methodColor
                    onMethodTextChanged: function(value) { updateCurrentTreeEndpoint(value, requestActionBar.getUrlText()) }
                    onUrlTextChanged: function(value) { autoParseUrlParams(value); updateCurrentTreeEndpoint(requestActionBar.getMethodText(), value) }
                    onSendClicked: sendCurrent()
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 36
                    visible: ApiUtils.requestModeForMethod(requestActionBar.getMethodText()) === "websocket"
                    color: root.panelBg
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.spacing.s3; anchors.rightMargin: Theme.spacing.s3
                        UiButton { text: "连接"; dark: root.dark; variant: "primary"; onClicked: connectWs() }
                        UiButton { text: "接收"; dark: root.dark; variant: "secondary"; onClicked: receiveWs() }
                        UiButton { text: "断开"; dark: root.dark; variant: "secondary"; onClicked: disconnectWs() }
                        Label {
                            text: vm.wsStatusText
                            color: vm.wsStatus === "connected"
                                ? Theme.token("color-success", root.dark)
                                : (vm.wsStatus === "error" ? Theme.token("color-danger", root.dark) : root.textMuted)
                            elide: Text.ElideRight
                            Layout.maximumWidth: 260
                        }
                        Label { text: "编码"; color: root.textMuted }
                        UiComboBox {
                            dark: root.dark; Layout.preferredWidth: 100; Layout.preferredHeight: 28
                            model: [{ text: "text", value: "text" }, { text: "binary", value: "binary" }]
                            textRole: "text"; valueRole: "value"
                            currentValue: vm.wsEncoding
                            onCurrentValueChanged: if (apiTestVm) apiTestVm.wsEncoding = currentValue
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                ApiRequestTabsBar {
                    Layout.fillWidth: true; Layout.preferredHeight: 36
                    dark: root.dark; panelBg: root.panelBg; textMain: root.textMain
                    currentTab: root.currentTab
                    onTabChanged: root.currentTab = index
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

                // ---- Split container (request / response) ----
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true

                    ColumnLayout {
                        id: requestPanel
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        height: root.requestPanelHeight > 0 ? root.requestPanelHeight : Math.round(parent.height * root.requestPanelRatio)
                        spacing: 0

                        StackLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            currentIndex: root.currentTab

                            KvTableSection {
                                rows: vm.queryParams; showTypeSelector: true; keyWidth: 220; descWidth: 180
                                dark: root.dark; textMain: root.textMain; textMuted: root.textMuted
                                panelBorder: root.panelBorder; tableHeaderBg: root.tableHeaderBg
                                onRowEnabledToggled: function(index, checked) { apiTestVm.toggleSectionRowEnabled("query", index, checked) }
                                onRowKeyCommitted: function(index, keyText) { apiTestVm.editSectionRowKey("query", index, keyText) }
                                onRowTypeCommitted: function(index, typeText) { /* noop */ }
                                onRowValueCommitted: function(index, valueText) { apiTestVm.editSectionRowValue("query", index, valueText) }
                                onRowDescCommitted: function(index, descText) { /* noop */ }
                                onRowDeleteRequested: function(index) { apiTestVm.deleteSectionRow("query", index) }
                            }
                            KvTableSection {
                                rows: vm.pathParams; keyTitle: "路径参数"; keyWidth: 220; descWidth: 180
                                dark: root.dark; textMain: root.textMain; textMuted: root.textMuted
                                panelBorder: root.panelBorder; tableHeaderBg: root.tableHeaderBg
                                onRowEnabledToggled: function(index, checked) { apiTestVm.toggleSectionRowEnabled("path", index, checked) }
                                onRowKeyCommitted: function(index, keyText) { apiTestVm.editSectionRowKey("path", index, keyText) }
                                onRowValueCommitted: function(index, valueText) { apiTestVm.editSectionRowValue("path", index, valueText) }
                                onRowDeleteRequested: function(index) { apiTestVm.deleteSectionRow("path", index) }
                            }
                            ApiBodyTab {
                                id: bodyTab
                                dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
                                textMain: root.textMain; textMuted: root.textMuted; textSubtle: root.textSubtle
                                tableHeaderBg: root.tableHeaderBg
                                bodyModes: vm.bodyModes; currentBodyMode: vm.currentBodyMode
                                bodyFormRows: vm.bodyFormRows; bodyText: vm.bodyText
                                bodyFilePath: vm.bodyFilePath; bodyFileParamName: vm.bodyFileParamName
                                activeBodyRow: root.activeBodyRow; showMagicPanel: root.showMagicPanel
                                onBodyModeClicked: function(index) { if (apiTestVm) apiTestVm.setCurrentBodyMode(index) }
                                onBodyTextEdited: function(text) { if (apiTestVm) apiTestVm.bodyText = text }
                                onFormRowEnabledToggled: function(index, checked) { apiTestVm.toggleSectionRowEnabled("body", index, checked) }
                                onFormRowKeyCommitted: function(index, keyText) { apiTestVm.editSectionRowKey("body", index, keyText) }
                                onFormRowValueCommitted: function(index, valueText) { apiTestVm.editSectionRowValue("body", index, valueText) }
                                onFormRowDeleteRequested: function(index) { apiTestVm.deleteSectionRow("body", index) }
                                onFormRowValueFocused: function(index) { root.activeBodyRow = index }
                                onFileBrowseClicked: fileDialog.open()
                                onFileParamNameEdited: function(name) { if (apiTestVm) apiTestVm.bodyFileParamName = name }
                                onMagicValueInsertRequested: function(value) { if (apiTestVm) apiTestVm.bodyText = vm.bodyText + value }
                                onMagicPanelCloseRequested: root.showMagicPanel = false
                            }
                            KvTableSection {
                                rows: vm.headersRows; keyTitle: "Header"; showTypeColumn: false; keyWidth: 240; descWidth: 200
                                dark: root.dark; textMain: root.textMain; textMuted: root.textMuted
                                panelBorder: root.panelBorder; tableHeaderBg: root.tableHeaderBg
                                onRowEnabledToggled: function(index, checked) { apiTestVm.toggleSectionRowEnabled("headers", index, checked) }
                                onRowKeyCommitted: function(index, keyText) { apiTestVm.editSectionRowKey("headers", index, keyText) }
                                onRowValueCommitted: function(index, valueText) { apiTestVm.editSectionRowValue("headers", index, valueText) }
                                onRowDescCommitted: function(index, descText) { /* noop */ }
                                onRowDeleteRequested: function(index) { apiTestVm.deleteSectionRow("headers", index) }
                            }
                            KvTableSection {
                                rows: vm.cookieRows; keyTitle: "Cookie"; showTypeColumn: false; keyWidth: 220; descWidth: 200
                                dark: root.dark; textMain: root.textMain; textMuted: root.textMuted
                                panelBorder: root.panelBorder; tableHeaderBg: root.tableHeaderBg
                                onRowEnabledToggled: function(index, checked) { apiTestVm.toggleSectionRowEnabled("cookies", index, checked) }
                                onRowKeyCommitted: function(index, keyText) { apiTestVm.editSectionRowKey("cookies", index, keyText) }
                                onRowValueCommitted: function(index, valueText) { apiTestVm.editSectionRowValue("cookies", index, valueText) }
                                onRowDescCommitted: function(index, descText) { /* noop */ }
                                onRowDeleteRequested: function(index) { apiTestVm.deleteSectionRow("cookies", index) }
                            }
                            ApiAuthTab {
                                id: authTab
                                dark: root.dark; textMain: root.textMain; textMuted: root.textMuted
                                authTypeValue: vm.authTypeValue; authValueText: vm.authValueText
                                onAuthTypeChanged: function(value) { if (apiTestVm) apiTestVm.authTypeValue = value }
                                onAuthValueChanged: function(text) { if (apiTestVm) apiTestVm.authValueText = text }
                            }
                            Item {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                UiTextArea {
                                    id: preOpsInput
                                    anchors.fill: parent; anchors.margins: Theme.spacing.s3
                                    dark: root.dark
                                    placeholderText: "前置操作：每行一条 KV，发送请求前会附加全局参数。"
                                    wrapMode: TextEdit.NoWrap
                                    text: vm.preOpsText
                                    onTextChanged: if (apiTestVm) apiTestVm.preOpsText = text
                                }
                            }
                            Item {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                UiTextArea {
                                    id: postOpsInput
                                    anchors.fill: parent; anchors.margins: Theme.spacing.s3
                                    dark: root.dark
                                    placeholderText: "后置操作：响应后执行的断言。\nstatus == 200\nbody contains \"ok\""
                                    wrapMode: TextEdit.NoWrap
                                    text: vm.postOpsText
                                    onTextChanged: if (apiTestVm) apiTestVm.postOpsText = text
                                }
                            }
                            ApiSettingsTab {
                                id: settingsTab
                                dark: root.dark; textMain: root.textMain; textSubtle: root.textSubtle
                                debugCases: vm.debugCases
                                selectedDebugCaseIds: vm.selectedDebugCaseIds
                                apiHistory: vm.apiHistory
                                wsTimeline: vm.wsTimeline
                                wsStatusText: vm.wsStatusText
                                currentMethod: requestActionBar.getMethodText()
                                methodColorFn: root.methodColor
                                onSaveAsCaseClicked: saveCurrentAsDebugCase()
                                onBatchRunClicked: {
                                    if (apiTestVm && vm.selectedDebugCaseIds.length > 0)
                                        apiTestVm.runDebugCases(endpointKey(), apiTestVm.selectedDebugCaseIds)
                                }
                                onCaseSelectionToggled: function(caseId, checked) { apiTestVm.toggleCaseSelectionById(caseId || "") }
                                onHistoryRestoreRequested: function(methodText, urlText) { restoreHistoryRequest(methodText, urlText) }
                            }
                        }
                    }

                    Rectangle {
                        id: verticalSplitter
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: requestPanel.bottom; height: 4; color: root.panelBorder
                        MouseArea {
                            anchors.fill: parent; anchors.topMargin: -4; anchors.bottomMargin: -4
                            cursorShape: Qt.SplitVCursor
                            property real _startY: 0; property real _startHeight: 0
                            onPressed: { var p = mapToItem(parent.parent, mouseX, mouseY); _startY = p.y; _startHeight = requestPanel.height }
                            onPositionChanged: {
                                var p = mapToItem(parent.parent, mouseX, mouseY); var total = parent.parent.height
                                if (total > 0) { root.requestPanelHeight = Math.round(Math.max(120, Math.min(total * 0.75, _startHeight + (p.y - _startY)))); root.requestPanelRatio = root.requestPanelHeight / total }
                            }
                        }
                    }

                    ApiResponsePanel {
                        id: responsePanel
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: verticalSplitter.bottom; anchors.bottom: parent.bottom
                        dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
                        textMain: root.textMain; textMuted: root.textMuted; textSubtle: root.textSubtle
                        softBorder: root.softBorder
                        mockMode: vm.mockMode; assertionsEnabled: vm.assertionsEnabled
                        titleText: vm.responseTitle
                        bodyText: vm.responseBody
                        headersText: vm.responseHeaders
                        requestText: vm.responseRequest
                        curlText: vm.responseCurl
                        requestLogText: vm.responseLog
                        logEntries: vm.responseLogs
                        onMockModeToggled: function(checked) { if (apiTestVm) apiTestVm.mockMode = checked }
                        onAssertionsToggled: function(checked) { if (apiTestVm) apiTestVm.assertionsEnabled = checked }
                    }
                }
            }
        }
    }

    // ---- Overlays ----
    ApiEnvPopup {
        id: envPopup; dark: root.dark; panelBg: root.panelBg; panelBorder: root.panelBorder
        environments: vm.environments; currentEnvIndex: vm.currentEnvIndex
        envTagFn: ApiUtils.envTag; envTagColorFn: root.envTagColor
        onEnvironmentSelected: function(index) { if (apiTestVm) apiTestVm.currentEnvIndex = index }
        onManageRequested: envDialog.open()
    }
    ApiTabActionsPopup {
        id: tabActionsMenu; dark: root.dark; panelBg: root.panelBg
        onCloseAllRequested: if (apiTestVm) { apiTestVm.endpointTabs = []; apiTestVm.currentEndpointTab = -1 }
        onCloseCurrentRequested: if (apiTestVm) { apiTestVm.closeCurrentTab(); root.syncRequestActionBarFromCurrentTab() }
        onCloseOthersRequested: {
            if (!apiTestVm || vm.currentEndpointTab < 0 || vm.currentEndpointTab >= vm.endpointTabs.length) return
            var keep = vm.endpointTabs[vm.currentEndpointTab]
            apiTestVm.endpointTabs = [keep]
            apiTestVm.currentEndpointTab = 0
            root.syncRequestActionBarFromCurrentTab()
        }
    }
    EnvManagerDialog {
        id: envDialog; anchors.centerIn: Overlay.overlay
        dark: root.dark; environments: vm.environments; currentEnvIndex: vm.currentEnvIndex
        onEnvironmentsSaved: function(envs, selectedIndex) {
            if (!apiTestVm) return
            apiTestVm.environments = envs; apiTestVm.currentEnvIndex = selectedIndex
            apiTestVm.saveEnvironments(envs)
        }
    }
    FileDialog {
        id: openApiDialog; fileMode: FileDialog.OpenFile; nameFilters: ["OpenAPI (*.json *.yaml *.yml)"]
        onAccepted: {
            if (!apiTestVm) return
            var filePath = decodeURIComponent(selectedFile.toString()).replace("file:///", "")
            apiTestVm.importOpenApi(filePath)
        }
    }
    FileDialog {
        id: fileDialog; fileMode: FileDialog.OpenFile; title: "选择上传文件"
        onAccepted: {
            if (!apiTestVm) return
            var path = decodeURIComponent(selectedFile.toString()).replace("file:///", "")
            apiTestVm.bodyFilePath = path
        }
    }

    // ---- Connections ----
    Connections {
        target: apiTestVm
        function onApiImported(items) {
            apiTestVm.replaceCollectionTree(items, true)
            apiTestVm.loadCollectionTree()
        }
        function onApiEnvironmentsImported(items) {
            if (items.length > 0) { apiTestVm.environments = items; apiTestVm.currentEnvIndex = 0 }
        }
        function onEnvironmentsLoaded(items) { apiTestVm.environments = items }
        function onCollectionTreeLoaded(items) { apiTestVm.collectionTree = items }
        function onTabsLoaded(items) {
            if (items.length > 0) {
                apiTestVm.endpointTabs = items
                apiTestVm.currentEndpointTab = 0
                root.syncRequestActionBarFromCurrentTab()
            }
        }
        function onApiResponseReady(title, bodyText, details) {
            responsePanel.detailTab = 0
        }
        function onApiSendingChanged(sending) { apiTestVm.requestSending = sending }
        function onApiHistoryUpdated(items) { apiTestVm.apiHistory = items }
        function onWsTimelineLoaded(items) { apiTestVm.wsTimeline = items }
        function onDebugCasesLoaded(items) { apiTestVm.debugCases = items; apiTestVm.selectedDebugCaseIds = [] }
        function onDebugCasesRunCompleted(items) {
            if (items.length === 0) return
            var lines = []
            for (var i = 0; i < items.length; i++)
                lines.push("[" + items[i].name + "] " + items[i].title)
            apiTestVm.applyResponseDetails("批量运行结果", lines.join("\n"), {})
        }
    }
}
