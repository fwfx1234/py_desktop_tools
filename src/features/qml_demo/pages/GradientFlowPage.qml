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

        Label { text: "Gradient / Flow"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "渐变色 + 自动换行布局 —— 让界面更精致的两个工具"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Gradient
        ColumnLayout { spacing: 8
            Label { text: "Gradient 渐变"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// LinearGradient\nRectangle {\n    gradient: Gradient {\n        GradientStop { position: 0.0; color: '#8B5CF6' }\n        GradientStop { position: 1.0; color: '#EC4899' }\n    }\n}" }
            }
            RowLayout { spacing: 12
                Rectangle { Layout.preferredWidth: 120; Layout.preferredHeight: 50; radius: 8
                    gradient: Gradient { GradientStop { position: 0.0; color: primary } GradientStop { position: 1.0; color: "#EC4899" } } }
                Rectangle { Layout.preferredWidth: 120; Layout.preferredHeight: 50; radius: 8
                    gradient: Gradient { GradientStop { position: 0.0; color: "#3B82F6" } GradientStop { position: 1.0; color: "#10B981" } } }
                Rectangle { Layout.preferredWidth: 120; Layout.preferredHeight: 50; radius: 8
                    gradient: Gradient { GradientStop { position: 0.0; color: "#F59E0B" } GradientStop { position: 1.0; color: "#EF4444" } } }
            }
        }

        // Flow
        ColumnLayout { spacing: 8
            Label { text: "Flow 自动换行布局"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Flow {  spacing: 4  // 子元素自动排列，超出宽度自动换行\n    Repeater { model: tags; delegate: ... }  }" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 100; radius: 8; border.width: 1; border.color: Theme.token("color-border-default", dark); color: "transparent"
                Flow { anchors.fill: parent; anchors.margins: 8; spacing: 6
                    Repeater {
                        model: ["QML", "PySide6", "Qt6", "MVVM", "Loader", "Signal", "Property", "Plugin", "Theme", "Binding", "JavaScript", "Python", "QObject", "TabBar", "ListView"]
                        delegate: Rectangle { width: tagText.implicitWidth + 20; height: 26; radius: 13; color: index % 3 === 0 ? primary : (index % 3 === 1 ? "#10B981" : "#F59E0B")
                            Label { id: tagText; anchors.centerIn: parent; text: modelData; color: "white"; font.pixelSize: 11 } }
                    }
                }
            }
        }

        Label { text: "Gradient 替代纯色让 UI 更丰富。Flow 自动处理换行，适合标签/筛选器等场景。"; font.pixelSize: 12; color: primary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
