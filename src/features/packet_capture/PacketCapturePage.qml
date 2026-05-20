import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    property var rows: []
    property var state: ({})
    property var selectedDetail: ({})
    property string selectedFlowId: ""
    property string statusText: "未启动代理"
    property color statusColor: textMuted
    property string filterKeyword: ""
    property string filterMethod: ""
    property string filterContentType: ""
    property int filterStatusMin: 0
    property int filterStatusMax: 0
    property bool filterOnlyErrors: false

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
    readonly property color accent: Theme.token("color-primary-active", dark)
    readonly property color tableHeader: Theme.token("color-table-header", dark)

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else statusColor = textMuted
    }

    function pushFilters() {
        packetCaptureVm.setFilters(filterKeyword, filterMethod, filterContentType,
                                   filterStatusMin, filterStatusMax, filterOnlyErrors)
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
        if (s >= 400) return Theme.token("color-warning", root.dark)
        if (s >= 300) return infoColor
        return successColor
    }

    function formatBytes(n) {
        if (!n || n <= 0) return "-"
        if (n < 1024) return n + " B"
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
        return (n / 1024 / 1024).toFixed(2) + " MB"
    }

    Component.onCompleted: state = packetCaptureVm.initialState() || ({})

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        // 顶部工具栏
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["2"]
            Label {
                text: "抓包工具"
                font.bold: true
                font.pixelSize: Theme.fontSize.title
                color: textMain
                font.family: Theme.fontFamily.ui
            }
            Item { Layout.fillWidth: true }
            Label {
                text: state.running ? "● 运行中" : "● 已停止"
                color: state.running ? successColor : textMuted
                font.pixelSize: Theme.fontSize.caption
            }
            UiButton {
                text: state.running ? "停止" : "启动"
                dark: root.dark
                variant: "primary"
                onClicked: state.running ? packetCaptureVm.stopPacketCapture() : packetCaptureVm.startPacketCapture()
            }
            UiButton {
                text: state.paused ? "继续" : "暂停"
                dark: root.dark
                variant: "secondary"
                enabled: !!state.running
                onClicked: state.paused ? packetCaptureVm.resumePacketCapture() : packetCaptureVm.pausePacketCapture()
            }
            UiButton {
                text: "清空"
                dark: root.dark
                variant: "ghost"
                onClicked: packetCaptureVm.clearPacketRows()
            }
        }

        // 提示卡片
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: certNote.implicitHeight + Theme.space["3"]
            color: subtleBg
            radius: Theme.radii.md
            border.color: panelBorder
            border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2"]
                Label {
                    id: certNote
                    Layout.fillWidth: true
                    color: textMuted
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    font.pixelSize: Theme.fontSize.caption
                    text: {
                        var addr = state.proxyUrl ? state.proxyUrl : (state.listenHost ? (state.listenHost + ":" + state.listenPort) : "127.0.0.1:" + 8899)
                        var certWord = state.certExists ? "已生成" : "尚未生成"
                        return "代理地址 " + addr + " · 证书 " + certWord
                            + (state.certPath ? (" (" + state.certPath + ")") : "")
                            + " · 应用不会自动修改系统代理或信任证书，请按提示自行操作"
                    }
                }
                UiButton { text: "复制代理"; dark: root.dark; variant: "ghost"; implicitWidth: 80; onClicked: packetCaptureVm.copyProxyAddress() }
                UiButton { text: "证书目录"; dark: root.dark; variant: "ghost"; implicitWidth: 80; onClicked: packetCaptureVm.revealCertDir() }
            }
        }

        // 过滤条
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["1"]
            UiTextField {
                dark: root.dark
                Layout.fillWidth: true
                placeholderText: "关键字 (host/path/method/content-type)"
                onTextChanged: { filterKeyword = text; pushFilters() }
            }
            UiComboBox {
                dark: root.dark
                model: ["", "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
                Layout.preferredWidth: 96
                onCurrentTextChanged: { filterMethod = currentText; pushFilters() }
            }
            UiTextField {
                dark: root.dark
                Layout.preferredWidth: 160
                placeholderText: "Content-Type 包含"
                onTextChanged: { filterContentType = text; pushFilters() }
            }
            UiTextField {
                dark: root.dark
                Layout.preferredWidth: 70
                placeholderText: "状态≥"
                validator: IntValidator { bottom: 0; top: 599 }
                onTextChanged: { filterStatusMin = parseInt(text || "0"); pushFilters() }
            }
            UiTextField {
                dark: root.dark
                Layout.preferredWidth: 70
                placeholderText: "状态≤"
                validator: IntValidator { bottom: 0; top: 599 }
                onTextChanged: { filterStatusMax = parseInt(text || "0"); pushFilters() }
            }
            CheckBox {
                text: "只看错误"
                checked: filterOnlyErrors
                onCheckedChanged: { filterOnlyErrors = checked; pushFilters() }
            }
        }

        // 主体：左列表 + 右详情
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle { implicitWidth: 4; color: "transparent" }

            // 左侧请求列表
            Rectangle {
                SplitView.preferredWidth: parent.width * 0.55
                SplitView.minimumWidth: 360
                color: panelBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 26
                        color: tableHeader
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["2"]
                            anchors.rightMargin: Theme.space["2"]
                            spacing: Theme.space["1"]
                            Label { text: "方法"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 50 }
                            Label { text: "Host"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 140; elide: Text.ElideMiddle }
                            Label { text: "路径"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.fillWidth: true }
                            Label { text: "状态"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 44; horizontalAlignment: Text.AlignRight }
                            Label { text: "类型"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 90; elide: Text.ElideMiddle }
                            Label { text: "大小"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                            Label { text: "耗时"; color: textSubtle; font.pixelSize: Theme.fontSize.caption; Layout.preferredWidth: 52; horizontalAlignment: Text.AlignRight }
                        }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: rows
                        spacing: 0
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 24
                            color: selectedFlowId === modelData.id
                                ? Theme.token("color-primary-bg", root.dark)
                                : (index % 2 === 0 ? panelBg : subtleBg)
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    selectedFlowId = modelData.id
                                    packetCaptureVm.selectFlow(modelData.id)
                                }
                            }
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space["2"]
                                anchors.rightMargin: Theme.space["2"]
                                spacing: Theme.space["1"]
                                Label {
                                    text: modelData.method
                                    Layout.preferredWidth: 50
                                    color: methodColor(modelData.method)
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                    font.bold: true
                                }
                                Label {
                                    text: modelData.host || ""
                                    Layout.preferredWidth: 140
                                    color: textMain
                                    elide: Text.ElideMiddle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                                Label {
                                    text: modelData.path || ""
                                    Layout.fillWidth: true
                                    color: textMain
                                    elide: Text.ElideMiddle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                                Label {
                                    text: modelData.status > 0 ? String(modelData.status) : "·"
                                    Layout.preferredWidth: 44
                                    horizontalAlignment: Text.AlignRight
                                    color: statusColorOf(modelData.status)
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                                Label {
                                    text: modelData.contentType || ""
                                    Layout.preferredWidth: 90
                                    color: textSubtle
                                    elide: Text.ElideMiddle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                                Label {
                                    text: formatBytes(modelData.size)
                                    Layout.preferredWidth: 64
                                    horizontalAlignment: Text.AlignRight
                                    color: textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                                Label {
                                    text: modelData.durationMs > 0 ? modelData.durationMs + "ms" : "·"
                                    Layout.preferredWidth: 52
                                    horizontalAlignment: Text.AlignRight
                                    color: textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    font.family: Theme.fontFamily.mono
                                }
                            }
                        }
                    }
                }
            }

            // 右侧详情
            Rectangle {
                color: panelBg
                radius: Theme.radii.md
                border.color: panelBorder
                border.width: 1
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space["2"]
                    spacing: Theme.space["1"]

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: selectedFlowId ? (selectedDetail.requestUrl || "(无)") : "选择一条请求查看详情"
                            color: textMain
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                            font.pixelSize: Theme.fontSize.caption
                            font.family: Theme.fontFamily.mono
                        }
                        UiButton { text: "复制 URL"; dark: root.dark; variant: "ghost"; implicitWidth: 76; enabled: selectedFlowId.length > 0; onClicked: packetCaptureVm.copyUrl(selectedFlowId) }
                        UiButton { text: "复制 cURL"; dark: root.dark; variant: "ghost"; implicitWidth: 80; enabled: selectedFlowId.length > 0; onClicked: packetCaptureVm.copyCurl(selectedFlowId) }
                        UiButton { text: "保存响应"; dark: root.dark; variant: "ghost"; implicitWidth: 80; enabled: selectedFlowId.length > 0; onClicked: bodySaveDialog.open() }
                    }

                    TabBar {
                        id: detailTabs
                        Layout.fillWidth: true
                        background: Rectangle { color: subtleBg; radius: Theme.radii.sm }
                        UiTabButton { text: "概览"; dark: root.dark }
                        UiTabButton { text: "请求头"; dark: root.dark }
                        UiTabButton { text: "请求体"; dark: root.dark }
                        UiTabButton { text: "响应头"; dark: root.dark }
                        UiTabButton { text: "响应体"; dark: root.dark }
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: detailTabs.currentIndex

                        // Overview
                        Flickable {
                            clip: true
                            contentWidth: width
                            contentHeight: overviewCol.implicitHeight
                            ColumnLayout {
                                id: overviewCol
                                width: parent.width
                                spacing: 4
                                Label { text: "方法: " + (selectedDetail.requestMethod || "-"); color: textMain; font.family: Theme.fontFamily.mono; font.pixelSize: Theme.fontSize.caption }
                                Label { text: "状态: " + (selectedDetail.responseStatus > 0 ? selectedDetail.responseStatus + " " + (selectedDetail.responseReason || "") : "-"); color: textMain; font.family: Theme.fontFamily.mono; font.pixelSize: Theme.fontSize.caption }
                                Label { text: "URL: " + (selectedDetail.requestUrl || "-"); color: textMain; font.family: Theme.fontFamily.mono; font.pixelSize: Theme.fontSize.caption; wrapMode: Text.WrapAtWordBoundaryOrAnywhere; Layout.fillWidth: true }
                                Label {
                                    text: selectedDetail.note ? "提示: " + selectedDetail.note : ""
                                    color: textSubtle
                                    visible: !!selectedDetail.note
                                    font.pixelSize: Theme.fontSize.caption
                                }
                            }
                        }
                        // Request Headers
                        UiScrollView {
                            clip: true
                            UiTextArea {
                                readOnly: true
                                width: parent.width
                                height: parent.height
                                dark: root.dark
                                wrapMode: TextEdit.NoWrap
                                text: (selectedDetail.requestHeaders || []).map(function(h){return h.name + ": " + h.value}).join("\n")
                            }
                        }
                        // Request Body
                        UiScrollView {
                            clip: true
                            UiTextArea {
                                readOnly: true
                                width: parent.width
                                height: parent.height
                                dark: root.dark
                                wrapMode: TextEdit.NoWrap
                                text: (selectedDetail.requestBody || "")
                                    + (selectedDetail.requestBodyTruncated ? "\n\n[正文过大已截断]" : "")
                            }
                        }
                        // Response Headers
                        UiScrollView {
                            clip: true
                            UiTextArea {
                                readOnly: true
                                width: parent.width
                                height: parent.height
                                dark: root.dark
                                wrapMode: TextEdit.NoWrap
                                text: (selectedDetail.responseHeaders || []).map(function(h){return h.name + ": " + h.value}).join("\n")
                            }
                        }
                        // Response Body
                        UiScrollView {
                            clip: true
                            UiTextArea {
                                readOnly: true
                                width: parent.width
                                height: parent.height
                                dark: root.dark
                                wrapMode: TextEdit.NoWrap
                                text: (selectedDetail.responseBody || "")
                                    + (selectedDetail.responseBodyTruncated ? "\n\n[正文过大已截断]" : "")
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
                    text: "共 " + rows.length + " 条" + (state.paused ? " · 已暂停记录" : "")
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }
            }
        }
    }

    FileDialog {
        id: bodySaveDialog
        title: "保存响应正文"
        fileMode: FileDialog.SaveFile
        onAccepted: packetCaptureVm.saveResponseBody(selectedFlowId, String(selectedFile))
    }

    Connections {
        target: packetCaptureVm
        function onPacketStateUpdated(payload) {
            state = payload || ({})
            if (state.error && state.error.length > 0)
                setStatus(state.error, "error")
            else if (state.running)
                setStatus("代理运行中：" + (state.proxyUrl || ""), "success")
            else
                setStatus("代理已停止", "info")
        }
        function onPacketRowsUpdated(items) { rows = items || [] }
        function onPacketDetailUpdated(payload) { selectedDetail = payload || ({}) }
        function onPacketActionResult(ok, message) { setStatus(message, ok ? "success" : "error") }
    }
}
