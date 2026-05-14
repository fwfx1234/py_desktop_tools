import QtQuick
import QtQuick.Controls
import "../theme"

Slider {
    id: control

    property bool dark: false

    implicitHeight: Theme.spacing.s5 + Theme.spacing.s2

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: Theme.spacing.s1 + 2
        radius: Theme.radius.sm / 2
        color: control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-border-default", false)

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: Theme.token("color-primary", control.dark)
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: Theme.spacing.s3 + Theme.spacing.s1
        height: Theme.spacing.s3 + Theme.spacing.s1
        radius: width / 2
        color: control.pressed ? Theme.token("color-primary-active", control.dark) : Theme.token("color-primary-hover", control.dark)
    }
}
