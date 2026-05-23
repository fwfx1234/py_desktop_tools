import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color iconColor: Theme.token("color-text-regular", root.dark)
    property color dangerColor: Theme.token("color-danger", root.dark)

    signal deleteRequested()

    Layout.preferredWidth: 48
    Layout.preferredHeight: 32
    implicitWidth: 48
    implicitHeight: 32
    radius: Theme.radii.md
    color: hit.containsMouse ? Qt.rgba(root.dangerColor.r, root.dangerColor.g, root.dangerColor.b, root.dark ? 0.18 : 0.10) : "transparent"
    border.width: hit.containsMouse ? 1 : 0
    border.color: Qt.rgba(root.dangerColor.r, root.dangerColor.g, root.dangerColor.b, root.dark ? 0.50 : 0.30)

    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on border.color { ColorAnimation { duration: 120 } }

    UiIcon {
        anchors.centerIn: parent
        width: 18
        height: 18
        useQta: true
        name: "mdi6.delete-outline"
        color: hit.containsMouse ? root.dangerColor : root.iconColor
        iconSize: 18
    }

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.deleteRequested()
    }

    ToolTip.visible: hit.containsMouse
    ToolTip.text: "删除"
    ToolTip.delay: 300
}
