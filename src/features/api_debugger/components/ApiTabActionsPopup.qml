import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Popup {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"

    signal closeAllRequested()
    signal closeCurrentRequested()
    signal closeOthersRequested()

    width: 196
    height: 164
    padding: 0
    modal: false
    closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

    background: UiPopupSurface {
        dark: root.dark
        radius: Theme.radii.lg
        fillColor: root.panelBg
    }

    contentItem: Column {
        spacing: 0

        Rectangle {
            width: root.width
            height: 54
            color: tabAllMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
            radius: Theme.radii.md
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.space["3"]
                text: "关闭全部标签页"
                color: Theme.token("color-text-primary", root.dark)
                font.pixelSize: Theme.fontSize.body
                font.bold: false
            }
            MouseArea {
                id: tabAllMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.closeAllRequested()
                    root.close()
                }
            }
        }

        Rectangle {
            width: root.width
            height: 54
            color: tabCurrentMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
            radius: Theme.radii.md
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.space["3"]
                text: "关闭当前标签页"
                color: Theme.token("color-text-primary", root.dark)
                font.pixelSize: Theme.fontSize.body
                font.bold: false
            }
            MouseArea {
                id: tabCurrentMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.closeCurrentRequested()
                    root.close()
                }
            }
        }

        Rectangle {
            width: root.width
            height: 54
            color: tabOtherMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
            radius: Theme.radii.md
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.space["3"]
                text: "关闭其它标签页"
                color: Theme.token("color-text-primary", root.dark)
                font.pixelSize: Theme.fontSize.body
                font.bold: false
            }
            MouseArea {
                id: tabOtherMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.closeOthersRequested()
                    root.close()
                }
            }
        }
    }
}
