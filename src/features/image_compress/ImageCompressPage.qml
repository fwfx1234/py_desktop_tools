import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    property var resultRows: []
    property int quality: 80
    property string mode: "visual"
    property string statusText: "粘贴或拖入图片即可开始"
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
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)
    readonly property color accent: Theme.token("color-primary-active", dark)

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else statusColor = textMuted
    }

    function formatBytes(n) {
        if (!n || n <= 0) return "-"
        if (n < 1024) return n + " B"
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
        return (n / 1024 / 1024).toFixed(2) + " MB"
    }

    function pathBaseName(p) {
        if (!p) return ""
        var idx = p.lastIndexOf("/")
        return idx >= 0 ? p.substring(idx + 1) : p
    }

    function compressInitial(files) {
        if (files && files.length > 0)
            imageCompressVm.compressFiles(files, quality, mode)
    }

    Component.onCompleted: compressInitial(imageCompressVm.initialFiles())

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        // 顶部工具栏：模式 + 质量
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

        // 主输入区
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 88
            color: dropArea.containsDrag ? Theme.token("color-primary-bg", root.dark) : subtleBg
            radius: Theme.radii.lg
            border.color: dropArea.containsDrag ? accent : panelBorder
            border.width: dropArea.containsDrag ? 2 : 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                spacing: Theme.space["3"]

                UiButton {
                    text: "粘贴并压缩"
                    dark: root.dark
                    variant: "primary"
                    implicitWidth: 116
                    onClicked: imageCompressVm.pasteAndCompress(quality, mode)
                }
                UiButton {
                    text: "选择图片"
                    dark: root.dark
                    variant: "secondary"
                    onClicked: picker.open()
                }
                UiButton {
                    text: "清空结果"
                    dark: root.dark
                    variant: "ghost"
                    enabled: resultRows.length > 0
                    onClicked: imageCompressVm.clearResults()
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: "或将图片拖到此处"
                    color: textSubtle
                    horizontalAlignment: Text.AlignRight
                }
            }

            DropArea {
                id: dropArea
                anchors.fill: parent
                onDropped: function(drop) {
                    if (drop.urls && drop.urls.length > 0) {
                        var arr = []
                        for (var i = 0; i < drop.urls.length; i++) arr.push(String(drop.urls[i]))
                        imageCompressVm.compressFiles(arr, quality, mode)
                        drop.acceptProposedAction()
                    }
                }
            }
        }

        // 结果列表
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: panelBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1

            Label {
                anchors.centerIn: parent
                visible: resultRows.length === 0
                text: "暂无结果\n复制一张图片后点击「粘贴并压缩」即可"
                color: textSubtle
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSize.caption
            }

            ListView {
                anchors.fill: parent
                anchors.margins: 4
                visible: resultRows.length > 0
                clip: true
                model: resultRows
                spacing: 4
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 64
                    color: index % 2 === 0 ? panelBg : subtleBg
                    radius: Theme.radii.sm
                    border.color: modelData.success ? "transparent" : Theme.token("color-warning", root.dark)
                    border.width: modelData.success ? 0 : 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space["2"]
                        anchors.rightMargin: Theme.space["2"]
                        spacing: Theme.space["2"]

                        // 缩略图
                        Rectangle {
                            Layout.preferredWidth: 56
                            Layout.preferredHeight: 56
                            color: subtleBg
                            radius: Theme.radii.sm
                            border.color: panelBorder
                            border.width: 1
                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: modelData.success && modelData.output ? ("file://" + modelData.output) : ""
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
                                    text: modelData.fileName || pathBaseName(modelData.source) || "(剪贴板)"
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
                                    text: modelData.success
                                        ? formatBytes(modelData.originalBytes) + " → " + formatBytes(modelData.compressedBytes)
                                        : (modelData.error || "失败")
                                    color: modelData.success ? textSubtle : dangerColor
                                    font.family: Theme.fontFamily.mono
                                    font.pixelSize: Theme.fontSize.caption
                                }
                                Label {
                                    visible: modelData.success
                                    text: modelData.savedRatio.toFixed(1) + "%"
                                    color: modelData.savedRatio > 0 ? successColor : textSubtle
                                    font.family: Theme.fontFamily.mono
                                    font.pixelSize: Theme.fontSize.caption
                                    Layout.preferredWidth: 56
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }

                        UiButton {
                            text: "复制"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 56
                            enabled: modelData.success
                            onClicked: imageCompressVm.copyResultToClipboard(modelData.id)
                        }
                        UiButton {
                            text: "覆盖原图"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 78
                            visible: modelData.success && !modelData.fromClipboard && modelData.source
                            onClicked: imageCompressVm.overwriteOriginal(modelData.id)
                        }
                        UiButton {
                            text: "另存为"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 66
                            enabled: modelData.success
                            onClicked: { pendingSaveAsId = modelData.id; saveAsDialog.open() }
                        }
                        UiButton {
                            text: "移除"
                            dark: root.dark
                            variant: "ghost"
                            implicitWidth: 56
                            onClicked: imageCompressVm.removeResult(modelData.id)
                        }
                    }
                }
            }
        }

        // 状态栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 2 + Theme.space["1"]
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
                    text: "共 " + resultRows.length + " 条结果"
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
            imageCompressVm.compressFiles(arr, quality, mode)
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
        function onResultsUpdated(rows) { resultRows = rows || [] }
        function onStatusMessage(message, kind) { setStatus(message, kind) }
    }
}
