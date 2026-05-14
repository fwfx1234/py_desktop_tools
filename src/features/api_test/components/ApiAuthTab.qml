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
    property string authTypeValue: "none"
    property string authValueText: ""

    signal authTypeChanged(string value)
    signal authValueChanged(string text)

    function setAuthValue(text) {
        authValueField.text = text
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s3
        spacing: Theme.spacing.s3

        RowLayout {
            spacing: Theme.spacing.s3
            Label {
                text: "认证方式"
                color: root.textMain
                font.pixelSize: Theme.typeScale.body
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

        UiTextField {
            id: authValueField
            dark: root.dark
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            text: root.authValueText
            placeholderText: "Token / Basic值 / API Key"
            onTextChanged: {
                root.authValueText = text
                root.authValueChanged(text)
            }
        }
        Label {
            text: "Bearer 会自动写入 Authorization 头"
            color: root.textMuted
            font.pixelSize: Theme.typeScale.caption
        }
        Item { Layout.fillHeight: true }
    }
}
