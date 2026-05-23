import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

ColumnLayout {
    id: root

    spacing: 0
    Layout.fillWidth: true
    Layout.fillHeight: true

    property var backend: null
    property var vm: null
    property bool dark: false
    property color panelBg: Theme.token("color-bg-surface", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color textSubtle: Theme.token("color-text-secondary", dark)
    property color tableHeaderBg: Theme.token("color-table-header", dark)
    property int currentTab: 0
    property int activeBodyRow: -1
    property bool showMagicPanel: false
    property string currentMethod: "GET"
    property var methodColorFn: null

    signal tabSelected(int index)
    signal fileBrowseClicked()
    signal saveAsCaseClicked()
    signal batchRunClicked()
    signal caseSelectionToggled(string caseId, bool checked)
    signal historyRestoreRequested(string methodText, string urlText)
    signal bodyRowFocused(int index)
    signal magicPanelToggleRequested()
    signal magicValueInsertRequested(string valueText)
    signal magicPanelCloseRequested()

    function insertPreOpsMagic(valueText) {
        var start = Math.min(preOpsInput.selectionStart, preOpsInput.selectionEnd)
        var end = Math.max(preOpsInput.selectionStart, preOpsInput.selectionEnd)
        if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
            start = preOpsInput.cursorPosition
            end = preOpsInput.cursorPosition
        }
        preOpsInput.text = preOpsInput.text.slice(0, start) + valueText + preOpsInput.text.slice(end)
        preOpsInput.cursorPosition = start + valueText.length
        preOpsInput.forceActiveFocus()
        if (root.backend)
            root.backend.preOpsText = preOpsInput.text
    }

    function insertPostOpsMagic(valueText) {
        var start = Math.min(postOpsInput.selectionStart, postOpsInput.selectionEnd)
        var end = Math.max(postOpsInput.selectionStart, postOpsInput.selectionEnd)
        if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
            start = postOpsInput.cursorPosition
            end = postOpsInput.cursorPosition
        }
        postOpsInput.text = postOpsInput.text.slice(0, start) + valueText + postOpsInput.text.slice(end)
        postOpsInput.cursorPosition = start + valueText.length
        postOpsInput.forceActiveFocus()
        if (root.backend)
            root.backend.postOpsText = postOpsInput.text
    }

    function countRows(rows) {
        var total = 0
        for (var i = 0; rows && i < rows.length; i++) {
            var row = rows[i] || {}
            if ((row.key || "").length > 0 || (row.value || "").length > 0)
                total += 1
        }
        return total
    }

    function bodyCount() {
        if (!root.vm)
            return 0
        if (root.vm.currentBodyMode === 1)
            return countRows(root.vm.bodyFormRows)
        if (root.vm.currentBodyMode === 5)
            return ((root.vm.bodyFilePath || "").length > 0 || (root.vm.bodyFileParamName || "").length > 0) ? 1 : 0
        return (root.vm.bodyText || "").trim().length > 0 ? 1 : 0
    }

    function requestTabCounts() {
        if (!root.vm)
            return [0, 0, 0, 0, 0, 0, 0, 0, 0]
        return [
            countRows(root.vm.queryParams),
            countRows(root.vm.pathParams),
            bodyCount(),
            countRows(root.vm.headersRows),
            countRows(root.vm.cookieRows),
            (root.vm.authTypeValue || "none") !== "none" || (root.vm.authValueText || "").length > 0 ? 1 : 0,
            (root.vm.preOpsText || "").trim().length > 0 ? 1 : 0,
            (root.vm.postOpsText || "").trim().length > 0 ? 1 : 0,
            0
        ]
    }

    ApiRequestTabsBar {
        Layout.fillWidth: true
        Layout.preferredHeight: 34
        dark: root.dark
        panelBg: root.panelBg
        textMain: root.textMain
        textMuted: root.textMuted
        currentTab: root.currentTab
        tabCounts: root.requestTabCounts()
        onTabChanged: function(index) { root.tabSelected(index) }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

    StackLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: root.currentTab

        KvTableSection {
            rows: root.vm ? root.vm.queryParams : []
            showTypeSelector: true
            sectionName: "query"
            keyWidth: 148
            typeWidth: 74
            descWidth: 72
            valueWeight: 8
            dark: root.dark
            textMain: root.textMain
            textMuted: root.textMuted
            panelBorder: root.panelBorder
            tableHeaderBg: root.tableHeaderBg
            onRowEnabledToggled: function(index, checked) { if (root.backend) root.backend.toggleSectionRowEnabled("query", index, checked) }
            onRowKeyEdited: function(index, keyText) { if (root.backend) root.backend.editSectionRowKeyLive("query", index, keyText) }
            onRowKeyCommitted: function(index, keyText) { if (root.backend) root.backend.editSectionRowKey("query", index, keyText) }
            onRowValueEdited: function(index, valueText) { if (root.backend) root.backend.editSectionRowValueLive("query", index, valueText) }
            onRowValueCommitted: function(index, valueText) { if (root.backend) root.backend.editSectionRowValue("query", index, valueText) }
            onRowDeleteRequested: function(index) { if (root.backend) root.backend.deleteSectionRow("query", index) }
            onRowsImported: function(rows) { if (root.backend) root.backend.queryParams = rows }
        }

        KvTableSection {
            rows: root.vm ? root.vm.pathParams : []
            keyTitle: "路径参数"
            sectionName: "path"
            keyWidth: 148
            typeWidth: 74
            descWidth: 72
            valueWeight: 8
            dark: root.dark
            textMain: root.textMain
            textMuted: root.textMuted
            panelBorder: root.panelBorder
            tableHeaderBg: root.tableHeaderBg
            onRowEnabledToggled: function(index, checked) { if (root.backend) root.backend.toggleSectionRowEnabled("path", index, checked) }
            onRowKeyEdited: function(index, keyText) { if (root.backend) root.backend.editSectionRowKeyLive("path", index, keyText) }
            onRowKeyCommitted: function(index, keyText) { if (root.backend) root.backend.editSectionRowKey("path", index, keyText) }
            onRowValueEdited: function(index, valueText) { if (root.backend) root.backend.editSectionRowValueLive("path", index, valueText) }
            onRowValueCommitted: function(index, valueText) { if (root.backend) root.backend.editSectionRowValue("path", index, valueText) }
            onRowDeleteRequested: function(index) { if (root.backend) root.backend.deleteSectionRow("path", index) }
            onRowsImported: function(rows) { if (root.backend) root.backend.pathParams = rows }
        }

        ApiBodyTab {
            dark: root.dark
            panelBg: root.panelBg
            panelBorder: root.panelBorder
            textMain: root.textMain
            textMuted: root.textMuted
            textSubtle: root.textSubtle
            tableHeaderBg: root.tableHeaderBg
            bodyModes: root.vm ? root.vm.bodyModes : []
            currentBodyMode: root.vm ? root.vm.currentBodyMode : 0
            bodyFormRows: root.vm ? root.vm.bodyFormRows : []
            bodyText: root.vm ? root.vm.bodyText : ""
            bodyFilePath: root.vm ? root.vm.bodyFilePath : ""
            bodyFileParamName: root.vm ? root.vm.bodyFileParamName : "file"
            activeBodyRow: root.activeBodyRow
            showMagicPanel: root.showMagicPanel
            onBodyModeClicked: function(index) { if (root.backend) root.backend.setCurrentBodyMode(index) }
            onBodyTextEdited: function(text) { if (root.backend) root.backend.bodyText = text }
            onFormRowEnabledToggled: function(index, checked) { if (root.backend) root.backend.toggleSectionRowEnabled("body", index, checked) }
            onFormRowKeyEdited: function(index, keyText) { if (root.backend) root.backend.editSectionRowKeyLive("body", index, keyText) }
            onFormRowKeyCommitted: function(index, keyText) { if (root.backend) root.backend.editSectionRowKey("body", index, keyText) }
            onFormRowValueEdited: function(index, valueText) { if (root.backend) root.backend.editSectionRowValueLive("body", index, valueText) }
            onFormRowValueCommitted: function(index, valueText) { if (root.backend) root.backend.editSectionRowValue("body", index, valueText) }
            onFormRowDeleteRequested: function(index) { if (root.backend) root.backend.deleteSectionRow("body", index) }
            onFormRowValueFocused: function(index) { root.bodyRowFocused(index) }
            onFormRowsImported: function(rows) { if (root.backend) root.backend.bodyFormRows = rows }
            onFileBrowseClicked: root.fileBrowseClicked()
            onFileParamNameEdited: function(name) { if (root.backend) root.backend.bodyFileParamName = name }
            onMagicPanelToggleRequested: root.magicPanelToggleRequested()
            onMagicValueInsertRequested: function(value) { root.magicValueInsertRequested(value) }
            onMagicPanelCloseRequested: root.magicPanelCloseRequested()
        }

        KvTableSection {
            rows: root.vm ? root.vm.headersRows : []
            keyTitle: "Header"
            showTypeColumn: false
            sectionName: "headers"
            keyWidth: 156
            descWidth: 72
            valueWeight: 8
            dark: root.dark
            textMain: root.textMain
            textMuted: root.textMuted
            panelBorder: root.panelBorder
            tableHeaderBg: root.tableHeaderBg
            onRowEnabledToggled: function(index, checked) { if (root.backend) root.backend.toggleSectionRowEnabled("headers", index, checked) }
            onRowKeyEdited: function(index, keyText) { if (root.backend) root.backend.editSectionRowKeyLive("headers", index, keyText) }
            onRowKeyCommitted: function(index, keyText) { if (root.backend) root.backend.editSectionRowKey("headers", index, keyText) }
            onRowValueEdited: function(index, valueText) { if (root.backend) root.backend.editSectionRowValueLive("headers", index, valueText) }
            onRowValueCommitted: function(index, valueText) { if (root.backend) root.backend.editSectionRowValue("headers", index, valueText) }
            onRowDeleteRequested: function(index) { if (root.backend) root.backend.deleteSectionRow("headers", index) }
            onRowsImported: function(rows) { if (root.backend) root.backend.headersRows = rows }
        }

        KvTableSection {
            rows: root.vm ? root.vm.cookieRows : []
            keyTitle: "Cookie"
            showTypeColumn: false
            sectionName: "cookies"
            keyWidth: 148
            descWidth: 72
            valueWeight: 8
            dark: root.dark
            textMain: root.textMain
            textMuted: root.textMuted
            panelBorder: root.panelBorder
            tableHeaderBg: root.tableHeaderBg
            onRowEnabledToggled: function(index, checked) { if (root.backend) root.backend.toggleSectionRowEnabled("cookies", index, checked) }
            onRowKeyEdited: function(index, keyText) { if (root.backend) root.backend.editSectionRowKeyLive("cookies", index, keyText) }
            onRowKeyCommitted: function(index, keyText) { if (root.backend) root.backend.editSectionRowKey("cookies", index, keyText) }
            onRowValueEdited: function(index, valueText) { if (root.backend) root.backend.editSectionRowValueLive("cookies", index, valueText) }
            onRowValueCommitted: function(index, valueText) { if (root.backend) root.backend.editSectionRowValue("cookies", index, valueText) }
            onRowDeleteRequested: function(index) { if (root.backend) root.backend.deleteSectionRow("cookies", index) }
            onRowsImported: function(rows) { if (root.backend) root.backend.cookieRows = rows }
        }

        ApiAuthTab {
            dark: root.dark
            textMain: root.textMain
            textMuted: root.textMuted
            panelBg: root.panelBg
            panelBorder: root.panelBorder
            authTypeValue: root.vm ? root.vm.authTypeValue : "none"
            authValueText: root.vm ? root.vm.authValueText : ""
            onAuthTypeChanged: function(value) { if (root.backend) root.backend.authTypeValue = value }
            onAuthValueChanged: function(text) { if (root.backend) root.backend.authValueText = text }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            property bool _settingPreOps: false
            property bool _preOpsReady: false
            UiTextArea {
                id: preOpsInput
                anchors.fill: parent
                anchors.margins: Theme.space["2"]
                dark: root.dark
                placeholderText: "key: value"
                wrapMode: TextEdit.NoWrap
                onTextChanged: {
                    if (!parent._settingPreOps && parent._preOpsReady && root.backend)
                        root.backend.preOpsText = text
                }
                Component.onCompleted: {
                    parent._settingPreOps = true
                    preOpsInput.text = (root.vm ? root.vm.preOpsText : "") || ""
                    parent._settingPreOps = false
                    parent._preOpsReady = true
                }
                Connections {
                    target: root.vm
                    function onEditorChanged() {
                        if (!parent || !parent._preOpsReady)
                            return
                        var next = root.vm ? (root.vm.preOpsText || "") : ""
                        if (preOpsInput.text === next)
                            return
                        parent._settingPreOps = true
                        preOpsInput.text = next
                        parent._settingPreOps = false
                    }
                }
            }
            ApiMagicInsertButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2.5"]
                dark: root.dark
                panelBg: root.panelBg
                panelBorder: root.panelBorder
                textMain: root.textMain
                textMuted: root.textMuted
                onInsertRequested: function(valueText) { root.insertPreOpsMagic(valueText) }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            property bool _settingPostOps: false
            property bool _postOpsReady: false
            UiTextArea {
                id: postOpsInput
                anchors.fill: parent
                anchors.margins: Theme.space["2"]
                dark: root.dark
                placeholderText: "status == 200\nbody contains \"ok\""
                wrapMode: TextEdit.NoWrap
                onTextChanged: {
                    if (!parent._settingPostOps && parent._postOpsReady && root.backend)
                        root.backend.postOpsText = text
                }
                Component.onCompleted: {
                    parent._settingPostOps = true
                    postOpsInput.text = (root.vm ? root.vm.postOpsText : "") || ""
                    parent._settingPostOps = false
                    parent._postOpsReady = true
                }
                Connections {
                    target: root.vm
                    function onEditorChanged() {
                        if (!parent || !parent._postOpsReady)
                            return
                        var next = root.vm ? (root.vm.postOpsText || "") : ""
                        if (postOpsInput.text === next)
                            return
                        parent._settingPostOps = true
                        postOpsInput.text = next
                        parent._settingPostOps = false
                    }
                }
            }
            ApiMagicInsertButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2.5"]
                dark: root.dark
                panelBg: root.panelBg
                panelBorder: root.panelBorder
                textMain: root.textMain
                textMuted: root.textMuted
                onInsertRequested: function(valueText) { root.insertPostOpsMagic(valueText) }
            }
        }

        ApiSettingsTab {
            dark: root.dark
            textMain: root.textMain
            textSubtle: root.textSubtle
            debugCases: root.vm ? root.vm.debugCases : []
            selectedDebugCaseIds: root.vm ? root.vm.selectedDebugCaseIds : []
            apiHistory: root.vm ? root.vm.apiHistory : []
            wsTimeline: root.vm ? root.vm.wsTimeline : []
            wsStatusText: root.vm ? root.vm.wsStatusText : "未连接"
            currentMethod: root.currentMethod
            methodColorFn: root.methodColorFn
            onSaveAsCaseClicked: root.saveAsCaseClicked()
            onBatchRunClicked: root.batchRunClicked()
            onCaseSelectionToggled: function(caseId, checked) { root.caseSelectionToggled(caseId, checked) }
            onHistoryRestoreRequested: function(methodText, urlText) { root.historyRestoreRequested(methodText, urlText) }
        }
    }
}
