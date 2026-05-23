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

    width: 260
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

        Repeater {
            model: root.environments
            delegate: Rectangle {
                required property int index
                required property var modelData
                width: root.width
                height: 52
                color: index === root.currentEnvIndex
                    ? Theme.token("color-bg-subtle", root.dark)
                    : (envMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent")
                radius: index === root.currentEnvIndex ? Theme.radii.md : 0

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["2.5"]
                    anchors.rightMargin: Theme.space["2.5"]
                    spacing: Theme.space["2"]

                    Rectangle {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        radius: 12
                        color: root.envTagColorFn ? root.envTagColorFn(modelData.name) : Theme.token("color-primary-active", root.dark)
                        Label {
                            anchors.centerIn: parent
                            text: root.envTagFn ? root.envTagFn(modelData.name) : ""
                            color: "white"
                            font.bold: true
                            font.pixelSize: Theme.fontSize.caption
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label {
                            Layout.fillWidth: true
                            text: modelData.name || "未命名环境"
                            color: Theme.token("color-text-primary", root.dark)
                            font.pixelSize: Theme.fontSize.body
                            font.bold: index === root.currentEnvIndex
                            elide: Text.ElideRight
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData.baseUrl || "未设置 Base URL"
                            color: Theme.token("color-text-secondary", root.dark)
                            font.pixelSize: Theme.fontSize.caption
                            elide: Text.ElideMiddle
                        }
                    }

                    UiIcon {
                        visible: index === root.currentEnvIndex
                        useQta: true
                        name: "mdi6.check"
                        color: Theme.token("color-primary-active", root.dark)
                        iconSize: 16
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                    }
                }
                MouseArea {
                    id: envMouse
                    anchors.fill: parent
                    hoverEnabled: true
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
            height: 40
            color: manageMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2.5"]
                spacing: Theme.space["2"]
                UiIcon {
                    useQta: true
                    name: "mdi6.cog-outline"
                    color: Theme.token("color-primary-active", root.dark)
                    iconSize: 16
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }
                Label {
                    text: "管理环境"
                    color: Theme.token("color-primary-active", root.dark)
                    font.pixelSize: Theme.fontSize.body
                    font.bold: false
                }
            }
            MouseArea {
                id: manageMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.close()
                    root.manageRequested()
                }
            }
        }
    }
}
