import QtQuick
import QtQuick.Controls
import "../theme"

Button {
    id: control

    property bool dark: false
    property string variant: "secondary" // primary, secondary, ghost

    implicitHeight: Theme.spacing.s4 * 3
    implicitWidth: 112
    hoverEnabled: true

    readonly property color accent: Theme.token("color-primary-active", dark)
    readonly property color primaryIdle: Theme.token("color-primary-active", dark)
    readonly property color secondaryIdle: dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-subtle", false)
    readonly property color secondaryHover: dark ? Theme.token("color-border-default", true) : Theme.token("color-border-default", false)
    readonly property color ghostHover: dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-subtle-2", false)

    background: Rectangle {
        radius: Theme.radius.md
        border.width: 0
        border.color: "transparent"
        color: {
            if (control.variant === "primary")
            return control.down ? Theme.token("color-primary-active", control.dark) : (control.hovered ? Theme.token("color-primary", control.dark) : control.primaryIdle)
            if (control.variant === "ghost")
                return control.down ? (control.dark ? Theme.token("color-border-default", true) : Theme.token("color-border-default", false)) : (control.hovered ? control.ghostHover : (control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-subtle-2", false)))
            return control.down ? (control.dark ? Theme.token("color-text-regular", true) : Theme.token("color-border-default", false)) : (control.hovered ? control.secondaryHover : control.secondaryIdle)
        }
    }

    contentItem: Text {
        text: control.text
        font.pixelSize: Theme.typeScale.body
        font.bold: false
        font.weight: Font.Normal
        font.family: "IBM Plex Sans"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: control.variant === "primary" ? Theme.token("color-bg-surface", false) : Theme.token("color-text-primary", control.dark)
    }
}
