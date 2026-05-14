import QtQuick
import "../theme"

Item {
    id: root

    property string name: ""
    property color color: Theme.token("color-text-regular", false)
    property bool useQta: true
    property int iconSize: Math.max(width, height)
    property string svgPathPrefix: "../assets/icons/"

    implicitWidth: 16
    implicitHeight: 16

    function qtaSource(iconName, iconColor, sizeValue) {
        var colorText = ("" + iconColor).replace("#", "")
        return "image://qta/" + iconName + ";color=" + colorText + ";size=" + sizeValue
    }

    Image {
        anchors.fill: parent
        source: {
            if (!root.name || root.name.length === 0)
                return ""
            if (root.useQta)
                return root.qtaSource(root.name, root.color, root.iconSize)
            return root.svgPathPrefix + root.name + ".svg"
        }
        sourceSize.width: root.width
        sourceSize.height: root.height
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
}
