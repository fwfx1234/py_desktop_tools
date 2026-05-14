import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 24

        Label { text: "动画"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "Behavior（自动）+ 显式 Animation（手动控制）—— 声明式动画"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Behavior
        ColumnLayout { spacing: 8
            Label { text: "Behavior — 属性变化自动动画"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Behavior on width {  NumberAnimation { duration: 300; easing.type: Easing.OutCubic }  }' }
            }
            Label { text: "点击方块 →"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
            Rectangle { id: box; width: 60; height: 44; radius: 8; color: primary
                Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: 300 } }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { box.width = box.width === 60 ? 220 : 60; box.color = box.width > 60 ? "#EF4444" : primary } }
                Label { anchors.centerIn: parent; text: box.width > 60 ? "点击收起" : "点击展开"; font.pixelSize: 12; color: "white" }
            }
        }

        // Rotation + Pulse
        ColumnLayout { spacing: 8
            Label { text: "RotationAnimation + SequentialAnimation"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            RowLayout { spacing: 40
                Rectangle { id: spinner; width: 56; height: 56; radius: 10; color: "#10B981"
                    RotationAnimation on rotation { id: spin; from: 0; to: 360; duration: 600; easing.type: Easing.OutCubic; running: false }
                    Label { anchors.centerIn: parent; text: "↻"; font.pixelSize: 24; color: "white" }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { spin.from = spinner.rotation; spin.to = spinner.rotation + 360; spin.restart() } }
                }
                Rectangle { id: pulse; width: 50; height: 50; radius: 25; color: "#F59E0B"
                    SequentialAnimation { running: true; loops: Animation.Infinite
                        NumberAnimation { target: pulse; property: "scale"; to: 1.25; duration: 500; easing.type: Easing.InOutQuad }
                        NumberAnimation { target: pulse; property: "scale"; to: 1.0; duration: 500; easing.type: Easing.InOutQuad } } }
            }
            Label { text: "点击旋转 / 自动脉冲"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
        }

        Label { text: "Behavior 最常用（属性变→自动动）。显式 Animation 用于复杂序列。不需要手动写帧循环。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
