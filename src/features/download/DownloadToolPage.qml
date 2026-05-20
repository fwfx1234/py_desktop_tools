import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    property var tasks: []
    property int runningCount: 0
    property int completedCount: 0
    property int failedCount: 0
    property string statusText: "就绪"
    property color statusColor: textMuted
    property string saveRootPath: ""
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
    readonly property color infoColor: Theme.token("color-info", dark)

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else statusColor = textMuted
    }

    function refreshStats() {
        var running = 0, completed = 0, failed = 0
        for (var i = 0; i < tasks.length; i++) {
            var s = tasks[i].status || ""
            if (s.indexOf("下载中") !== -1 || s.indexOf("排队") !== -1) running++
            else if (s.indexOf("失败") !== -1) failed++
            else if (s.indexOf("完成") !== -1) completed++
        }
        runningCount = running
        completedCount = completed
        failedCount = failed
    }

    function formatBytes(n) {
        if (!n || n <= 0) return "-"
        if (n < 1024) return n + " B"
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
        if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB"
        return (n / 1024 / 1024 / 1024).toFixed(2) + " GB"
    }

    function formatElapsed(ms) {
        if (!ms || ms <= 0) return "-"
        var sec = Math.floor(ms / 1000)
        if (sec < 60) return sec + "s"
        var m = Math.floor(sec / 60)
        var s = sec % 60
        return m + "m" + s + "s"
    }

    Component.onCompleted: saveRootPath = downloadVm.saveRoot()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["2"]
            Label {
                text: "下载工具"
                font.bold: true
                font.pixelSize: Theme.fontSize.title
                color: textMain
                font.family: Theme.fontFamily.ui
            }
            Item { Layout.fillWidth: true }
            Label { text: "下载中 " + runningCount; color: infoColor; font.pixelSize: Theme.fontSize.caption }
            Label { text: "已完成 " + completedCount; color: successColor; font.pixelSize: Theme.fontSize.caption }
            Label { text: "失败 " + failedCount; color: dangerColor; font.pixelSize: Theme.fontSize.caption }
            Label { text: "总计 " + tasks.length; color: textSubtle; font.pixelSize: Theme.fontSize.caption }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["1"]
            UiTextField {
                id: urlInput
                dark: root.dark
                Layout.fillWidth: true
                placeholderText: "输入下载链接 (回车开始)"
                onAccepted: {
                    if (text.trim().length > 0) {
                        downloadVm.downloadUrl(text)
                        text = ""
                    }
                }
            }
            UiButton {
                text: "开始下载"
                dark: root.dark
                variant: "primary"
                enabled: urlInput.text.trim().length > 0
                onClicked: {
                    downloadVm.downloadUrl(urlInput.text)
                    urlInput.text = ""
                }
            }
            UiButton {
                text: "从剪贴板"
                dark: root.dark
                variant: "secondary"
                onClicked: {
                    var t = downloadVm.fillFromClipboard()
                    if (t && t.length > 0) urlInput.text = t
                }
            }
            UiButton { text: "清除已完成"; dark: root.dark; variant: "ghost"; onClicked: downloadVm.clearCompleted() }
            UiButton { text: "清除失败"; dark: root.dark; variant: "ghost"; onClicked: downloadVm.clearFailed() }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: panelBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1

            ListView {
                anchors.fill: parent
                anchors.margins: 2
                clip: true
                model: tasks
                spacing: 1
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 64
                    radius: Theme.radii.sm
                    color: index % 2 === 0 ? panelBg : subtleBg

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space["2.5"]
                        anchors.rightMargin: Theme.space["2"]
                        anchors.topMargin: Theme.space["1"] + 2
                        anchors.bottomMargin: Theme.space["1"] + 2
                        spacing: 3
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["2"]
                            Label {
                                text: modelData.fileName || modelData.url || ""
                                color: textMain
                                font.pixelSize: Theme.fontSize.body
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                            Label {
                                text: modelData.domain || ""
                                color: textSubtle
                                font.pixelSize: Theme.fontSize.caption
                                Layout.preferredWidth: 160
                                elide: Text.ElideMiddle
                            }
                            Label {
                                text: modelData.status || ""
                                color: (modelData.status || "").indexOf("完成") !== -1 ? successColor
                                     : (modelData.status || "").indexOf("失败") !== -1 ? dangerColor
                                     : (modelData.status || "").indexOf("取消") !== -1 ? textSubtle
                                     : infoColor
                                font.pixelSize: Theme.fontSize.caption
                                Layout.preferredWidth: 120
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideMiddle
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["2"]
                            ProgressBar {
                                Layout.fillWidth: true
                                from: 0
                                to: 100
                                value: modelData.progress || 0
                            }
                            Label {
                                text: (modelData.progress || 0) + "%"
                                color: textMain
                                Layout.preferredWidth: 38
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                            }
                            Label {
                                text: modelData.speed || "0 KB/s"
                                color: textSubtle
                                Layout.preferredWidth: 80
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                horizontalAlignment: Text.AlignRight
                            }
                            Label {
                                text: formatBytes(modelData.writtenBytes) + " / " + formatBytes(modelData.totalBytes)
                                color: textSubtle
                                Layout.preferredWidth: 150
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                horizontalAlignment: Text.AlignRight
                            }
                            Label {
                                text: formatElapsed(modelData.elapsedMs)
                                color: textSubtle
                                Layout.preferredWidth: 50
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                horizontalAlignment: Text.AlignRight
                            }
                            UiButton {
                                text: "取消"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 52
                                visible: (modelData.status || "").indexOf("下载中") !== -1 || (modelData.status || "").indexOf("排队") !== -1
                                onClicked: downloadVm.cancelDownloadTask(modelData.id || "")
                            }
                            UiButton {
                                text: "重试"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 52
                                visible: (modelData.status || "").indexOf("失败") !== -1 || (modelData.status || "").indexOf("取消") !== -1
                                onClicked: downloadVm.retryDownloadTask(modelData.id || "")
                            }
                            UiButton {
                                text: "打开"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 52
                                visible: (modelData.status || "").indexOf("完成") !== -1
                                onClicked: downloadVm.openDownloadedFile(modelData.id || "")
                            }
                            UiButton {
                                text: "定位"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 52
                                visible: (modelData.status || "").indexOf("完成") !== -1
                                onClicked: downloadVm.revealDownload(modelData.id || "")
                            }
                            UiButton {
                                text: "移除"
                                dark: root.dark
                                variant: "ghost"
                                implicitWidth: 52
                                onClicked: downloadVm.removeDownloadTask(modelData.id || "")
                            }
                        }
                    }
                }
            }
        }

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
                    text: "下载目录: " + saveRootPath
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: root.width * 0.5
                }
                UiButton {
                    text: "打开 Finder"
                    dark: root.dark
                    variant: "ghost"
                    implicitWidth: 86
                    onClicked: downloadVm.revealSaveRoot()
                }
            }
        }
    }

    Connections {
        target: downloadVm
        function onDownloadTaskUpdated(items) {
            tasks = items
            refreshStats()
        }
        function onDownloadFinished(message) {
            if (message.length > 0) setStatus(message, message.indexOf("失败") !== -1 ? "error" : "success")
        }
        function onDownloadActionResult(ok, message) {
            setStatus(message, ok ? "success" : "error")
        }
    }
}
