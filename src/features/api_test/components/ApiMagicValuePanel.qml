import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color panelBorder: "#D0D7DE"
    property color textMain: "#333333"
    property color textMuted: "#666666"

    signal insertRequested(string valueText)
    signal closeRequested()

    radius: Theme.radius.lg
    color: root.panelBg
    border.color: root.panelBorder

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacing.s3
                anchors.rightMargin: Theme.spacing.s3
                Label { text: "插入动态值"; color: root.textMain; font.bold: false; Layout.fillWidth: true }
                Item {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    Label {
                        anchors.centerIn: parent
                        text: "×"
                        color: root.textMuted
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.closeRequested()
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

        Repeater {
            model: [
                { title: "读取变量", desc: "读取环境变量/全局变量", value: "{{var.env}}" },
                { title: "数据生成器", desc: "生成特定规则/随机数据（Mock）", value: "{{mock.random}}" },
                { title: "固定值", desc: "写死固定值，可进一步数据处理", value: "fixed_value" },
                { title: "自定义表达式", desc: "满足特定复杂的业务场景需求", value: "{{expr.custom()}}" }
            ]
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacing.s3
                    anchors.rightMargin: Theme.spacing.s3
                    spacing: Theme.spacing.s2
                    Label {
                        text: modelData.title
                        color: root.textMain
                        Layout.fillWidth: true
                        font.pixelSize: Theme.typeScale.body
                    }
                    Label { text: "›"; color: root.textMuted; font.pixelSize: Theme.typeScale.title }
                }
                Label {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.spacing.s3
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Theme.spacing.s2
                    text: modelData.desc
                    color: root.textMuted
                    font.pixelSize: Theme.typeScale.caption
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.insertRequested(modelData.value)
                }
            }
        }
    }
}
