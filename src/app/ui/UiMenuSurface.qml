import QtQuick
import QtQuick.Effects
import "../theme"

Item {
    id: root

    property bool dark: false
    property int radius: 8
    property color fillColor: root.dark ? "#1F2330" : "#FFFFFF"
    property color borderColor: root.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.08)

    MultiEffect {
        anchors.fill: surface
        source: surface
        shadowEnabled: true
        shadowBlur: 0.9
        shadowOpacity: 0.18
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 6
        shadowColor: "#000000"
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.width: 1
        border.color: root.borderColor
        antialiasing: true
    }
}
