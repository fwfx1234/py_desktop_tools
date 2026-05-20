pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root

    readonly property var vm: typeof quickLaunchVm !== "undefined" ? quickLaunchVm : null
    readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false

    // ---- macOS palette ----
    readonly property color pageBg: dark ? "#1E1E1E" : "#ECECEC"
    readonly property color surfaceBg: dark ? "#2A2A2C" : "#FFFFFF"
    readonly property color sheetBg: dark ? "#2C2C2E" : "#F6F6F6"
    readonly property color rowHover: dark ? Qt.rgba(1,1,1,0.04) : Qt.rgba(0,0,0,0.04)
    readonly property color separator: dark ? Qt.rgba(1,1,1,0.08) : Qt.rgba(0,0,0,0.08)
    readonly property color fieldBg: dark ? "#1F1F22" : "#FFFFFF"
    readonly property color fieldBorder: dark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.15)
    readonly property color textMain: dark ? "#F5F5F7" : "#1D1D1F"
    readonly property color textMuted: dark ? "#9B9BA0" : "#86868B"
    readonly property color textFaint: dark ? "#6B6B70" : "#A1A1A6"
    readonly property color accent: dark ? "#0A84FF" : "#007AFF"
    readonly property color accentText: "#FFFFFF"
    readonly property color danger: dark ? "#FF453A" : "#FF3B30"
    readonly property color success: dark ? "#30D158" : "#34C759"
    readonly property color warning: dark ? "#FFD60A" : "#FF9F0A"
    readonly property string sfFont: Qt.platform.os === "osx" ? "SF Pro Text" : "Helvetica Neue"
    readonly property string sfMono: Qt.platform.os === "osx" ? "SF Mono" : "Menlo"

    function statusColor(status) {
        if (status === "success") return success
        if (status === "failed" || status === "timeout" || status === "error") return danger
        return textMuted
    }

    function kindLabel(action) {
        if (!action) return ""
        if (action.kind === "open_path") return "打开路径"
        if (action.kind === "open_url") return "打开链接"
        return ({
            shell: "Shell",
            node: "Node",
            python: "Python",
            other: "脚本"
        })[action.scriptType] || "脚本"
    }

    function kindIcon(action) {
        if (!action) return "⏵"
        if (action.kind === "open_path") return "📁"
        if (action.kind === "open_url") return "🌐"
        return ({
            shell: "⌘",
            node: "⬢",
            python: "🐍",
            other: "⚙"
        })[action.scriptType] || "⏵"
    }

    function feedbackLabel(mode) {
        return ({ silent: "静默", popup: "弹窗", notification: "通知" })[mode] || mode
    }

    Component.onCompleted: {
        if (vm && vm.initialMode === "form" && vm.pendingActionId > 0) {
            parameterSheet.openFor(vm.pendingActionId)
        }
    }

    Connections {
        target: vm
        ignoreUnknownSignals: true
        function onPendingActionChanged() {
            if (vm.pendingActionId > 0 && !parameterSheet.visible) {
                parameterSheet.openFor(vm.pendingActionId)
            }
        }
        function onPopupResult(payload) {
            resultSheet.openWith(payload)
        }
        function onFeedbackMessageChanged() {
            if (vm.feedbackMessage) {
                toast.show(vm.feedbackMessage)
            }
        }
    }

    Rectangle { anchors.fill: parent; color: pageBg }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        // ---- Title bar ----
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: pageBg
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 14
                spacing: 12

                Label {
                    text: "快速启动"
                    color: textMain
                    font.family: sfFont
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    Layout.preferredWidth: 240
                    Layout.preferredHeight: 28
                    radius: 7
                    color: fieldBg
                    border.color: fieldBorder
                    border.width: 1
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6
                        Label { text: "🔍"; color: textMuted; font.pixelSize: 12 }
                        TextField {
                            id: searchField
                            Layout.fillWidth: true
                            placeholderText: "搜索动作"
                            font.family: sfFont
                            font.pixelSize: 12
                            color: textMain
                            placeholderTextColor: textFaint
                            background: Item {}
                            selectByMouse: true
                            onTextChanged: vm && vm.setSearchQuery(text)
                        }
                    }
                }

                MacButton {
                    text: "  + 新建动作  "
                    variant: "primary"
                    onClicked: actionSheet.openCreate()
                }
            }
            Rectangle {
                width: parent.width; height: 1
                anchors.bottom: parent.bottom
                color: separator
            }
        }

        // ---- Action list ----
        ListView {
            id: actionList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 0
            model: vm ? vm.actions : []
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Rectangle {
                required property var modelData
                required property int index
                width: ListView.view.width
                height: 64
                color: rowMouse.containsMouse ? rowHover : "transparent"

                Rectangle {
                    width: parent.width
                    height: 1
                    color: separator
                    anchors.bottom: parent.bottom
                    visible: index < actionList.count - 1
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 14
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 36
                        radius: 8
                        color: modelData.enabled ? Qt.rgba(0.039, 0.518, 1, dark ? 0.22 : 0.12) : Qt.rgba(0,0,0, dark ? 0.18 : 0.05)
                        Label {
                            anchors.centerIn: parent
                            text: kindIcon(modelData)
                            color: modelData.enabled ? accent : textMuted
                            font.pixelSize: 18
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        RowLayout {
                            spacing: 8
                            Label {
                                text: modelData.name || "(未命名)"
                                color: modelData.enabled ? textMain : textMuted
                                font.family: sfFont
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                elide: Label.ElideRight
                                Layout.fillWidth: true
                            }
                            MacChip { text: kindLabel(modelData); chipColor: separator; textColor: textMuted }
                            MacChip {
                                visible: modelData.feedbackMode && modelData.feedbackMode !== "notification"
                                text: feedbackLabel(modelData.feedbackMode)
                                chipColor: separator
                                textColor: textMuted
                            }
                            MacChip {
                                visible: !modelData.enabled
                                text: "已停用"
                                chipColor: Qt.rgba(0.5,0.5,0.5,0.18)
                                textColor: textMuted
                            }
                        }
                        Label {
                            text: subtitleFor(modelData)
                            color: textMuted
                            font.family: sfMono
                            font.pixelSize: 11
                            elide: Label.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    MacButton {
                        text: "  ▶ 运行  "
                        variant: "primary"
                        onClicked: vm && vm.runNow(modelData.id)
                    }
                    MacButton {
                        text: "  编辑  "
                        onClicked: actionSheet.openEdit(modelData)
                    }
                    MacIconButton {
                        text: "⋯"
                        onClicked: actionMenu.openFor(modelData)
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }

            Label {
                anchors.centerIn: parent
                visible: !vm || vm.actions.length === 0
                text: vm && vm.searchQuery ? "没有匹配的动作" : "还没有动作\n点击右上角“新建动作”开始"
                horizontalAlignment: Text.AlignHCenter
                color: textMuted
                font.family: sfFont
                font.pixelSize: 13
            }
        }
    }

    // ---- Action context menu (more options) ----
    Menu {
        id: actionMenu
        property var current: null
        function openFor(action) {
            current = action
            popup()
        }
        MenuItem {
            text: actionMenu.current && actionMenu.current.enabled ? "停用" : "启用"
            onTriggered: if (vm && actionMenu.current) vm.setActionEnabled(actionMenu.current.id, !actionMenu.current.enabled)
        }
        MenuItem {
            text: "复制"
            onTriggered: if (vm && actionMenu.current) vm.duplicateAction(actionMenu.current.id)
        }
        MenuItem {
            text: "查看运行历史"
            onTriggered: if (actionMenu.current) historySheet.openFor(actionMenu.current.id, actionMenu.current.name)
        }
        MenuSeparator {}
        MenuItem {
            text: "删除"
            onTriggered: if (actionMenu.current) confirmSheet.openFor(actionMenu.current.id, actionMenu.current.name)
        }
    }

    // ---- Edit / Create sheet ----
    MacSheet {
        id: actionSheet
        title: editingId > 0 ? "编辑动作" : "新建动作"
        width: 540
        height: Math.min(root.height - 60, 660)

        property int editingId: 0

        contentItem: Flickable {
            contentWidth: width
            contentHeight: editForm.implicitHeight + 40
            clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: editForm
                x: 24
                width: parent.width - 48
                spacing: 14
                y: 12

                MacFormRow {
                    label: "名称"
                    MacTextField {
                        id: fName
                        Layout.fillWidth: true
                        placeholderText: "为该动作起一个名字"
                    }
                }

                MacFormRow {
                    label: "类型"
                    MacSegmented {
                        id: fKind
                        Layout.fillWidth: true
                        options: ["脚本", "打开路径", "打开链接"]
                        keys: ["script", "open_path", "open_url"]
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script"
                    label: "脚本类型"
                    MacSegmented {
                        id: fScriptType
                        Layout.fillWidth: true
                        options: ["Shell", "Node", "Python", "其他"]
                        keys: ["shell", "node", "python", "other"]
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script" && fScriptType.currentKey === "other"
                    label: "解释器"
                    MacTextField {
                        id: fInterpreter
                        Layout.fillWidth: true
                        placeholderText: "如 /opt/homebrew/bin/ruby"
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script" || fKind.currentKey === "open_path"
                    label: fKind.currentKey === "script" ? "脚本路径" : "目标路径"
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        MacTextField {
                            id: fPath
                            Layout.fillWidth: true
                            placeholderText: "/path/to/file"
                        }
                        MacButton {
                            text: "  选择…  "
                            onClicked: {
                                if (!vm) return
                                var picked = vm.pickScriptFile()
                                if (picked) fPath.text = picked
                            }
                        }
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script"
                    label: "运行参数"
                    MacTextField {
                        id: fArgs
                        Layout.fillWidth: true
                        placeholderText: "如：--env prod ${branch}"
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "open_url"
                    label: "URL"
                    MacTextField {
                        id: fUrl
                        Layout.fillWidth: true
                        placeholderText: "https://example.com"
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script"
                    label: "工作目录"
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        MacTextField {
                            id: fCwd
                            Layout.fillWidth: true
                            placeholderText: "可选，默认使用当前目录"
                        }
                        MacButton {
                            text: "  选择…  "
                            onClicked: {
                                if (!vm) return
                                var picked = vm.pickDirectory()
                                if (picked) fCwd.text = picked
                            }
                        }
                    }
                }

                MacFormRow {
                    label: "反馈方式"
                    MacSegmented {
                        id: fFeedback
                        Layout.fillWidth: true
                        options: ["静默", "弹窗", "通知"]
                        keys: ["silent", "popup", "notification"]
                    }
                }

                MacFormRow {
                    label: "关键词"
                    MacTextField {
                        id: fKeywords
                        Layout.fillWidth: true
                        placeholderText: "逗号分隔，便于搜索"
                    }
                }

                MacFormRow {
                    label: "前缀"
                    MacTextField {
                        id: fPrefixes
                        Layout.fillWidth: true
                        placeholderText: "逗号分隔，如 g, build"
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script"
                    label: "超时"
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        SpinBox {
                            id: fTimeout
                            from: 0; to: 86400; value: 300
                            font.family: sfFont
                            font.pixelSize: 12
                        }
                        Label {
                            text: "秒，0 表示不超时"
                            color: textFaint
                            font.family: sfFont
                            font.pixelSize: 11
                        }
                    }
                }

                MacFormRow {
                    visible: fKind.currentKey === "script"
                    label: "环境变量"
                    MacTextArea {
                        id: fEnv
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        placeholderText: "KEY=VAL，每行一个"
                    }
                }

                MacFormRow {
                    label: "描述"
                    MacTextField {
                        id: fDesc
                        Layout.fillWidth: true
                        placeholderText: "可选"
                    }
                }

                MacFormRow {
                    label: "启用"
                    Switch {
                        id: fEnabled
                        checked: true
                    }
                }

                Label {
                    visible: fKind.currentKey === "script"
                    text: "提示：在路径、参数、cwd、URL 中使用 ${name} 声明运行时参数。"
                    color: textFaint
                    font.family: sfFont
                    font.pixelSize: 11
                    wrapMode: Label.Wrap
                    Layout.fillWidth: true
                }
            }
        }

        function openCreate() {
            editingId = 0
            fName.text = ""
            fDesc.text = ""
            fPath.text = ""
            fUrl.text = ""
            fArgs.text = ""
            fCwd.text = ""
            fInterpreter.text = ""
            fKeywords.text = ""
            fPrefixes.text = ""
            fEnv.text = ""
            fTimeout.value = 300
            fEnabled.checked = true
            fKind.currentIndex = 0
            fScriptType.currentIndex = 0
            fFeedback.currentIndex = 2
            open()
        }

        function openEdit(a) {
            editingId = a.id
            fName.text = a.name || ""
            fDesc.text = a.description || ""
            fPath.text = a.path || ""
            fUrl.text = a.url || ""
            fArgs.text = a.args || ""
            fCwd.text = a.cwd || ""
            fInterpreter.text = a.interpreter || ""
            fKeywords.text = (a.keywords || []).join(", ")
            fPrefixes.text = (a.prefixes || []).join(", ")
            fTimeout.value = a.timeoutSec || 0
            fEnabled.checked = !!a.enabled
            fKind.setKey(a.kind || "script")
            fScriptType.setKey(a.scriptType || "shell")
            fFeedback.setKey(a.feedbackMode || "notification")
            var envText = ""
            var env = a.env || {}
            for (var key in env) envText += key + "=" + env[key] + "\n"
            fEnv.text = envText.trim()
            open()
        }

        function _parseEnv(text) {
            var env = {}
            var lines = (text || "").split(/[\n;]/)
            for (var i = 0; i < lines.length; ++i) {
                var line = lines[i].trim()
                if (!line) continue
                var eq = line.indexOf("=")
                if (eq <= 0) continue
                env[line.substring(0, eq).trim()] = line.substring(eq + 1).trim()
            }
            return env
        }

        function _collectPayload() {
            return {
                name: fName.text,
                description: fDesc.text,
                kind: fKind.currentKey,
                scriptType: fScriptType.currentKey,
                interpreter: fInterpreter.text,
                path: fPath.text,
                url: fUrl.text,
                args: fArgs.text,
                cwd: fCwd.text,
                keywords: fKeywords.text,
                prefixes: fPrefixes.text,
                feedbackMode: fFeedback.currentKey,
                timeoutSec: fTimeout.value,
                enabled: fEnabled.checked,
                env: _parseEnv(fEnv.text)
            }
        }

        primaryText: editingId > 0 ? "保存" : "创建"
        onAccepted: {
            if (!vm) return
            var payload = _collectPayload()
            if (editingId > 0) vm.updateAction(editingId, payload)
            else vm.createAction(payload)
        }
    }

    // ---- Parameter form sheet ----
    MacSheet {
        id: parameterSheet
        title: "填写参数"
        width: 460
        height: 60 + paramColumn.implicitHeight + 80
        property int actionId: 0
        property var paramNames: []
        property var values: ({})

        contentItem: Item {
            ColumnLayout {
                id: paramColumn
                anchors.top: parent.top
                anchors.topMargin: 16
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 10

                Label {
                    text: parameterSheet.paramNames.length === 0 ? "该动作不需要参数" : "请填写下列参数后执行"
                    color: textMuted
                    font.family: sfFont
                    font.pixelSize: 12
                    Layout.fillWidth: true
                }

                Repeater {
                    id: paramRepeater
                    model: parameterSheet.paramNames
                    delegate: MacFormRow {
                        required property string modelData
                        label: modelData
                        MacTextField {
                            id: paramField
                            Layout.fillWidth: true
                            placeholderText: "${" + modelData + "}"
                            onTextChanged: parameterSheet.values[modelData] = text
                        }
                    }
                }
            }
        }

        function openFor(actionId) {
            parameterSheet.actionId = actionId
            var params = vm ? vm.parametersOf(actionId) : []
            var names = []
            for (var i = 0; i < params.length; ++i) names.push(params[i].name)
            parameterSheet.paramNames = names
            parameterSheet.values = {}
            open()
        }

        primaryText: "执行"
        onAccepted: {
            if (!vm) return
            var result = vm.runWithParameters(parameterSheet.actionId, values)
            if (result && result.status === "needsParameters") open()
        }
        onCancelled: if (vm) vm.clearPending()
    }

    // ---- Result popup sheet ----
    MacSheet {
        id: resultSheet
        title: "执行结果"
        width: 600
        height: 480
        property var resultData: ({})

        contentItem: Flickable {
            contentWidth: width
            contentHeight: resultColumn.implicitHeight + 40
            clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            ColumnLayout {
                id: resultColumn
                x: 24
                y: 12
                width: parent.width - 48
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        width: 28; height: 28; radius: 14
                        color: resultSheet.resultData.ok ? Qt.rgba(0.18, 0.78, 0.35, 0.18) : Qt.rgba(1, 0.23, 0.18, 0.18)
                        Label {
                            anchors.centerIn: parent
                            text: resultSheet.resultData.ok ? "✓" : "!"
                            color: resultSheet.resultData.ok ? success : danger
                            font.pixelSize: 16
                            font.bold: true
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label {
                            text: resultSheet.resultData.actionName || ""
                            color: textMain
                            font.family: sfFont
                            font.pixelSize: 14
                            font.weight: Font.Medium
                        }
                        Label {
                            text: {
                                var parts = [resultSheet.resultData.status || ""]
                                if (resultSheet.resultData.exitCode !== undefined && resultSheet.resultData.exitCode !== null) parts.push("exit " + resultSheet.resultData.exitCode)
                                parts.push((resultSheet.resultData.durationMs || 0) + "ms")
                                return parts.join("  ·  ")
                            }
                            color: textMuted
                            font.family: sfFont
                            font.pixelSize: 11
                        }
                    }
                }

                Label {
                    visible: resultSheet.resultData.message && resultSheet.resultData.message.length > 0
                    text: resultSheet.resultData.message || ""
                    color: textMuted
                    font.family: sfFont
                    font.pixelSize: 11
                    wrapMode: Label.Wrap
                    Layout.fillWidth: true
                }

                Label {
                    text: "stdout"
                    color: textFaint
                    font.family: sfFont
                    font.pixelSize: 11
                    font.weight: Font.Medium
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 140
                    radius: 8
                    color: fieldBg
                    border.color: fieldBorder
                    border.width: 1
                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 8
                        contentWidth: width - 16
                        contentHeight: stdoutText.implicitHeight
                        clip: true
                        ScrollBar.vertical: ScrollBar {}
                        Label {
                            id: stdoutText
                            width: parent.width
                            text: resultSheet.resultData.stdout || "(空)"
                            color: textMain
                            font.family: sfMono
                            font.pixelSize: 11
                            wrapMode: Label.Wrap
                        }
                    }
                }

                Label {
                    text: "stderr"
                    color: textFaint
                    font.family: sfFont
                    font.pixelSize: 11
                    font.weight: Font.Medium
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    radius: 8
                    color: fieldBg
                    border.color: fieldBorder
                    border.width: 1
                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 8
                        contentWidth: width - 16
                        contentHeight: stderrText.implicitHeight
                        clip: true
                        ScrollBar.vertical: ScrollBar {}
                        Label {
                            id: stderrText
                            width: parent.width
                            text: resultSheet.resultData.stderr || "(空)"
                            color: resultSheet.resultData.ok ? textMuted : danger
                            font.family: sfMono
                            font.pixelSize: 11
                            wrapMode: Label.Wrap
                        }
                    }
                }
            }
        }

        function openWith(payload) {
            resultData = payload
            open()
        }

        primaryText: "完成"
        showCancel: false
    }

    // ---- Run history sheet ----
    MacSheet {
        id: historySheet
        title: targetName ? "运行历史 · " + targetName : "运行历史"
        width: 560
        height: 460
        property int actionId: 0
        property string targetName: ""

        contentItem: ListView {
            anchors.fill: parent
            anchors.margins: 12
            clip: true
            spacing: 8
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: vm ? (vm.runs || []).filter(function(r) { return historySheet.actionId <= 0 || r.actionId === historySheet.actionId }) : []
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: histContent.implicitHeight + 16
                radius: 8
                color: surfaceBg
                border.color: separator
                border.width: 1
                ColumnLayout {
                    id: histContent
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        MacChip {
                            text: modelData.status
                            chipColor: Qt.rgba(0,0,0, dark ? 0.18 : 0.06)
                            textColor: statusColor(modelData.status)
                        }
                        Label {
                            text: modelData.exitCode !== undefined && modelData.exitCode !== null ? "exit " + modelData.exitCode : ""
                            color: textMuted
                            font.family: sfMono
                            font.pixelSize: 11
                        }
                        Label {
                            text: (modelData.durationMs || 0) + "ms"
                            color: textMuted
                            font.family: sfFont
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }
                        Label {
                            text: modelData.startedAt
                            color: textFaint
                            font.family: sfFont
                            font.pixelSize: 10
                        }
                    }
                    Label {
                        visible: modelData.message && modelData.message.length > 0
                        Layout.fillWidth: true
                        text: modelData.message
                        color: textMuted
                        font.family: sfFont
                        font.pixelSize: 11
                        wrapMode: Label.Wrap
                    }
                    Label {
                        visible: modelData.stderr && modelData.stderr.length > 0
                        Layout.fillWidth: true
                        text: modelData.stderr.substring(0, 600)
                        color: danger
                        font.family: sfMono
                        font.pixelSize: 11
                        wrapMode: Label.Wrap
                    }
                    Label {
                        visible: modelData.stdout && modelData.stdout.length > 0
                        Layout.fillWidth: true
                        text: modelData.stdout.substring(0, 600)
                        color: textMain
                        font.family: sfMono
                        font.pixelSize: 11
                        wrapMode: Label.Wrap
                    }
                }
            }
        }

        function openFor(actionId, name) {
            historySheet.actionId = actionId
            historySheet.targetName = name || ""
            if (vm) vm.refreshRuns()
            open()
        }

        primaryText: "关闭"
        showCancel: false
    }

    // ---- Confirm delete ----
    MacSheet {
        id: confirmSheet
        title: "删除动作"
        width: 400
        height: 180
        property int targetId: 0
        property string targetName: ""

        contentItem: Item {
            Label {
                anchors.fill: parent
                anchors.margins: 24
                wrapMode: Label.Wrap
                verticalAlignment: Text.AlignVCenter
                text: "确定要删除动作 “" + confirmSheet.targetName + "” 吗？此操作不可撤销。"
                color: textMain
                font.family: sfFont
                font.pixelSize: 12
            }
        }
        function openFor(id, name) { targetId = id; targetName = name || ""; open() }
        primaryText: "删除"
        primaryDanger: true
        onAccepted: if (vm && targetId > 0) vm.deleteAction(targetId)
    }

    // ---- Toast ----
    Rectangle {
        id: toast
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 20
        width: Math.min(parent.width - 80, toastLabel.implicitWidth + 40)
        height: 34
        radius: 17
        color: dark ? "#3A3A3C" : "#1D1D1F"
        opacity: 0
        property string text: ""
        function show(t) { text = t; opacity = 0.96; hideTimer.restart() }
        Label {
            id: toastLabel
            anchors.centerIn: parent
            text: toast.text
            color: "#FFFFFF"
            font.family: sfFont
            font.pixelSize: 12
        }
        Behavior on opacity { NumberAnimation { duration: 200 } }
        Timer { id: hideTimer; interval: 2400; onTriggered: toast.opacity = 0 }
    }

    function subtitleFor(action) {
        if (!action) return ""
        if (action.kind === "open_url") return action.url || ""
        if (action.kind === "open_path") return action.path || ""
        var bits = []
        if (action.path) bits.push(action.path)
        if (action.args) bits.push(action.args)
        return bits.join("  ") || (action.description || "")
    }

    // ====== Mini macOS-styled components ======

    component MacButton: Button {
        id: btn
        property string variant: "secondary"
        property bool danger: false
        implicitHeight: 28
        padding: 0
        font.family: sfFont
        font.pixelSize: 12
        background: Rectangle {
            radius: 6
            color: btn.variant === "primary"
                ? (btn.down ? Qt.darker(accent, 1.1) : (btn.hovered ? Qt.lighter(accent, 1.05) : accent))
                : (btn.danger
                    ? (btn.hovered ? Qt.rgba(1, 0.23, 0.18, 0.16) : "transparent")
                    : (btn.down ? Qt.rgba(0,0,0,0.08) : (btn.hovered ? rowHover : fieldBg)))
            border.color: btn.variant === "primary" ? "transparent" : fieldBorder
            border.width: btn.variant === "primary" ? 0 : 1
        }
        contentItem: Label {
            text: btn.text
            color: btn.variant === "primary" ? accentText : (btn.danger ? danger : textMain)
            font: btn.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component MacIconButton: Button {
        id: ibtn
        implicitWidth: 28
        implicitHeight: 28
        padding: 0
        font.family: sfFont
        font.pixelSize: 16
        background: Rectangle {
            radius: 6
            color: ibtn.down ? Qt.rgba(0,0,0,0.08) : (ibtn.hovered ? rowHover : "transparent")
        }
        contentItem: Label {
            text: ibtn.text
            color: textMuted
            font: ibtn.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component MacChip: Rectangle {
        id: chip
        property string text: ""
        property color chipColor: separator
        property color textColor: textMuted
        implicitWidth: chipLabel.implicitWidth + 12
        implicitHeight: 18
        radius: 9
        color: chipColor
        Label {
            id: chipLabel
            anchors.centerIn: parent
            text: chip.text
            color: chip.textColor
            font.family: sfFont
            font.pixelSize: 10
            font.weight: Font.Medium
        }
    }

    component MacTextField: TextField {
        id: tf
        implicitHeight: 28
        font.family: sfFont
        font.pixelSize: 12
        color: textMain
        placeholderTextColor: textFaint
        selectByMouse: true
        leftPadding: 8
        rightPadding: 8
        background: Rectangle {
            radius: 6
            color: fieldBg
            border.color: tf.activeFocus ? accent : fieldBorder
            border.width: 1
        }
    }

    component MacTextArea: ScrollView {
        id: ta
        property alias text: textArea.text
        property alias placeholderText: textArea.placeholderText
        TextArea {
            id: textArea
            font.family: sfFont
            font.pixelSize: 12
            color: textMain
            placeholderTextColor: textFaint
            selectByMouse: true
            wrapMode: TextArea.Wrap
            background: Rectangle {
                radius: 6
                color: fieldBg
                border.color: textArea.activeFocus ? accent : fieldBorder
                border.width: 1
            }
        }
    }

    component MacFormRow: RowLayout {
        property string label: ""
        Layout.fillWidth: true
        spacing: 10
        Label {
            text: parent.label
            color: textMuted
            font.family: sfFont
            font.pixelSize: 12
            Layout.preferredWidth: 80
            horizontalAlignment: Text.AlignRight
        }
    }

    component MacSegmented: Rectangle {
        id: seg
        property var options: []
        property var keys: []
        property int currentIndex: 0
        readonly property string currentKey: keys.length > currentIndex ? keys[currentIndex] : ""
        function setKey(k) {
            for (var i = 0; i < keys.length; ++i) if (keys[i] === k) { currentIndex = i; return }
            currentIndex = 0
        }
        implicitHeight: 28
        radius: 7
        color: dark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.06)

        Row {
            anchors.fill: parent
            anchors.margins: 2
            spacing: 0
            Repeater {
                model: seg.options
                delegate: Item {
                    required property string modelData
                    required property int index
                    width: seg.width / seg.options.length - (seg.options.length > 1 ? (4 / seg.options.length) : 0)
                    height: seg.height - 4
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: 5
                        color: seg.currentIndex === index ? surfaceBg : "transparent"
                        border.width: 0
                    }
                    Label {
                        anchors.centerIn: parent
                        text: modelData
                        color: seg.currentIndex === index ? textMain : textMuted
                        font.family: sfFont
                        font.pixelSize: 11
                        font.weight: seg.currentIndex === index ? Font.Medium : Font.Normal
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: seg.currentIndex = index
                    }
                }
            }
        }
    }

    component MacSheet: Popup {
        id: sheet
        anchors.centerIn: parent
        modal: true
        dim: true
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.4) }
        padding: 0
        focus: true
        closePolicy: Popup.CloseOnEscape
        background: Rectangle {
            radius: 12
            color: sheetBg
            border.color: separator
            border.width: 1
        }

        property string title: ""
        property string primaryText: "确定"
        property bool primaryDanger: false
        property bool showCancel: true
        property Item contentItem
        signal accepted()
        signal cancelled()

        onAboutToHide: cancelled()

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Title bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: "transparent"
                Label {
                    anchors.centerIn: parent
                    text: sheet.title
                    color: textMain
                    font.family: sfFont
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }
                Rectangle {
                    width: parent.width; height: 1
                    anchors.bottom: parent.bottom
                    color: separator
                }
            }

            // Slot for contentItem
            Item {
                id: contentHolder
                Layout.fillWidth: true
                Layout.fillHeight: true
                children: sheet.contentItem ? [sheet.contentItem] : []
                onChildrenChanged: {
                    for (var i = 0; i < children.length; ++i) {
                        children[i].anchors.fill = contentHolder
                    }
                }
            }

            // Footer
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                color: dark ? Qt.rgba(0,0,0,0.18) : Qt.rgba(0,0,0,0.03)
                Rectangle {
                    width: parent.width; height: 1
                    color: separator
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 8
                    Item { Layout.fillWidth: true }
                    MacButton {
                        visible: sheet.showCancel
                        text: "  取消  "
                        onClicked: { sheet.close() }
                    }
                    MacButton {
                        text: "  " + sheet.primaryText + "  "
                        variant: sheet.primaryDanger ? "secondary" : "primary"
                        danger: sheet.primaryDanger
                        onClicked: { sheet.accepted(); sheet.close() }
                    }
                }
            }
        }
    }
}
