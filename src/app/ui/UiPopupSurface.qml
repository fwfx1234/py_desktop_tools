import QtQuick
import Qt5Compat.GraphicalEffects
import "../theme"

Item {
    id: root

    property bool dark: false
    property int radius: Theme.radius.lg
    property color fillColor: Theme.token("color-bg-surface", dark)
    DropShadow {
        anchors.fill: surface
        source: surface
        horizontalOffset: 0
        verticalOffset: 2
        radius: 16
        samples: 33
        color: "#4D000000"
        transparentBorder: true
        cached: false
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.width: 0
        border.color: "transparent"
    }
}
