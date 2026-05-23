import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Dialog {
    id: dialog

    property bool dark: false
    property color panelBg: Theme.token("color-bg-surface", dark)
    property color panelBorder: Theme.token("color-border-default", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color textSubtle: Theme.token("color-text-secondary", dark)
    property string sectionName: "query"
    property string titleText: "导入参数"
    property bool replaceExisting: false

    signal importRequested(string textValue, bool replaceExisting)

    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    width: Math.min(620, Overlay.overlay ? Overlay.overlay.width * 0.7 : 620)
    height: Math.min(440, Overlay.overlay ? Overlay.overlay.height * 0.72 : 440)
    padding: 0

    function openForSection(name, title) {
        dialog.sectionName = name || "query"
        dialog.titleText = title || "导入参数"
        input.text = ""
        dialog.replaceExisting = false
        open()
        Qt.callLater(function() { input.forceActiveFocus() })
    }

    function placeholder() {
        if (dialog.sectionName === "headers")
            return "Authorization: Bearer {{token}}\nContent-Type: application/json"
        if (dialog.sectionName === "cookies")
            return "token=abc; locale=zh-CN"
        if (dialog.sectionName === "query")
            return "https://example.com/users?page=1&size=20\n或\npage=1\nsize=20"
        return "id=123\nname=demo"
    }

    background: Rectangle {
        color: dialog.panelBg
        radius: Theme.radii.md
        border.width: 1
        border.color: dialog.panelBorder
    }

    contentItem: Rectangle {
        color: dialog.panelBg
        radius: Theme.radii.md
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                color: dialog.panelBg
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["3"]
                    anchors.rightMargin: Theme.space["2"]
                    spacing: Theme.space["2"]

                    Label {
                        Layout.fillWidth: true
                        text: dialog.titleText
                        color: dialog.textMain
                        font.pixelSize: Theme.fontSize.heading
                        font.bold: true
                    }

                    UiButton {
                        text: "关闭"
                        dark: dialog.dark
                        variant: "ghost"
                        implicitWidth: 56
                        implicitHeight: 28
                        onClicked: dialog.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.panelBorder }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: Theme.space["3"]
                spacing: Theme.space["2"]

                UiTextArea {
                    id: input
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    dark: dialog.dark
                    wrapMode: TextEdit.NoWrap
                    placeholderText: dialog.placeholder()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["2"]

                    RowLayout {
                        id: replaceCheckRow
                        spacing: Theme.space["1"]

                        UiCheckBox {
                            id: replaceCheck
                            dark: dialog.dark
                            checked: dialog.replaceExisting
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 30
                            onToggled: dialog.replaceExisting = checked
                        }

                        Label {
                            text: "覆盖现有参数"
                            color: Theme.token("color-text-primary", dialog.dark)
                            font.pixelSize: Theme.fontSize.body
                            verticalAlignment: Text.AlignVCenter

                            TapHandler {
                                gesturePolicy: TapHandler.ReleaseWithinBounds
                                onTapped: replaceCheck.toggle()
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    UiButton {
                        text: "取消"
                        dark: dialog.dark
                        variant: "secondary"
                        implicitWidth: 72
                        implicitHeight: 30
                        onClicked: dialog.close()
                    }

                    UiButton {
                        text: "导入"
                        dark: dialog.dark
                        variant: "primary"
                        implicitWidth: 72
                        implicitHeight: 30
                        enabled: input.text.trim().length > 0
                        onClicked: {
                            dialog.importRequested(input.text, dialog.replaceExisting)
                            dialog.close()
                        }
                    }
                }
            }
        }
    }
}
