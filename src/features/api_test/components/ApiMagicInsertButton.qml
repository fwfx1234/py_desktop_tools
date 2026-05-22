import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: Theme.token("color-bg-surface", dark)
    property color panelBorder: Theme.token("color-border-default", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property bool opened: magicPopup.opened

    signal insertRequested(string valueText)

    function closePanel() {
        magicPopup.close()
    }

    function openPanel() {
        magicPopup.openAt(root, root.width - magicPopup.width, root.height + 6)
    }

    Layout.preferredWidth: 28
    Layout.preferredHeight: 28
    implicitWidth: 28
    implicitHeight: 28
    radius: Theme.radii.md
    color: {
        if (magicPopup.opened)
            return root.dark ? Theme.token("color-primary-soft", true) : Theme.token("color-primary-bg", false)
        if (hit.containsMouse || hit.pressed)
            return Theme.token("color-bg-subtle-2", root.dark)
        return "transparent"
    }
    border.width: magicPopup.opened ? 1 : 0
    border.color: root.dark ? Qt.rgba(0.04, 0.52, 1, 0.45) : Qt.rgba(0.04, 0.52, 1, 0.24)

    UiIcon {
        anchors.centerIn: parent
        width: 16
        height: 16
        useQta: true
        name: "mdi6.code-json"
        color: magicPopup.opened ? Theme.token("color-primary-active", root.dark) : Theme.token("color-text-secondary", root.dark)
        iconSize: 16
    }

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: magicPopup.opened ? magicPopup.close() : root.openPanel()
    }

    ToolTip.visible: hit.containsMouse
    ToolTip.text: "插入变量 / 魔法参数"
    ToolTip.delay: 300

    UiPopup {
        id: magicPopup
        width: 352
        height: 386
        padding: 0
        z: 100
        surfaceRadius: 12
        surfaceFillColor: root.dark ? Qt.rgba(0.11, 0.12, 0.15, 0.98) : Qt.rgba(1, 1, 1, 0.98)
        surfaceBorderColor: root.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.08)

        contentItem: ApiMagicValuePanel {
            dark: root.dark
            panelBg: root.dark ? Theme.token("color-bg-elevated", true) : "#FFFFFF"
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
