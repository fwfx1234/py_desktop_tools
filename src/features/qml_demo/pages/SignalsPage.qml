import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property var logItems: []

    function addLog(msg) {
        var items = logItems.slice()
        items.unshift({ text: "[" + new Date().toLocaleTimeString() + "] " + msg })
        if (items.length > 12) items.pop()
        logItems = items
    }

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "信号与槽"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "Python Signal → QML Connections / QML 行为 → Python Slot —— 双向通信的核心机制"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Signal → QML
        ColumnLayout { spacing: 8
            Label { text: "Python Signal → QML Connections"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// Python\ndataReady = Signal(str)\nself.dataReady.emit('hello')\n\n// QML\nConnections {\n    target: vm\n    function onDataReady(msg) { ... }\n}" }
            }
            RowLayout {
                UiButton { text: "发信号"; dark: dark; variant: "primary"; onClicked: qmlDemoVm.sendMessage("测试 " + (qmlDemoVm.count + 1)) }
                UiButton { text: "提交表单"; dark: dark; onClicked: qmlDemoVm.submitForm() }
            }
        }

        // @Slot
        ColumnLayout { spacing: 8
            Label { text: "QML 调用 Python @Slot"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// Python: @Slot(result=str)       // QML: var msg = vm.getGreeting()" }
            }
            UiButton { text: "调用 getGreeting()"; dark: dark; variant: "primary"; onClicked: root.addLog(qmlDemoVm.getGreeting()) }
        }

        // 日志
        ColumnLayout { spacing: 8
            Label { text: "接收日志"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 150; radius: 8; color: Theme.token("color-bg-subtle", dark); clip: true
                ListView { anchors.fill: parent; anchors.margins: 4; spacing: 2
                    model: root.logItems
                    delegate: Label { width: ListView.view.width; text: modelData.text; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-regular", dark) } }
            }
        }

        Label { text: "Signal（Python → QML）、@Slot（QML → Python）、@Property（双向）。三者构成完整的通信体系。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }

    Connections { target: qmlDemoVm; function onMessageReceived(msg) { root.addLog(msg) } }
}
