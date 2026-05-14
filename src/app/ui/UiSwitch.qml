import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property bool checked: false
    property bool switchEnabled: true
    signal toggled(bool checked)

    Layout.preferredWidth: 36
    Layout.preferredHeight: 20
    implicitWidth: 36
    implicitHeight: 20
    radius: height / 2
    color: !root.switchEnabled
        ? Theme.token("color-bg-subtle", root.dark)
        : (root.checked ? Theme.token("color-primary-active", root.dark) : Theme.token("color-bg-subtle", root.dark))
    border.width: 1
    border.color: root.checked
        ? Theme.token("color-primary-active", root.dark)
        : Theme.token("color-border-default", root.dark)
    opacity: root.switchEnabled ? 1.0 : 0.6

    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on border.color { ColorAnimation { duration: 120 } }

    Rectangle {
        width: 16
        height: 16
        radius: 8
        y: 2
        x: root.checked ? root.width - width - 2 : 2
        color: "#FFFFFF"
        border.width: 1
        border.color: Qt.rgba(0, 0, 0, 0.08)

        Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.switchEnabled
        hoverEnabled: true
        cursorShape: root.switchEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
