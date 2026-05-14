import QtQuick
import QtQuick.Controls
import "../theme"

TabButton {
    id: control

    property bool dark: false

    implicitHeight: Theme.spacing.s4 * 3 - 2
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radius.sm
        color: control.checked
            ? Theme.token("color-nav-active-bg", control.dark)
            : (control.hovered ? (control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-subtle-2", false)) : "transparent")
        border.color: "transparent"
        border.width: 0
    }

    contentItem: Text {
        text: control.text
        color: control.checked ? (control.dark ? Theme.token("color-nav-active-text", true) : Theme.token("color-primary-active", false)) : Theme.token("color-text-regular", control.dark)
        font.pixelSize: Theme.typeScale.mono
        font.bold: false
        font.weight: Font.Normal
        font.family: "IBM Plex Sans"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
