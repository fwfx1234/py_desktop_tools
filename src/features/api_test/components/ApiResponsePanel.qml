import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

ColumnLayout {
    id: root

    spacing: 0

    property bool dark: false
    property color panelBg
    property color panelBorder
    property color textMain
    property color textMuted
    property color textSubtle
    property color softBorder
    property bool mockMode: false
    property bool assertionsEnabled: true
    property int detailTab: 0
    property var detailTabs: ["Body", "Headers", "Request", "cURL", "日志"]
    property string bodyText: ""
    property string headersText: ""
    property string requestText: ""
    property string curlText: ""
    property string requestLogText: ""
    property var logEntries: []
    property string titleText: "返回响应"

    signal mockModeToggled(bool checked)
    signal assertionsToggled(bool checked)

    function responseHasContent() {
        return bodyText.length > 0
            || headersText.length > 0
            || requestText.length > 0
            || curlText.length > 0
            || requestLogText.length > 0
    }

    function currentResponseText() {
        if (detailTab === 1) return headersText || "暂无响应头"
        if (detailTab === 2) return requestText || "暂无实际请求"
        if (detailTab === 3) return curlText || "暂无 cURL"
        if (detailTab === 4) return requestLogText || "暂无请求日志"
        return bodyText || ""
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 38
        color: root.panelBg
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacing.s4
            anchors.rightMargin: Theme.spacing.s3
            Label {
                text: root.titleText
                color: root.textMain
                font.bold: false
                font.pixelSize: Theme.typeScale.body
                Layout.fillWidth: true
            }
            Label { text: "Mock"; color: root.textMuted; font.pixelSize: Theme.typeScale.caption }
            UiSwitch {
                dark: root.dark
                checked: root.mockMode
                onToggled: root.mockModeToggled(checked)
            }
            Label { text: "校验响应"; color: root.textMuted; font.pixelSize: Theme.typeScale.caption }
            UiSwitch {
                dark: root.dark
                checked: root.assertionsEnabled
                onToggled: root.assertionsToggled(checked)
            }
            Label {
                visible: root.titleText.indexOf("状态:") === 0
                text: root.titleText.indexOf("ERR") >= 0 || root.titleText.indexOf("FAIL") >= 0 ? "失败" : "完成"
                color: root.titleText.indexOf("ERR") >= 0 || root.titleText.indexOf("FAIL") >= 0
                    ? Theme.token("color-danger", root.dark)
                    : Theme.token("color-success", root.dark)
                font.bold: false
                font.pixelSize: Theme.typeScale.caption
            }
        }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 38
        color: root.panelBg
        visible: root.responseHasContent()

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacing.s3
            anchors.rightMargin: Theme.spacing.s3
            spacing: Theme.spacing.s2

            Repeater {
                model: root.detailTabs
                delegate: Rectangle {
                    id: responseTabItem
                    required property int index
                    required property string modelData
                    property bool active: index === root.detailTab
                    Layout.preferredWidth: Math.max(74, responseTabLabel.implicitWidth + Theme.spacing.s5)
                    Layout.preferredHeight: 28
                    radius: Theme.radius.xs
                    color: active
                        ? Theme.token("color-primary-bg", root.dark)
                        : (responseTabMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent")
                    border.width: active ? 1 : 0
                    border.color: active ? Theme.token("color-primary-active", root.dark) : "transparent"
                    Label {
                        id: responseTabLabel
                        anchors.centerIn: parent
                        text: modelData
                        color: responseTabItem.active
                            ? Theme.token("color-primary-active", root.dark)
                            : root.textMain
                        font.pixelSize: Theme.typeScale.body
                        font.bold: responseTabItem.active
                    }
                    MouseArea {
                        id: responseTabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.detailTab = index
                    }
                }
            }

            Item { Layout.fillWidth: true }
            Label {
                visible: root.logEntries.length > 0
                text: "日志 " + root.logEntries.length
                color: root.textSubtle
                font.pixelSize: Theme.typeScale.caption
            }
        }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: root.responseHasContent() ? 1 : 0; color: root.panelBorder }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: root.panelBg

        ColumnLayout {
            anchors.centerIn: parent
            spacing: Theme.spacing.s2
            visible: !root.responseHasContent()
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 60; Layout.preferredHeight: 60
                radius: 30
                color: Theme.token("color-bg-subtle", root.dark)
                Image {
                    anchors.centerIn: parent
                    width: 32; height: 32
                    source: "../../../app/assets/icons/rocket.svg"
                }
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: '点击 "发送" 按钮获取返回结果'
                color: root.textSubtle
                font.pixelSize: Theme.typeScale.body
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: Theme.spacing.s3
            radius: Theme.radius.md
            color: Theme.token("color-bg-subtle-2", root.dark)
            border.width: 1
            border.color: root.softBorder
            visible: root.responseHasContent()

            UiTextArea {
                id: responseOutput
                anchors.fill: parent
                anchors.margins: 1
                dark: root.dark
                readOnly: true
                wrapMode: root.detailTab === 0 ? TextEdit.Wrap : TextEdit.NoWrap
                text: root.currentResponseText()
                visible: root.detailTab !== 4
            }

            Flickable {
                anchors.fill: parent
                anchors.margins: Theme.spacing.s2
                clip: true
                visible: root.detailTab === 4
                contentWidth: width
                contentHeight: responseLogColumn.implicitHeight

                ColumnLayout {
                    id: responseLogColumn
                    width: parent.width
                    spacing: Theme.spacing.s2

                    Repeater {
                        model: root.logEntries
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: logBlock.implicitHeight + Theme.spacing.s4
                            radius: Theme.radius.sm
                            color: Theme.token("color-bg-surface", root.dark)
                            border.width: 1
                            border.color: root.softBorder

                            ColumnLayout {
                                id: logBlock
                                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                anchors.margins: Theme.spacing.s2
                                spacing: Theme.spacing.s1
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: modelData.title || "请求日志"
                                        color: root.textMain
                                        font.pixelSize: Theme.typeScale.body
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.time || ""
                                        color: root.textSubtle
                                        font.pixelSize: Theme.typeScale.caption
                                    }
                                }
                                TextArea {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: Math.max(96, implicitHeight + Theme.spacing.s2)
                                    text: modelData.text || ""
                                    readOnly: true
                                    wrapMode: TextEdit.NoWrap
                                    selectByMouse: true
                                    color: root.textMain
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: Theme.typeScale.mono
                                    padding: Theme.spacing.s2
                                    background: Rectangle {
                                        radius: Theme.radius.xs
                                        color: Theme.token("color-bg-subtle", root.dark)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
