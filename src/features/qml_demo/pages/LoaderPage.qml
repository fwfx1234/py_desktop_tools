import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property string loadedTitle: ""

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "Loader 动态加载"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "按需加载 QML 页面 —— 插件系统的核心机制。不 active 时占零资源。"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        ColumnLayout { spacing: 8
            Label { text: "基本用法"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// 声明占位\nLoader {\n    id: loader\n    active: false\n    source: 'SomePage.qml'\n}\n\n// 触发加载\nButton { onClicked: loader.active = true }\n\n// 访问加载的内容\nloader.item.someProperty" }
            }
        }

        ColumnLayout { spacing: 8
            Label { text: "活例：加载 / 卸载"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            RowLayout {
                UiButton { text: "加载卡片"; dark: dark; variant: "primary"; onClicked: demoLoader.active = true }
                UiButton { text: "卸载"; dark: dark; variant: "secondary"; onClicked: demoLoader.active = false }
                Label { text: demoLoader.active ? "状态: 已加载" : "状态: 空闲（零开销）"; font.pixelSize: 12; color: demoLoader.active ? "#10B981" : Theme.token("color-text-secondary", dark) }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 80; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Loader {
                    id: demoLoader; anchors.fill: parent; anchors.margins: 8; active: false
                    sourceComponent: Component {
                        Rectangle { color: "transparent"
                            RowLayout { anchors.centerIn: parent; spacing: 12
                                Rectangle { width: 40; height: 40; radius: 8; color: primary
                                    Label { anchors.centerIn: parent; text: "✓"; color: "white"; font.pixelSize: 18 } }
                                Label { text: "我是 Loader 加载的！"; font.pixelSize: 14; font.bold: true; color: Theme.token("color-text-primary", dark) } } } }
                }
            }
        }

        ColumnLayout { spacing: 8
            Label { text: "项目中的实际使用"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Label { text: "LauncherWindow 和 PluginWindow 都在用 Loader 实现插件页面的懒加载。"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }

        Label { text: "Loader 的核心优势：active=false 时完全不创建内部对象，零内存占用。配合 asynchronous:true 后台加载不卡 UI。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
