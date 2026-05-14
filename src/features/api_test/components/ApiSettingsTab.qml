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

    signal saveAsCaseClicked()
    signal batchRunClicked()
    signal caseSelectionToggled(string caseId, bool checked)
    signal historyRestoreRequested(string method, string url)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s3
        spacing: Theme.spacing.s2

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "调试用例"
                color: root.textMain
                font.pixelSize: Theme.typeScale.body
            }
            Item { Layout.fillWidth: true }
            UiButton {
                text: "保存当前为用例"
                dark: root.dark; variant: "secondary"
                onClicked: root.saveAsCaseClicked()
            }
            UiButton {
                text: "批量运行选中"
                dark: root.dark; variant: "primary"
                onClicked: root.batchRunClicked()
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: 140
            clip: true
            contentHeight: casesColumn.implicitHeight
            Rectangle {
                anchors.fill: parent
                color: Theme.token("color-bg-subtle", root.dark)
                radius: Theme.radius.md
            }
            Column {
                id: casesColumn; width: parent.width
                Repeater {
                    model: root.debugCases
                    delegate: Rectangle {
                        required property var modelData
                        width: casesColumn.width; height: 30
                        color: "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacing.s2
                            anchors.rightMargin: Theme.spacing.s2
                            CheckBox {
                                checked: root.selectedDebugCaseIds.indexOf(modelData.id) >= 0
                                onCheckedChanged: root.caseSelectionToggled(modelData.id, checked)
                            }
                            Label {
                                text: modelData.name + " (" + modelData.method + ")"
                                color: root.textMain
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "最近请求"
                color: root.textMain
                font.pixelSize: Theme.typeScale.body
            }
            Item { Layout.fillWidth: true }
            Label {
                text: root.apiHistory.length + " 条"
                color: root.textSubtle
                font.pixelSize: Theme.typeScale.caption
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: 140
            clip: true
            contentHeight: historyColumn.implicitHeight
            Rectangle {
                anchors.fill: parent
                color: Theme.token("color-bg-subtle", root.dark)
                radius: Theme.radius.md
            }
            Column {
                id: historyColumn
                width: parent.width
                Repeater {
                    model: root.apiHistory
                    delegate: Rectangle {
                        required property var modelData
                        width: historyColumn.width
                        height: 34
                        radius: Theme.radius.xs
                        color: historyMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacing.s2
                            anchors.rightMargin: Theme.spacing.s2
                            Label {
                                text: modelData.method || "GET"
                                color: root.methodColorFn(modelData.method || "GET")
                                font.pixelSize: Theme.typeScale.caption
                                font.bold: true
                                Layout.preferredWidth: 52
                            }
                            Label {
                                text: modelData.url || "/"
                                color: root.textMain
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Label {
                                text: modelData.title || ""
                                color: root.textSubtle
                                elide: Text.ElideRight
                                Layout.preferredWidth: 150
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

        Label {
            visible: ApiUtils.requestModeForMethod(root.currentMethod) === "websocket"
            text: "WebSocket 时间线 - " + root.wsStatusText
            color: root.textMain
            font.pixelSize: Theme.typeScale.body
        }
        UiTextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            dark: root.dark; readOnly: true
            visible: ApiUtils.requestModeForMethod(root.currentMethod) === "websocket"
            text: root.wsTimeline.length > 0 ? root.wsTimeline.map(function (it) {
                return "[" + it.direction + "/" + it.encoding + "] " + it.content
            }).join("\n") : "暂无消息"
        }
    }
}
