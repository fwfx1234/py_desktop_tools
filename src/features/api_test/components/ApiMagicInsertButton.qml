import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: Theme.token("color-bg-surface", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property bool opened: magicPopup.opened

    signal insertRequested(string valueText)

    function closePanel() {
        magicPopup.close()
    }

    Layout.preferredWidth: 28
    Layout.preferredHeight: 28
    implicitWidth: 28
    implicitHeight: 28
    radius: Theme.radii.xs
    color: magicPopup.opened || hit.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
    border.width: magicPopup.opened ? 1 : 0
    border.color: Theme.token("color-primary-active", root.dark)

    UiIcon {
        anchors.centerIn: parent
        width: 16
        height: 16
        useQta: true
        name: "mdi6.code-json"
        color: magicPopup.opened ? Theme.token("color-primary-active", root.dark) : root.textMuted
        iconSize: 16
    }

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: magicPopup.opened ? magicPopup.close() : magicPopup.open()
    }

    ToolTip.visible: hit.containsMouse
    ToolTip.text: "插入变量 / 魔法参数"
    ToolTip.delay: 300

    Popup {
        id: magicPopup
        x: root.width - width
        y: root.height + 4
        width: 320
        height: 420
        padding: 0
        modal: false
        z: 100
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

        background: Rectangle { color: "transparent" }

        contentItem: ApiMagicValuePanel {
            dark: root.dark
            panelBg: root.panelBg
            panelBorder: root.panelBorder
            textMain: root.textMain
            textMuted: root.textMuted
            onInsertRequested: function(valueText) {
                root.insertRequested(valueText)
                magicPopup.close()
            }
            onCloseRequested: magicPopup.close()
        }
    }
}
