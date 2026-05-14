import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    property var historyModel: []
    property var filteredHistory: []
    property string exportMessage: ""
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    function applyHistoryFilter() {
        var q = historyQuery.text ? historyQuery.text.toLowerCase() : ""
        if (q.length === 0) {
            filteredHistory = historyModel
            return
        }
        var out = []
        for (var i = 0; i < historyModel.length; i++) {
            var item = historyModel[i]
            var content = (item.content || "").toLowerCase()
            var t = (item.type || "").toLowerCase()
            if (content.indexOf(q) !== -1 || t.indexOf(q) !== -1)
                out.push(item)
        }
        filteredHistory = out
    }

    Component.onCompleted: {
        content.text = qrVm.initialText()
        if (content.text.length > 0)
            qrVm.generateQr(content.text)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4
        spacing: Theme.spacing.s2
        Label { text: "二维码工具"; font.bold: true; font.pixelSize: Theme.typeScale.title; color: textMain; font.family: "IBM Plex Sans" }
        TabBar {
            id: tabs
            Layout.fillWidth: true
            background: Rectangle { color: panelBg; radius: Theme.radius.md }
            UiTabButton { text: "生成"; dark: dark }
            UiTabButton { text: "扫描"; dark: dark }
            UiTabButton { text: "历史"; dark: dark }
        }
        StackLayout {
            currentIndex: tabs.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "输入文本，实时生成二维码预览"; color: textMuted }
                UiTextArea {
                    id: content
                    dark: dark
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.spacing.s4 * 10
                    placeholderText: "输入文本生成二维码..."
                    onTextChanged: qrVm.generateQr(text)
                }
                Rectangle {
                    Layout.preferredWidth: 220
                    Layout.preferredHeight: 220
                    color: panelBg
                    radius: Theme.radius.xl
                    Image { id: qrVmImage; anchors.fill: parent; anchors.margins: Theme.spacing.s2; fillMode: Image.PreserveAspectFit }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                UiButton {
                    text: "选择二维码图片"
                    dark: dark
                    variant: "primary"
                    onClicked: picker.open()
                }
                UiTextArea { id: scanResult; dark: dark; Layout.fillWidth: true; Layout.fillHeight: true; readOnly: true; placeholderText: "扫描结果会显示在这里" }
            }

            ColumnLayout {
                Layout.fillWidth: true
                RowLayout {
                    UiButton {
                        text: "清空历史"
                        dark: dark
                        variant: "secondary"
                        onClicked: qrVm.clearQrHistory()
                    }
                    UiButton {
                        text: "导出历史"
                        dark: dark
                        variant: "secondary"
                        onClicked: exportDialog.open()
                    }
                    Label { text: "共 " + filteredHistory.length + " / " + historyModel.length + " 条"; color: textMuted }
                }
                UiTextField {
                    id: historyQuery
                    dark: dark
                    Layout.fillWidth: true
                    placeholderText: "搜索历史内容"
                    onTextChanged: applyHistoryFilter()
                }
                Label { visible: exportMessage.length > 0; text: exportMessage; color: Theme.token("color-success", dark) }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: filteredHistory
                    delegate: Rectangle {
                        width: ListView.view.width
                        height: Theme.spacing.s4 * 3 + 2
                        color: index % 2 === 0 ? panelBg : Theme.token("color-bg-subtle-2", dark)
                        border.color: "transparent"
                        radius: Theme.radius.md
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            Label { text: modelData.type; Layout.preferredWidth: 45; color: modelData.type === "扫描" ? Theme.token("color-primary-active", dark) : Theme.token("color-success", dark) }
                            Label { text: modelData.content; Layout.fillWidth: true; elide: Text.ElideRight; color: textMain }
                            Label { text: modelData.createdAt || ""; Layout.preferredWidth: 130; horizontalAlignment: Text.AlignRight; color: textMuted; font.pixelSize: Theme.typeScale.caption }
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: picker
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp)"]
        onAccepted: qrVm.scanQrImage(selectedFile.toString().replace("file:///", ""))
    }

    FileDialog {
        id: exportDialog
        title: "导出二维码历史"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text files (*.txt)"]
        onAccepted: qrVm.exportQrHistory(selectedFile.toString().replace("file:///", ""))
    }

    Connections {
        target: qrVm
        function onQrGenerated(path) { qrVmImage.source = path ? "file:///" + path : "" }
        function onQrScanFinished(text, error) { scanResult.text = error ? error : text }
        function onQrHistoryUpdated(items) {
            historyModel = items
            applyHistoryFilter()
        }
        function onQrHistoryExported(ok, message) {
            exportMessage = message
        }
        function onInputTextChanged(text) {
            if (content.text !== text)
                content.text = text
        }
    }
}
