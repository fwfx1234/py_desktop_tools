import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property string dialogResult: ""; property string filePath: ""

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "弹窗与对话框"; font.pixelSize: 20; font.bold: true; color: primary }
        Label { text: "MessageDialog / FileDialog / Popup —— QML 内置弹窗三种形态"; font.pixelSize: 13; color: Theme.token("color-text-secondary", dark) }

        // MessageDialog
        ColumnLayout { spacing: 8
            Label { text: "MessageDialog 消息弹窗"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'MessageDialog { title: "提示"; text: "消息内容"; buttons: MessageDialog.Ok }' }
            }
            RowLayout { spacing: 8; UiButton { text: "显示消息"; dark: dark; variant: "primary"; onClicked: msgDialog.open() } Label { text: dialogResult; font.pixelSize: 12; color: Theme.token("color-text-secondary", dark) } }
        }

        // FileDialog
        ColumnLayout { spacing: 8
            Label { text: "FileDialog 文件选择"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'FileDialog { fileMode: FileDialog.OpenFile; title: "选择文件" }' }
            }
            RowLayout { spacing: 8; UiButton { text: "选择文件..."; dark: dark; variant: "secondary"; onClicked: filePickDialog.open() } Label { text: filePath; font.pixelSize: 12; color: primary; Layout.fillWidth: true; elide: Text.ElideMiddle } }
        }

        // Popup
        ColumnLayout { spacing: 8
            Label { text: "Popup 自定义面板"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: "JetBrains Mono"; color: Theme.token("color-text-primary", dark)
                    text: 'Popup { width: 300; height: 200;  // 放任意 QML，就是一个小窗口' }
            }
            UiButton { text: "打开自定义面板"; dark: dark; variant: "primary"; onClicked: customPanel.open() }
        }

        Label { text: "MessageDialog 最常用（消息提示/确认）。FileDialog 选文件。Popup 自定义任意内容。"; font.pixelSize: 12; color: primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }

    // ---- Dialogs ----
    MessageDialog { id: msgDialog; title: "消息"; text: "这是一条来自 QML 的消息弹窗。"; buttons: MessageDialog.Ok; onAccepted: parent.dialogResult = "用户点击了 OK" }
    FileDialog { id: filePickDialog; fileMode: FileDialog.OpenFile; title: "选择一个文件"; onAccepted: { parent.filePath = decodeURIComponent(selectedFile.toString()).replace("file:///", "") } }
    Popup { id: customPanel; width: 300; height: 180; anchors.centerIn: Overlay.overlay; background: Rectangle { radius: 12; color: Theme.token("color-bg-surface", parent.dark); border.width: 1; border.color: Theme.token("color-border-default", parent.dark) }
        ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 12
            Label { text: "自定义弹窗"; font.pixelSize: 16; font.bold: true; color: Theme.token("color-text-primary", parent.dark) }
            Label { text: "这里可以放任何 QML 组件：表单、列表、图片……"; font.pixelSize: 13; color: Theme.token("color-text-secondary", parent.dark); Layout.fillWidth: true; wrapMode: Text.Wrap }
            UiButton { text: "关闭"; dark: parent.dark; variant: "primary"; Layout.alignment: Qt.AlignHCenter; onClicked: customPanel.close() } } }
}
