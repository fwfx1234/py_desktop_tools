import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    property var tasks: []
    property var visibleTasks: []
    property string selectedFilter: "all"
    property string statusText: "就绪"
    property color statusColor: textMuted
    property string saveRootPath: ""
    property int maxConcurrent: 3
    property int speedLimitKbps: 0
    property string userAgent: ""
    property string referer: ""
    property string cookie: ""
    property string customHeaders: ""
    property string proxyUrl: ""
    property int timeoutSec: 30
    property int retryLimit: 2
    property int runningCount: 0
    property int queuedCount: 0
    property int pausedCount: 0
    property int completedCount: 0
    property int failedCount: 0
    property real totalBytes: 0
    property real writtenBytes: 0

    readonly property bool dark: app.theme === "dark"
    readonly property color pageBg: Theme.token("color-bg-page", dark)
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color raisedBg: dark ? "#172033" : "#FFFFFF"
    readonly property color hoverBg: Theme.token("color-row-hover", dark)
    readonly property color subtleBg: Theme.token("color-bg-subtle", dark)
    readonly property color subtleBg2: Theme.token("color-bg-subtle-2", dark)
    readonly property color borderColor: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color accent: dark ? "#2563EB" : "#1D4ED8"
    readonly property color accentSoft: dark ? "#0B2C5C" : "#DBEAFE"
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)
    readonly property color warnColor: Theme.token("color-warning", dark)
    readonly property color infoColor: Theme.token("color-info", dark)
    readonly property string uiFont: Theme.fontFamily.ui
    readonly property string monoFont: Theme.fontFamily.mono
    readonly property var filters: [
        { id: "all", label: "全部任务", icon: "mdi6.tray-full", count: tasks.length },
        { id: "active", label: "下载中", icon: "mdi6.progress-download", count: runningCount + queuedCount },
        { id: "paused", label: "已暂停", icon: "mdi6.pause-circle-outline", count: pausedCount },
        { id: "completed", label: "已完成", icon: "mdi6.check-circle-outline", count: completedCount },
        { id: "failed", label: "异常任务", icon: "mdi6.alert-circle-outline", count: failedCount },
        { id: "video", label: "视频", icon: "mdi6.video-outline", count: countCategory("video") },
        { id: "archive", label: "压缩包", icon: "mdi6.archive-outline", count: countCategory("archive") },
        { id: "document", label: "文档", icon: "mdi6.file-document-outline", count: countCategory("document") },
        { id: "image", label: "图片", icon: "mdi6.image-outline", count: countCategory("image") },
        { id: "other", label: "其他", icon: "mdi6.file-outline", count: countOther() }
    ]

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else if (kind === "info") statusColor = infoColor
        else if (kind === "warn") statusColor = warnColor
        else statusColor = textMuted
    }

    function countCategory(category) {
        var count = 0
        for (var i = 0; i < tasks.length; i++) {
            if ((tasks[i].category || "") === category) count++
        }
        return count
    }

    function countOther() {
        var count = 0
        for (var i = 0; i < tasks.length; i++) {
            var category = tasks[i].category || "other"
            if (category !== "video" && category !== "archive" && category !== "document" && category !== "image")
                count++
        }
        return count
    }

    function refreshStats() {
        var running = 0, queued = 0, paused = 0, completed = 0, failed = 0
        var written = 0, total = 0
        for (var i = 0; i < tasks.length; i++) {
            var state = tasks[i].state || ""
            if (state === "running") running++
            else if (state === "queued") queued++
            else if (state === "paused" || state === "pausing") paused++
            else if (state === "completed") completed++
            else if (state === "failed" || state === "cancelled" || state === "cancelling") failed++
            written += Number(tasks[i].writtenBytes || 0)
            total += Number(tasks[i].totalBytes || 0)
        }
        runningCount = running
        queuedCount = queued
        pausedCount = paused
        completedCount = completed
        failedCount = failed
        writtenBytes = written
        totalBytes = total
        applyFilter()
    }

    function applyFilter() {
        var result = []
        for (var i = 0; i < tasks.length; i++) {
            var item = tasks[i]
            var state = item.state || ""
            var category = item.category || "other"
            var include = false
            if (selectedFilter === "all") include = true
            else if (selectedFilter === "active") include = state === "running" || state === "queued"
            else if (selectedFilter === "paused") include = state === "paused" || state === "pausing"
            else if (selectedFilter === "completed") include = state === "completed"
            else if (selectedFilter === "failed") include = state === "failed" || state === "cancelled" || state === "cancelling"
            else if (selectedFilter === "other") include = category !== "video" && category !== "archive" && category !== "document" && category !== "image"
            else include = category === selectedFilter
            if (include) result.push(item)
        }
        visibleTasks = result
    }

    function formatBytes(n) {
        var value = Number(n || 0)
        if (value <= 0) return "-"
        if (value < 1024) return value + " B"
        if (value < 1024 * 1024) return (value / 1024).toFixed(1) + " KB"
        if (value < 1024 * 1024 * 1024) return (value / 1024 / 1024).toFixed(1) + " MB"
        return (value / 1024 / 1024 / 1024).toFixed(2) + " GB"
    }

    function globalProgress() {
        if (totalBytes <= 0) return 0
        return Math.max(0, Math.min(100, Math.round(writtenBytes * 100 / totalBytes)))
    }

    function categoryLabel(category) {
        if (category === "archive") return "压缩包"
        if (category === "video") return "视频"
        if (category === "audio") return "音频"
        if (category === "image") return "图片"
        if (category === "document") return "文档"
        if (category === "program") return "程序"
        return "其他"
    }

    function stateColor(state) {
        if (state === "completed") return successColor
        if (state === "failed" || state === "cancelled" || state === "cancelling") return dangerColor
        if (state === "paused" || state === "pausing") return warnColor
        if (state === "running") return infoColor
        return textSubtle
    }

    function stateLabel(state) {
        if (state === "running") return "下载中"
        if (state === "queued") return "排队中"
        if (state === "paused") return "已暂停"
        if (state === "pausing") return "暂停中"
        if (state === "completed") return "已完成"
        if (state === "failed") return "失败"
        if (state === "cancelled") return "已取消"
        if (state === "cancelling") return "取消中"
        return "等待"
    }

    function addUrlsFromInput() {
        var payload = urlInput.text.trim()
        if (payload.length === 0) return
        downloadManagerVm.downloadUrls(payload)
        urlInput.text = ""
    }

    function loadSettings() {
        var settings = downloadManagerVm.settings()
        saveRootPath = settings.saveRoot || downloadManagerVm.saveRoot()
        maxConcurrent = Number(settings.maxConcurrent || 3)
        speedLimitKbps = Number(settings.speedLimitKbps || 0)
        timeoutSec = Number(settings.timeoutSec || 30)
        retryLimit = Number(settings.retryLimit || 2)
        proxyUrl = settings.proxyUrl || ""
        userAgent = settings.userAgent || ""
        referer = settings.referer || ""
        cookie = settings.cookie || ""
        customHeaders = settings.customHeaders || ""
        concurrentBox.currentIndex = Math.max(0, Math.min(5, maxConcurrent - 1))
        speedLimitInput.text = speedLimitKbps > 0 ? String(speedLimitKbps) : ""
        timeoutInput.text = String(timeoutSec)
        retryInput.text = String(retryLimit)
        proxyInput.text = proxyUrl
        userAgentInput.text = userAgent
        refererInput.text = referer
        cookieInput.text = cookie
        customHeadersInput.text = customHeaders
    }

    function saveNetworkOptions() {
        var cleanTimeout = Math.max(1, Number(timeoutInput.text || "30"))
        var cleanRetry = Math.max(0, Number(retryInput.text || "0"))
        timeoutSec = cleanTimeout
        retryLimit = cleanRetry
        proxyUrl = proxyInput.text.trim()
        userAgent = userAgentInput.text.trim()
        referer = refererInput.text.trim()
        cookie = cookieInput.text.trim()
        customHeaders = customHeadersInput.text.trim()
        downloadManagerVm.setNetworkOptions(userAgent, referer, cookie, customHeaders, proxyUrl, cleanTimeout, cleanRetry)
    }

    function networkSummary() {
        var parts = []
        parts.push("超时 " + timeoutSec + "s")
        parts.push("重试 " + retryLimit)
        if (proxyUrl.length > 0) parts.push("代理")
        if (userAgent.length > 0 || referer.length > 0 || cookie.length > 0 || customHeaders.length > 0) parts.push("自定义请求")
        return parts.join("  ")
    }

    Component.onCompleted: {
        loadSettings()
        tasks = downloadManagerVm.tasksSnapshot()
        refreshStats()
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 214
                Layout.fillHeight: true
                radius: 8
                color: panelBg
                border.width: 1
                border.color: borderColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            Layout.preferredWidth: 34
                            Layout.preferredHeight: 34
                            radius: 8
                            color: accent

                            UiIcon {
                                anchors.centerIn: parent
                                width: 20
                                height: 20
                                iconSize: 20
                                name: "mdi6.download"
                                color: "#FFFFFF"
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            Label {
                                text: "下载管理"
                                color: textMain
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                font.family: uiFont
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Label {
                                text: "HTTP/HTTPS 队列"
                                color: textSubtle
                                font.pixelSize: 11
                                font.family: uiFont
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: borderColor
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: filters
                        spacing: 4
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: FilterRow {
                            width: ListView.view.width
                            label: modelData.label
                            iconName: modelData.icon
                            count: modelData.count
                            selected: root.selectedFilter === modelData.id
                            onClicked: {
                                root.selectedFilter = modelData.id
                                root.applyFilter()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        radius: 8
                        color: subtleBg2
                        border.width: 1
                        border.color: borderColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6

                            Label {
                                text: "总体进度"
                                color: textSubtle
                                font.pixelSize: 11
                                font.family: uiFont
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                ProgressBar {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    value: globalProgress()
                                }

                                Label {
                                    text: globalProgress() + "%"
                                    color: textMain
                                    font.pixelSize: 11
                                    font.family: monoFont
                                    Layout.preferredWidth: 36
                                    horizontalAlignment: Text.AlignRight
                                }
                            }

                            Label {
                                text: formatBytes(writtenBytes) + " / " + formatBytes(totalBytes)
                                color: textMuted
                                font.pixelSize: 11
                                font.family: monoFont
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }

                            Label {
                                text: runningCount + " 下载中  " + queuedCount + " 排队"
                                color: infoColor
                                font.pixelSize: 11
                                font.family: uiFont
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 118
                    radius: 8
                    color: panelBg
                    border.width: 1
                    border.color: borderColor

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            UiTextField {
                                id: urlInput
                                dark: root.dark
                                Layout.fillWidth: true
                                placeholderText: "粘贴一个或多行 HTTP/HTTPS 下载链接"
                                onAccepted: addUrlsFromInput()
                            }

                            IconActionButton {
                                id: pasteButton
                                iconName: "mdi6.clipboard-text-outline"
                                tooltip: "从剪贴板填充"
                                onClicked: {
                                    var text = downloadManagerVm.fillFromClipboard()
                                    if (text && text.length > 0) urlInput.text = text
                                }
                            }

                            IconActionButton {
                                iconName: "mdi6.plus"
                                tooltip: "添加任务"
                                accent: true
                                enabled: urlInput.text.trim().length > 0
                                onClicked: addUrlsFromInput()
                            }

                            IconActionButton {
                                iconName: "mdi6.pause"
                                tooltip: "全部暂停"
                                enabled: runningCount + queuedCount > 0
                                onClicked: downloadManagerVm.pauseAll()
                            }

                            IconActionButton {
                                iconName: "mdi6.play"
                                tooltip: "全部开始"
                                enabled: pausedCount + failedCount > 0
                                onClicked: downloadManagerVm.resumeAll()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Label {
                                text: "并发"
                                color: textSubtle
                                font.pixelSize: 12
                                font.family: uiFont
                            }

                            UiComboBox {
                                id: concurrentBox
                                dark: root.dark
                                model: ["1", "2", "3", "4", "5", "6"]
                                Layout.preferredWidth: 78
                                onActivated: function(index) {
                                    var value = index + 1
                                    maxConcurrent = value
                                    downloadManagerVm.setMaxConcurrent(value)
                                }
                            }

                            Label {
                                text: "限速 KB/s"
                                color: textSubtle
                                font.pixelSize: 12
                                font.family: uiFont
                            }

                            UiTextField {
                                id: speedLimitInput
                                dark: root.dark
                                Layout.preferredWidth: 112
                                placeholderText: "不限速"
                                inputMethodHints: Qt.ImhDigitsOnly
                                onAccepted: {
                                    var value = Number(text || "0")
                                    speedLimitKbps = value
                                    downloadManagerVm.setSpeedLimitKbps(value)
                                }
                            }

                            IconActionButton {
                                iconName: "mdi6.speedometer"
                                tooltip: "应用限速"
                                onClicked: {
                                    var value = Number(speedLimitInput.text || "0")
                                    speedLimitKbps = value
                                    downloadManagerVm.setSpeedLimitKbps(value)
                                }
                            }

                            IconActionButton {
                                iconName: "mdi6.tune"
                                tooltip: "高级下载设置"
                                onClicked: advancedSettingsPopup.open()
                            }

                            Label {
                                text: networkSummary()
                                color: textSubtle
                                font.pixelSize: 11
                                font.family: uiFont
                                elide: Text.ElideRight
                                Layout.maximumWidth: 270
                            }

                            Item { Layout.fillWidth: true }

                            IconActionButton {
                                iconName: "mdi6.check-circle-outline"
                                tooltip: "清除已完成"
                                enabled: completedCount > 0
                                onClicked: downloadManagerVm.clearCompleted()
                            }

                            IconActionButton {
                                iconName: "mdi6.alert-circle-outline"
                                tooltip: "清除失败"
                                enabled: failedCount > 0
                                onClicked: downloadManagerVm.clearFailed()
                            }

                            IconActionButton {
                                iconName: "mdi6.folder-open-outline"
                                tooltip: "打开下载目录"
                                onClicked: downloadManagerVm.revealSaveRoot()
                            }

                            IconActionButton {
                                iconName: "mdi6.folder-cog-outline"
                                tooltip: "设置下载目录"
                                onClicked: folderPicker.open()
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: 8
                    color: subtleBg2
                    border.width: 1
                    border.color: borderColor

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        spacing: 8

                        HeaderLabel { text: "文件名"; Layout.fillWidth: true }
                        HeaderLabel { text: "大小"; Layout.preferredWidth: 92; horizontalAlignment: Text.AlignRight }
                        HeaderLabel { text: "进度"; Layout.preferredWidth: 170 }
                        HeaderLabel { text: "速度"; Layout.preferredWidth: 92; horizontalAlignment: Text.AlignRight }
                        HeaderLabel { text: "剩余"; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                        HeaderLabel { text: "状态"; Layout.preferredWidth: 82; horizontalAlignment: Text.AlignRight }
                        Item { Layout.preferredWidth: 184 }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: panelBg
                    border.width: 1
                    border.color: borderColor

                    Label {
                        anchors.centerIn: parent
                        visible: tasks.length === 0
                        text: "暂无下载任务"
                        color: textSubtle
                        font.pixelSize: 13
                        font.family: uiFont
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: tasks.length > 0 && visibleTasks.length === 0
                        text: "当前分类没有任务"
                        color: textSubtle
                        font.pixelSize: 13
                        font.family: uiFont
                    }

                    ListView {
                        anchors.fill: parent
                        anchors.margins: 4
                        visible: visibleTasks.length > 0
                        clip: true
                        model: visibleTasks
                        spacing: 4
                        reuseItems: true
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: TaskRow {
                            width: ListView.view.width
                            task: modelData
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    radius: 8
                    color: Theme.token("color-status-bar-bg", dark)
                    border.width: 1
                    border.color: borderColor

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        spacing: 10

                        Label {
                            text: statusText
                            color: statusColor
                            font.pixelSize: 11
                            font.family: uiFont
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Label {
                            text: "目录: " + saveRootPath
                            color: textSubtle
                            font.pixelSize: 11
                            font.family: uiFont
                            elide: Text.ElideMiddle
                            Layout.maximumWidth: root.width * 0.44
                        }

                        Label {
                            text: "并发 " + maxConcurrent + (speedLimitKbps > 0 ? ("  限速 " + speedLimitKbps + " KB/s") : "  不限速")
                            color: textSubtle
                            font.pixelSize: 11
                            font.family: monoFont
                        }
                    }
                }
            }
        }
    }

    FolderDialog {
        id: folderPicker
        title: "选择下载目录"
        onAccepted: {
            downloadManagerVm.setSaveRoot(String(selectedFolder))
            loadSettings()
        }
    }

    Popup {
        id: advancedSettingsPopup

        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        width: Math.min(root.width - 32, 680)
        height: Math.min(root.height - 32, 560)
        x: Math.max(16, Math.round((root.width - width) / 2))
        y: Math.max(16, Math.round((root.height - height) / 2))
        padding: 0

        background: Rectangle {
            radius: 8
            color: panelBg
            border.width: 1
            border.color: borderColor
        }

        contentItem: ColumnLayout {
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                radius: 8
                color: panelBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 10
                    spacing: 10

                    Label {
                        Layout.fillWidth: true
                        text: "高级下载设置"
                        color: textMain
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.family: uiFont
                        elide: Text.ElideRight
                    }

                    Label {
                        text: networkSummary()
                        color: textSubtle
                        font.pixelSize: 11
                        font.family: uiFont
                        elide: Text.ElideRight
                        Layout.maximumWidth: advancedSettingsPopup.width * 0.42
                    }

                    IconActionButton {
                        iconName: "mdi6.close"
                        tooltip: "关闭"
                        onClicked: advancedSettingsPopup.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: borderColor
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                ColumnLayout {
                    width: Math.max(0, advancedSettingsPopup.width - 32)
                    spacing: 12

                    SettingsField {
                        label: "User-Agent"

                        UiTextField {
                            id: userAgentInput
                            dark: root.dark
                            Layout.fillWidth: true
                            placeholderText: "默认 requests"
                            onAccepted: saveNetworkOptions()
                        }
                    }

                    SettingsField {
                        label: "Referer"

                        UiTextField {
                            id: refererInput
                            dark: root.dark
                            Layout.fillWidth: true
                            placeholderText: "可选"
                            onAccepted: saveNetworkOptions()
                        }
                    }

                    SettingsField {
                        label: "Cookie"

                        UiTextField {
                            id: cookieInput
                            dark: root.dark
                            Layout.fillWidth: true
                            placeholderText: "name=value; ..."
                            onAccepted: saveNetworkOptions()
                        }
                    }

                    SettingsField {
                        label: "代理"

                        UiTextField {
                            id: proxyInput
                            dark: root.dark
                            Layout.fillWidth: true
                            placeholderText: "HTTP/HTTPS 代理，如 http://127.0.0.1:7890"
                            onAccepted: saveNetworkOptions()
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: advancedSettingsPopup.width < 520 ? 1 : 2
                        rowSpacing: 12
                        columnSpacing: 12

                        SettingsField {
                            label: "超时"
                            Layout.fillWidth: true

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                UiTextField {
                                    id: timeoutInput
                                    dark: root.dark
                                    Layout.preferredWidth: 120
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    onAccepted: saveNetworkOptions()
                                }

                                Label {
                                    text: "秒"
                                    color: textSubtle
                                    font.pixelSize: 12
                                    font.family: uiFont
                                }

                                Item { Layout.fillWidth: true }
                            }
                        }

                        SettingsField {
                            label: "重试"
                            Layout.fillWidth: true

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                UiTextField {
                                    id: retryInput
                                    dark: root.dark
                                    Layout.preferredWidth: 120
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    onAccepted: saveNetworkOptions()
                                }

                                Label {
                                    text: "次"
                                    color: textSubtle
                                    font.pixelSize: 12
                                    font.family: uiFont
                                }

                                Item { Layout.fillWidth: true }
                            }
                        }
                    }

                    SettingsField {
                        label: "额外 Header"

                        UiTextArea {
                            id: customHeadersInput
                            dark: root.dark
                            Layout.fillWidth: true
                            Layout.preferredHeight: 112
                            placeholderText: "X-Token: value，多行用换行分隔"
                            wrapMode: TextArea.Wrap
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                color: panelBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 8

                    Label {
                        Layout.fillWidth: true
                        visible: advancedSettingsPopup.width >= 520
                        text: "新建任务会使用当前配置；已排队任务保留创建时配置。"
                        color: textSubtle
                        font.pixelSize: 11
                        font.family: uiFont
                        elide: Text.ElideRight
                    }

                    TextButton {
                        text: "取消"
                        onClicked: {
                            loadSettings()
                            advancedSettingsPopup.close()
                        }
                    }

                    TextButton {
                        text: "保存"
                        accent: true
                        onClicked: {
                            saveNetworkOptions()
                            advancedSettingsPopup.close()
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: downloadManagerVm
        function onDownloadTaskUpdated(items) {
            tasks = items || []
            refreshStats()
        }
        function onDownloadFinished(message) {
            if (message.length > 0)
                setStatus(message, message.indexOf("失败") !== -1 ? "error" : (message.indexOf("已存在") !== -1 ? "warn" : "success"))
        }
        function onDownloadActionResult(ok, message) {
            setStatus(message, ok ? "success" : "error")
            loadSettings()
        }
    }

    component HeaderLabel: Label {
        color: textSubtle
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.family: uiFont
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    component FormLabel: Label {
        color: textSubtle
        font.pixelSize: 11
        font.family: uiFont
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignRight
        Layout.preferredWidth: 74
        elide: Text.ElideRight
    }

    component SettingsField: ColumnLayout {
        id: settingsFieldRoot

        property string label: ""

        Layout.fillWidth: true
        spacing: 5

        Label {
            Layout.fillWidth: true
            text: settingsFieldRoot.label
            color: textSubtle
            font.pixelSize: 11
            font.family: uiFont
            elide: Text.ElideRight
        }
    }

    component TextButton: Rectangle {
        id: textButtonRoot

        property string text: ""
        property bool accent: false
        signal clicked()

        implicitWidth: Math.max(72, buttonText.implicitWidth + 24)
        implicitHeight: 34
        radius: 8
        color: accent
            ? (textButtonMouse.pressed ? Qt.darker(root.accent, 1.12) : root.accent)
            : (textButtonMouse.containsMouse || textButtonMouse.pressed ? hoverBg : subtleBg2)
        border.width: accent ? 0 : 1
        border.color: borderColor

        Label {
            id: buttonText
            anchors.centerIn: parent
            text: textButtonRoot.text
            color: textButtonRoot.accent ? "#FFFFFF" : textMuted
            font.pixelSize: 12
            font.family: uiFont
            font.weight: textButtonRoot.accent ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }

        MouseArea {
            id: textButtonMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: textButtonRoot.clicked()
        }
    }

    component FilterRow: Rectangle {
        id: filterRoot

        property string label: ""
        property string iconName: ""
        property int count: 0
        property bool selected: false
        signal clicked()

        height: 34
        radius: 7
        color: selected ? accentSoft : (filterMouse.containsMouse ? hoverBg : "transparent")
        border.width: selected ? 1 : 0
        border.color: selected ? Qt.rgba(accent.r, accent.g, accent.b, dark ? 0.55 : 0.28) : "transparent"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 9
            anchors.rightMargin: 8
            spacing: 8

            UiIcon {
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                iconSize: 16
                name: iconName
                color: selected ? accent : textMuted
            }

            Label {
                Layout.fillWidth: true
                text: label
                color: selected ? textMain : textMuted
                font.pixelSize: 12
                font.weight: selected ? Font.DemiBold : Font.Normal
                font.family: uiFont
                elide: Text.ElideRight
            }

            Label {
                text: count
                color: selected ? accent : textSubtle
                font.pixelSize: 11
                font.family: monoFont
                horizontalAlignment: Text.AlignRight
            }
        }

        MouseArea {
            id: filterMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: filterRoot.clicked()
        }
    }

    component IconActionButton: Rectangle {
        id: buttonRoot

        property string iconName: ""
        property string tooltip: ""
        property bool accent: false
        signal clicked()

        implicitWidth: 36
        implicitHeight: 34
        radius: 8
        opacity: enabled ? 1.0 : 0.42
        color: {
            if (accent)
                return buttonMouse.pressed ? Qt.darker(root.accent, 1.12) : root.accent
            if (buttonMouse.containsMouse || buttonMouse.pressed)
                return hoverBg
            return subtleBg2
        }
        border.width: accent ? 0 : 1
        border.color: borderColor

        UiIcon {
            anchors.centerIn: parent
            width: 17
            height: 17
            iconSize: 17
            name: buttonRoot.iconName
            color: buttonRoot.accent ? "#FFFFFF" : textMuted
        }

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            enabled: buttonRoot.enabled
            hoverEnabled: true
            cursorShape: buttonRoot.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: buttonRoot.clicked()
        }

        ToolTip.visible: buttonMouse.containsMouse && buttonRoot.tooltip.length > 0
        ToolTip.text: buttonRoot.tooltip
        ToolTip.delay: 420
    }

    component TaskRow: Rectangle {
        id: rowRoot

        property var task: ({})
        readonly property string taskState: task.state || ""
        readonly property bool running: taskState === "running" || taskState === "queued"
        readonly property bool resumable: taskState === "paused" || taskState === "failed" || taskState === "cancelled" || taskState === "cancelling"
        readonly property bool finished: taskState === "completed"

        height: 70
        radius: 8
        color: rowMouse.containsMouse ? hoverBg : raisedBg
        border.width: 1
        border.color: taskState === "failed" || taskState === "cancelled" || taskState === "cancelling"
            ? Qt.rgba(dangerColor.r, dangerColor.g, dangerColor.b, dark ? 0.45 : 0.24)
            : (rowMouse.containsMouse ? borderColor : "transparent")

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 8
            spacing: 8

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 26
                        Layout.preferredHeight: 26
                        radius: 7
                        color: subtleBg

                        UiIcon {
                            anchors.centerIn: parent
                            width: 15
                            height: 15
                            iconSize: 15
                            name: task.category === "video" ? "mdi6.video-outline"
                                : task.category === "archive" ? "mdi6.archive-outline"
                                : task.category === "document" ? "mdi6.file-document-outline"
                                : task.category === "image" ? "mdi6.image-outline"
                                : task.category === "audio" ? "mdi6.music-note-outline"
                                : "mdi6.file-outline"
                            color: textMuted
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: task.fileName || task.url || ""
                        color: textMain
                        font.pixelSize: 13
                        font.family: uiFont
                        elide: Text.ElideMiddle
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        Layout.fillWidth: true
                        text: (task.domain || "-") + "  " + categoryLabel(task.category || "other")
                        color: textSubtle
                        font.pixelSize: 11
                        font.family: uiFont
                        elide: Text.ElideMiddle
                    }

                    Label {
                        visible: task.error && task.error.length > 0
                        text: task.error
                        color: dangerColor
                        font.pixelSize: 11
                        font.family: uiFont
                        elide: Text.ElideRight
                        Layout.maximumWidth: 260
                    }
                }
            }

            Label {
                text: formatBytes(task.totalBytes || task.writtenBytes)
                color: textMuted
                font.pixelSize: 11
                font.family: monoFont
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 92
            }

            ColumnLayout {
                Layout.preferredWidth: 170
                spacing: 5

                ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: task.progress || 0
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Label {
                        text: (task.progress || 0) + "%"
                        color: textMuted
                        font.pixelSize: 11
                        font.family: monoFont
                    }

                    Label {
                        Layout.fillWidth: true
                        text: formatBytes(task.writtenBytes) + " / " + formatBytes(task.totalBytes)
                        color: textSubtle
                        font.pixelSize: 11
                        font.family: monoFont
                        elide: Text.ElideMiddle
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }

            Label {
                text: task.speed || "0 KB/s"
                color: taskState === "running" ? infoColor : textSubtle
                font.pixelSize: 11
                font.family: monoFont
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 92
            }

            Label {
                text: task.eta || "-"
                color: textSubtle
                font.pixelSize: 11
                font.family: monoFont
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 64
            }

            Label {
                text: stateLabel(rowRoot.taskState)
                color: stateColor(rowRoot.taskState)
                font.pixelSize: 11
                font.family: uiFont
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 82
            }

            RowLayout {
                Layout.preferredWidth: 184
                spacing: 4

                IconActionButton {
                    iconName: rowRoot.running ? "mdi6.pause" : "mdi6.play"
                    tooltip: rowRoot.running ? "暂停" : "继续"
                    visible: rowRoot.running || rowRoot.resumable
                    enabled: rowRoot.running || rowRoot.resumable
                    onClicked: {
                        if (rowRoot.running) downloadManagerVm.pauseDownloadTask(task.id || "")
                        else downloadManagerVm.resumeDownloadTask(task.id || "")
                    }
                }

                IconActionButton {
                    iconName: "mdi6.refresh"
                    tooltip: "重试"
                    visible: rowRoot.taskState === "failed" || rowRoot.taskState === "cancelled"
                    onClicked: downloadManagerVm.retryDownloadTask(task.id || "")
                }

                IconActionButton {
                    iconName: "mdi6.open-in-new"
                    tooltip: "打开文件"
                    visible: rowRoot.finished
                    onClicked: downloadManagerVm.openDownloadedFile(task.id || "")
                }

                IconActionButton {
                    iconName: "mdi6.folder-search-outline"
                    tooltip: "定位文件"
                    visible: rowRoot.finished
                    onClicked: downloadManagerVm.revealDownload(task.id || "")
                }

                IconActionButton {
                    iconName: "mdi6.close"
                    tooltip: "取消任务"
                    visible: rowRoot.running
                    onClicked: downloadManagerVm.cancelDownloadTask(task.id || "")
                }

                IconActionButton {
                    iconName: "mdi6.delete-outline"
                    tooltip: "移除"
                    onClicked: downloadManagerVm.removeDownloadTask(task.id || "")
                }
            }
        }

        MouseArea {
            id: rowMouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }
    }
}
