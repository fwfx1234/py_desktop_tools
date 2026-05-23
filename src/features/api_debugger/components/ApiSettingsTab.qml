import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"
import "../api_utils.js" as ApiUtils

Item {
    id: root

    Layout.fillWidth: true
    Layout.fillHeight: true

    property bool dark: false
    property color textMain
    property color textSubtle
    property var debugCases: []
    property var selectedDebugCaseIds: []
    property var apiHistory: []
    property var wsTimeline: []
    property string wsStatusText: "未连接"
    property string currentMethod: "GET"
    property var methodColorFn: function(method) { return root.textMain }
    property color surface: Theme.token("color-bg-subtle-2", dark)
    property color borderColor: Theme.token("color-border-default", dark)

    signal saveAsCaseClicked()
    signal batchRunClicked()
    signal caseSelectionToggled(string caseId, bool checked)
    signal historyRestoreRequested(string method, string url)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["2"]
        spacing: Theme.space["2"]

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 280
            spacing: Theme.space["2"]

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.space["2"]
                    Label {
                        text: "调试用例"
                        color: root.textMain
                        font.pixelSize: Theme.fontSize.body
                        Layout.fillWidth: true
                    }
                    Label {
                        text: root.selectedDebugCaseIds.length + "/" + root.debugCases.length
                        color: root.textSubtle
                        font.pixelSize: Theme.fontSize.caption
                    }
                    UiButton {
                        text: "保存"
                        dark: root.dark
                        variant: "secondary"
                        implicitWidth: 58
                        implicitHeight: 28
                        onClicked: root.saveAsCaseClicked()
                    }
                    UiButton {
                        text: "运行"
                        dark: root.dark
                        variant: "primary"
                        implicitWidth: 58
                        implicitHeight: 28
                        enabled: root.selectedDebugCaseIds.length > 0
                        onClicked: root.batchRunClicked()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radii.xs
                color: root.surface
                border.width: 1
                border.color: root.borderColor
                clip: true

                Label {
                    anchors.centerIn: parent
                    visible: root.debugCases.length === 0
                    text: "暂无用例"
                    color: root.textSubtle
                    font.pixelSize: Theme.fontSize.body
                }

                Flickable {
                    anchors.fill: parent
                    visible: root.debugCases.length > 0
                    clip: true
                    contentHeight: casesColumn.implicitHeight

                    Column {
                        id: casesColumn
                        width: parent.width
                        Repeater {
                            model: root.debugCases
                            delegate: Rectangle {
                                required property var modelData
                                width: casesColumn.width
                                height: 32
                                color: caseMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.space["1"]
                                    anchors.rightMargin: Theme.space["2"]
                                    spacing: Theme.space["1"]
                                    UiCheckBox {
                                        dark: root.dark
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
                                        checked: root.selectedDebugCaseIds.indexOf(modelData.id) >= 0
                                        onCheckedChanged: root.caseSelectionToggled(modelData.id, checked)
                                    }
                                    Label {
                                        text: modelData.method || "GET"
                                        color: root.methodColorFn(modelData.method || "GET")
                                        font.pixelSize: Theme.fontSize.caption
                                        font.family: Theme.fontFamily.mono
                                        Layout.preferredWidth: 48
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.name || "未命名用例"
                                        color: root.textMain
                                        font.pixelSize: Theme.fontSize.body
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                                MouseArea {
                                    id: caseMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            color: Theme.token("color-bg-subtle", root.dark)
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 300
            spacing: Theme.space["2"]

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    Label {
                        text: "最近请求"
                        color: root.textMain
                        font.pixelSize: Theme.fontSize.body
                        Layout.fillWidth: true
                    }
                    Label {
                        text: root.apiHistory.length + " 条"
                        color: root.textSubtle
                        font.pixelSize: Theme.fontSize.caption
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radii.xs
                color: root.surface
                border.width: 1
                border.color: root.borderColor
                clip: true

                Label {
                    anchors.centerIn: parent
                    visible: root.apiHistory.length === 0
                    text: "暂无历史"
                    color: root.textSubtle
                    font.pixelSize: Theme.fontSize.body
                }

                Flickable {
                    anchors.fill: parent
                    visible: root.apiHistory.length > 0
                    clip: true
                    contentHeight: historyColumn.implicitHeight
                    Column {
                        id: historyColumn
                        width: parent.width
                        Repeater {
                            model: root.apiHistory
                            delegate: Rectangle {
                                required property var modelData
                                width: historyColumn.width
                                height: 34
                                color: historyMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.space["2"]
                                    anchors.rightMargin: Theme.space["2"]
                                    spacing: Theme.space["1"]
                                    Label {
                                        text: modelData.method || "GET"
                                        color: root.methodColorFn(modelData.method || "GET")
                                        font.pixelSize: Theme.fontSize.caption
                                        font.family: Theme.fontFamily.mono
                                        Layout.preferredWidth: 52
                                    }
                                    Label {
                                        text: modelData.url || "/"
                                        color: root.textMain
                                        font.pixelSize: Theme.fontSize.body
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: modelData.status !== undefined ? ("" + modelData.status) : ""
                                        color: root.textSubtle
                                        font.pixelSize: Theme.fontSize.caption
                                        Layout.preferredWidth: 46
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                                MouseArea {
                                    id: historyMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.historyRestoreRequested(modelData.method || "GET", modelData.url || "/")
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: ApiUtils.requestModeForMethod(root.currentMethod) === "websocket" ? 96 : 0
                visible: ApiUtils.requestModeForMethod(root.currentMethod) === "websocket"
                radius: Theme.radii.xs
                color: root.surface
                border.width: 1
                border.color: root.borderColor
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space["2"]
                    spacing: Theme.space["1"]
                    Label {
                        Layout.fillWidth: true
                        text: "WebSocket"
                        color: root.textMain
                        font.pixelSize: Theme.fontSize.caption
                        elide: Text.ElideRight
                    }
                    TextArea {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        readOnly: true
                        wrapMode: TextEdit.NoWrap
                        color: root.textMain
                        font.pixelSize: Theme.fontSize.mono
                        font.family: Theme.fontFamily.mono
                        text: root.wsTimeline.length > 0 ? root.wsTimeline.map(function (it) {
                            return "[" + it.direction + "/" + it.encoding + "] " + it.content
                        }).join("\n") : "暂无消息"
                        background: Rectangle {
                            color: Theme.token("color-bg-surface", root.dark)
                            radius: Theme.radii.xs
                        }
                    }
                }
            }
        }
    }
}
