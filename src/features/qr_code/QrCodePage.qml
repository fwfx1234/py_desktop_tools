import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    property var historyModel: []
    property var filteredHistory: []
    property string statusText: "就绪"
    property color statusColor: textMuted
    property string saveRootPath: ""
    property string scanResultText: ""
    property string scanErrorText: ""

    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color subtleBg: Theme.token("color-bg-subtle", dark)
    readonly property color statusBg: Theme.token("color-status-bar-bg", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color accent: Theme.token("color-primary-active", dark)
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)
    readonly property color infoColor: Theme.token("color-info", dark)

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else statusColor = textMuted
    }

    function applyHistoryFilter() {
        var q = historyQuery.text ? historyQuery.text.toLowerCase() : ""
        if (q.length === 0) { filteredHistory = historyModel; return }
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
        saveRootPath = qrVm.saveRoot()
        inputArea.text = qrVm.initialText()
        if (inputArea.text.length > 0)
            qrVm.previewQr(inputArea.text)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        // ===== 顶部标题栏 =====
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["1"]

            Label {
                text: "二维码"
                font.bold: true
                font.pixelSize: Theme.fontSize.title
                color: textMain
                font.family: Theme.fontFamily.ui
            }

            Item { Layout.fillWidth: true }

            // 圆形图标按钮：扫描
            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 14
                color: scanArea.containsMouse ? Theme.token("color-nav-icon-idle-bg", root.dark) : "transparent"
                border.color: panelBorder
                border.width: 1
                UiIcon {
                    anchors.centerIn: parent
                    width: 14
                    height: 14
                    name: "mdi6.qrcode-scan"
                    color: textMain
                }
                MouseArea {
                    id: scanArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: scanPopup.open()
                    ToolTip.visible: containsMouse
                    ToolTip.text: "扫描二维码图片"
                }
            }

            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 14
                color: historyArea.containsMouse ? Theme.token("color-nav-icon-idle-bg", root.dark) : "transparent"
                border.color: panelBorder
                border.width: 1
                UiIcon {
                    anchors.centerIn: parent
                    width: 14
                    height: 14
                    name: "mdi6.history"
                    color: textMain
                }
                Rectangle {
                    visible: historyModel.length > 0
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: -2
                    anchors.rightMargin: -2
                    width: 8
                    height: 8
                    radius: 4
                    color: accent
                }
                MouseArea {
                    id: historyArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { applyHistoryFilter(); historyPopup.open() }
                    ToolTip.visible: containsMouse
                    ToolTip.text: "查看历史 (" + historyModel.length + ")"
                }
            }
        }

        // ===== 主区域：输入 + 预览 =====
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.space["3"]

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.space["1"]
                Label {
                    text: "内容"
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: panelBg
                    radius: Theme.radii.md
                    border.color: panelBorder
                    border.width: 1
                    UiTextArea {
                        id: inputArea
                        anchors.fill: parent
                        anchors.margins: 2
                        dark: root.dark
                        placeholderText: "输入文本生成二维码..."
                        wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                        onTextChanged: qrVm.previewQr(text)
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 200
                spacing: Theme.space["1"]
                Label {
                    text: "预览"
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }
                Rectangle {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 200
                    Layout.alignment: Qt.AlignTop
                    color: panelBg
                    radius: Theme.radii.lg
                    border.color: panelBorder
                    border.width: 1
                    Image {
                        id: qrImage
                        anchors.fill: parent
                        anchors.margins: Theme.space["2"]
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        asynchronous: true
                        sourceSize.width: 360
                        sourceSize.height: 360
                    }
                    Label {
                        visible: !qrImage.source || String(qrImage.source).length === 0
                        anchors.centerIn: parent
                        text: "二维码预览"
                        color: textSubtle
                        font.pixelSize: Theme.fontSize.caption
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // ===== 主操作按钮 =====
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["1"]
            UiButton {
                text: "保存图片"
                dark: root.dark
                variant: "primary"
                enabled: inputArea.text.trim().length > 0
                onClicked: qrVm.saveQr(inputArea.text)
            }
            UiButton {
                text: "复制内容"
                dark: root.dark
                variant: "secondary"
                enabled: inputArea.text.trim().length > 0
                onClicked: qrVm.copyQrContent(inputArea.text)
            }
            UiButton {
                text: "从剪贴板"
                dark: root.dark
                variant: "ghost"
                onClicked: qrVm.fillFromClipboard()
            }
            Item { Layout.fillWidth: true }
            UiButton {
                text: "清空"
                dark: root.dark
                variant: "ghost"
                enabled: inputArea.text.length > 0
                onClicked: { inputArea.text = ""; qrVm.previewQr("") }
            }
        }

        // ===== 状态栏 =====
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 26
            color: statusBg
            radius: Theme.radii.sm
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["1"]
                spacing: Theme.space["2"]
                Label {
                    text: statusText
                    color: statusColor
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
                Label {
                    text: saveRootPath
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    font.family: Theme.fontFamily.mono
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: root.width * 0.45
                }
                Rectangle {
                    Layout.preferredWidth: 22
                    Layout.preferredHeight: 22
                    radius: 11
                    color: finderArea.containsMouse ? Theme.token("color-nav-icon-idle-bg", root.dark) : "transparent"
                    UiIcon {
                        anchors.centerIn: parent
                        width: 12
                        height: 12
                        name: "mdi6.folder-open-outline"
                        color: textMain
                    }
                    MouseArea {
                        id: finderArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: qrVm.revealSaveRoot()
                        ToolTip.visible: containsMouse
                        ToolTip.text: "在 Finder 中显示"
                    }
                }
            }
        }
    }

    // ===== 扫描 Popup =====
    Popup {
        id: scanPopup
        modal: true
        focus: true
        width: Math.min(420, root.width - 40)
        height: Math.min(360, root.height - 40)
        anchors.centerIn: parent
        padding: 0
        background: Rectangle {
            color: panelBg
            radius: Theme.radii.lg
            border.color: panelBorder
            border.width: 1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space["3"]
            spacing: Theme.space["2"]

            RowLayout {
                Layout.fillWidth: true
                Label { text: "扫描二维码"; color: textMain; font.bold: true; font.pixelSize: Theme.fontSize.heading }
                Item { Layout.fillWidth: true }
                UiButton { text: "关闭"; dark: root.dark; variant: "ghost"; implicitWidth: 56; onClicked: scanPopup.close() }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                color: scanDrop.containsDrag ? Theme.token("color-primary-bg", root.dark) : subtleBg
                radius: Theme.radii.md
                border.color: scanDrop.containsDrag ? accent : panelBorder
                border.width: scanDrop.containsDrag ? 2 : 1
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Label { text: "将图片拖到此处"; color: textSubtle; horizontalAlignment: Text.AlignHCenter; Layout.alignment: Qt.AlignHCenter }
                    UiButton { text: "选择图片"; dark: root.dark; variant: "secondary"; Layout.alignment: Qt.AlignHCenter; onClicked: scanPicker.open() }
                }
                DropArea {
                    id: scanDrop
                    anchors.fill: parent
                    onDropped: function(drop) {
                        if (drop.urls && drop.urls.length > 0) {
                            qrVm.scanQrImage(String(drop.urls[0]))
                            drop.acceptProposedAction()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: subtleBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1
                UiScrollView {
                    anchors.fill: parent
                    clip: true
                    UiTextArea {
                        readOnly: true
                        dark: root.dark
                        width: parent.width
                        height: parent.height
                        text: scanErrorText.length > 0 ? scanErrorText : (scanResultText.length > 0 ? scanResultText : "扫描结果将显示在这里")
                        color: scanErrorText.length > 0 ? dangerColor : textMain
                        wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                UiButton {
                    text: "复制结果"
                    dark: root.dark
                    variant: "secondary"
                    enabled: scanResultText.length > 0
                    onClicked: qrVm.copyQrContent(scanResultText)
                }
                UiButton {
                    text: "用作生成内容"
                    dark: root.dark
                    variant: "primary"
                    enabled: scanResultText.length > 0
                    onClicked: {
                        inputArea.text = scanResultText
                        qrVm.previewQr(scanResultText)
                        scanPopup.close()
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }
    }

    // ===== 历史 Popup =====
    Popup {
        id: historyPopup
        modal: true
        focus: true
        width: Math.min(480, root.width - 40)
        height: Math.min(420, root.height - 40)
        anchors.centerIn: parent
        padding: 0
        background: Rectangle {
            color: panelBg
            radius: Theme.radii.lg
            border.color: panelBorder
            border.width: 1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space["3"]
            spacing: Theme.space["2"]

            RowLayout {
                Layout.fillWidth: true
                Label { text: "历史记录"; color: textMain; font.bold: true; font.pixelSize: Theme.fontSize.heading }
                Item { Layout.fillWidth: true }
                UiButton { text: "导出"; dark: root.dark; variant: "ghost"; implicitWidth: 56; onClicked: qrVm.exportQrHistoryAuto() }
                UiButton { text: "清空"; dark: root.dark; variant: "ghost"; implicitWidth: 56; onClicked: qrVm.clearQrHistory() }
                UiButton { text: "关闭"; dark: root.dark; variant: "ghost"; implicitWidth: 56; onClicked: historyPopup.close() }
            }

            UiTextField {
                id: historyQuery
                dark: root.dark
                Layout.fillWidth: true
                placeholderText: "搜索历史内容"
                onTextChanged: applyHistoryFilter()
            }

            Label {
                text: "共 " + filteredHistory.length + " / " + historyModel.length + " 条"
                color: textSubtle
                font.pixelSize: Theme.fontSize.caption
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: subtleBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1

                Label {
                    anchors.centerIn: parent
                    visible: filteredHistory.length === 0
                    text: historyModel.length === 0 ? "暂无历史" : "无匹配项"
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }

                ListView {
                    anchors.fill: parent
                    anchors.margins: 2
                    visible: filteredHistory.length > 0
                    clip: true
                    model: filteredHistory
                    spacing: 1
                    delegate: Rectangle {
                        width: ListView.view.width
                        height: 38
                        color: index % 2 === 0 ? panelBg : subtleBg
                        radius: Theme.radii.xs
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["2"]
                            anchors.rightMargin: Theme.space["1"]
                            spacing: Theme.space["1"]
                            Label {
                                text: modelData.type
                                Layout.preferredWidth: 36
                                font.pixelSize: Theme.fontSize.caption
                                color: modelData.type === "扫描" ? infoColor
                                     : modelData.type === "保存" ? successColor
                                     : accent
                            }
                            Label {
                                text: modelData.content
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                                color: textMain
                                font.family: Theme.fontFamily.mono
                                font.pixelSize: Theme.fontSize.mono
                            }
                            Label {
                                text: (modelData.createdAt || "").split(" ").pop()
                                color: textSubtle
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                Layout.preferredWidth: 60
                                horizontalAlignment: Text.AlignRight
                            }
                            UiButton {
                                text: "用"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 34
                                implicitHeight: 24
                                ToolTip.visible: hovered
                                ToolTip.text: "用作生成内容"
                                onClicked: {
                                    inputArea.text = modelData.content
                                    qrVm.previewQr(modelData.content)
                                    historyPopup.close()
                                }
                            }
                            UiButton {
                                text: "复制"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 46
                                implicitHeight: 24
                                onClicked: qrVm.copyQrContent(modelData.content)
                            }
                            UiButton {
                                text: "删除"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 46
                                implicitHeight: 24
                                onClicked: qrVm.removeHistoryItem(modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: scanPicker
        title: "选择二维码图片"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp)"]
        onAccepted: qrVm.scanQrImage(String(selectedFile))
    }

    Connections {
        target: qrVm
        function onPreviewUpdated(path) {
            qrImage.source = path ? ("file://" + path + "?t=" + Date.now()) : ""
        }
        function onQrSaved(ok, path, message) {
            setStatus(message, ok ? "success" : "error")
        }
        function onQrCopied(ok, message) {
            setStatus(message, ok ? "success" : "error")
        }
        function onQrScanFinished(text, error) {
            if (error) {
                scanResultText = ""
                scanErrorText = error
                setStatus(error, "error")
            } else {
                scanResultText = text
                scanErrorText = ""
                setStatus("扫描成功", "success")
                if (!scanPopup.opened) scanPopup.open()
            }
        }
        function onQrHistoryUpdated(items) {
            historyModel = items
            applyHistoryFilter()
        }
        function onQrHistoryExported(ok, message) {
            setStatus(message, ok ? "success" : "error")
        }
        function onQrSaveRootRevealed(ok, message) {
            if (!ok) setStatus(message, "error")
        }
        function onInputTextChanged(text) {
            if (inputArea.text !== text)
                inputArea.text = text
        }
    }
}
