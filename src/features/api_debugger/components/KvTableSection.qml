import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"
import "../api_utils.js" as ApiUtils

ColumnLayout {
    id: root

    spacing: 0
    Layout.fillWidth: true
    Layout.fillHeight: true

    property var rows: []
    property bool showTypeColumn: true
    property bool showTypeSelector: false
    property string fixedTypeText: "string"
    property int keyWidth: 180
    property int descWidth: 112
    property int checkWidth: 22
    property int typeWidth: 86
    property int magicWidth: 30
    property int deleteWidth: 26
    property int valueWeight: 7
    property bool magicEnabled: true
    property bool importEnabled: true
    property string sectionName: "query"
    property string keyTitle: "参数"
    property string valueTitle: "参数值"
    property string typeTitle: "类型"
    property string descTitle: "说明"
    property bool dark: false
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property color tableHeaderBg: Theme.token("color-table-header", dark)
    property int pendingValueFocusIndex: -1

    signal rowEnabledToggled(int index, bool checked)
    signal rowKeyCommitted(int index, string keyText)
    signal rowKeyEdited(int index, string keyText)
    signal rowTypeCommitted(int index, string typeText)
    signal rowValueCommitted(int index, string valueText)
    signal rowValueEdited(int index, string valueText)
    signal rowDescCommitted(int index, string descText)
    signal rowDeleteRequested(int index)
    signal rowValueFocused(int index)
    signal rowMagicInsertRequested(int index, string valueText)
    signal rowsImported(var rows)

    onRowsChanged: {
        if (pendingValueFocusIndex >= 0)
            Qt.callLater(root.restorePendingValueFocus)
    }

    function restorePendingValueFocus() {
        if (root.pendingValueFocusIndex < 0)
            return
        var row = rowsRepeater.itemAt(root.pendingValueFocusIndex)
        root.pendingValueFocusIndex = -1
        if (row && row.forceValueFocus)
            row.forceValueFocus()
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 34
        color: root.tableHeaderBg

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.space["2"]
            anchors.rightMargin: Theme.space["2"]
            spacing: Theme.space["2"]

            ApiKvTableHeader {
                Layout.fillWidth: true
                dark: root.dark
                textMuted: root.textMuted
                panelBorder: root.panelBorder
                tableHeaderBg: root.tableHeaderBg
                keyWidth: root.keyWidth
                descWidth: root.descWidth
                checkWidth: root.checkWidth
                typeWidth: root.typeWidth
                magicWidth: root.magicWidth
                deleteWidth: root.deleteWidth
                magicEnabled: root.magicEnabled
                valueWeight: root.valueWeight
                showTypeColumn: root.showTypeColumn
                keyTitle: root.keyTitle
                valueTitle: root.valueTitle
                typeTitle: root.typeTitle
                descTitle: root.descTitle
            }

            UiButton {
                visible: root.importEnabled
                text: "导入"
                dark: root.dark
                variant: "secondary"
                implicitWidth: 56
                implicitHeight: 26
                onClicked: importDialog.openForSection(root.sectionName, "导入" + root.keyTitle)
            }
        }
    }

    UiScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 0
            Repeater {
                id: rowsRepeater
                model: root.rows
                delegate: ApiKvRow {
                    required property int index
                    required property var modelData
                    dark: root.dark
                    textMain: root.textMain
                    textMuted: root.textMuted
                    panelBorder: root.panelBorder
                    rowData: modelData
                    sectionName: root.sectionName
                    showTypeColumn: root.showTypeColumn
                    showTypeSelector: root.showTypeSelector
                    fixedTypeText: root.fixedTypeText
                    keyWidth: root.keyWidth
                    descWidth: root.descWidth
                    checkWidth: root.checkWidth
                    typeWidth: root.typeWidth
                    magicWidth: root.magicWidth
                    deleteWidth: root.deleteWidth
                    valueWeight: root.valueWeight
                    magicEnabled: root.magicEnabled
                    onEnabledToggled: function(checked) { root.rowEnabledToggled(index, checked) }
                    onKeyCommitted: function(keyText, focusValueAfterCommit) {
                        root.pendingValueFocusIndex = focusValueAfterCommit ? index : -1
                        root.rowKeyCommitted(index, keyText)
                    }
                    onKeyEdited: function(keyText) { root.rowKeyEdited(index, keyText) }
                    onTypeCommitted: function(typeText) { root.rowTypeCommitted(index, typeText) }
                    onValueCommitted: function(valueText) { root.rowValueCommitted(index, valueText) }
                    onValueEdited: function(valueText) { root.rowValueEdited(index, valueText) }
                    onDescCommitted: function(descText) { root.rowDescCommitted(index, descText) }
                    onDeleteRequested: root.rowDeleteRequested(index)
                    onValueFocused: root.rowValueFocused(index)
                    onMagicInsertRequested: function(valueText) { root.rowMagicInsertRequested(index, valueText) }
                }
            }
        }
    }

    ApiKvImportDialog {
        id: importDialog
        dark: root.dark
        panelBg: Theme.token("color-bg-surface", root.dark)
        panelBorder: root.panelBorder
        textMain: root.textMain
        textMuted: root.textMuted
        onImportRequested: function(textValue, replaceExisting) {
            var parsed = ApiUtils.parseRowsBySection(root.sectionName, textValue)
            root.rowsImported(ApiUtils.mergeImportedRows(root.sectionName, root.rows, parsed, replaceExisting))
        }
    }
}
