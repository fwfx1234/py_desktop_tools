import QtQuick
import QtQuick.Effects
import "../theme"

Item {
    id: root

    property string name: "about"
    property bool active: false
    property bool dark: false
    property color highlightColor: Theme.token("color-primary-active", dark)
    readonly property bool useQtAwesome: root.name.indexOf("qta:") === 0

    width: 18
    height: 18

    function qtaSource(iconName) {
        var colorText = ("" + (root.active ? root.highlightColor : Theme.token("color-nav-idle", root.dark))).replace("#", "")
        return "image://qta/" + iconName + ";color=" + colorText + ";size=" + Math.max(root.width, root.height)
    }

    Image {
        id: sourceIcon
        visible: !root.useQtAwesome
        anchors.fill: parent
        source: root.useQtAwesome ? "" : ("../assets/icons/" + root.name + ".svg")
        sourceSize.width: root.width
        sourceSize.height: root.height
        fillMode: Image.PreserveAspectFit
        opacity: 0
    }

    Image {
        visible: root.useQtAwesome
        anchors.fill: parent
        source: root.useQtAwesome ? root.qtaSource(root.name.slice(4)) : ""
        sourceSize.width: root.width
        sourceSize.height: root.height
        fillMode: Image.PreserveAspectFit
    }

    MultiEffect {
        visible: !root.useQtAwesome
        anchors.fill: sourceIcon
        source: sourceIcon
        colorization: 1
        colorizationColor: root.active
            ? root.highlightColor
            : Theme.token("color-nav-idle", root.dark)
    }
}
