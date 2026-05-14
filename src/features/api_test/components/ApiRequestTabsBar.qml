import QtQuick
import QtQuick.Controls
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color textMain: "#333333"
    property int currentTab: 0

    signal tabChanged(int index)

    color: root.panelBg

    Flickable {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.s3
        anchors.rightMargin: Theme.spacing.s3
        clip: true
        interactive: contentWidth > width
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: tabRow.implicitWidth
        contentHeight: height

        Row {
            id: tabRow
            height: parent.height
            spacing: Theme.spacing.s2

            Repeater {
                model: ["Params", "Path", "Body", "Headers", "Cookies", "Auth", "前置操作", "后置操作", "设置"]
                delegate: Rectangle {
                    id: tabItem
                    required property int index
                    required property string modelData

                    property bool active: index === root.currentTab

                    width: Math.max(58, tabLabel.implicitWidth + Theme.spacing.s5)
                    height: tabRow.height
                    color: active ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"

                    Label {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: modelData
                        color: tabItem.active
                            ? Theme.token("color-primary-active", root.dark)
                            : root.textMain
                        font.pixelSize: Theme.typeScale.body
                        font.bold: false
                    }

                    Rectangle {
                        visible: tabItem.active
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 2
                        color: Theme.token("color-primary-active", root.dark)
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.tabChanged(index)
                    }
                }
            }
        }
    }
}
