import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property bool toggled: false
    property string checkedText: "⟨"
    property string uncheckedText: "⟩"
    signal toggleRequested(bool checked)

    implicitHeight: Theme.spacing.s4 * 2 + 6
    radius: Theme.radius.md
    color: Theme.token("color-bg-subtle", dark)

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggleRequested(!root.toggled)
    }

    Label {
        anchors.centerIn: parent
        text: root.toggled ? root.checkedText : root.uncheckedText
        font.pixelSize: Theme.typeScale.heading
        font.family: "IBM Plex Sans"
        color: Theme.token("color-text-regular", root.dark)
    }

    ToolTip.visible: hit.containsMouse
    ToolTip.text: root.toggled ? "展开侧栏" : "收起侧栏"
    ToolTip.delay: 250
}
