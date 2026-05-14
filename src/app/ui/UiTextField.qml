import QtQuick
import QtQuick.Controls
import "../theme"

TextField {
    id: control

    property bool dark: false

    implicitHeight: Theme.spacing.s4 * 3
    hoverEnabled: true
    color: Theme.token("color-text-primary", dark)
    placeholderTextColor: Theme.token("color-text-secondary", dark)
    selectedTextColor: Theme.token("color-text-primary", dark)
    selectionColor: Theme.token("color-primary-active", dark)
    font.pixelSize: Theme.typeScale.body
    font.family: "IBM Plex Sans"

    background: Rectangle {
        radius: Theme.radius.md
        color: control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-surface", false)
        border.width: control.activeFocus ? 2 : (control.hovered ? 1 : 0)
        border.color: control.activeFocus
            ? Theme.token("color-primary-active", control.dark)
            : (control.hovered ? Theme.token("color-border-default", control.dark) : "transparent")
    }
}
