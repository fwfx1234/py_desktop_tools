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

    property var rows: []
    property bool showTypeColumn: true
    property bool showTypeSelector: false
    property string fixedTypeText: "string"
    property int keyWidth: 210
    property int descWidth: 180
    property int checkWidth: 22
    property int typeWidth: 86
    property int deleteWidth: 26
    property int valueWeight: 2
    property string keyTitle: "参数"
    property string valueTitle: "参数值"
    property string typeTitle: "类型"
    property string descTitle: "说明"
    property bool dark: false
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property color tableHeaderBg: Theme.token("color-table-header", dark)

    signal rowEnabledToggled(int index, bool checked)
    signal rowKeyCommitted(int index, string keyText)
    signal rowTypeCommitted(int index, string typeText)
    signal rowValueCommitted(int index, string valueText)
    signal rowDescCommitted(int index, string descText)
    signal rowDeleteRequested(int index)
    signal rowValueFocused(int index)

    ApiKvTableHeader {
        dark: root.dark
        textMuted: root.textMuted
        panelBorder: root.panelBorder
        tableHeaderBg: root.tableHeaderBg
        keyWidth: root.keyWidth
        descWidth: root.descWidth
        checkWidth: root.checkWidth
        typeWidth: root.typeWidth
        deleteWidth: root.deleteWidth
        valueWeight: root.valueWeight
        showTypeColumn: root.showTypeColumn
        keyTitle: root.keyTitle
        valueTitle: root.valueTitle
        typeTitle: root.typeTitle
        descTitle: root.descTitle
    }

    UiScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 0
            Repeater {
                model: root.rows
                delegate: ApiKvRow {
                    required property int index
                    required property var modelData
                    dark: root.dark
                    textMain: root.textMain
                    textMuted: root.textMuted
                    panelBorder: root.panelBorder
                    rowData: modelData
                    showTypeColumn: root.showTypeColumn
                    showTypeSelector: root.showTypeSelector
                    fixedTypeText: root.fixedTypeText
                    keyWidth: root.keyWidth
                    descWidth: root.descWidth
                    checkWidth: root.checkWidth
                    typeWidth: root.typeWidth
                    deleteWidth: root.deleteWidth
                    valueWeight: root.valueWeight
                    onEnabledToggled: function(checked) { root.rowEnabledToggled(index, checked) }
                    onKeyCommitted: function(keyText) { root.rowKeyCommitted(index, keyText) }
                    onTypeCommitted: function(typeText) { root.rowTypeCommitted(index, typeText) }
                    onValueCommitted: function(valueText) { root.rowValueCommitted(index, valueText) }
                    onDescCommitted: function(descText) { root.rowDescCommitted(index, descText) }
                    onDeleteRequested: root.rowDeleteRequested(index)
                    onValueFocused: root.rowValueFocused(index)
                }
            }
        }
    }
}
