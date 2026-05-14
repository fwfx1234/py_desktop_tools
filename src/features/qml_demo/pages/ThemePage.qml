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

        Label { text: "主题系统"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "Theme.token(name, dark) → 深浅色自动切换，全局统一"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        ColumnLayout { spacing: 8
            Label { text: "语义色板（所有颜色来源）"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'color: Theme.token("color-text-primary", dark)  // ✓  正确\ncolor: "#333333"  // ✗  硬编码，深色模式下不可见' }
            }
            Repeater {
                model: [
                    "color-bg-page", "color-bg-surface", "color-bg-subtle", "color-bg-subtle-2",
                    "color-text-primary", "color-text-regular", "color-text-secondary",
                    "color-primary-active", "color-border-default",
                ]
                delegate: RowLayout { spacing: 8
                    Rectangle { Layout.preferredWidth: 28; Layout.preferredHeight: 22; radius: 4; color: Theme.token(modelData, dark); border.width: 1; border.color: Theme.token("color-border-default", dark) }
                    Label { text: modelData; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark) }
                }
            }
        }

        ColumnLayout { spacing: 8
            Label { text: "当前主题：" + (dark ? "深色" : "浅色"); font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Label { text: "Theme 是 qmldir 声明的 singleton。所有颜色走 token，修改 Theme.qml 全局生效。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
}
