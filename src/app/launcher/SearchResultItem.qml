import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "../theme"

Rectangle {
    id: root

    signal activated()

    property bool dark: false
    property string pluginName: ""
    property string pluginDescription: ""
    property string pluginIcon: ""
    property string pluginMode: "window"
    property string source: "plugin"  // "plugin" | "system" | "app"
    property int highlightStart: -1
    property int highlightLen: 0
    property bool isSelected: false
    property color accentColor: Theme.token("color-primary", dark)

    readonly property bool _useQta: pluginIcon.indexOf("qta:") === 0
    readonly property bool _useFile: pluginIcon.indexOf("file:///") === 0
    readonly property string _qtaName: _useQta ? pluginIcon.slice(4) : ""

    implicitHeight: 56
    radius: 6
    color: isSelected ? Theme.token("color-bg-subtle", dark) : "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 12

        // 图标
        Rectangle {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            Layout.alignment: Qt.AlignVCenter
            radius: 8
            color: isSelected
                ? Theme.token("color-primary-bg", dark)
                : Theme.token("color-bg-subtle", dark)

            // QtAwesome 图标
            Image {
                visible: root._useQta
                anchors.centerIn: parent
                width: 22
                height: 22
                source: root._useQta ? ("image://qta/" + root._qtaName + ";color=" + ("" + root.accentColor).replace("#", "") + ";size=22") : ""
                sourceSize.width: 22
                sourceSize.height: 22
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            // file:/// 图标（应用提取的图标）
            Image {
                visible: root._useFile
                anchors.fill: parent
                anchors.margins: 4
                source: root._useFile ? root.pluginIcon : ""
                sourceSize.width: 28
                sourceSize.height: 28
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            // SVG 图标
            Image {
                id: svgIcon
                visible: !root._useQta && !root._useFile
                anchors.centerIn: parent
                width: 22
                height: 22
                source: (!root._useQta && !root._useFile) ? ("../assets/icons/" + root.pluginIcon + ".svg") : ""
                sourceSize.width: 22
                sourceSize.height: 22
                fillMode: Image.PreserveAspectFit
                opacity: 0
            }

            MultiEffect {
                visible: !root._useQta && !root._useFile
                anchors.fill: svgIcon
                source: svgIcon
                colorization: 1
                colorizationColor: root.accentColor
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 2

            // 名称（支持高亮）
            Label {
                id: nameLabel
                text: {
                    if (root.highlightStart >= 0 && root.highlightLen > 0) {
                        return root.pluginName.substring(0, root.highlightStart) +
                            "<b>" + root.pluginName.substring(root.highlightStart, root.highlightStart + root.highlightLen) + "</b>" +
                            root.pluginName.substring(root.highlightStart + root.highlightLen)
                    }
                    return root.pluginName
                }
                textFormat: Text.RichText
                font.pixelSize: 14
                font.family: "IBM Plex Sans"
                color: Theme.token("color-text-primary", dark)
                elide: Text.ElideRight
            }

            // 描述
            Label {
                text: root.pluginDescription
                font.pixelSize: 11
                font.family: "JetBrains Mono"
                color: Theme.token("color-text-regular", dark)
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        // 来源标签
        Rectangle {
            visible: tagLabel.text !== ""
            Layout.alignment: Qt.AlignVCenter
            radius: 4
            color: {
                if (root.source === "system") return Theme.token("color-warning", dark) + "20"
                if (root.source === "app") return Theme.token("color-info", dark) + "20"
                return Theme.token("color-primary-bg", dark)
            }
            implicitWidth: tagLabel.implicitWidth + 10
            implicitHeight: 20
            Label {
                id: tagLabel
                anchors.centerIn: parent
                text: {
                    if (root.source === "system") return "系统"
                    if (root.source === "app") return "应用"
                    if (root.pluginMode === "inline_view") return "内嵌"
                    if (root.pluginMode === "window") return "窗口"
                    return ""
                }
                font.pixelSize: 10
                font.family: "IBM Plex Sans"
                color: {
                    if (root.source === "system") return Theme.token("color-warning", dark)
                    if (root.source === "app") return Theme.token("color-info", dark)
                    return Theme.token("color-primary", dark)
                }
            }
        }

        // 快捷键提示（选中时显示 Enter 图标）
        Label {
            visible: root.isSelected
            text: "⏎"
            font.pixelSize: 14
            color: Theme.token("color-text-regular", dark)
            Layout.alignment: Qt.AlignVCenter
            Layout.rightMargin: 4
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activated()
    }
}
