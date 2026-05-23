import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    id: root
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property int elapsed: 0

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "Timer + states"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "Timer 定时操作 / states 状态机 —— QML 的两大实用机制"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Timer
        ColumnLayout { spacing: 8
            Label { text: "Timer 定时器"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", dark)
                    text: "Timer {  interval: 1000;  running: true;  repeat: true;  onTriggered: { }  }" }
            }
            RowLayout { spacing: 12
                UiButton { text: "开始"; dark: dark; variant: "primary"; onClicked: ticker.start() }
                UiButton { text: "暂停"; dark: dark; variant: "secondary"; onClicked: ticker.stop() }
                UiButton { text: "重置"; dark: dark; onClicked: { root.elapsed = 0; ticker.stop() } }
                Label { text: "计时: " + root.elapsed + " 秒"; font.pixelSize: 18; font.bold: true; color: primary; Layout.leftMargin: 12 }
            }
            Timer { id: ticker; interval: 1000; repeat: true; running: false; onTriggered: root.elapsed += 1 }
        }

        // states
        ColumnLayout { spacing: 8
            Label { text: "states 状态机"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", dark)
                    text: 'states: [\n    State { name: "normal"; PropertyChanges { target: box; color: "#10B981" } },\n    State { name: "warning"; PropertyChanges { target: box; color: "#F59E0B" } },\n    State { name: "error"; PropertyChanges { target: box; color: "#EF4444" } }\n]\n// 切换: root.state = "error"' }
            }
            RowLayout { spacing: 8
                UiButton { text: "正常"; dark: dark; variant: stateBox.state === "normal" ? "primary" : "secondary"; onClicked: stateBox.state = "normal" }
                UiButton { text: "警告"; dark: dark; variant: stateBox.state === "warning" ? "primary" : "secondary"; onClicked: stateBox.state = "warning" }
                UiButton { text: "错误"; dark: dark; variant: stateBox.state === "error" ? "primary" : "secondary"; onClicked: stateBox.state = "error" }
            }
            Rectangle {
                id: stateBox; Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8
                states: [
                    State { name: "normal"; PropertyChanges { target: stateBox; color: "#10B981" } },
                    State { name: "warning"; PropertyChanges { target: stateBox; color: "#F59E0B" } },
                    State { name: "error"; PropertyChanges { target: stateBox; color: "#EF4444" } }
                ]
                state: "normal"
                Label { anchors.centerIn: parent; font.pixelSize: 14; font.bold: true; color: "white"
                    text: stateBox.state === "error" ? "✗ 发生错误" : (stateBox.state === "warning" ? "⚠ 需要注意" : "✓ 系统正常") }
                transitions: Transition { ColorAnimation { duration: 300 } }
            }
        }

        Label { text: "Timer 用于延迟/定时操作（如剪贴板隐藏延迟、热重载防抖）。states 用声明式替代 if/else 写不同状态 UI。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
