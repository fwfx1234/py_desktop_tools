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

        Label { text: "布局系统"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "RowLayout / ColumnLayout / Grid / anchors —— 声明式布局，告别手算坐标"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // RowLayout
        ColumnLayout { spacing: 8
            Label { text: "RowLayout 水平排列"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "RowLayout { spacing: 8  ...  }  // 子元素自动水平排列" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; border.width: 1; border.color: primary; color: "transparent"
                RowLayout { anchors.fill: parent; anchors.margins: 4; spacing: 4
                    Repeater { model: 4; delegate: Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; color: primary; opacity: 0.15 + index * 0.25 } } }
            }
        }

        // ColumnLayout
        ColumnLayout { spacing: 8
            Label { text: "ColumnLayout 垂直排列"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "ColumnLayout { spacing: 6  ...  }  // 子元素自动垂直排列" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 90; radius: 8; border.width: 1; border.color: primary; color: "transparent"
                ColumnLayout { anchors.fill: parent; anchors.margins: 4; spacing: 2
                    Repeater { model: 3; delegate: Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 3; color: primary; opacity: 0.2 + index * 0.35 } } }
            }
        }

        // Grid
        ColumnLayout { spacing: 8
            Label { text: "Grid / GridLayout 网格"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "GridLayout { columns: 3;  rowSpacing: 4;  columnSpacing: 4  ...  }" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 64; radius: 8; border.width: 1; border.color: primary; color: "transparent"
                GridLayout { anchors.centerIn: parent; columns: 3; rowSpacing: 4; columnSpacing: 4
                    Repeater { model: 6; delegate: Rectangle { width: 44; height: 24; radius: 3; color: primary; opacity: 0.2 + (index % 3) * 0.35 } } }
            }
        }

        // anchors
        ColumnLayout { spacing: 8
            Label { text: "anchors 锚定"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: "anchors.left: parent.left   anchors.top: parent.top   anchors.centerIn: parent" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 56; radius: 8; border.width: 1; border.color: primary; color: "transparent"
                Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 6; width: 70; height: 18; radius: 3; color: primary }
                Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 6; width: 70; height: 18; radius: 3; color: "#EF4444" }
                Rectangle { anchors.centerIn: parent; width: 60; height: 18; radius: 3; color: "#10B981" }
            }
        }

        Label { text: "要点：用 Layout 系列（RowLayout/ColumnLayout/GridLayout）+ spacing 控制间距，用 fillWidth/fillHeight 控制伸缩。anchors 适合精确定位。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
