import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    property var historyItems: []
    property var selectedItem: ({})
    property int selectedIndex: -1
    property string statusText: ""
    property bool captureTextEnabled: true
    property bool captureImageEnabled: true
    property bool captureFilesEnabled: true
    readonly property int historyRowHeight: 68
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelAlt: Theme.token("color-bg-subtle-2", dark)
    readonly property color softBg: Theme.token("color-bg-subtle", dark)
    readonly property color border: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    function selectItem(item, idx) {
        selectedItem = item || ({})
        selectedIndex = idx
        historyList.currentIndex = selectedIndex
    }

    function refreshSelection() {
        if (historyItems.length === 0) {
            selectItem({}, -1)
            return
        }
        if (selectedIndex < 0 || selectedIndex >= historyItems.length) {
            selectItem(historyItems[0], 0)
            return
        }
        selectItem(historyItems[selectedIndex], selectedIndex)
    }

    function moveSelection(delta) {
        if (tabs.currentIndex !== 0 || historyItems.length === 0) {
            return false
        }
        var nextIndex = selectedIndex < 0 ? 0 : selectedIndex + delta
        nextIndex = Math.max(0, Math.min(historyItems.length - 1, nextIndex))
        selectItem(historyItems[nextIndex], nextIndex)
        historyList.positionViewAtIndex(nextIndex, ListView.Contain)
        return true
    }

    function activateSelection() {
        if (tabs.currentIndex !== 0 || selectedIndex < 0 || !selectedItem.id) {
            return false
        }
        clipboardVm.copyItem(String(selectedItem.id || ""))
        launcherBridge.hideLauncher()
        return true
    }

    Component.onCompleted: {
        clipboardVm.refreshHistory(clipboardVm.initialQuery())
        clipboardVm.loadConfig()
        tabs.currentIndex = clipboardVm.initialPanel() === "settings" ? 1 : 0
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.token("color-bg-page", dark)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            spacing: 8

            Label {
                text: "剪切板"
                font.pixelSize: 20
                font.bold: true
                font.family: "IBM Plex Sans"
                color: textMain
            }

            Label {
                Layout.fillWidth: true
                text: statusText
                elide: Text.ElideRight
                color: textMuted
                font.pixelSize: 12
            }

            TabBar {
                id: tabs
                Layout.preferredWidth: 240
                Layout.preferredHeight: 34

                TabButton { text: "历史" }
                TabButton { text: "设置" }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            RowLayout {
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 330
                    Layout.fillHeight: true
                    radius: 8
                    color: panelBg
                    border.color: border

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        ListView {
                            id: historyList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 4
                            model: historyItems
                            currentIndex: selectedIndex

                            delegate: Rectangle {
                                id: row

                                width: ListView.view.width
                                height: root.historyRowHeight
                                radius: 6
                                color: index === selectedIndex ? softBg : "transparent"
                                border.color: "transparent"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 44
                                        Layout.preferredHeight: 44
                                        Layout.alignment: Qt.AlignVCenter
                                        radius: 8
                                        color: Theme.token("color-primary-bg", dark)
                                        clip: true

                                        UiIcon {
                                            visible: modelData.itemType !== "image" || !modelData.imageUrl
                                            anchors.centerIn: parent
                                            width: 20
                                            height: 20
                                            name: String(modelData.icon || "").replace("qta:", "")
                                            color: Theme.token("color-primary", dark)
                                            iconSize: 20
                                        }

                                        Image {
                                            visible: modelData.itemType === "image" && !!modelData.imageUrl
                                            anchors.fill: parent
                                            source: modelData.imageUrl || ""
                                            sourceSize.width: 88
                                            sourceSize.height: 88
                                            fillMode: Image.PreserveAspectCrop
                                            smooth: true
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 3

                                        RowLayout {
                                            Layout.fillWidth: true

                                            Label {
                                                Layout.fillWidth: true
                                                text: modelData.title || ""
                                                color: textMain
                                                font.pixelSize: 13
                                                elide: Text.ElideRight
                                            }

                                            Label {
                                                visible: !!modelData.pinned
                                                text: "置顶"
                                                color: Theme.token("color-primary", dark)
                                                font.pixelSize: 10
                                            }
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: (modelData.subtitle || modelData.typeLabel || "") + " · " + (modelData.createdAt || "")
                                            color: textMuted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: selectItem(modelData, index)
                                    onDoubleClicked: root.activateSelection()
                                }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: historyList.count === 0
                                text: "暂无历史"
                                color: textMuted
                                font.pixelSize: 13
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: panelBg
                    border.color: border

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Label {
                                    text: selectedItem.title || "未选择"
                                    color: textMain
                                    font.pixelSize: 15
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: selectedItem.typeLabel ? (selectedItem.typeLabel + " · " + selectedItem.createdAt) : "选择左侧历史项查看详情"
                                    color: textMuted
                                    font.pixelSize: 11
                                }
                            }

                            UiButton {
                                Layout.preferredWidth: 76
                                text: selectedItem.pinned ? "取消置顶" : "置顶"
                                dark: root.dark
                                enabled: selectedIndex >= 0
                                onClicked: clipboardVm.togglePin(String(selectedItem.id || ""))
                            }

                            UiButton {
                                Layout.preferredWidth: 64
                                text: "复制"
                                variant: "primary"
                                dark: root.dark
                                enabled: selectedIndex >= 0
                                onClicked: {
                                    clipboardVm.copyItem(String(selectedItem.id || ""))
                                    launcherBridge.hideLauncher()
                                }
                            }

                            UiButton {
                                Layout.preferredWidth: 64
                                text: "删除"
                                dark: root.dark
                                enabled: selectedIndex >= 0
                                onClicked: clipboardVm.deleteItem(String(selectedItem.id || ""))
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 8
                            color: panelAlt
                            border.color: border

                            Item {
                                anchors.fill: parent
                                anchors.margins: 10

                                TextArea {
                                    visible: selectedItem.itemType !== "image"
                                    anchors.fill: parent
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    text: selectedItem.detail || ""
                                    color: textMain
                                    selectedTextColor: textMain
                                    selectionColor: Theme.token("color-primary-bg", dark)
                                    font.pixelSize: 12
                                    font.family: selectedItem.itemType === "text" ? "JetBrains Mono" : "IBM Plex Sans"
                                    background: null
                                }

                                Image {
                                    visible: selectedItem.itemType === "image"
                                    anchors.fill: parent
                                    source: selectedItem.imageUrl || ""
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28

                            Label {
                                Layout.fillWidth: true
                                text: "双击左侧历史项也可以复制"
                                color: textMuted
                                font.pixelSize: 11
                            }

                            UiButton {
                                Layout.preferredWidth: 90
                                text: "清空历史"
                                dark: root.dark
                                onClicked: clipboardVm.clearHistory()
                            }
                        }
                    }
                }
            }

            Flickable {
                clip: true
                contentWidth: width
                contentHeight: settingsColumn.implicitHeight

                ColumnLayout {
                    id: settingsColumn
                    width: parent.width
                    spacing: 10

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 156
                        radius: 8
                        color: panelBg
                        border.color: border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10

                            Label {
                                text: "记录类型"
                                color: textMain
                                font.pixelSize: 15
                                font.bold: true
                            }

                            SettingSwitch {
                                label: "文本"
                                checked: root.captureTextEnabled
                                onToggled: function(value) {
                                    root.captureTextEnabled = value
                                    clipboardVm.setCaptureText(value)
                                }
                            }

                            SettingSwitch {
                                label: "图片"
                                checked: root.captureImageEnabled
                                onToggled: function(value) {
                                    root.captureImageEnabled = value
                                    clipboardVm.setCaptureImage(value)
                                }
                            }

                            SettingSwitch {
                                label: "文件"
                                checked: root.captureFilesEnabled
                                onToggled: function(value) {
                                    root.captureFilesEnabled = value
                                    clipboardVm.setCaptureFiles(value)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 250
                        radius: 8
                        color: panelBg
                        border.color: border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Label {
                                text: "过滤与限制"
                                color: textMain
                                font.pixelSize: 15
                                font.bold: true
                            }

                            Label {
                                text: "过滤规则"
                                color: textMuted
                                font.pixelSize: 12
                            }

                            TextArea {
                                id: ignorePatternsInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 86
                                wrapMode: TextEdit.Wrap
                                color: textMain
                                placeholderText: "关键词或正则，用 | 或换行分隔"
                                placeholderTextColor: textMuted
                                font.pixelSize: 12
                                background: Rectangle {
                                    radius: 8
                                    color: panelAlt
                                    border.color: border
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "文本长度上限"
                                    color: textMuted
                                    font.pixelSize: 12
                                }
                                UiTextField {
                                    id: maxCharsInput
                                    Layout.preferredWidth: 140
                                    dark: root.dark
                                    placeholderText: "20000"
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: "0 表示不限制"
                                    color: textMuted
                                    font.pixelSize: 11
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                UiButton {
                                    text: "保存过滤"
                                    dark: root.dark
                                    variant: "primary"
                                    onClicked: {
                                        clipboardVm.saveIgnorePatterns(ignorePatternsInput.text)
                                        clipboardVm.saveMaxTextChars(maxCharsInput.text)
                                    }
                                }
                                UiButton {
                                    text: "清空过滤"
                                    dark: root.dark
                                    onClicked: clipboardVm.clearIgnorePatterns()
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 116
                        radius: 8
                        color: panelBg
                        border.color: border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Label {
                                text: "快捷键"
                                color: textMain
                                font.pixelSize: 15
                                font.bold: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                UiTextField {
                                    id: hotkeyInput
                                    Layout.preferredWidth: 180
                                    dark: root.dark
                                    placeholderText: "Alt+V"
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: "用于直接打开剪切板窗口"
                                    color: textMuted
                                    font.pixelSize: 12
                                }
                                UiButton {
                                    Layout.preferredWidth: 84
                                    text: "保存"
                                    variant: "primary"
                                    dark: root.dark
                                    onClicked: clipboardVm.saveHotkey(hotkeyInput.text)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    component SettingSwitch: RowLayout {
        property string label: ""
        property bool checked: false
        signal toggled(bool value)

        Layout.fillWidth: true

        Label {
            Layout.fillWidth: true
            text: label
            color: textMain
            font.pixelSize: 13
        }

        Rectangle {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 20
            radius: 10
            color: parent.checked
                ? Theme.token("color-primary-active", root.dark)
                : Theme.token("color-bg-subtle", root.dark)
            border.width: 1
            border.color: parent.checked
                ? Theme.token("color-primary-active", root.dark)
                : Theme.token("color-border-default", root.dark)

            Rectangle {
                width: 16
                height: 16
                radius: 8
                y: 2
                x: parent.parent.checked ? parent.width - width - 2 : 2
                color: "#FFFFFF"
                border.width: 1
                border.color: Qt.rgba(0, 0, 0, 0.08)

                Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: parent.parent.toggled(!parent.parent.checked)
            }
        }
    }

    Connections {
        target: clipboardVm

        function onHistoryChanged(items) {
            historyItems = items
            refreshSelection()
        }

        function onConfigChanged(config) {
            root.captureTextEnabled = !!config.capture_text
            root.captureImageEnabled = !!config.capture_image
            root.captureFilesEnabled = !!config.capture_files
            ignorePatternsInput.text = config.ignore_patterns || ""
            maxCharsInput.text = config.max_text_chars || "0"
            hotkeyInput.text = config.hotkey || ""
        }

        function onMessageChanged(message) {
            statusText = message
            if (message === "已写回系统剪切板") {
                launcherBridge.hideLauncher()
            }
        }
    }

}
