import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property int tabIndex: 0

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "TabBar + StackLayout"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "选项卡切换 + 内容区 —— api_debugger、clipboard 等插件的基础布局模式"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        ColumnLayout { spacing: 8
            Label { text: "基本模式"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", dark)
                    text: "TabBar {\n    id: bar; currentIndex: root.tabIndex\n    TabButton { text: '标签 A' }\n    TabButton { text: '标签 B' }\n    TabButton { text: '标签 C' }\n}\n\nStackLayout {\n    currentIndex: bar.currentIndex\n    Rectangle { }  // 页面 A\n    Rectangle { }  // 页面 B\n    Rectangle { }  // 页面 C\n}" }
            }
        }

        ColumnLayout { spacing: 8
            Label { text: "活例"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            TabBar {
                id: bar; Layout.fillWidth: true
                TabButton { text: "基础信息"; font.pixelSize: 12 }
                TabButton { text: "高级设置"; font.pixelSize: 12 }
                TabButton { text: "日志"; font.pixelSize: 12 }
                background: Rectangle { color: "transparent" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 140; radius: 8; border.width: 1; border.color: Theme.token("color-border-default", dark); color: "transparent"
                StackLayout { anchors.fill: parent; anchors.margins: 12; currentIndex: bar.currentIndex
                    ColumnLayout { spacing: 6
                        Label { text: "名称: 演示项目"; font.pixelSize: 14; color: Theme.token("color-text-primary", dark) }
                        Label { text: "版本: 1.0.0"; font.pixelSize: 14; color: Theme.token("color-text-primary", dark) }
                        Label { text: "作者: Py Desktop Tools"; font.pixelSize: 14; color: Theme.token("color-text-primary", dark) }
                        Item { Layout.fillHeight: true } }
                    ColumnLayout { spacing: 6
                        RowLayout { Label { text: "自动更新"; font.pixelSize: 13; color: Theme.token("color-text-primary", dark); Layout.fillWidth: true } UiSwitch { dark: dark; checked: true } }
                        RowLayout { Label { text: "通知提醒"; font.pixelSize: 13; color: Theme.token("color-text-primary", dark); Layout.fillWidth: true } UiSwitch { dark: dark; checked: false } }
                        RowLayout { Label { text: "深色模式"; font.pixelSize: 13; color: Theme.token("color-text-primary", dark); Layout.fillWidth: true } UiSwitch { dark: dark; checked: dark } }
                        Item { Layout.fillHeight: true } }
                    ColumnLayout { spacing: 4
                        Label { text: "[12:00] 启动完成"; font.pixelSize: 12; color: "#10B981"; font.family: Theme.fontFamily.mono }
                        Label { text: "[12:01] 加载插件列表"; font.pixelSize: 12; color: Theme.token("color-text-regular", dark); font.family: Theme.fontFamily.mono }
                        Label { text: "[12:02] 初始化完成"; font.pixelSize: 12; color: Theme.token("color-text-regular", dark); font.family: Theme.fontFamily.mono }
                        Item { Layout.fillHeight: true } } }
            }
        }

        Label { text: "TabBar 控制 currentIndex，StackLayout 跟随。这是 api_debugger、clipboard 等插件的标准布局模式。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
