import QtQuick
import QtQuick.Controls
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color textMain: "#333333"
    property color textMuted: "#666666"
    property int currentTab: 0
    property var tabCounts: []
    property var tabModel: [
        { title: "Params", icon: "mdi6.tune-variant" },
        { title: "Path", icon: "mdi6.link-variant" },
        { title: "Body", icon: "mdi6.code-json" },
        { title: "Headers", icon: "mdi6.format-header-pound" },
        { title: "Cookies", icon: "mdi6.cookie-outline" },
        { title: "Auth", icon: "mdi6.shield-key-outline" },
        { title: "Pre", icon: "mdi6.playlist-edit" },
        { title: "Assert", icon: "mdi6.check-decagram-outline" },
        { title: "Tools", icon: "mdi6.history" }
    ]

    signal tabChanged(int index)

    function countAt(index) {
        if (!root.tabCounts || index < 0 || index >= root.tabCounts.length)
            return 0
        var value = Number(root.tabCounts[index])
        return isNaN(value) ? 0 : value
    }

    color: root.panelBg

    Flickable {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["2.5"]
        anchors.rightMargin: Theme.space["2.5"]
        clip: true
        interactive: contentWidth > width
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: tabRow.implicitWidth
        contentHeight: height

        Row {
            id: tabRow
            height: parent.height
            spacing: Theme.space["1"]

            Repeater {
                model: root.tabModel
                delegate: Rectangle {
                    id: tabItem
                    required property int index
                    required property var modelData

                    property bool active: index === root.currentTab

                    width: Math.max(48, tabContent.implicitWidth + Theme.space["3"])
                    height: tabRow.height - 4
                    anchors.verticalCenter: parent.verticalCenter
                    radius: Theme.radii.xs
                    color: active
                        ? Theme.token("color-bg-subtle", root.dark)
                        : (tabMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent")

                    Row {
                        id: tabContent
                        anchors.centerIn: parent
                        spacing: 5
                        Image {
                            width: 13
                            height: 13
                            anchors.verticalCenter: parent.verticalCenter
                            source: "image://qta/" + modelData.icon + ";color=" + ("" + (tabItem.active ? Theme.token("color-primary-active", root.dark) : root.textMain)).replace("#", "") + ";size=13"
                            sourceSize.width: 13
                            sourceSize.height: 13
                            fillMode: Image.PreserveAspectFit
                        }
                        Label {
                            text: modelData.title
                            color: tabItem.active
                                ? Theme.token("color-primary-active", root.dark)
                                : root.textMain
                            font.pixelSize: Theme.fontSize.caption
                            font.bold: false
                        }
                        Rectangle {
                            visible: root.countAt(index) > 0
                            width: Math.max(16, tabCountLabel.implicitWidth + 8)
                            height: 16
                            radius: Theme.radii.xs
                            color: tabItem.active
                                ? Qt.rgba(Theme.token("color-primary-active", root.dark).r, Theme.token("color-primary-active", root.dark).g, Theme.token("color-primary-active", root.dark).b, root.dark ? 0.26 : 0.12)
                                : Theme.token("color-bg-subtle-2", root.dark)
                            border.width: tabItem.active ? 1 : 0
                            border.color: Theme.token("color-primary-active", root.dark)
                            Label {
                                id: tabCountLabel
                                anchors.centerIn: parent
                                text: root.countAt(index)
                                color: tabItem.active ? Theme.token("color-primary-active", root.dark) : root.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                            }
                        }
                    }

                    Rectangle {
                        visible: tabItem.active
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: Theme.token("color-primary-active", root.dark)
                    }

                    MouseArea {
                        id: tabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.tabChanged(index)
                    }
                }
            }
        }
    }
}
