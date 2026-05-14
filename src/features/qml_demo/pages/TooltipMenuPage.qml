import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "ToolTip / Menu"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "悬停提示 + 右键菜单 —— 辅助交互的核心组件"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // ToolTip
        ColumnLayout { spacing: 8
            Label { text: "ToolTip 悬停提示"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Button {\n    ToolTip.visible: hovered\n    ToolTip.text: '点击发送请求'\n    ToolTip.delay: 500  // 延迟 500ms 显示\n}" }
            }
            RowLayout { spacing: 16
                Rectangle { width: 100; height: 36; radius: 8; color: primary
                    Label { anchors.centerIn: parent; text: "悬停我"; color: "white"; font.pixelSize: 13 }
                    ToolTip.visible: hoverEnabled && ttMouse.containsMouse; ToolTip.text: "这是一个 ToolTip 提示"; ToolTip.delay: 300
                    MouseArea { id: ttMouse; anchors.fill: parent; hoverEnabled: true }
                }
                Rectangle { width: 100; height: 36; radius: 8; color: "#F59E0B"
                    Label { anchors.centerIn: parent; text: "也悬停我"; color: "white"; font.pixelSize: 13 }
                    ToolTip.visible: ttMouse2.containsMouse; ToolTip.text: "可以显示多行\n帮助信息"; ToolTip.delay: 200
                    MouseArea { id: ttMouse2; anchors.fill: parent; hoverEnabled: true }
                }
            }
        }

        // Menu
        ColumnLayout { spacing: 8
            Label { text: "Menu 右键菜单"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Menu {\n    id: ctxMenu\n    MenuItem { text: '复制'; onTriggered: ... }\n    MenuItem { text: '粘贴'; onTriggered: ... }\n    MenuSeparator { }\n    MenuItem { text: '删除'; onTriggered: ... }\n}\n\n// 在 MouseArea 中\nonClicked: ctxMenu.popup()" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 80; radius: 8; border.width: 1; border.color: Theme.token("color-border-default", dark); color: "transparent"
                Label { anchors.centerIn: parent; text: menuResult || "在此区域右键点击"; font.pixelSize: 14; color: Theme.token("color-text-secondary", dark) }
                MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: ctxMenu.popup() }
            }
            property string menuResult: ""
            Menu {
                id: ctxMenu
                MenuItem { text: "复制"; onTriggered: parent.menuResult = "复制" }
                MenuItem { text: "粘贴"; onTriggered: parent.menuResult = "粘贴" }
                MenuSeparator { }
                MenuItem { text: "删除"; onTriggered: parent.menuResult = "删除" }
            }
        }

        Label { text: "ToolTip 用 ToolTip.visible + ToolTip.text + ToolTip.delay 三步。Menu 用 MenuItem + MenuSeparator 构建菜单结构，popup() 弹出。"; font.pixelSize: 12; color: primary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
