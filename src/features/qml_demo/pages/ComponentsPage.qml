import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"

    component StarRating: RowLayout {
        property int rating: 0; property int maxStars: 5; property bool dark: false
        spacing: 2
        Repeater { model: maxStars
            delegate: Rectangle { width: 28; height: 28; radius: 14; color: index < parent.rating ? "#F59E0B" : Theme.token("color-bg-subtle-2", parent.parent.dark)
                Label { anchors.centerIn: parent; text: "★"; font.pixelSize: 18; color: index < parent.rating ? "white" : Theme.token("color-text-secondary", parent.parent.dark) }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.parent.rating = index + 1 } } }
    }

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "自定义组件"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "通过 property 暴露接口、signal 发出事件，内部封装 UI 和逻辑"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        ColumnLayout { spacing: 8
            Label { text: "内联组件 component 关键字（同文件内复用）"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 60; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "component StarRating: RowLayout {\n    property int rating: 0\n    property int maxStars: 5\n    // Repeater + 星标 UI ...\n}\n\nStarRating { rating: 3; maxStars: 5; dark: root.dark }" }
            }
            Label { text: "评分组件示例："; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }
            StarRating { id: stars; rating: 3; dark: dark }
            Label { text: "当前评分: " + stars.rating + " / 5"; font.pixelSize: 13; color: primary }
        }

        ColumnLayout { spacing: 8
            Label { text: "独立文件组件（跨页面复用）"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 60; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 11; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "// KvTableSection.qml  — 独立文件\nColumnLayout {\n    property var rows: []\n    signal rowKeyCommitted(int idx, string key)\n    // ...\n}\n\n// 使用： import 'components'\nKvTableSection { rows: vm.data; onRowKeyCommitted: ... }" }
            }
        }

        Label { text: "组件化原则：通用 UI 放 src/app/ui/；插件专属放 components/。property 下传数据，signal 上抛事件。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
