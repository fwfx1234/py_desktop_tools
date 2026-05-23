import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    property var rows: []
    property var captureState: ({})
    property var stats: ({ totalRows: 0, visibleRows: 0, errorRows: 0, totalBytes: 0, avgDurationMs: 0, topHost: "" })
    property var selectedDetail: ({})
    property string selectedFlowId: ""
    property string statusText: "代理未启动"
    property color statusColor: textMuted
    property string filterKeyword: ""
    property string filterHost: ""
    property string filterMethod: ""
    property string filterContentType: ""
    property string filterScheme: ""
    property int filterStatusMin: 0
    property int filterStatusMax: 0
    property int filterMinDurationMs: 0
    property bool filterOnlyErrors: false
    property bool filterHideStatic: true
    property string pendingExportFormat: "har"
    property bool composerSending: false
    property string composerHeadersText: ""
    property string composerBodyText: ""
    property string guideMode: "desktop"

    readonly property bool compressedLayout: width < 1180
    readonly property bool compactLayout: width < 1040
    readonly property bool narrowLayout: width < 820
    readonly property int sidePanelWidth: narrowLayout ? 210 : (compressedLayout ? 220 : 248)
    readonly property int inspectorPanelWidth: compactLayout ? 0 : (compressedLayout ? 292 : (width < 1360 ? 340 : 360))
    readonly property int hostColumnWidth: narrowLayout ? 104 : (compressedLayout ? 116 : 150)
    readonly property bool dark: app.theme === "dark"
    readonly property color pageBg: Theme.token("color-bg-page", dark)
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color subtleBg: Theme.token("color-bg-subtle", dark)
    readonly property color subtleBg2: Theme.token("color-bg-subtle-2", dark)
    readonly property color statusBg: Theme.token("color-status-bar-bg", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color tableHeader: Theme.token("color-table-header", dark)
    readonly property color rowHover: Theme.token("color-row-hover", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property color warningColor: Theme.token("color-warning", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)
    readonly property color infoColor: Theme.token("color-info", dark)
    readonly property color accent: Theme.token("color-primary-active", dark)

    function qta(name, colorValue, iconSize) {
        return "image://qta/" + name + ";color=" + ("" + colorValue).replace("#", "") + ";size=" + iconSize
    }

    function setStatus(text, kind) {
        statusText = text || ""
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else if (kind === "warning") statusColor = warningColor
        else statusColor = textMuted
    }

    function updateStatusFromState() {
        if (captureState.error && captureState.error.length > 0) {
            setStatus(captureState.error, "error")
        } else if (captureState.busy) {
            setStatus(captureState.busyText || "代理处理中", "warning")
        } else if (captureState.running) {
            var proxyText = captureState.proxyUrl || ""
            if (captureState.systemProxyEnabled)
                proxyText += " · 系统代理已接管"
            else if (captureState.systemProxyError)
                proxyText += " · " + captureState.systemProxyError
            else if (captureState.systemProxySupported)
                proxyText += " · 系统代理未接管"
            if (captureState.mobileProxyUrl)
                proxyText += " · 手机 " + captureState.mobileProxyUrl
            setStatus((captureState.paused ? "已暂停记录: " : "代理运行中: ") + proxyText, captureState.paused || captureState.systemProxyError ? "warning" : "success")
        } else if (captureState.systemProxyRecoveryMessage) {
            setStatus(captureState.systemProxyRecoveryMessage, "success")
        } else if (captureState.systemProxyError) {
            setStatus(captureState.systemProxyError, "error")
        } else {
            setStatus("代理已停止", "info")
        }
    }

    function pushFilters() {
        httpCaptureVm.setFilters(
            filterKeyword,
            filterHost,
            filterMethod,
            filterContentType,
            filterStatusMin,
            filterStatusMax,
            filterScheme,
            filterOnlyErrors,
            filterHideStatic,
            filterMinDurationMs
        )
    }

    function resetFilters() {
        filterKeyword = ""
        filterHost = ""
        filterMethod = ""
        filterContentType = ""
        filterScheme = ""
        filterStatusMin = 0
        filterStatusMax = 0
        filterMinDurationMs = 0
        filterOnlyErrors = false
        filterHideStatic = true
        keywordInput.text = ""
        hostInput.text = ""
        contentTypeInput.text = ""
        statusMinInput.text = ""
        statusMaxInput.text = ""
        durationInput.text = ""
        methodCombo.currentIndex = 0
        schemeCombo.currentIndex = 0
        onlyErrorsCheck.checked = false
        hideStaticCheck.checked = true
        pushFilters()
    }

    function methodColor(m) {
        var x = (m || "").toUpperCase()
        if (x === "GET") return Theme.token("color-method-get", root.dark)
        if (x === "POST") return Theme.token("color-method-post", root.dark)
        if (x === "PUT") return Theme.token("color-method-put", root.dark)
        if (x === "DELETE") return Theme.token("color-method-delete", root.dark)
        if (x === "PATCH") return Theme.token("color-method-patch", root.dark)
        return textMuted
    }

    function statusColorOf(s) {
        if (!s) return textSubtle
        if (s >= 500) return dangerColor
        if (s >= 400) return warningColor
        if (s >= 300) return infoColor
        return successColor
    }

    function formatBytes(n) {
        if (!n || n <= 0) return "-"
        if (n < 1024) return n + " B"
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
        if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB"
        return (n / 1024 / 1024 / 1024).toFixed(2) + " GB"
    }

    function durationText(ms) {
        if (!ms || ms <= 0) return "-"
        if (ms < 1000) return ms + " ms"
        return (ms / 1000).toFixed(2) + " s"
    }

    function headersText(items) {
        return (items || []).map(function(h) { return h.name + ": " + h.value }).join("\n")
    }

    function kvText(items) {
        return (items || []).map(function(h) { return h.name + " = " + h.value }).join("\n")
    }

    function responseBodyText() {
        var body = selectedDetail.responseBodyDisplay || selectedDetail.responseBody || ""
        if (body.length === 0 && (selectedDetail.responseSize || currentSummary().responseSize || 0) > 0)
            body = "[响应正文无法按文本显示，可能是二进制内容或服务器未返回可解码文本]"
        if (selectedDetail.responseBodyTruncated)
            body += "\n\n[正文过大已截断]"
        return body
    }

    function requestBodyText() {
        var body = selectedDetail.requestBodyDisplay || selectedDetail.requestBody || ""
        if (body.length === 0 && (selectedDetail.requestSize || currentSummary().requestSize || 0) > 0)
            body = "[请求正文无法按文本显示，可能是二进制内容或上传流]"
        if (selectedDetail.requestBodyTruncated)
            body += "\n\n[正文过大已截断]"
        return body
    }

    function openGuide(mode) {
        guideMode = mode || "desktop"
        setupGuidePopup.open()
    }

    function currentSummary() {
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].id === selectedFlowId) return rows[i]
        }
        return ({})
    }

    function rowTitle(row) {
        var path = row.path || row.url || ""
        if (!path) return "(connect)"
        return path
    }

    Component.onCompleted: {
        captureState = httpCaptureVm.initialState() || ({})
        updateStatusFromState()
        pushFilters()
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 54
            color: panelBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2.5"]
                spacing: Theme.space["2"]

                Rectangle {
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    radius: Theme.radii.md
                    color: captureState.running ? (root.dark ? "#052E2B" : "#D1FAE5") : subtleBg

                    UiIcon {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        name: captureState.running ? "mdi6.access-point-network" : "mdi6.access-point-network-off"
                        color: captureState.running ? successColor : textSubtle
                        iconSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        Label {
                            text: "HTTP 抓包工作台"
                            color: textMain
                            font.family: Theme.fontFamily.ui
                            font.pixelSize: narrowLayout ? Theme.fontSize.heading : Theme.fontSize.title
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.maximumWidth: narrowLayout ? 132 : 220
                        }

                        StatusPill {
                            label: captureState.running ? (captureState.paused ? "暂停记录" : "实时捕获") : "未启动"
                            tone: captureState.running ? (captureState.paused ? "warning" : "success") : "neutral"
                        }

                        StatusPill {
                            visible: stats.errorRows > 0
                            label: stats.errorRows + " 错误"
                            tone: "danger"
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            visible: !narrowLayout
                            text: "可见 " + (stats.visibleRows || 0) + " / 总计 " + (stats.totalRows || 0)
                            color: textSubtle
                            font.pixelSize: Theme.fontSize.caption
                            font.family: Theme.fontFamily.ui
                        }
                    }

                    SelectableLine {
                        Layout.fillWidth: true
                        text: captureState.proxyUrl ? (captureState.mobileProxyUrl ? captureState.proxyUrl + " / 手机 " + captureState.mobileProxyUrl : captureState.proxyUrl) : "默认监听 127.0.0.1:8899"
                        color: textSubtle
                        font.pixelSize: Theme.fontSize.caption
                        font.family: Theme.fontFamily.mono
                    }
                }

                IconAction {
                    iconName: captureState.busy ? "mdi6.loading" : (captureState.running ? "mdi6.stop" : "mdi6.play")
                    tooltip: captureState.busy ? (captureState.busyText || "代理处理中") : (captureState.running ? "停止代理" : "启动代理")
                    accent: true
                    enabled: !captureState.busy
                    onClicked: captureState.running ? httpCaptureVm.stopHttpCapture() : httpCaptureVm.startHttpCapture()
                }

                IconAction {
                    visible: !narrowLayout
                    iconName: "mdi6.cellphone-link"
                    tooltip: "启动手机抓包"
                    enabled: !captureState.running && !captureState.busy
                    onClicked: httpCaptureVm.startMobileCapture()
                }

                IconAction {
                    iconName: captureState.paused ? "mdi6.play-pause" : "mdi6.pause"
                    tooltip: captureState.paused ? "继续记录" : "暂停记录"
                    enabled: !!captureState.running && !captureState.busy
                    onClicked: captureState.paused ? httpCaptureVm.resumeHttpCapture() : httpCaptureVm.pauseHttpCapture()
                }

                IconAction {
                    iconName: "mdi6.broom"
                    tooltip: "清空会话"
                    onClicked: httpCaptureVm.clearCaptureRows()
                }

                Rectangle {
                    visible: !narrowLayout
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 26
                    color: panelBorder
                }

                IconAction {
                    visible: !narrowLayout
                    iconName: "mdi6.content-copy"
                    tooltip: "复制代理地址"
                    onClicked: httpCaptureVm.copyProxyAddress()
                }

                IconAction {
                    visible: !narrowLayout
                    iconName: "mdi6.certificate-outline"
                    tooltip: "HTTPS 解密证书引导"
                    onClicked: openGuide("desktop")
                }

                IconAction {
                    visible: !!captureState.systemProxyRecoverable && !narrowLayout
                    iconName: "mdi6.restore"
                    tooltip: "恢复上次残留的系统代理"
                    enabled: !captureState.busy
                    onClicked: httpCaptureVm.recoverSystemProxy()
                }

                IconAction {
                    iconName: "mdi6.export-variant"
                    tooltip: "导出可见会话为 HAR"
                    enabled: rows.length > 0
                    onClicked: {
                        pendingExportFormat = "har"
                        exportVisibleDialog.nameFilters = ["HAR 文件 (*.har)", "JSON 文件 (*.json)"]
                        exportVisibleDialog.open()
                    }
                }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 6
                color: "transparent"
                Rectangle {
                    anchors.centerIn: parent
                    width: 1
                    height: parent.height
                    color: panelBorder
                }
            }

            Rectangle {
                id: filterPanel
                SplitView.preferredWidth: sidePanelWidth
                SplitView.minimumWidth: narrowLayout ? 198 : 220
                SplitView.maximumWidth: compactLayout ? 250 : 320
                color: panelBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1

                Flickable {
                    id: filterScroll
                    anchors.fill: parent
                    anchors.margins: Theme.space["2"]
                    clip: true
                    contentWidth: width
                    contentHeight: filterColumn.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }

                    ColumnLayout {
                        id: filterColumn
                        width: filterScroll.width
                        spacing: Theme.space["2"]

                    SectionLabel { text: "过滤器" }

                    UiTextField {
                        id: keywordInput
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "URL / 状态 / 类型"
                        onTextChanged: {
                            filterKeyword = text
                            pushFilters()
                        }
                    }

                    UiTextField {
                        id: hostInput
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "Host 包含"
                        onTextChanged: {
                            filterHost = text
                            pushFilters()
                        }
                    }

                        UiComboBox {
                            id: methodCombo
                            Layout.fillWidth: true
                            dark: root.dark
                            compact: true
                            model: ["全部方法", "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
                            onCurrentTextChanged: {
                                filterMethod = currentIndex === 0 ? "" : currentText
                                pushFilters()
                            }
                        }

                        UiComboBox {
                            id: schemeCombo
                            Layout.fillWidth: true
                            dark: root.dark
                            compact: true
                            model: ["协议", "http", "https"]
                            onCurrentTextChanged: {
                                filterScheme = currentIndex === 0 ? "" : currentText
                                pushFilters()
                            }
                        }

                    UiTextField {
                        id: contentTypeInput
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "Content-Type"
                        onTextChanged: {
                            filterContentType = text
                            pushFilters()
                        }
                    }

                        UiTextField {
                            id: statusMinInput
                            Layout.fillWidth: true
                            dark: root.dark
                            placeholderText: "状态 >="
                            validator: IntValidator { bottom: 0; top: 599 }
                            onTextChanged: {
                                filterStatusMin = parseInt(text || "0")
                                pushFilters()
                            }
                        }

                        UiTextField {
                            id: statusMaxInput
                            Layout.fillWidth: true
                            dark: root.dark
                            placeholderText: "状态 <="
                            validator: IntValidator { bottom: 0; top: 599 }
                            onTextChanged: {
                                filterStatusMax = parseInt(text || "0")
                                pushFilters()
                            }
                        }

                    UiTextField {
                        id: durationInput
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "耗时 >= ms"
                        validator: IntValidator { bottom: 0; top: 600000 }
                        onTextChanged: {
                            filterMinDurationMs = parseInt(text || "0")
                            pushFilters()
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        RowLayout {
                            id: onlyErrorsFilterRow
                            spacing: 0

                            UiCheckBox {
                                id: onlyErrorsCheck
                                dark: root.dark
                                checked: filterOnlyErrors
                                Layout.preferredWidth: 28
                                Layout.preferredHeight: 28
                                onCheckedChanged: {
                                    filterOnlyErrors = checked
                                    pushFilters()
                                }
                            }

                            Label {
                                text: "错误"
                                color: textMuted
                                font.pixelSize: Theme.fontSize.caption
                                verticalAlignment: Text.AlignVCenter

                                TapHandler {
                                    gesturePolicy: TapHandler.ReleaseWithinBounds
                                    onTapped: onlyErrorsCheck.toggle()
                                }
                            }
                        }

                        RowLayout {
                            id: hideStaticFilterRow
                            spacing: 0

                            UiCheckBox {
                                id: hideStaticCheck
                                dark: root.dark
                                checked: filterHideStatic
                                Layout.preferredWidth: 28
                                Layout.preferredHeight: 28
                                onCheckedChanged: {
                                    filterHideStatic = checked
                                    pushFilters()
                                }
                            }

                            Label {
                                text: "隐藏静态"
                                color: textMuted
                                font.pixelSize: Theme.fontSize.caption
                                verticalAlignment: Text.AlignVCenter

                                TapHandler {
                                    gesturePolicy: TapHandler.ReleaseWithinBounds
                                    onTapped: hideStaticCheck.toggle()
                                }
                            }
                        }
                    }

                    UiButton {
                        Layout.fillWidth: true
                        text: "重置过滤"
                        dark: root.dark
                        variant: "ghost"
                        onClicked: resetFilters()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: panelBorder
                    }

                    SectionLabel { text: "会话统计" }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        MetricCell { title: "可见"; value: String(stats.visibleRows || 0); tone: "info" }
                        MetricCell { title: "错误"; value: String(stats.errorRows || 0); tone: stats.errorRows > 0 ? "danger" : "neutral" }
                        MetricCell { title: "HTTPS"; value: String(stats.httpsRows || 0); tone: "success" }
                        MetricCell { title: "重放"; value: String(stats.replayedRows || 0); tone: "warning" }
                        MetricCell { title: "平均耗时"; value: durationText(stats.avgDurationMs || 0); tone: "neutral" }
                        MetricCell { title: "传输"; value: formatBytes(stats.totalBytes || 0); tone: "neutral" }
                    }

                    SectionLabel {
                        text: "状态分布"
                        Layout.topMargin: Theme.space["1"]
                    }

                    StatusBars {
                        Layout.fillWidth: true
                        okCount: stats.status2xx || 0
                        redirectCount: stats.status3xx || 0
                        clientErrorCount: stats.status4xx || 0
                        serverErrorCount: stats.status5xx || 0
                    }

                    InfoCard {
                        title: "HTTPS 解密"
                        body: captureState.certExists
                            ? "证书已生成。按引导信任后可查看 HTTPS 请求和响应正文。"
                            : "先启动代理生成证书，再按引导完成信任。"
                        tone: captureState.certExists ? "success" : "warning"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        UiButton {
                            Layout.fillWidth: true
                            text: "安装引导"
                            dark: root.dark
                            variant: "ghost"
                            onClicked: openGuide("desktop")
                        }

                        UiButton {
                            Layout.fillWidth: true
                            text: "自动信任"
                            dark: root.dark
                            variant: "ghost"
                            enabled: !!captureState.certExists
                            onClicked: httpCaptureVm.installDesktopCertificate()
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        UiButton {
                            Layout.fillWidth: true
                            text: "mitm.it"
                            dark: root.dark
                            variant: "ghost"
                            enabled: !!captureState.running
                            onClicked: httpCaptureVm.openCertInstallUrl()
                        }

                        UiButton {
                            Layout.fillWidth: true
                            text: "复制地址"
                            dark: root.dark
                            variant: "ghost"
                            onClicked: httpCaptureVm.copyCertInstallUrl()
                        }
                    }

                    InfoCard {
                        title: "手机抓包"
                        body: captureState.mobileProxyUrl
                            ? ("手机代理 " + captureState.mobileProxyUrl + "，按引导安装手机证书。")
                            : ((captureState.lanIp || "").length > 0 ? ("可用局域网 IP: " + captureState.lanIp) : "未识别到局域网 IP")
                        tone: captureState.mobileProxyUrl ? "success" : "neutral"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        UiButton {
                            Layout.fillWidth: true
                            text: "手机引导"
                            dark: root.dark
                            variant: "ghost"
                            onClicked: openGuide("mobile")
                        }

                        UiButton {
                            Layout.fillWidth: true
                            text: "复制地址"
                            dark: root.dark
                            variant: "ghost"
                            enabled: !!captureState.mobileProxyUrl
                            onClicked: httpCaptureVm.copyMobileProxyAddress()
                        }
                    }

                    InfoCard {
                        visible: !!captureState.systemProxyRecoverable || !!captureState.systemProxyRecoveryMessage
                        title: "系统代理恢复"
                        body: captureState.systemProxyRecoveryMessage || "发现上次异常退出残留的代理接管记录"
                        tone: captureState.systemProxyError ? "warning" : "info"
                    }

                    UiButton {
                        visible: !!captureState.systemProxyRecoverable
                        Layout.fillWidth: true
                        text: "恢复系统代理"
                        dark: root.dark
                        variant: "ghost"
                        enabled: !captureState.busy
                        onClicked: httpCaptureVm.recoverSystemProxy()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        radius: Theme.radii.md
                        color: subtleBg2
                        border.color: panelBorder
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 2

                            Label {
                                text: "Top Host"
                                color: textSubtle
                                font.pixelSize: Theme.fontSize.caption
                            }
                            Label {
                                Layout.fillWidth: true
                                text: stats.topHost || "-"
                                color: textMain
                                elide: Text.ElideMiddle
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                            }
                        }
                    }

                    Item { Layout.preferredHeight: Theme.space["1"] }

                    Label {
                        Layout.fillWidth: true
                        text: captureState.certExists ? "证书已生成" : "启动 HTTPS 抓包后生成证书"
                        color: captureState.certExists ? successColor : textSubtle
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        font.pixelSize: Theme.fontSize.caption
                    }
                    }
                }
            }

            Rectangle {
                id: sessionPanel
                SplitView.preferredWidth: compactLayout
                    ? Math.max(420, parent.width - sidePanelWidth - 6)
                    : Math.max(520, parent.width - sidePanelWidth - inspectorPanelWidth - 12)
                SplitView.minimumWidth: narrowLayout ? 360 : 430
                color: panelBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        color: tableHeader
                        radius: Theme.radii.md

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["2"]
                            anchors.rightMargin: Theme.space["2"]
                            spacing: Theme.space["1"]

                            HeaderCell { text: "时间"; w: 58 }
                            HeaderCell { text: "方法"; w: 54 }
                            HeaderCell { text: "Host"; w: hostColumnWidth }
                            HeaderCell { text: "Path"; fill: true }
                            HeaderCell { text: "状态"; w: 48; alignRight: true }
                            HeaderCell { visible: !compressedLayout; text: "类型"; w: 104 }
                            HeaderCell { visible: !compressedLayout; text: "大小"; w: 70; alignRight: true }
                            HeaderCell { text: "耗时"; w: 62; alignRight: true }
                        }
                    }

                    ListView {
                        id: sessionList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: rows
                        reuseItems: true
                        cacheBuffer: 1600

                        delegate: Rectangle {
                            id: rowItem
                            width: ListView.view.width
                            height: 32
                            color: selectedFlowId === modelData.id
                                ? Theme.token("color-primary-bg", root.dark)
                                : (rowMouse.containsMouse ? rowHover : (index % 2 === 0 ? panelBg : subtleBg2))

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    selectedFlowId = modelData.id
                                    httpCaptureVm.selectFlow(modelData.id)
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space["2"]
                                anchors.rightMargin: Theme.space["2"]
                                spacing: Theme.space["1"]

                                Label {
                                    text: modelData.startedAt || "-"
                                    Layout.preferredWidth: 58
                                    color: textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }

                                Label {
                                    text: modelData.method || "-"
                                    Layout.preferredWidth: 54
                                    color: methodColor(modelData.method)
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                    font.bold: true
                                }

                                RowLayout {
                                    Layout.preferredWidth: hostColumnWidth
                                    spacing: 4
                                    UiIcon {
                                        visible: !!modelData.encrypted
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                        name: "mdi6.lock-outline"
                                        color: successColor
                                        iconSize: 12
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.host || "-"
                                        color: textMain
                                        elide: Text.ElideMiddle
                                        font.pixelSize: Theme.fontSize.caption
                                        font.family: Theme.fontFamily.mono
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    StatusPill {
                                        visible: !!modelData.replayed
                                        label: "R"
                                        tone: "warning"
                                        compact: true
                                    }
                                    TextEdit {
                                        Layout.fillWidth: true
                                        text: rowTitle(modelData)
                                        color: modelData.error ? dangerColor : textMain
                                        font.pixelSize: Theme.fontSize.caption
                                        font.family: Theme.fontFamily.mono
                                        readOnly: true
                                        selectByMouse: true
                                        selectByKeyboard: true
                                        persistentSelection: true
                                        activeFocusOnPress: true
                                        textFormat: TextEdit.PlainText
                                        wrapMode: TextEdit.NoWrap
                                        clip: true
                                        selectedTextColor: root.textMain
                                        selectionColor: Theme.token("color-primary-hover", root.dark)
                                    }
                                }

                                Label {
                                    text: modelData.status > 0 ? String(modelData.status) : (modelData.error ? "ERR" : "...")
                                    Layout.preferredWidth: 48
                                    horizontalAlignment: Text.AlignRight
                                    color: modelData.error ? dangerColor : statusColorOf(modelData.status)
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                    font.bold: modelData.status >= 400 || !!modelData.error
                                }

                                Label {
                                    visible: !compressedLayout
                                    text: modelData.contentType || "-"
                                    Layout.preferredWidth: 104
                                    color: textSubtle
                                    elide: Text.ElideMiddle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }

                                Label {
                                    visible: !compressedLayout
                                    text: formatBytes(modelData.totalSize || modelData.size)
                                    Layout.preferredWidth: 70
                                    horizontalAlignment: Text.AlignRight
                                    color: textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }

                                Label {
                                    text: durationText(modelData.durationMs)
                                    Layout.preferredWidth: 62
                                    horizontalAlignment: Text.AlignRight
                                    color: modelData.durationMs >= 1000 ? warningColor : textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: rows.length === 0
                            text: captureState.running ? "等待请求进入代理" : "启动代理后开始捕获"
                            color: textSubtle
                            font.pixelSize: Theme.fontSize.body
                        }
                    }
                }
            }

            Rectangle {
                id: inspectorPanel
                visible: !compactLayout
                SplitView.preferredWidth: inspectorPanelWidth
                SplitView.minimumWidth: 320
                color: panelBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space["2"]
                    spacing: Theme.space["1"]

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["1"]

                        SelectableLine {
                            Layout.fillWidth: true
                            text: selectedFlowId ? (selectedDetail.requestUrl || currentSummary().url || "-") : "未选择会话"
                            color: textMain
                            font.pixelSize: Theme.fontSize.caption
                            font.family: Theme.fontFamily.mono
                        }

                        IconAction {
                            iconName: "mdi6.refresh"
                            tooltip: "重放请求"
                            enabled: selectedFlowId.length > 0
                            onClicked: httpCaptureVm.replayFlow(selectedFlowId)
                        }

                        IconAction {
                            iconName: "mdi6.link-variant"
                            tooltip: "复制 URL"
                            enabled: selectedFlowId.length > 0
                            onClicked: httpCaptureVm.copyUrl(selectedFlowId)
                        }

                        IconAction {
                            iconName: "mdi6.console"
                            tooltip: "复制 cURL"
                            enabled: selectedFlowId.length > 0
                            onClicked: httpCaptureVm.copyCurl(selectedFlowId)
                        }

                        IconAction {
                            iconName: "mdi6.content-save-outline"
                            tooltip: "保存响应正文"
                            enabled: selectedFlowId.length > 0
                            onClicked: bodySaveDialog.open()
                        }

                        IconAction {
                            iconName: "mdi6.file-export-outline"
                            tooltip: "导出当前会话"
                            enabled: selectedFlowId.length > 0
                            onClicked: selectedExportDialog.open()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        radius: Theme.radii.md
                        color: subtleBg2
                        border.color: panelBorder
                        border.width: 1

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            columns: 4
                            columnSpacing: Theme.space["1"]
                            rowSpacing: 2

                            MiniDetail { title: "状态"; value: selectedDetail.responseStatus ? String(selectedDetail.responseStatus) : "-"; valueColor: statusColorOf(selectedDetail.responseStatus) }
                            MiniDetail { title: "耗时"; value: durationText(selectedDetail.durationMs || currentSummary().durationMs) }
                            MiniDetail { title: "请求"; value: formatBytes(selectedDetail.requestSize || currentSummary().requestSize) }
                            MiniDetail { title: "响应"; value: formatBytes(selectedDetail.responseSize || currentSummary().responseSize) }
                        }
                    }

                    TabBar {
                        id: detailTabs
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        property int tabWidth: Math.max(42, Math.floor(width / 6))
                        spacing: 0
                        clip: true
                        background: Rectangle { color: subtleBg; radius: Theme.radii.sm }
                        DetailTabButton { text: "概览"; tooltip: "概览"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                        DetailTabButton { text: "请求"; tooltip: "请求头和请求体"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                        DetailTabButton { text: "响应"; tooltip: "响应头和响应体"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                        DetailTabButton { text: "参数"; tooltip: "Query 参数"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                        DetailTabButton { text: "Cookie"; tooltip: "请求和响应 Cookie"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                        DetailTabButton { text: "发包"; tooltip: "Composer 发包"; compact: detailTabs.width < 340; implicitWidth: detailTabs.tabWidth }
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: detailTabs.currentIndex

                        Flickable {
                            clip: true
                            contentWidth: width
                            contentHeight: overviewCol.implicitHeight

                            ColumnLayout {
                                id: overviewCol
                                width: parent.width
                                spacing: Theme.space["1"]

                                InspectorRow { k: "Method"; v: selectedDetail.requestMethod || currentSummary().method || "-" }
                                InspectorRow { k: "URL"; v: selectedDetail.requestUrl || currentSummary().url || "-" }
                                InspectorRow { k: "Path"; v: currentSummary().path || "-" }
                                InspectorRow { k: "Host"; v: currentSummary().host || "-" }
                                InspectorRow { k: "Status"; v: selectedDetail.responseStatus ? selectedDetail.responseStatus + " " + (selectedDetail.responseReason || "") : (currentSummary().error ? "ERR" : "-") }
                                InspectorRow { k: "Started"; v: selectedDetail.startedIso || currentSummary().startedIso || "-" }
                                InspectorRow { k: "TLS"; v: currentSummary().encrypted ? "HTTPS" : "HTTP" }
                                InspectorRow { k: "Replay"; v: selectedDetail.replayed || currentSummary().replayed ? "是" : "否" }
                                InspectorRow { k: "Error"; v: currentSummary().error || selectedDetail.note || "-"; danger: !!(currentSummary().error || selectedDetail.note) && currentSummary().status === 0 }
                            }
                        }

                        SplitView {
                            orientation: Qt.Vertical
                            handle: Rectangle { implicitHeight: 5; color: "transparent" }

                            TextInspector {
                                SplitView.preferredHeight: Math.max(112, inspectorPanel.height * 0.34)
                                SplitView.minimumHeight: 92
                                title: "Request Headers"
                                body: headersText(selectedDetail.requestHeaders)
                            }
                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Request Body"
                                body: requestBodyText()
                            }
                        }

                        SplitView {
                            orientation: Qt.Vertical
                            handle: Rectangle { implicitHeight: 5; color: "transparent" }

                            TextInspector {
                                SplitView.preferredHeight: Math.max(112, inspectorPanel.height * 0.34)
                                SplitView.minimumHeight: 92
                                title: "Response Headers"
                                body: headersText(selectedDetail.responseHeaders)
                            }
                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Response Body"
                                body: responseBodyText()
                                placeholder: selectedFlowId ? "响应正文为空" : "选择一条会话查看响应正文"
                            }
                        }

                        SplitView {
                            orientation: Qt.Vertical
                            handle: Rectangle { implicitHeight: 5; color: "transparent" }

                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Query String"
                                body: kvText(selectedDetail.queryParams)
                            }
                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Request Body Params"
                                body: kvText(selectedDetail.requestBodyParams)
                            }
                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Response Fields"
                                body: kvText(selectedDetail.responseBodyParams)
                            }
                        }

                        SplitView {
                            orientation: Qt.Vertical
                            handle: Rectangle { implicitHeight: 5; color: "transparent" }

                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Request Cookies"
                                body: kvText(selectedDetail.requestCookies)
                            }
                            TextInspector {
                                SplitView.fillHeight: true
                                title: "Response Cookies"
                                body: kvText(selectedDetail.responseCookies)
                            }
                        }

                        Rectangle {
                            color: subtleBg2
                            radius: Theme.radii.md
                            border.color: panelBorder
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.space["2"]
                                spacing: Theme.space["1"]

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.space["1"]

                                    UiComboBox {
                                        id: composerMethod
                                        Layout.preferredWidth: 96
                                        dark: root.dark
                                        compact: true
                                        model: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
                                    }

                                    UiTextField {
                                        id: composerUrl
                                        Layout.fillWidth: true
                                        dark: root.dark
                                        placeholderText: "https://example.com/api"
                                        onAccepted: {
                                            root.composerSending = true
                                            httpCaptureVm.sendComposerRequest(composerMethod.currentText, text, root.composerHeadersText, root.composerBodyText)
                                        }
                                    }

                                    UiButton {
                                        text: root.composerSending ? "发送中" : "发送"
                                        dark: root.dark
                                        variant: "primary"
                                        implicitWidth: 72
                                        enabled: !root.composerSending && composerUrl.text.trim().length > 0
                                        onClicked: {
                                            root.composerSending = true
                                            httpCaptureVm.sendComposerRequest(composerMethod.currentText, composerUrl.text, root.composerHeadersText, root.composerBodyText)
                                        }
                                    }
                                }

                                TextInspector {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: Math.max(104, parent.height * 0.32)
                                    title: "Headers"
                                    editable: true
                                    body: ""
                                    placeholder: "Content-Type: application/json"
                                    onBodyEdited: function(value) { root.composerHeadersText = value }
                                }

                                TextInspector {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    title: "Body"
                                    editable: true
                                    body: ""
                                    placeholder: "{\n  \"key\": \"value\"\n}"
                                    onBodyEdited: function(value) { root.composerBodyText = value }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: statusBg
            radius: Theme.radii.sm

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2"]

                SelectableLine {
                    text: statusText
                    color: statusColor
                    font.pixelSize: Theme.fontSize.caption
                    Layout.fillWidth: true
                }

                SelectableLine {
                    text: "证书: " + (captureState.certExists ? captureState.certPath : "未生成")
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    font.family: Theme.fontFamily.mono
                    Layout.maximumWidth: root.width * 0.48
                }
            }
        }
    }

    Popup {
        id: setupGuidePopup
        modal: true
        dim: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(root.width - 48, guideMode === "mobile" ? 620 : 580)
        height: Math.min(root.height - 48, guideColumn.implicitHeight + 28)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: panelBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1
        }

        ColumnLayout {
            id: guideColumn
            anchors.fill: parent
            anchors.margins: Theme.space["2"]
            spacing: Theme.space["2"]

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space["1.5"]

                Rectangle {
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    radius: Theme.radii.md
                    color: subtleBg2

                    UiIcon {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        name: guideMode === "mobile" ? "mdi6.cellphone-link" : "mdi6.certificate-outline"
                        color: guideMode === "mobile" ? infoColor : successColor
                        iconSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        Layout.fillWidth: true
                        text: guideMode === "mobile" ? "手机抓包与证书安装" : "HTTPS 解密证书安装"
                        color: textMain
                        font.family: Theme.fontFamily.ui
                        font.pixelSize: Theme.fontSize.title
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: guideMode === "mobile"
                            ? (captureState.mobileProxyUrl ? "代理地址 " + captureState.mobileProxyUrl : "先启动手机模式，再在手机 Wi-Fi 中配置代理")
                            : (captureState.certExists ? "证书已生成: " + captureState.certPath : "先启动代理生成 mitmproxy CA 证书")
                        color: textSubtle
                        font.pixelSize: Theme.fontSize.caption
                        font.family: Theme.fontFamily.mono
                        elide: Text.ElideMiddle
                    }
                }

                IconAction {
                    iconName: "mdi6.close"
                    tooltip: "关闭"
                    onClicked: setupGuidePopup.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: panelBorder
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space["1"]
                visible: guideMode !== "mobile"

                GuideStep {
                    number: "1"
                    title: "启动代理"
                    body: captureState.running
                        ? "代理已启动，系统代理会自动指向本机代理地址。"
                        : "点击启动代理，应用会生成证书并接管系统 HTTP/HTTPS 代理。"
                    actionText: captureState.running ? "已启动" : "启动代理"
                    actionEnabled: !captureState.running && !captureState.busy
                    actionIcon: captureState.running ? "mdi6.check" : "mdi6.play"
                    onAction: httpCaptureVm.startHttpCapture()
                }

                GuideStep {
                    number: "2"
                    title: "信任桌面证书"
                    body: captureState.certExists
                        ? "点击自动信任会把证书加入当前用户信任根；也可以打开目录手动安装。"
                        : "证书还未生成，请先启动一次代理。"
                    actionText: "自动信任"
                    actionEnabled: !!captureState.certExists
                    actionIcon: "mdi6.certificate-outline"
                    secondaryText: "打开目录"
                    secondaryEnabled: true
                    onAction: httpCaptureVm.installDesktopCertificate()
                    onSecondary: httpCaptureVm.revealCertDir()
                }

                GuideStep {
                    number: "3"
                    title: "验证 HTTPS 解密"
                    body: "访问任意 HTTPS 网站后，在会话列表中选择请求，响应页会显示 Headers 和 Body。"
                    actionText: "打开 mitm.it"
                    actionEnabled: !!captureState.running
                    actionIcon: "mdi6.open-in-new"
                    secondaryText: "复制地址"
                    secondaryEnabled: true
                    onAction: httpCaptureVm.openCertInstallUrl()
                    onSecondary: httpCaptureVm.copyCertInstallUrl()
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space["1"]
                visible: guideMode === "mobile"

                GuideStep {
                    number: "1"
                    title: "启动手机模式"
                    body: captureState.mobileProxyUrl
                        ? "手机模式已启动，本机正在监听局域网代理地址。"
                        : ((captureState.lanIp || "").length > 0 ? "确保电脑和手机在同一 Wi-Fi，然后启动手机模式。" : "未识别到局域网 IP，请确认电脑已连接网络。")
                    actionText: captureState.mobileProxyUrl ? "已启动" : "启动手机模式"
                    actionEnabled: !captureState.running && !captureState.busy
                    actionIcon: captureState.mobileProxyUrl ? "mdi6.check" : "mdi6.cellphone-link"
                    onAction: httpCaptureVm.startMobileCapture()
                }

                GuideStep {
                    number: "2"
                    title: "配置手机 Wi-Fi 代理"
                    body: captureState.mobileProxyUrl
                        ? "在手机当前 Wi-Fi 的 HTTP 代理中选择手动，服务器填 " + captureState.lanIp + "，端口填 " + captureState.listenPort + "。"
                        : "手机模式启动后，这里会显示服务器和端口。"
                    actionText: "复制代理"
                    actionEnabled: !!captureState.mobileProxyUrl
                    actionIcon: "mdi6.content-copy"
                    onAction: httpCaptureVm.copyMobileProxyAddress()
                }

                GuideStep {
                    number: "3"
                    title: "安装并信任手机证书"
                    body: "手机浏览器访问 mitm.it。iOS 安装描述文件后到证书信任中启用完全信任；Android 在安全/凭据中安装 CA 证书。"
                    actionText: "复制 mitm.it"
                    actionEnabled: !!captureState.running
                    actionIcon: "mdi6.content-copy"
                    secondaryText: "桌面打开"
                    secondaryEnabled: true
                    onAction: httpCaptureVm.copyCertInstallUrl()
                    onSecondary: httpCaptureVm.openCertInstallUrl()
                }

                GuideStep {
                    number: "4"
                    title: "开始抓包"
                    body: "手机应用或浏览器产生请求后，会话会实时进入列表；HTTPS 正文需要手机证书已信任。"
                    actionText: "关闭"
                    actionEnabled: true
                    actionIcon: "mdi6.check"
                    onAction: setupGuidePopup.close()
                }
            }
        }
    }

    FileDialog {
        id: bodySaveDialog
        title: "保存响应正文"
        fileMode: FileDialog.SaveFile
        onAccepted: httpCaptureVm.saveResponseBody(selectedFlowId, String(selectedFile))
    }

    FileDialog {
        id: selectedExportDialog
        title: "导出当前会话"
        fileMode: FileDialog.SaveFile
        nameFilters: ["HAR 文件 (*.har)", "JSON 文件 (*.json)"]
        onAccepted: httpCaptureVm.exportSelectedSession(selectedFlowId, String(selectedFile))
    }

    FileDialog {
        id: exportVisibleDialog
        title: "导出可见会话"
        fileMode: FileDialog.SaveFile
        nameFilters: ["HAR 文件 (*.har)", "JSON 文件 (*.json)"]
        onAccepted: {
            var file = String(selectedFile)
            var lower = file.toLowerCase()
            var fmt = lower.indexOf(".json") === lower.length - 5 ? "json" : pendingExportFormat
            httpCaptureVm.exportVisibleSessions(file, fmt)
        }
    }

    Connections {
        target: httpCaptureVm
        function onCaptureStateUpdated(payload) {
            captureState = payload || ({})
            updateStatusFromState()
        }

        function onCaptureRowsUpdated(items) {
            rows = items || []
            if (selectedFlowId.length > 0) {
                var found = false
                for (var i = 0; i < rows.length; i++) {
                    if (rows[i].id === selectedFlowId) {
                        found = true
                        break
                    }
                }
                if (!found) {
                    selectedFlowId = ""
                    selectedDetail = ({})
                }
            }
        }

        function onCaptureDetailUpdated(payload) {
            selectedDetail = payload || ({})
            if (selectedDetail.id) selectedFlowId = selectedDetail.id
        }

        function onCaptureStatsUpdated(payload) {
            stats = payload || ({})
        }

        function onCaptureActionResult(ok, message) {
            composerSending = false
            setStatus(message, ok ? "success" : "error")
        }
    }

    component HeaderCell: Label {
        property int w: 0
        property bool fill: false
        property bool alignRight: false

        Layout.preferredWidth: fill ? -1 : w
        Layout.fillWidth: fill
        horizontalAlignment: alignRight ? Text.AlignRight : Text.AlignLeft
        color: textSubtle
        elide: Text.ElideRight
        font.pixelSize: Theme.fontSize.caption
        font.family: Theme.fontFamily.ui
    }

    component SectionLabel: Label {
        color: textSubtle
        font.pixelSize: Theme.fontSize.caption
        font.family: Theme.fontFamily.ui
        font.bold: true
    }

    component IconAction: Rectangle {
        property string iconName: ""
        property string tooltip: ""
        property bool accent: false
        signal clicked()

        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        radius: Theme.radii.md
        color: {
            if (!enabled) return subtleBg2
            if (buttonMouse.pressed) return accent ? Qt.darker(root.accent, 1.15) : panelBorder
            if (buttonMouse.containsMouse) return accent ? Theme.token("color-primary", root.dark) : subtleBg
            return accent ? root.accent : subtleBg2
        }
        border.color: accent || buttonMouse.containsMouse ? "transparent" : panelBorder
        border.width: 1
        opacity: enabled ? 1 : 0.5

        UiIcon {
            id: actionIcon
            anchors.centerIn: parent
            width: 16
            height: 16
            name: iconName
            color: parent.enabled ? (accent ? Theme.token("color-bg-surface", false) : textMain) : textSubtle
            iconSize: 16

            RotationAnimator on rotation {
                running: iconName === "mdi6.loading"
                loops: Animation.Infinite
                from: 0
                to: 360
                duration: 900
            }
        }

        onIconNameChanged: if (iconName !== "mdi6.loading") actionIcon.rotation = 0

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: if (parent.enabled) parent.clicked()
        }

        ToolTip.visible: buttonMouse.containsMouse && tooltip.length > 0
        ToolTip.text: tooltip
        ToolTip.delay: 250
    }

    component DetailTabButton: TabButton {
        id: control

        property bool compact: false
        property string tooltip: ""

        implicitHeight: 30
        leftPadding: 0
        rightPadding: 0
        topPadding: 0
        bottomPadding: 0
        hoverEnabled: true

        background: Rectangle {
            radius: Theme.radii.sm
            color: control.checked
                ? Theme.token("color-nav-active-bg", root.dark)
                : (control.hovered ? subtleBg2 : "transparent")
        }

        contentItem: Text {
            text: control.text
            color: control.checked ? Theme.token("color-primary-active", root.dark) : textMain
            font.pixelSize: control.compact ? 10 : Theme.fontSize.caption
            font.family: Theme.fontFamily.ui
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            clip: true
        }

        ToolTip.visible: hovered && tooltip.length > 0
        ToolTip.text: tooltip
        ToolTip.delay: 250
    }

    component StatusPill: Rectangle {
        property string label: ""
        property string tone: "neutral"
        property bool compact: false

        implicitWidth: pillText.implicitWidth + (compact ? 10 : 14)
        implicitHeight: compact ? 18 : 20
        radius: Theme.radii.sm
        color: {
            if (tone === "success") return root.dark ? "#052E2B" : "#D1FAE5"
            if (tone === "warning") return root.dark ? "#3A2608" : "#FEF3C7"
            if (tone === "danger") return root.dark ? "#3F1118" : "#FEE2E2"
            if (tone === "info") return root.dark ? "#082F49" : "#DBEAFE"
            return subtleBg
        }

        Label {
            id: pillText
            anchors.centerIn: parent
            text: label
            color: {
                if (tone === "success") return successColor
                if (tone === "warning") return warningColor
                if (tone === "danger") return dangerColor
                if (tone === "info") return infoColor
                return textSubtle
            }
            font.pixelSize: Theme.fontSize.caption
            font.bold: true
        }
    }

    component MetricCell: Rectangle {
        property string title: ""
        property string value: ""
        property string tone: "neutral"
        property bool wide: false

        Layout.fillWidth: true
        Layout.columnSpan: wide ? 2 : 1
        Layout.preferredHeight: 46
        radius: Theme.radii.md
        color: subtleBg2
        border.color: panelBorder
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.space["2"]
            anchors.rightMargin: Theme.space["2"]
            anchors.topMargin: 5
            anchors.bottomMargin: 5
            spacing: 0

            Label {
                Layout.fillWidth: true
                text: title
                color: textSubtle
                font.pixelSize: Theme.fontSize.caption
                elide: Text.ElideRight
            }

            Label {
                Layout.fillWidth: true
                text: value
                color: {
                    if (tone === "success") return successColor
                    if (tone === "warning") return warningColor
                    if (tone === "danger") return dangerColor
                    if (tone === "info") return infoColor
                    return textMain
                }
                font.pixelSize: Theme.fontSize.body
                font.family: Theme.fontFamily.mono
                font.bold: true
                elide: Text.ElideRight
            }
        }
    }

    component InfoCard: Rectangle {
        property string title: ""
        property string body: ""
        property string tone: "neutral"

        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(58, infoColumn.implicitHeight + 12)
        radius: Theme.radii.md
        color: {
            if (tone === "success") return root.dark ? "#052E2B" : "#ECFDF5"
            if (tone === "warning") return root.dark ? "#3A2608" : "#FFFBEB"
            if (tone === "info") return root.dark ? "#082F49" : "#EFF6FF"
            return subtleBg2
        }
        border.color: panelBorder
        border.width: 1

        ColumnLayout {
            id: infoColumn
            anchors.fill: parent
            anchors.margins: Theme.space["1"]
            spacing: 2

            Label {
                Layout.fillWidth: true
                text: title
                color: textMain
                font.pixelSize: Theme.fontSize.caption
                font.bold: true
                elide: Text.ElideRight
            }

            Label {
                Layout.fillWidth: true
                text: body
                color: textSubtle
                font.pixelSize: Theme.fontSize.caption
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
        }
    }

    component GuideStep: Rectangle {
        property string number: ""
        property string title: ""
        property string body: ""
        property string actionText: ""
        property string actionIcon: "mdi6.play"
        property bool actionEnabled: true
        property string secondaryText: ""
        property bool secondaryEnabled: false
        signal action()
        signal secondary()

        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(74, guideStepRow.implicitHeight + 16)
        radius: Theme.radii.md
        color: subtleBg2
        border.color: panelBorder
        border.width: 1

        RowLayout {
            id: guideStepRow
            anchors.fill: parent
            anchors.margins: Theme.space["1"]
            spacing: Theme.space["1.5"]

            Rectangle {
                Layout.preferredWidth: 26
                Layout.preferredHeight: 26
                radius: 13
                color: root.accent

                Label {
                    anchors.centerIn: parent
                    text: number
                    color: Theme.token("color-bg-surface", false)
                    font.pixelSize: Theme.fontSize.caption
                    font.bold: true
                    font.family: Theme.fontFamily.ui
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Label {
                    Layout.fillWidth: true
                    text: title
                    color: textMain
                    font.pixelSize: Theme.fontSize.body
                    font.bold: true
                    font.family: Theme.fontFamily.ui
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    text: body
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
            }

            IconTextAction {
                visible: secondaryText.length > 0
                text: secondaryText
                iconName: "mdi6.dots-horizontal"
                enabled: secondaryEnabled
                onClicked: secondary()
            }

            IconTextAction {
                text: actionText
                iconName: actionIcon
                accent: true
                enabled: actionEnabled
                onClicked: action()
            }
        }
    }

    component IconTextAction: Rectangle {
        id: iconTextAction

        property alias text: actionLabel.text
        property string iconName: ""
        property bool accent: false
        signal clicked()

        Layout.preferredWidth: Math.max(76, actionLabel.implicitWidth + 36)
        Layout.preferredHeight: 30
        radius: Theme.radii.md
        color: {
            if (!enabled) return subtleBg
            if (actionMouse.pressed) return accent ? Qt.darker(root.accent, 1.15) : panelBorder
            if (actionMouse.containsMouse) return accent ? Theme.token("color-primary", root.dark) : subtleBg
            return accent ? root.accent : panelBg
        }
        border.color: accent ? "transparent" : panelBorder
        border.width: 1
        opacity: enabled ? 1 : 0.5

        RowLayout {
            anchors.centerIn: parent
            spacing: 4

            UiIcon {
                Layout.preferredWidth: 14
                Layout.preferredHeight: 14
                name: iconTextAction.iconName
                color: iconTextAction.accent ? Theme.token("color-bg-surface", false) : root.textMain
                iconSize: 14
            }

            Label {
                id: actionLabel
                color: iconTextAction.accent ? Theme.token("color-bg-surface", false) : root.textMain
                font.pixelSize: Theme.fontSize.caption
                font.family: Theme.fontFamily.ui
                elide: Text.ElideRight
            }
        }

        MouseArea {
            id: actionMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: if (parent.enabled) parent.clicked()
        }
    }

    component StatusBars: ColumnLayout {
        property int okCount: 0
        property int redirectCount: 0
        property int clientErrorCount: 0
        property int serverErrorCount: 0
        readonly property int total: Math.max(1, okCount + redirectCount + clientErrorCount + serverErrorCount)

        spacing: 5

        RowLayout {
            Layout.fillWidth: true
            spacing: 2

            Rectangle { Layout.fillWidth: true; Layout.preferredWidth: okCount; Layout.preferredHeight: 8; radius: 3; color: successColor; opacity: okCount > 0 ? 1 : 0.18 }
            Rectangle { Layout.fillWidth: true; Layout.preferredWidth: redirectCount; Layout.preferredHeight: 8; radius: 3; color: infoColor; opacity: redirectCount > 0 ? 1 : 0.18 }
            Rectangle { Layout.fillWidth: true; Layout.preferredWidth: clientErrorCount; Layout.preferredHeight: 8; radius: 3; color: warningColor; opacity: clientErrorCount > 0 ? 1 : 0.18 }
            Rectangle { Layout.fillWidth: true; Layout.preferredWidth: serverErrorCount; Layout.preferredHeight: 8; radius: 3; color: dangerColor; opacity: serverErrorCount > 0 ? 1 : 0.18 }
        }

        Label {
            Layout.fillWidth: true
            text: "2xx " + okCount + "   3xx " + redirectCount + "   4xx " + clientErrorCount + "   5xx " + serverErrorCount
            color: textSubtle
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.mono
            elide: Text.ElideRight
        }
    }

    component MiniDetail: ColumnLayout {
        property string title: ""
        property string value: ""
        property color valueColor: textMain

        Layout.fillWidth: true
        spacing: 0

        Label {
            Layout.fillWidth: true
            text: title
            color: textSubtle
            font.pixelSize: Theme.fontSize.caption
            horizontalAlignment: Text.AlignHCenter
        }

        Label {
            Layout.fillWidth: true
            text: value
            color: valueColor
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.mono
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    component InspectorRow: RowLayout {
        id: inspectorRow

        property string k: ""
        property string v: ""
        property bool danger: false

        width: parent.width
        spacing: Theme.space["2"]

        Label {
            text: inspectorRow.k
            Layout.preferredWidth: 72
            color: root.textSubtle
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.mono
        }

        TextEdit {
            Layout.fillWidth: true
            text: inspectorRow.v
            color: inspectorRow.danger ? root.dangerColor : root.textMain
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.mono
            readOnly: true
            selectByMouse: true
            selectByKeyboard: true
            persistentSelection: true
            activeFocusOnPress: true
            textFormat: TextEdit.PlainText
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-hover", root.dark)
        }
    }

    component SelectableLine: TextEdit {
        readOnly: true
        selectByMouse: true
        selectByKeyboard: true
        persistentSelection: true
        activeFocusOnPress: true
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.NoWrap
        clip: true
        selectedTextColor: root.textMain
        selectionColor: Theme.token("color-primary-hover", root.dark)
    }

    component TextInspector: Rectangle {
        id: inspector

        property string title: ""
        property string body: ""
        property string placeholder: "无内容"
        property bool editable: false
        signal bodyEdited(string value)

        color: subtleBg2
        radius: Theme.radii.md
        border.color: panelBorder
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space["1"]
            spacing: Theme.space["1"]

            Label {
                Layout.fillWidth: true
                text: inspector.title
                color: root.textSubtle
                font.pixelSize: Theme.fontSize.caption
                font.bold: true
            }

            UiScrollView {
                id: inspectorScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                UiTextArea {
                    id: inspectorText
                    width: inspector.editable
                        ? inspectorScroll.availableWidth
                        : Math.max(inspectorScroll.availableWidth, contentWidth + leftPadding + rightPadding)
                    height: Math.max(inspectorScroll.availableHeight, contentHeight + topPadding + bottomPadding)
                    dark: root.dark
                    readOnly: !inspector.editable
                    selectByMouse: true
                    persistentSelection: true
                    wrapMode: TextEdit.NoWrap
                    text: inspector.body || ""
                    placeholderText: inspector.placeholder
                    onTextChanged: if (inspector.editable) inspector.bodyEdited(text)
                }
            }
        }
    }
}

