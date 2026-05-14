import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property var rowData: ({})
    property int checkWidth: 22
    property int keyWidth: 210
    property int valueWeight: 2
    property int typeWidth: 86
    property int descWidth: 180
    property int deleteWidth: 26
    property int rowHeight: 36
    property bool showTypeSelector: false
    property bool showTypeColumn: true
    property var typeOptions: ["string", "number", "boolean", "array", "object"]
    property string fixedTypeText: "string"
    property color fieldHoverBg: Theme.token("color-bg-subtle-2", dark)
    property color fieldFocusBg: Theme.token("color-bg-surface", dark)

    signal enabledToggled(bool checked)
    signal keyCommitted(string keyText)
    signal valueCommitted(string valueText)
    signal typeCommitted(string typeText)
    signal descCommitted(string descText)
    signal deleteRequested()
    signal valueFocused()

    Layout.fillWidth: true
    Layout.preferredHeight: root.rowHeight
    color: "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.s4
        anchors.rightMargin: Theme.spacing.s4
        spacing: Theme.spacing.s3

        UiCheckBox {
            dark: root.dark
            checked: root.rowData.enabled !== false
            Layout.preferredWidth: root.checkWidth
            onToggled: root.enabledToggled(checked)
        }

        TextField {
            id: keyField
            Layout.preferredWidth: root.keyWidth
            text: root.rowData.key || ""
            hoverEnabled: true
            leftPadding: Theme.spacing.s2
            rightPadding: Theme.spacing.s2
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radius.xs
                color: keyField.activeFocus
                    ? root.fieldFocusBg
                    : (keyField.hovered ? root.fieldHoverBg : "transparent")
                border.width: keyField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: "JetBrains Mono"
            placeholderText: "Key"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.keyCommitted(text)
        }

        TextField {
            id: valueField
            Layout.fillWidth: true
            Layout.horizontalStretchFactor: root.valueWeight
            text: root.rowData.value || ""
            hoverEnabled: true
            leftPadding: Theme.spacing.s2
            rightPadding: Theme.spacing.s2
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radius.xs
                color: valueField.activeFocus
                    ? root.fieldFocusBg
                    : (valueField.hovered ? root.fieldHoverBg : "transparent")
                border.width: valueField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: "JetBrains Mono"
            placeholderText: "Value"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.valueCommitted(text)
            onActiveFocusChanged: if (activeFocus) root.valueFocused()
        }

        Loader {
            visible: root.showTypeColumn
            Layout.preferredWidth: root.showTypeColumn ? root.typeWidth : 0
            sourceComponent: root.showTypeColumn ? (root.showTypeSelector ? typeEditor : typeLabel) : null
        }

        Component {
            id: typeLabel
            Label {
                text: root.fixedTypeText
                color: root.textMuted
                font.family: "JetBrains Mono"
                font.pixelSize: Theme.typeScale.caption
                verticalAlignment: Text.AlignVCenter
            }
        }

        Component {
            id: typeEditor
            ApiTypeSelector {
                dark: root.dark
                model: root.typeOptions
                value: root.rowData.type || "string"
                textMain: root.textMain
                textMuted: root.textMuted
                width: root.typeWidth
                height: 26
                onValueCommitted: function(valueText) { root.typeCommitted(valueText) }
            }
        }

        TextField {
            id: descField
            Layout.preferredWidth: root.descWidth
            text: root.rowData.desc || ""
            hoverEnabled: true
            leftPadding: Theme.spacing.s2
            rightPadding: Theme.spacing.s2
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radius.xs
                color: descField.activeFocus
                    ? root.fieldFocusBg
                    : (descField.hovered ? root.fieldHoverBg : "transparent")
                border.width: descField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: "JetBrains Mono"
            placeholderText: "Description"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.descCommitted(text)
        }

        ApiDeleteButton {
            dark: root.dark
            iconColor: root.textMuted
            dangerColor: Theme.token("color-danger", root.dark)
            Layout.preferredWidth: root.deleteWidth
            onDeleteRequested: root.deleteRequested()
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: root.panelBorder
    }
}
