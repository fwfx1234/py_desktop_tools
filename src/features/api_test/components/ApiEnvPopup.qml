import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Popup {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color panelBorder: "#D0D7DE"
    property var environments: []
    property int currentEnvIndex: 0
    property var envTagFn: null
    property var envTagColorFn: null

    signal environmentSelected(int index)
    signal manageRequested()

    width: 210
    padding: 0
    modal: false
    closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

    background: UiPopupSurface {
        dark: root.dark
        radius: Theme.radius.lg
        fillColor: root.panelBg
    }

    contentItem: Column {
        spacing: 0

        Repeater {
            model: root.environments
            delegate: Rectangle {
                required property int index
                required property var modelData
                width: root.width
                height: 44
                color: index === root.currentEnvIndex
                    ? Theme.token("color-bg-subtle", root.dark)
                    : "transparent"
                radius: index === root.currentEnvIndex ? Theme.radius.md : 0

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacing.s3
                    anchors.rightMargin: Theme.spacing.s3
                    spacing: Theme.spacing.s2

                    Label {
                        text: root.envTagFn ? root.envTagFn(modelData.name) : ""
                        color: root.envTagColorFn ? root.envTagColorFn(modelData.name) : Theme.token("color-text-primary", root.dark)
                        font.bold: false
                        font.pixelSize: Theme.typeScale.caption
                        Layout.preferredWidth: 18
                    }
                    Label {
                        text: modelData.name
                        color: Theme.token("color-text-primary", root.dark)
                        font.pixelSize: Theme.typeScale.body
                        font.bold: false
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.environmentSelected(index)
                        root.close()
                    }
                }
            }
        }

        Rectangle { width: root.width; height: 1; color: root.panelBorder }

        Rectangle {
            width: root.width
            height: 44
            color: "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacing.s3
                anchors.rightMargin: Theme.spacing.s3
                spacing: Theme.spacing.s2
                Label {
                    text: "管理环境"
                    color: Theme.token("color-primary-active", root.dark)
                    font.pixelSize: Theme.typeScale.body
                    font.bold: false
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.close()
                    root.manageRequested()
                }
            }
        }
    }
}
