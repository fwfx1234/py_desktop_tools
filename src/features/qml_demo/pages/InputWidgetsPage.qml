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

        Label { text: "Slider / ProgressBar / SpinBox"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "数值输入输出三件套 —— 滑块、进度条、数字框"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // Slider
        ColumnLayout { spacing: 8
            Label { text: "Slider 滑块"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Slider {  from: 0;  to: 100;  value: 50;  onValueChanged: ...  }' }
            }
            RowLayout { spacing: 12
                Label { text: "0"; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) }
                Slider { id: quality; from: 0; to: 100; value: 75; Layout.fillWidth: true
                    background: Rectangle { x: quality.leftPadding; y: quality.topPadding + quality.availableHeight / 2 - 2; implicitWidth: 200; implicitHeight: 4; width: quality.availableWidth; height: 4; radius: 2; color: Theme.token("color-bg-subtle-2", dark)
                        Rectangle { width: quality.visualPosition * parent.width; height: parent.height; radius: 2; color: primary } }
                    handle: Rectangle { x: quality.leftPadding + quality.visualPosition * (quality.availableWidth - width); y: quality.topPadding + quality.availableHeight / 2 - height / 2; implicitWidth: 18; implicitHeight: 18; radius: 9; color: primary } }
                Label { text: quality.value; font.pixelSize: 14; font.bold: true; color: primary; Layout.preferredWidth: 30 }
            }
        }

        // ProgressBar
        ColumnLayout { spacing: 8
            Label { text: "ProgressBar 进度条"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'ProgressBar {  from: 0;  to: 100;  value: 75  }' }
            }
            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: quality.value
                background: Rectangle { implicitWidth: 200; implicitHeight: 8; radius: 4; color: Theme.token("color-bg-subtle-2", dark) }
                contentItem: Item { implicitWidth: 200; implicitHeight: 8
                    Rectangle { width: quality.visualPosition * parent.width; height: parent.height; radius: 4; color: value > 80 ? "#EF4444" : (value > 50 ? primary : "#10B981") } } }
        }

        // SpinBox
        ColumnLayout { spacing: 8
            Label { text: "SpinBox 数字输入"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'SpinBox {  from: 0;  to: 100;  value: 50;  editable: true  }' }
            }
            RowLayout { SpinBox { id: sp; from: 0; to: 100; value: 50; editable: true; Layout.preferredWidth: 120 } Label { text: "值: " + sp.value; font.pixelSize: 14; font.bold: true; color: primary; Layout.leftMargin: 12 } }
        }

        Label { text: "Slider 适合质量/尺寸调节（如图片压缩）。ProgressBar 展示进度。SpinBox 精确数值输入。"; font.pixelSize: 12; color: primary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
