import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property string keyLog: "按任意键..."

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "Keys / Shortcut / Focus"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "键盘事件处理 —— 全局快捷键、组件级按键、焦点管理"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Keys attached property
        ColumnLayout { spacing: 8
            Label { text: "Keys 组件级按键捕获"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Item {\n    focus: true\n    Keys.onPressed: console.log(event.key)  // 捕获按键\n    Keys.onEscapePressed: close()          // 监听特定键\n    Keys.onReturnPressed: submit()         // 回车\n}" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 56; radius: 8; border.width: 1; border.color: primary; color: "transparent"
                focus: true
                Label { anchors.centerIn: parent; text: keyLog; font.pixelSize: 14; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark) }
                Keys.onPressed: function (event) { root.keyLog = "Key: " + event.key + "  Text: " + event.text; event.accepted = true } }
            Label { text: "点击上方区域获得焦点后按任意键"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
        }

        // Shortcut
        ColumnLayout { spacing: 8
            Label { text: "Shortcut 快捷键"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Shortcut { sequence: "Ctrl+W"; onActivated: window.close() }' }
            }
            RowLayout {
                Label { text: '按 Ctrl+Shift+T 试试 →'; font.pixelSize: 14; color: Theme.token("color-text-primary", dark) }
                Label { text: shortcutResult; font.pixelSize: 14; font.bold: true; color: primary }
            }
            property string shortcutResult: "等待触发"
            Shortcut { sequence: "Ctrl+Shift+T"; onActivated: parent.shortcutResult = "Shortcut 触发成功！" }
        }

        Label { text: "Keys 附加属性可挂到任何 Item 上捕获按键。Shortcut 是全局的（不受焦点影响）。LauncherWindow 中用 Keys.onEscapePressed 关闭窗口。"; font.pixelSize: 12; color: primary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
