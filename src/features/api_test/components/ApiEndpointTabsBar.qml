import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    Layout.fillWidth: true
    Layout.preferredHeight: 40

    property var endpointTabs: []
    property int currentEndpointTab: -1
    property var environments: []
    property int currentEnvIndex: 0
    property bool dark: false
    property color panelBg
    property color textMain
    property color textMuted
    property var methodColorFn: null
    property var envTagFn: null
    property var envTagColorFn: null

    signal tabClicked(int index)
    signal tabCloseClicked(int index)
    signal tabMoreClicked(var buttonItem)
    signal environmentSelected(var buttonItem)

    function ensureCurrentTabVisible() {
        if (currentEndpointTab < 0 || !endpointTabsFlick || !endpointTabsRepeater)
            return
        var item = endpointTabsRepeater.itemAt(currentEndpointTab)
        if (!item) return
        var left = item.x
        var right = item.x + item.width
        var viewportLeft = endpointTabsFlick.contentX
        var viewportRight = viewportLeft + endpointTabsFlick.width
        var nextX = viewportLeft
        if (left < viewportLeft)
            nextX = left
        else if (right > viewportRight)
            nextX = right - endpointTabsFlick.width
        var maxX = Math.max(0, endpointTabsFlick.contentWidth - endpointTabsFlick.width)
        endpointTabsFlick.contentX = Math.max(0, Math.min(nextX, maxX))
    }

    function currentEnvName() {
        if (environments.length === 0) return "无环境"
        var idx = currentEnvIndex
        if (idx < 0 || idx >= environments.length) return environments[0].name || "无环境"
        return environments[idx].name || "无环境"
    }

    color: root.panelBg

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["2"]
        anchors.rightMargin: Theme.space["2"]
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            radius: Theme.radii.xs
            visible: endpointTabsFlick.contentWidth > endpointTabsFlick.width
            opacity: endpointTabsFlick.contentX > 0 ? 1 : 0.4
            color: tabLeftMouse.containsMouse
                ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"
            UiIcon {
                anchors.centerIn: parent; width: 16; height: 16
                useQta: true; name: "mdi6.chevron-left"; color: root.textMuted; iconSize: 16
            }
            MouseArea {
                id: tabLeftMouse; anchors.fill: parent
                enabled: endpointTabsFlick.contentX > 0; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: endpointTabsFlick.contentX = Math.max(0, endpointTabsFlick.contentX - Math.max(120, endpointTabsFlick.width * 0.65))
            }
        }

        Flickable {
            id: endpointTabsFlick
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; interactive: contentWidth > width
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: endpointTabsRow.implicitWidth; contentHeight: height

            Row {
                id: endpointTabsRow; height: endpointTabsFlick.height; spacing: 2

                Repeater {
                    id: endpointTabsRepeater
                    model: root.endpointTabs
                    delegate: Rectangle {
                        required property int index
                        required property var modelData
                        property bool active: index === root.currentEndpointTab
                        width: Math.max(116, Math.min(220, tabMethod.implicitWidth + tabName.implicitWidth + 54))
                        height: endpointTabsFlick.height
                        color: endpointTabMouse.containsMouse
                            ? Theme.token("color-bg-subtle-2", root.dark) : root.panelBg
                        border.width: active ? 1 : 0
                        border.color: active ? Qt.rgba(root.panelBg.r, root.panelBg.g, root.panelBg.b, 0.55) : "transparent"
                        Rectangle {
                            visible: active
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            height: 2; color: Theme.token("color-primary-active", root.dark)
                        }
                        Rectangle {
                            visible: active
                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                            height: 1; color: root.panelBg
                        }
                        MouseArea {
                            id: endpointTabMouse; anchors.fill: parent
                            hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: root.tabClicked(index)
                        }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["2.5"]; anchors.rightMargin: Theme.space["1"]
                            spacing: Theme.space["1"]
                            Label {
                                id: tabMethod; text: modelData.method || "GET"
                                color: root.methodColorFn ? root.methodColorFn(modelData.method || "GET") : root.textMain
                                font.bold: false; font.italic: true
                                font.pixelSize: Theme.fontSize.caption; font.family: Theme.fontFamily.mono
                            }
                            Label {
                                id: tabName; text: modelData.name || modelData.url || "新接口"
                                color: root.textMain; font.pixelSize: Theme.fontSize.body
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                            Rectangle {
                                Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: Theme.radii.xs
                                color: closeMouse.containsMouse
                                    ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                                UiIcon {
                                    anchors.centerIn: parent; width: 14; height: 14
                                    useQta: true; name: "mdi6.close"; color: root.textMuted; iconSize: 14
                                }
                                MouseArea {
                                    id: closeMouse; anchors.fill: parent; hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor; onClicked: root.tabCloseClicked(index)
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: Theme.radii.xs
            visible: endpointTabsFlick.contentWidth > endpointTabsFlick.width
            opacity: endpointTabsFlick.contentX < Math.max(0, endpointTabsFlick.contentWidth - endpointTabsFlick.width) ? 1 : 0.4
            color: tabRightMouse.containsMouse
                ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"
            UiIcon {
                anchors.centerIn: parent; width: 16; height: 16
                useQta: true; name: "mdi6.chevron-right"; color: root.textMuted; iconSize: 16
            }
            MouseArea {
                id: tabRightMouse; anchors.fill: parent
                enabled: endpointTabsFlick.contentX < Math.max(0, endpointTabsFlick.contentWidth - endpointTabsFlick.width)
                hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var maxX = Math.max(0, endpointTabsFlick.contentWidth - endpointTabsFlick.width)
                    endpointTabsFlick.contentX = Math.min(maxX, endpointTabsFlick.contentX + Math.max(120, endpointTabsFlick.width * 0.65))
                }
            }
        }

        Rectangle {
            id: tabMoreButton; Layout.preferredWidth: 36; Layout.preferredHeight: 28
            radius: Theme.radii.md
            color: tabMoreMouse.containsMouse
                ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"
            UiIcon {
                anchors.centerIn: parent; width: 16; height: 16
                useQta: true; name: "mdi6.dots-horizontal"; color: root.textMuted; iconSize: 16
            }
            MouseArea {
                id: tabMoreMouse; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.tabMoreClicked(tabMoreButton)
            }
        }

        Rectangle {
            id: envSelector; Layout.preferredWidth: 180; Layout.preferredHeight: 28
            radius: Theme.radii.xs
            color: envMouse.containsMouse
                ? Theme.token("color-bg-subtle", root.dark) : "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]; anchors.rightMargin: Theme.space["1"]
                spacing: Theme.space["1"]
                Rectangle {
                    Layout.preferredWidth: 20; Layout.preferredHeight: 20; radius: 10
                    color: root.envTagColorFn ? root.envTagColorFn(currentEnvName()) : "transparent"
                    Label {
                        anchors.centerIn: parent
                        text: root.envTagFn ? root.envTagFn(currentEnvName()) : "?"; color: "white"; font.pixelSize: 9
                    }
                }
                Label {
                    Layout.fillWidth: true; text: currentEnvName()
                    color: root.textMain; font.pixelSize: Theme.fontSize.body; elide: Text.ElideRight
                }
                UiIcon {
                    width: 14; height: 14; useQta: true; name: "mdi6.chevron-down"
                    color: root.textMuted; iconSize: 14
                }
            }
            MouseArea {
                id: envMouse; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.environmentSelected(envSelector)
            }
        }
    }
}
