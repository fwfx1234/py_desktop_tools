import QtQuick
import QtQuick.Controls
import "../theme"

TextField {
    id: control

    property bool dark: false

    implicitHeight: Theme.space["3"] * 3
    hoverEnabled: true
    color: Theme.token("color-text-primary", dark)
    placeholderTextColor: Theme.token("color-text-secondary", dark)
    selectedTextColor: Theme.token("color-text-primary", dark)
    selectionColor: Theme.token("color-primary-active", dark)
    font.pixelSize: Theme.fontSize.body
    font.family: Theme.fontFamily.ui

    background: Rectangle {
        radius: Theme.radii.md
        color: control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-surface", false)
        border.width: control.activeFocus ? 2 : (control.hovered ? 1 : 0)
        border.color: control.activeFocus
            ? Theme.token("color-primary-active", control.dark)
            : (control.hovered ? Theme.token("color-border-default", control.dark) : "transparent")
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onTapped: function(eventPoint) {
            control.forceActiveFocus()
            uiTextEditMenu.openAt(control, eventPoint.position.x, eventPoint.position.y)
        }
    }

    UiTextEditMenu {
        id: uiTextEditMenu
        target: control
        dark: control.dark
    }
}
