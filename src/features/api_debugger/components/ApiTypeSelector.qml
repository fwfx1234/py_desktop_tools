import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Item {
    id: root

    property bool dark: false
    property var model: ["string", "number", "boolean", "array", "object"]
    property string value: "string"
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)

    signal valueCommitted(string value)

    implicitWidth: 92
    implicitHeight: 26

    readonly property color borderColor: root.dark
        ? Qt.rgba(1, 1, 1, 0.18)
        : Qt.rgba(0, 0, 0, 0.20)
    readonly property color hoverBorderColor: root.dark
        ? Qt.rgba(1, 1, 1, 0.28)
        : Qt.rgba(0, 0, 0, 0.28)

    function pick(valueText) {
        root.value = valueText
        root.valueCommitted(valueText)
        popup.close()
    }

    Rectangle {
        id: trigger
        anchors.fill: parent
        radius: Theme.radii.sm
        color: triggerMouse.containsMouse || popup.opened
            ? (root.dark ? Theme.token("color-bg-subtle", true) : Theme.token("color-bg-subtle-2", false))
            : (root.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-surface", false))
        border.width: 1
        border.color: popup.opened
            ? Theme.token("color-primary-active", root.dark)
            : (triggerMouse.containsMouse ? root.hoverBorderColor : root.borderColor)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 8
            spacing: Theme.space["1"]

            Label {
                text: root.value || "string"
                Layout.fillWidth: true
                color: root.textMain
                elide: Text.ElideRight
                font.family: Theme.fontFamily.mono
                font.pixelSize: Theme.fontSize.caption
                verticalAlignment: Text.AlignVCenter
            }

            UiIcon {
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                useQta: true
                name: "mdi6.chevron-down"
                color: root.textMuted
                iconSize: 16
            }
        }

        MouseArea {
            id: triggerMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: popup.opened ? popup.close() : popup.open()
        }
    }

    Popup {
        id: popup
        x: 0
        y: root.height + 4
        width: Math.max(root.width, 132)
        height: Math.min(240, 8 + root.model.length * 30)
        padding: 4
        modal: false
        focus: true
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

        background: UiPopupSurface {
            dark: root.dark
            radius: Theme.radii.md
            fillColor: Theme.token("color-bg-surface", root.dark)
        }

        contentItem: Column {
            spacing: 2

            Repeater {
                model: root.model
                delegate: Rectangle {
                    id: option
                    required property var modelData

                    readonly property string optionText: "" + modelData
                    readonly property bool selected: optionText === root.value

                    width: popup.width - 8
                    height: 30
                    radius: Theme.radii.sm
                    color: optionMouse.containsMouse || selected
                        ? Theme.token("color-bg-subtle", root.dark)
                        : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space["2"]
                        anchors.rightMargin: Theme.space["2"]
                        spacing: Theme.space["2"]

                        Label {
                            text: option.optionText
                            Layout.fillWidth: true
                            color: option.selected
                                ? Theme.token("color-primary-active", root.dark)
                                : root.textMain
                            font.family: Theme.fontFamily.mono
                            font.pixelSize: Theme.fontSize.caption
                            verticalAlignment: Text.AlignVCenter
                        }

                        UiIcon {
                            visible: option.selected
                            Layout.preferredWidth: 14
                            Layout.preferredHeight: 14
                            useQta: true
                            name: "mdi6.check"
                            color: Theme.token("color-primary-active", root.dark)
                            iconSize: 14
                        }
                    }

                    MouseArea {
                        id: optionMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.pick(option.optionText)
                    }
                }
            }
        }
    }
}
