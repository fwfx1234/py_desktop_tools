import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Button {
    id: control

    property bool dark: false
    property string variant: "secondary"
    property string iconName: ""
    property bool useQtaIcon: true
    property bool danger: false
    property int controlRadius: Theme.radii.md
    property int iconSize: 15
    property int contentPaddingX: Theme.space["3"] + Theme.space["1"]
    property int minWidth: 76

    implicitHeight: 30
    implicitWidth: Math.max(control.minWidth, contentRow.implicitWidth + control.contentPaddingX * 2)
    Layout.minimumWidth: Math.max(control.minWidth, contentRow.implicitWidth + control.contentPaddingX * 2)
    hoverEnabled: true
    opacity: enabled ? 1.0 : 0.45
    padding: 0
    font.family: Theme.fontFamily.ui
    font.pixelSize: Theme.fontSize.body

    readonly property color accentColor: Theme.token("color-primary-active", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)
    readonly property bool isPrimary: variant === "primary"
    readonly property bool isGhost: variant === "ghost"

    background: Rectangle {
        radius: control.controlRadius
        border.width: control.isGhost ? 0 : 1
        border.color: {
            if (control.isPrimary)
                return control.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.06)
            if (control.danger)
                return Qt.rgba(control.dangerColor.r, control.dangerColor.g, control.dangerColor.b, control.dark ? 0.42 : 0.30)
            return control.hovered || control.activeFocus ? Theme.token("color-border-strong", control.dark) : Theme.token("color-border-default", control.dark)
        }
        color: {
            if (control.isPrimary)
                return control.down ? Theme.token("color-primary-active", control.dark) : (control.hovered ? Theme.token("color-primary-hover", control.dark) : Theme.token("color-primary", control.dark))
            if (control.danger)
                return control.down ? Qt.rgba(control.dangerColor.r, control.dangerColor.g, control.dangerColor.b, control.dark ? 0.24 : 0.16)
                    : (control.hovered ? Qt.rgba(control.dangerColor.r, control.dangerColor.g, control.dangerColor.b, control.dark ? 0.16 : 0.08) : (control.dark ? Qt.rgba(1, 1, 1, 0.035) : "#FFFFFF"))
            if (control.isGhost)
                return control.down ? Theme.token("color-bg-subtle", control.dark) : (control.hovered ? Theme.token("color-bg-subtle-2", control.dark) : "transparent")
            return control.down ? Theme.token("color-bg-subtle", control.dark) : (control.hovered ? Theme.token("color-bg-subtle-2", control.dark) : (control.dark ? Theme.token("color-bg-elevated", true) : "#FFFFFF"))
        }
        antialiasing: true

        Behavior on color { ColorAnimation { duration: 100 } }
        Behavior on border.color { ColorAnimation { duration: 100 } }
    }

    contentItem: Item {
        anchors.fill: parent
        implicitWidth: contentRow.implicitWidth
        implicitHeight: Math.max(control.iconSize, label.implicitHeight)

        Row {
            id: contentRow
            spacing: control.iconName.length > 0 && control.text.length > 0 ? Theme.space["1.5"] : 0
            width: implicitWidth
            height: Math.max(control.iconSize, label.implicitHeight)
            x: Math.round((control.width - width) / 2)
            y: Math.round((control.height - height) / 2) + (control.down ? 1 : 0)

            UiIcon {
                visible: control.iconName.length > 0
                width: control.iconSize
                height: control.iconSize
                iconSize: control.iconSize
                name: control.iconName
                useQta: control.useQtaIcon
                color: control.isPrimary ? "#FFFFFF" : (control.danger ? control.dangerColor : Theme.token("color-text-regular", control.dark))
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                id: label
                visible: control.text.length > 0
                text: control.text
                font: control.font
                color: control.isPrimary ? "#FFFFFF" : (control.danger ? control.dangerColor : Theme.token("color-text-primary", control.dark))
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenter: parent.verticalCenter
                renderType: Text.NativeRendering
            }
        }
    }
}
