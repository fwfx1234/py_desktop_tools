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

        Label { text: "控件大全"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "项目通用 UI 组件（src/app/ui/），所有控件接受 dark 属性自动适配主题"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // 每个控件 = 代码 + 实例
        Repeater {
            model: [
                { title: "UiButton", code: 'UiButton {  text: "按钮";  variant: "primary";  dark: root.dark;  onClicked: { }  }', demo: 'button' },
                { title: "UiTextField", code: 'UiTextField {  dark: root.dark;  placeholderText: "输入...";  text: vm.prop  }', demo: 'textfield' },
                { title: "UiTextArea", code: 'UiTextArea {  dark: root.dark;  readOnly: false;  Layout.fillWidth: true  }', demo: 'textarea' },
                { title: "UiSwitch", code: 'UiSwitch {  dark: root.dark;  checked: vm.boolProp;  onToggled: { }  }', demo: 'switch' },
                { title: "UiCheckBox", code: 'UiCheckBox {  dark: root.dark;  checked: vm.boolProp  }', demo: 'checkbox' },
                { title: "UiComboBox", code: 'UiComboBox {  dark: root.dark;  model: [{text:"A",value:"a"}];  textRole: "text"  }', demo: 'combobox' },
            ]
            delegate: ColumnLayout { spacing: 6
                Label { text: modelData.title; font.pixelSize: 14; font.bold: true; color: Theme.token("color-text-primary", dark) }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 6; color: Theme.token("color-bg-subtle", dark)
                    Label { anchors.verticalCenter: parent.verticalCenter; x: 10; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark); text: modelData.code }
                }
            }
        }

        // 活例
        Label { text: "活例"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
        RowLayout { spacing: 12
            UiButton { text: "主要按钮"; dark: dark; variant: "primary" }
            UiButton { text: "次要按钮"; dark: dark; variant: "secondary" }
            UiSwitch { dark: dark; checked: true }
            UiCheckBox { dark: dark; checked: true }
        }
        UiTextField { dark: dark; Layout.fillWidth: true; placeholderText: "输入框示例..." }
        UiComboBox { dark: dark; Layout.preferredWidth: 180; model: [{text:"选项 A",value:"a"},{text:"选项 B",value:"b"},{text:"选项 C",value:"c"}]; textRole: "text"; valueRole: "value" }

        Label { text: "所有控件位于 src/app/ui/。新插件页面优先使用这些通用组件，保证主题和风格一致。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
