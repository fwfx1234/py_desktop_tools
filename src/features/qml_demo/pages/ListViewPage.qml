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

        Label { text: "ListView 列表"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "model（数据源）+ delegate（行模板）—— 声明式列表的核心模式"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        ColumnLayout { spacing: 8
            Label { text: "数据过滤 + 列表展示"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "ListView {  model: vm.items;  delegate: Rectangle { ... }  }  // model 来自 Python @Property" }
            }
            UiTextField { dark: dark; Layout.fillWidth: true; placeholderText: "搜索过滤..."; onTextChanged: qmlDemoVm.filterItems(text) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 220; radius: 8; color: Theme.token("color-bg-subtle", dark); clip: true
                ListView { anchors.fill: parent; anchors.margins: 4; spacing: 4
                    model: qmlDemoVm.items
                    delegate: Rectangle { width: ListView.view.width; height: 34; radius: 6; color: index % 2 === 0 ? "transparent" : Theme.token("color-bg-subtle-2", dark)
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                            Label { text: modelData.name; font.pixelSize: 13; Layout.preferredWidth: 100; color: Theme.token("color-text-primary", dark) }
                            Rectangle { Layout.preferredWidth: 56; Layout.preferredHeight: 20; radius: 10; color: modelData.category === "水果" ? "#F59E0B" : (modelData.category === "蔬菜" ? "#10B981" : (modelData.category === "乳制品" ? "#3B82F6" : "#EC4899"))
                                Label { anchors.centerIn: parent; text: modelData.category; font.pixelSize: 10; color: "white" } }
                            Item { Layout.fillWidth: true }
                            Label { text: modelData.price; font.pixelSize: 14; font.bold: true; color: Theme.token("color-text-primary", dark) } } } }
            }
        }

        Label { text: "model 来自 ViewModel 的 @Property。delegate 定义每行的 UI 模板。数据变了列表自动刷新。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
