import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Item {
    id: root

    Layout.fillWidth: true
    Layout.fillHeight: true

    property bool dark: false
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBg: Theme.token("color-bg-surface", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property string authTypeValue: "none"
    property string authValueText: ""

    signal authTypeChanged(string value)
    signal authValueChanged(string text)

    function setAuthValue(text) {
        authValueField.text = text
    }

    function insertMagicValue(valueText) {
        var start = Math.min(authValueField.selectionStart, authValueField.selectionEnd)
        var end = Math.max(authValueField.selectionStart, authValueField.selectionEnd)
        if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
            start = authValueField.cursorPosition
            end = authValueField.cursorPosition
        }
        authValueField.text = authValueField.text.slice(0, start) + valueText + authValueField.text.slice(end)
        authValueField.cursorPosition = start + valueText.length
        authValueField.forceActiveFocus()
        root.authValueChanged(authValueField.text)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["2.5"]
        spacing: Theme.space["2.5"]

        RowLayout {
            spacing: Theme.space["2.5"]
            Label {
                text: "认证方式"
                color: root.textMain
                font.pixelSize: Theme.fontSize.body
            }
            UiComboBox {
                id: authTypeCombo
                dark: root.dark
                model: [
                    { text: "None", value: "none" },
                    { text: "Bearer Token", value: "bearer" },
                    { text: "Basic", value: "basic" },
                    { text: "API Key", value: "apikey" }
                ]
                textRole: "text"
                valueRole: "value"
                currentValue: root.authTypeValue
                Layout.preferredWidth: 220
                Layout.preferredHeight: 30
                onCurrentValueChanged: {
                    root.authTypeValue = currentValue
                    root.authTypeChanged(currentValue)
                }
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 30

            UiTextField {
                id: authValueField
                dark: root.dark
                Layout.fillWidth: true
                text: root.authValueText
                placeholderText: "Token / Basic值 / API Key"
                onTextChanged: {
                    root.authValueText = text
                    root.authValueChanged(text)
                }
            }

            ApiMagicInsertButton {
                dark: root.dark
                panelBg: root.panelBg
                panelBorder: root.panelBorder
                textMain: root.textMain
                textMuted: root.textMuted
                onInsertRequested: function(valueText) { root.insertMagicValue(valueText) }
            }
        }
        Label {
            text: "Bearer 会自动写入 Authorization 头"
            color: root.textMuted
            font.pixelSize: Theme.fontSize.caption
        }
        Item { Layout.fillHeight: true }
    }
}
