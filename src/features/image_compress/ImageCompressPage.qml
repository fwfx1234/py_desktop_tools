import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    property var entries: []
    property int pendingCount: 0
    property int quality: 80
    property string mode: "visual"
    property string statusText: "复制一张图片后点击「粘贴剪贴板」"
    property color statusColor: textMuted
    property string pendingSaveAsId: ""

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
    readonly property color warnColor: Theme.token("color-warning", dark)

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else if (kind === "info") statusColor = infoColor
        else statusColor = textMuted
    }

    function refreshCounters() {
        var p = 0
        for (var i = 0; i < entries.length; i++)
            if ((entries[i].state || "") === "pending") p++
        pendingCount = p
    }

    function formatBytes(n) {
        if (!n || n <= 0) return "-"
        if (n < 1024) return n + " B"
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
        return (n / 1024 / 1024).toFixed(2) + " MB"
    }

    function pathBase(p) {
        if (!p) return ""
        var idx = p.lastIndexOf("/")
        return idx >= 0 ? p.substring(idx + 1) : p
    }

    function stateLabel(s) {
        if (s === "success") return "✓ 已压缩"
        if (s === "failed") return "失败"
        return "待压缩"
    }

    Component.onCompleted: imageCompressVm.emitInitial()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        // 顶部：标题 + 模式 + 质量
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["2"]
            Label {
                text: "图片压缩"
                font.bold: true
                font.pixelSize: Theme.fontSize.title
                color: textMain
                font.family: Theme.fontFamily.ui
            }
            Item { Layout.fillWidth: true }
            UiButton {
                text: "视觉无损"
                dark: root.dark
                checkable: true
                checked: mode === "visual"
                variant: checked ? "primary" : "secondary"
                onClicked: mode = "visual"
            }
            UiButton {
                text: "普通压缩"
                dark: root.dark
                checkable: true
                checked: mode === "normal"
                variant: checked ? "primary" : "secondary"
                onClicked: mode = "normal"
            }
            Label {
                text: "质量 " + quality + "%"
                color: textMain
                font.family: Theme.fontFamily.mono
                font.pixelSize: Theme.fontSize.mono
                Layout.preferredWidth: 80
            }
            UiSlider {
                dark: root.dark
                from: 10
                to: 100
                value: quality
                Layout.preferredWidth: 140
                onValueChanged: quality = Math.round(value)
            }
        }

        // 操作栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 70
            color: dropArea.containsDrag ? Theme.token("color-primary-bg", root.dark) : subtleBg
            radius: Theme.radii.lg
            border.color: dropArea.containsDrag ? accent : panelBorder
            border.width: dropArea.containsDrag ? 2 : 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["2.5"]
                spacing: Theme.space["2"]

                UiButton {
                    text: "粘贴剪贴板"
                    dark: root.dark
                    variant: "secondary"
                    implicitWidth: 108
                    onClicked: imageCompressVm.pasteClipboard()
                }
                UiButton {
                    text: "选择图片"
                    dark: root.dark
                    variant: "ghost"
                    onClicked: picker.open()
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: pendingCount > 0
                        ? ("待压缩 " + pendingCount + " 张")
                        : "或将图片拖到此处"
                    color: pendingCount > 0 ? warnColor : textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }
                UiButton {
                    text: "开始压缩"
                    dark: root.dark
                    variant: "primary"
                    enabled: pendingCount > 0
                    implicitWidth: 96
                    onClicked: imageCompressVm.startCompression(quality, mode)
                }
                UiButton {
                    text: "清空"
                    dark: root.dark
                    variant: "ghost"
                    enabled: entries.length > 0
                    onClicked: imageCompressVm.clearAll()
                }
            }

            DropArea {
                id: dropArea
                anchors.fill: parent
                onDropped: function(drop) {
                    if (drop.urls && drop.urls.length > 0) {
                        var arr = []
                        for (var i = 0; i < drop.urls.length; i++) arr.push(String(drop.urls[i]))
                        imageCompressVm.addFiles(arr)
                        drop.acceptProposedAction()
                    }
                }
            }
        }

        // 列表（待压缩 + 已压缩 + 失败 同列）
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: panelBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1

            Label {
                anchors.centerIn: parent
                visible: entries.length === 0
                text: "暂无图片\n复制一张图片后点击「粘贴剪贴板」加入待压缩列表"
                color: textSubtle
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSize.caption
            }

            ListView {
                anchors.fill: parent
                anchors.margins: 4
                visible: entries.length > 0
                clip: true
                model: entries
                spacing: 4
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 68
                    color: index % 2 === 0 ? panelBg : subtleBg
                    radius: Theme.radii.sm
                    border.color: modelData.state === "failed" ? warnColor : "transparent"
                    border.width: modelData.state === "failed" ? 1 : 0

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space["2"]
                        anchors.rightMargin: Theme.space["2"]
                        spacing: Theme.space["2"]

                        // 缩略图（成功时显示压缩后的，否则尝试源文件）
                        Rectangle {
                            Layout.preferredWidth: 58
                            Layout.preferredHeight: 58
                            color: subtleBg
                            radius: Theme.radii.sm
                            border.color: panelBorder
                            border.width: 1
                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: modelData.state === "success" && modelData.output
                                    ? ("file://" + modelData.output + "?t=" + index)
                                    : (modelData.source ? ("file://" + modelData.source) : "")
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: false
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space["1"]
                                Label {
                                    text: modelData.fileName || pathBase(modelData.source) || "(未命名)"
                                    color: textMain
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                    font.pixelSize: Theme.fontSize.body
                                }
                                Label {
                                    visible: modelData.fromClipboard
                                    text: "📋"
                                    color: textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space["1"]
                                Label {
                                    text: modelData.state === "success"
                                        ? formatBytes(modelData.originalBytes) + " → " + formatBytes(modelData.compressedBytes)
                                        : (modelData.state === "failed"
                                            ? (modelData.error || "失败")
                                            : formatBytes(modelData.originalBytes))
                                    color: modelData.state === "failed" ? dangerColor : textSubtle
                                    font.family: Theme.fontFamily.mono
                                    font.pixelSize: Theme.fontSize.caption
                                }
                                Label {
                                    visible: modelData.state === "success"
                                    text: modelData.savedRatio.toFixed(1) + "%"
                                    color: modelData.savedRatio > 0 ? successColor : textSubtle
                                    font.family: Theme.fontFamily.mono
                                    font.pixelSize: Theme.fontSize.caption
                                    Layout.preferredWidth: 56
                                    horizontalAlignment: Text.AlignRight
                                }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: stateLabel(modelData.state)
                                    color: modelData.state === "success" ? successColor
                                         : modelData.state === "failed" ? dangerColor
                                         : warnColor
                                    font.pixelSize: Theme.fontSize.caption
                                }
                            }
                        }

                        // 操作按钮
                        UiButton {
                            visible: modelData.state === "success"
                            text: "复制"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 52
                            onClicked: imageCompressVm.copyResultToClipboard(modelData.id)
                        }
                        UiButton {
                            visible: modelData.state === "success" && !modelData.fromClipboard && modelData.source
                            text: "覆盖原图"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 76
                            onClicked: imageCompressVm.overwriteOriginal(modelData.id)
                        }
                        UiButton {
                            visible: modelData.state === "success"
                            text: "另存为"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 64
                            onClicked: { pendingSaveAsId = modelData.id; saveAsDialog.open() }
                        }
                        UiButton {
                            visible: modelData.state === "failed"
                            text: "重试"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 52
                            onClicked: imageCompressVm.retryEntry(modelData.id, quality, mode)
                        }
                        UiButton {
                            text: "移除"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 52
                            onClicked: imageCompressVm.removeEntry(modelData.id)
                        }
                    }
                }
            }
        }

        // 状态栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 26
            color: statusBg
            radius: Theme.radii.sm
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2"]
                Label {
                    text: statusText
                    color: statusColor
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
                Label {
                    text: "共 " + entries.length + " 条"
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    font.family: Theme.fontFamily.mono
                }
            }
        }
    }

    FileDialog {
        id: picker
        title: "选择图片文件"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"]
        onAccepted: {
            var arr = []
            for (var i = 0; i < picker.selectedFiles.length; i++)
                arr.push(String(picker.selectedFiles[i]))
            imageCompressVm.addFiles(arr)
        }
    }

    FileDialog {
        id: saveAsDialog
        title: "另存为"
        fileMode: FileDialog.SaveFile
        onAccepted: {
            if (pendingSaveAsId)
                imageCompressVm.saveAs(pendingSaveAsId, String(selectedFile))
            pendingSaveAsId = ""
        }
        onRejected: pendingSaveAsId = ""
    }

    Connections {
        target: imageCompressVm
        function onEntriesUpdated(items) {
            entries = items || []
            refreshCounters()
        }
        function onStatusMessage(message, kind) { setStatus(message, kind) }
    }
}
