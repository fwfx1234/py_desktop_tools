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

        Label { text: "属性绑定"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "QML 最强大的特性 —— 属性自动跟踪变化，无需手动刷新 UI"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // 双向绑定
        ColumnLayout { spacing: 8
            Label { text: "双向绑定 Python ↔ QML"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// Python: @Property(str) formName\n// QML: text: qmlDemoVm.formName\n// 改任何一边，另一边自动同步" }
            }
            RowLayout {
                UiTextField { dark: dark; Layout.preferredWidth: 150; placeholderText: "姓名"; text: qmlDemoVm.formName; onTextChanged: qmlDemoVm.formName = text }
                UiTextField { dark: dark; Layout.preferredWidth: 200; placeholderText: "邮箱"; text: qmlDemoVm.formEmail; onTextChanged: qmlDemoVm.formEmail = text }
                UiButton { text: "提交"; dark: dark; variant: "primary"; onClicked: qmlDemoVm.submitForm() }
            }
        }

        // 声明式绑定
        ColumnLayout { spacing: 8
            Label { text: "声明式绑定：自动跟随变化"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "Rectangle {  width: 40 + count * 5;  color: count > 5 ? '#EF4444' : '#10B981'  }" }
            }
            RowLayout { spacing: 12
                UiButton { text: "-"; dark: dark; onClicked: qmlDemoVm.decrement() }
                Label { text: qmlDemoVm.count; font.pixelSize: 24; font.bold: true; Layout.preferredWidth: 50; horizontalAlignment: Text.AlignHCenter
                    color: qmlDemoVm.count > 5 ? "#EF4444" : (qmlDemoVm.count > 0 ? primary : Theme.token("color-text-primary", dark)) }
                UiButton { text: "+"; dark: dark; variant: "primary"; onClicked: qmlDemoVm.increment() }
                Rectangle { width: 40 + qmlDemoVm.count * 5; height: 36; radius: 6; color: qmlDemoVm.count > 5 ? "#EF4444" : primary }
            }
        }

        // 颜色双向绑定
        ColumnLayout { spacing: 8
            Label { text: "颜色选择：跨组件同步"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            RowLayout { spacing: 6
                Repeater { model: ["#8B5CF6", "#EF4444", "#10B981", "#F59E0B", "#3B82F6", "#EC4899"]
                    delegate: Rectangle { width: 32; height: 32; radius: 16; color: modelData; border.width: qmlDemoVm.demoColor === modelData ? 3 : 0; border.color: Theme.token("color-text-primary", dark)
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: qmlDemoVm.setDemoColor(modelData) } } }
            }
            Rectangle { width: 120; height: 36; radius: 8; color: qmlDemoVm.demoColor
                Label { anchors.centerIn: parent; text: qmlDemoVm.demoColor; color: "white"; font.family: "JetBrains Mono"; font.pixelSize: 12 } }
        }

        Label { text: "QML 绑定是自动跟踪的 —— 值变了，所有依赖它的表达式自动重新计算。不需要手动 setState/updateView。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
