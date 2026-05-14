import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    property var tasks: []
    property string pendingUrl: ""
    property int runningCount: 0
    property int completedCount: 0
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    function refreshStats() {
        var running = 0
        var completed = 0
        for (var i = 0; i < tasks.length; i++) {
            var s = tasks[i].status || ""
            if (s.indexOf("下载中") !== -1)
                running++
            if (s.indexOf("完成") !== -1)
                completed++
        }
        runningCount = running
        completedCount = completed
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4
        spacing: Theme.spacing.s2
        Label { text: "下载工具"; font.bold: true; font.pixelSize: Theme.typeScale.title; color: textMain; font.family: "IBM Plex Sans" }
        RowLayout {
            UiTextField { id: url; dark: dark; Layout.fillWidth: true; placeholderText: "输入下载链接..." }
            UiButton {
                text: "添加任务"
                dark: dark
                variant: "primary"
                onClicked: {
                    if (url.text.length > 0) {
                        pendingUrl = url.text
                        saveDialog.open()
                    }
                }
            }
            UiButton {
                text: "清空任务"
                dark: dark
                variant: "secondary"
                onClicked: downloadVm.clearDownloadTasks()
            }
            Label { text: "下载中: " + runningCount; color: textMuted }
            Label { text: "已完成: " + completedCount; color: textMuted }
            Label { text: "总数: " + tasks.length; color: textMuted }
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: tasks
            delegate: Rectangle {
                width: ListView.view.width
                height: Theme.spacing.s4 * 4 + Theme.spacing.s1
                radius: Theme.radius.md
                color: index % 2 === 0 ? panelBg : Theme.token("color-bg-subtle-2", dark)
                border.color: "transparent"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacing.s3
                    anchors.rightMargin: Theme.spacing.s3
                    anchors.topMargin: Theme.spacing.s2 - 2
                    anchors.bottomMargin: Theme.spacing.s2 - 2
                    spacing: 3
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: modelData.url; elide: Text.ElideRight; color: textMain }
                        Label { text: modelData.status; color: modelData.status.indexOf("完成") !== -1 ? Theme.token("color-success", dark) : modelData.status.indexOf("失败") !== -1 ? Theme.token("color-danger", dark) : textMuted }
                        UiButton {
                            visible: (modelData.status || "").indexOf("下载中") !== -1 || (modelData.status || "").indexOf("正在取消") !== -1
                            enabled: (modelData.status || "").indexOf("下载中") !== -1
                            text: "取消"
                            dark: dark
                            variant: "secondary"
                            Layout.preferredWidth: 64
                            onClicked: downloadVm.cancelDownloadTask(modelData.id || "")
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: modelData.progress || 0 }
                        Label { text: (modelData.progress || 0) + "%"; Layout.preferredWidth: 42; color: textMain }
                        Label { text: modelData.speed || "0 KB/s"; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; color: textMuted }
                    }
                }
            }
        }
    }

    FileDialog {
        id: saveDialog
        title: "保存文件"
        fileMode: FileDialog.SaveFile
        onAccepted: {
            if (!pendingUrl)
                return
            downloadVm.downloadFile(pendingUrl, selectedFile.toString().replace("file:///", ""))
            pendingUrl = ""
            url.text = ""
        }
    }

    Connections {
        target: downloadVm
        function onDownloadTaskUpdated(items) {
            tasks = items
            refreshStats()
        }
    }
}
