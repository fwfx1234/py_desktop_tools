import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

CheckBox {
    id: control

    property bool dark: false

    Layout.preferredWidth: 48
    Layout.preferredHeight: 32
    padding: 0
    spacing: 0
    hoverEnabled: true

    indicator: Rectangle {
        width: 20
        height: 20
        x: Math.round((control.width - width) / 2)
        y: Math.round((control.height - height) / 2)
        radius: 6
        color: control.checked
            ? Theme.token("color-primary-active", control.dark)
            : Theme.token("color-bg-surface", control.dark)
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked
            ? Theme.token("color-primary-active", control.dark)
            : (control.hovered ? Theme.token("color-primary-active", control.dark) : Theme.token("color-border-default", control.dark))

        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on border.color { ColorAnimation { duration: 120 } }

        UiIcon {
            anchors.centerIn: parent
            visible: control.checked
            useQta: true
            name: "mdi6.check-bold"
            color: "#FFFFFF"
            width: 14
            height: 14
            iconSize: 14
        }
    }

    background: Rectangle {
        radius: Theme.radius.md
        color: control.hovered
            ? Qt.rgba(Theme.token("color-primary-active", control.dark).r, Theme.token("color-primary-active", control.dark).g, Theme.token("color-primary-active", control.dark).b, control.dark ? 0.16 : 0.08)
            : "transparent"
        border.width: control.activeFocus ? 1 : 0
        border.color: Theme.token("color-primary-active", control.dark)

        Behavior on color { ColorAnimation { duration: 120 } }
    }

    contentItem: Item {}
}
