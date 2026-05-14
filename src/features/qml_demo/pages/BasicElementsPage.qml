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

        // ── 标题 ──
        Label { text: "基础元素"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "Rectangle、Text、Image、Item —— 一切 QML 页面的起点"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // ── Rectangle ──
        ColumnLayout { spacing: 8
            Label { text: "Rectangle 矩形容器"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Rectangle {  width: 100;  height: 60;  radius: 12;  color: "#8B5CF6"  }' }
            }
            RowLayout { spacing: 20
                Rectangle { width: 100; height: 60; radius: 4; color: primary; Layout.alignment: Qt.AlignVCenter }
                Rectangle { width: 80; height: 40; radius: 20; color: "#EF4444"; Layout.alignment: Qt.AlignVCenter }
                Rectangle { width: 60; height: 60; radius: 8; color: "#10B981"; border.width: 2; border.color: "#064E3B"; Layout.alignment: Qt.AlignVCenter }
            }
            Label { text: "设置 width/height/radius/color，基础矩形就有了。"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
        }

        // ── Text ──
        ColumnLayout { spacing: 8
            Label { text: "Text / Label 文本"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Text {  text: 'Hello';  font.pixelSize: 20;  font.bold: true  }" }
            }
            RowLayout { spacing: 20
                Text { text: "Hello QML"; font.pixelSize: 22; font.bold: true; color: primary }
                Text { text: "优雅"; font.pixelSize: 24; font.italic: true; color: "#F59E0B" }
                Text { text: "简洁"; font.pixelSize: 18; font.family: "JetBrains Mono"; color: "#10B981" }
            }
            Label { text: "font 系列属性控制大小、粗细、斜体、字体。"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
        }

        // ── Image ──
        ColumnLayout { spacing: 8
            Label { text: "Image 图片"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Image {  width: 44;  height: 44;  source: "image://qta/mdi6.star;color=xxx;size=44"  }' }
            }
            RowLayout { spacing: 16
                Repeater {
                    model: ["mdi6.emoticon-happy-outline", "mdi6.star", "mdi6.heart", "mdi6.thumb-up-outline"]
                    delegate: Image { width: 40; height: 40; fillMode: Image.PreserveAspectFit; source: "image://qta/" + modelData + ";color=" + primary.replace("#", "") + ";size=40" }
                }
            }
            Label { text: "本项目用 image://qta/ 协议加载 qtawesome 图标。"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
        }

        // ── Item ──
        ColumnLayout { spacing: 8
            Label { text: "Item 透明容器"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Item { } —— 没有视觉外观的容器，页面根元素必须是它" }
            }
            Label { text: "作为最轻量容器使用。做 inline_view 插件页面时，根元素必须是 Item。"; font.pixelSize: 12; color: primary }
        }
    }
}
