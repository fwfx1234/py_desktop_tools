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

    signal bodyModeClicked(int index)
    signal bodyTextEdited(string text)
    signal formRowEnabledToggled(int index, bool checked)
    signal formRowKeyCommitted(int index, string keyText)
    signal formRowValueCommitted(int index, string valueText)
    signal formRowDeleteRequested(int index)
    signal formRowValueFocused(int index)
    signal fileBrowseClicked()
    signal fileParamNameEdited(string name)
    signal magicValueInsertRequested(string value)
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
        bodyInput.text = text
    }

    Rectangle { anchors.fill: parent; color: root.panelBg }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: root.panelBg
            Row {
                anchors.left: parent.left
                anchors.leftMargin: Theme.spacing.s3
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.spacing.s3
                Repeater {
                    model: root.bodyModes
                    delegate: Rectangle {
                        required property int index
                        required property var modelData
                        radius: 10
                        height: 24
                        width: modeLabel.implicitWidth + 16
                        color: index === root.currentBodyMode
                            ? Theme.token("color-primary-active", root.dark)
                            : "transparent"
                        Label {
                            id: modeLabel
                            anchors.centerIn: parent
                            text: modelData
                            color: index === root.currentBodyMode ? "white" : root.textMuted
                            font.pixelSize: Theme.typeScale.caption
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.bodyModeClicked(index)
                        }
                    }
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
                    keyWidth: 220
                    descWidth: 180
                    dark: root.dark
                    textMain: root.textMain
                    textMuted: root.textMuted
                    panelBorder: root.panelBorder
                    tableHeaderBg: root.tableHeaderBg
                    onRowEnabledToggled: function(index, checked) { root.formRowEnabledToggled(index, checked) }
                    onRowKeyCommitted: function(index, keyText) { root.formRowKeyCommitted(index, keyText) }
                    onRowValueCommitted: function(index, valueText) { root.formRowValueCommitted(index, valueText) }
                    onRowValueFocused: function(index) { root.formRowValueFocused(index) }
                    onRowDeleteRequested: function(index) { root.formRowDeleteRequested(index) }
                }
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacing.s2
                visible: root.currentBodyModeIndexIsFile(root.currentBodyMode)
                anchors.margins: Theme.spacing.s3

                RowLayout {
                    Label {
                        text: "文件路径"
                        color: root.textMain
                        font.pixelSize: Theme.typeScale.body
                    }
                    UiTextField {
                        Layout.fillWidth: true
                        dark: root.dark
                        text: root.bodyFilePath
                        placeholderText: "选择要上传的文件..."
                        readOnly: true
                    }
                    UiButton {
                        text: "浏览"
                        dark: root.dark
                        variant: "secondary"
                        implicitWidth: 64
                        implicitHeight: 30
                        onClicked: root.fileBrowseClicked()
                    }
                }

                RowLayout {
                    Label {
                        text: "参数名"
                        color: root.textMain
                        font.pixelSize: Theme.typeScale.body
                    }
                    UiTextField {
                        Layout.preferredWidth: 180
                        dark: root.dark
                        text: root.bodyFileParamName
                        placeholderText: "file"
                        onEditingFinished: root.fileParamNameEdited(text.trim() || "file")
                    }
                    Item { Layout.fillWidth: true }
                }

                Label {
                    visible: root.bodyFilePath.length === 0
                    text: "选择文件后将以 multipart/form-data 方式上传"
                    color: root.textSubtle
                    font.pixelSize: Theme.typeScale.caption
                }
            }

            UiTextArea {
                id: bodyInput
                anchors.fill: parent
                visible: !root.usesBodyFormRows() && !root.currentBodyModeIndexIsFile(root.currentBodyMode)
                dark: root.dark
                placeholderText: "{\n  \"k\": \"v\"\n}"
                wrapMode: TextEdit.NoWrap
                text: root.bodyText
                onTextChanged: root.bodyTextEdited(text)
            }

            ApiMagicValuePanel {
                visible: root.showMagicPanel
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.rightMargin: Theme.spacing.s3
                width: 320
                height: 286
                z: 20
                dark: root.dark
                panelBg: root.panelBg
                panelBorder: root.panelBorder
                textMain: root.textMain
                textMuted: root.textMuted
                onInsertRequested: function(valueText) { root.magicValueInsertRequested(valueText) }
                onCloseRequested: root.magicPanelCloseRequested()
            }
        }
    }
}
