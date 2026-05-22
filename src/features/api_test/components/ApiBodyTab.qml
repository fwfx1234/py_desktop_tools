pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"
import "."

Item {
    id: root

    Layout.fillWidth: true
    Layout.fillHeight: true

    property bool dark: false
    property color panelBg
    property color panelBorder
    property color textMain
    property color textMuted
    property color textSubtle
    property color tableHeaderBg
    property var bodyModes: ["none", "x-www-form-urlencoded", "JSON", "XML", "Text", "file"]
    property int currentBodyMode: 0
    property var bodyFormRows: []
    property string bodyFilePath: ""
    property string bodyFileParamName: "file"
    property string bodyText: ""
    property int activeBodyRow: -1
    property bool showMagicPanel: false
    property bool _settingBodyText: false
    property bool _bodyInputReady: false

    signal bodyModeClicked(int index)
    signal bodyTextEdited(string text)
    signal formRowEnabledToggled(int index, bool checked)
    signal formRowKeyEdited(int index, string keyText)
    signal formRowKeyCommitted(int index, string keyText)
    signal formRowValueEdited(int index, string valueText)
    signal formRowValueCommitted(int index, string valueText)
    signal formRowDeleteRequested(int index)
    signal formRowValueFocused(int index)
    signal formRowsImported(var rows)
    signal fileBrowseClicked()
    signal fileParamNameEdited(string name)
    signal magicValueInsertRequested(string value)
    signal magicPanelToggleRequested()
    signal magicPanelCloseRequested()

    function currentBodyModeName() {
        if (currentBodyMode < 0 || currentBodyMode >= bodyModes.length)
            return "none"
        return bodyModes[currentBodyMode]
    }

    function usesBodyFormRows() {
        return currentBodyModeName() === "x-www-form-urlencoded"
    }

    function currentBodyModeIndexIsFile(idx) {
        return idx === 5
    }

    function setBodyText(text) {
        if (!root._bodyInputReady)
            return
        var next = text || ""
        if (bodyInput.text === next)
            return
        root._settingBodyText = true
        bodyInput.text = next
        root._settingBodyText = false
    }

    onBodyTextChanged: if (root._bodyInputReady) setBodyText(root.bodyText)

    function insertMagicValue(valueText) {
        if (!bodyInput.visible) {
            root.magicValueInsertRequested(valueText)
            return
        }
        var start = Math.min(bodyInput.selectionStart, bodyInput.selectionEnd)
        var end = Math.max(bodyInput.selectionStart, bodyInput.selectionEnd)
        if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
            start = bodyInput.cursorPosition
            end = bodyInput.cursorPosition
        }
        root._settingBodyText = true
        bodyInput.text = bodyInput.text.slice(0, start) + valueText + bodyInput.text.slice(end)
        bodyInput.cursorPosition = start + valueText.length
        root._settingBodyText = false
        root.bodyTextEdited(bodyInput.text)
        root.magicPanelCloseRequested()
    }

    Rectangle { anchors.fill: parent; color: root.panelBg }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: root.panelBg
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2"]

                Row {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: Theme.space["1"]
                    Repeater {
                        model: root.bodyModes
                        delegate: Rectangle {
                            id: bodyModeDelegate
                            required property int index
                            required property var modelData
                            radius: 10
                            height: 24
                            width: modeLabel.implicitWidth + 16
                            color: bodyModeDelegate.index === root.currentBodyMode
                                ? Theme.token("color-primary-active", root.dark)
                                : "transparent"
                            Label {
                                id: modeLabel
                                anchors.centerIn: parent
                                text: bodyModeDelegate.modelData
                                color: bodyModeDelegate.index === root.currentBodyMode ? "white" : root.textMuted
                                font.pixelSize: Theme.fontSize.caption
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.bodyModeClicked(bodyModeDelegate.index)
                            }
                        }
                    }
                }

                UiButton {
                    text: "魔法参数"
                    dark: root.dark
                    variant: root.showMagicPanel ? "primary" : "secondary"
                    implicitWidth: 86
                    implicitHeight: 28
                    visible: !root.usesBodyFormRows() && !root.currentBodyModeIndexIsFile(root.currentBodyMode)
                    onClicked: root.magicPanelToggleRequested()
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                visible: root.usesBodyFormRows()

                KvTableSection {
                    rows: root.bodyFormRows
                    keyTitle: "字段"
                    showTypeColumn: false
                    sectionName: "body"
                    keyWidth: 148
                    descWidth: 72
                    valueWeight: 8
                    dark: root.dark
                    textMain: root.textMain
                    textMuted: root.textMuted
                    panelBorder: root.panelBorder
                    tableHeaderBg: root.tableHeaderBg
                    onRowEnabledToggled: function(index, checked) { root.formRowEnabledToggled(index, checked) }
                    onRowKeyEdited: function(index, keyText) { root.formRowKeyEdited(index, keyText) }
                    onRowKeyCommitted: function(index, keyText) { root.formRowKeyCommitted(index, keyText) }
                    onRowValueEdited: function(index, valueText) { root.formRowValueEdited(index, valueText) }
                    onRowValueCommitted: function(index, valueText) { root.formRowValueCommitted(index, valueText) }
                    onRowValueFocused: function(index) { root.formRowValueFocused(index) }
                    onRowDeleteRequested: function(index) { root.formRowDeleteRequested(index) }
                    onRowsImported: function(rows) { root.formRowsImported(rows) }
                }
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.space["2.5"]
                visible: root.currentBodyModeIndexIsFile(root.currentBodyMode)
                anchors.margins: Theme.space["3"]

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 92
                    radius: Theme.radii.xs
                    color: Theme.token("color-bg-subtle", root.dark)
                    border.width: 1
                    border.color: root.panelBorder

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.space["2.5"]
                        spacing: Theme.space["2"]

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["2"]
                            Label {
                                Layout.preferredWidth: 58
                                text: "文件路径"
                                color: root.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                verticalAlignment: Text.AlignVCenter
                            }
                            UiTextField {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30
                                dark: root.dark
                                text: root.bodyFilePath
                                placeholderText: "选择要上传的文件..."
                                readOnly: true
                                font.family: Theme.fontFamily.mono
                            }
                            UiButton {
                                text: "浏览"
                                dark: root.dark
                                variant: "secondary"
                                implicitWidth: 60
                                implicitHeight: 30
                                onClicked: root.fileBrowseClicked()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["2"]
                            Label {
                                Layout.preferredWidth: 58
                                text: "参数名"
                                color: root.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                verticalAlignment: Text.AlignVCenter
                            }
                            UiTextField {
                                id: fileParamField
                                Layout.preferredWidth: 220
                                Layout.preferredHeight: 30
                                dark: root.dark
                                text: root.bodyFileParamName
                                placeholderText: "file"
                                font.family: Theme.fontFamily.mono
                                onEditingFinished: root.fileParamNameEdited(text.trim() || "file")
                            }
                            ApiMagicInsertButton {
                                dark: root.dark
                                panelBg: root.panelBg
                                panelBorder: root.panelBorder
                                textMain: root.textMain
                                textMuted: root.textMuted
                                onInsertRequested: function(valueText) {
                                    var start = Math.min(fileParamField.selectionStart, fileParamField.selectionEnd)
                                    var end = Math.max(fileParamField.selectionStart, fileParamField.selectionEnd)
                                    if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
                                        start = fileParamField.cursorPosition
                                        end = fileParamField.cursorPosition
                                    }
                                    fileParamField.text = fileParamField.text.slice(0, start) + valueText + fileParamField.text.slice(end)
                                    fileParamField.cursorPosition = start + valueText.length
                                    fileParamField.forceActiveFocus()
                                    root.fileParamNameEdited(fileParamField.text.trim() || "file")
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }

                Label {
                    visible: root.bodyFilePath.length === 0
                    text: "选择文件后将以 multipart/form-data 方式上传"
                    color: root.textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }
            }

            UiTextArea {
                id: bodyInput
                anchors.fill: parent
                visible: !root.usesBodyFormRows() && !root.currentBodyModeIndexIsFile(root.currentBodyMode)
                dark: root.dark
                placeholderText: "{\n  \"k\": \"v\"\n}"
                wrapMode: TextEdit.NoWrap
                onTextChanged: {
                    if (!root._settingBodyText && root._bodyInputReady)
                        root.bodyTextEdited(text)
                }
                Component.onCompleted: {
                    root._settingBodyText = true
                    bodyInput.text = root.bodyText || ""
                    root._settingBodyText = false
                    root._bodyInputReady = true
                }
            }

            ApiMagicValuePanel {
                visible: root.showMagicPanel
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.rightMargin: Theme.space["2.5"]
                width: Math.min(352, parent.width - Theme.space["5"])
                height: Math.min(386, parent.height - Theme.space["5"])
                z: 20
                dark: root.dark
                panelBg: root.panelBg
                panelBorder: root.panelBorder
                textMain: root.textMain
                textMuted: root.textMuted
                onInsertRequested: function(valueText) { root.insertMagicValue(valueText) }
                onCloseRequested: root.magicPanelCloseRequested()
            }
        }
    }
}
