pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    focus: true

    property var historyModel: clipboardVm ? clipboardVm.historyModel : null
    property var selectedItem: ({})
    property int selectedIndex: -1
    property string selectedItemId: ""
    property string activeFilter: "all"
    property var hostWindow: root.Window.window
    property string statusText: ""
    property bool suppressSearchRefresh: false
    property bool captureTextEnabled: true
    property bool captureImageEnabled: true
    property bool captureFilesEnabled: true
    property bool forceLatestSelection: false
    readonly property int historyRowHeight: 82
    readonly property int historyCount: historyModel ? historyModel.count : 0
    readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false
    readonly property string macFont: Qt.platform.os === "osx" ? "SF Pro Text" : Theme.fontFamily.ui
    readonly property string monoFont: Qt.platform.os === "osx" ? "SF Mono" : Theme.fontFamily.mono
    readonly property color pageBg: dark ? "#1C1C1E" : "#F5F5F7"
    readonly property color sidebarBg: dark ? "#252529" : "#ECECF0"
    readonly property color surfaceBg: dark ? "#2C2C2E" : "#FFFFFF"
    readonly property color raisedBg: dark ? "#343437" : "#FBFBFD"
    readonly property color fieldBg: dark ? "#1F1F22" : "#FFFFFF"
    readonly property color hoverBg: dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(0, 0, 0, 0.045)
    readonly property color selectedBg: dark ? Qt.rgba(0.039, 0.518, 1, 0.24) : Qt.rgba(0.039, 0.518, 1, 0.13)
    readonly property color selectedStrongBg: dark ? "#0A84FF" : "#007AFF"
    readonly property color borderColor: dark ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(0, 0, 0, 0.12)
    readonly property color hairlineColor: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.08)
    readonly property color textMain: dark ? "#F5F5F7" : "#1D1D1F"
    readonly property color textMuted: dark ? "#A1A1A6" : "#6E6E73"
    readonly property color textFaint: dark ? "#77777D" : "#8E8E93"
    readonly property color danger: dark ? "#FF453A" : "#FF3B30"
    readonly property color success: dark ? "#30D158" : "#34C759"

    function selectItem(item, idx) {
        selectedItem = item || ({})
        selectedIndex = idx
        selectedItemId = item && item.id ? String(item.id) : ""
        historyList.currentIndex = selectedIndex
    }

    function indexOfItemId(itemId) {
        if (!itemId || !historyModel) {
            return -1
        }
        return historyModel.indexOfId(String(itemId))
    }

    function itemAtIndex(idx) {
        if (!historyModel || idx < 0 || idx >= historyModel.count) {
            return null
        }
        return historyModel.itemAt(idx)
    }

    function refreshSelection() {
        if (historyCount === 0) {
            forceLatestSelection = false
            selectItem({}, -1)
            return
        }
        if (forceLatestSelection) {
            forceLatestSelection = false
            selectItem(itemAtIndex(0), 0)
            historyList.positionViewAtIndex(0, ListView.Beginning)
            return
        }
        var retainedIndex = indexOfItemId(selectedItemId)
        if (retainedIndex >= 0) {
            selectItem(itemAtIndex(retainedIndex), retainedIndex)
            return
        }
        if (selectedIndex < 0 || selectedIndex >= historyCount) {
            selectItem(itemAtIndex(0), 0)
            return
        }
        selectItem(itemAtIndex(selectedIndex), selectedIndex)
    }

    function moveSelection(delta) {
        if (tabs.currentIndex !== 0 || historyCount === 0) {
            return false
        }
        var nextIndex = selectedIndex < 0 ? 0 : selectedIndex + delta
        nextIndex = Math.max(0, Math.min(historyCount - 1, nextIndex))
        selectItem(itemAtIndex(nextIndex), nextIndex)
        historyList.positionViewAtIndex(nextIndex, ListView.Contain)
        if (historyModel && historyModel.hasMore
            && nextIndex >= historyCount - 8) {
            historyModel.loadMore()
        }
        return true
    }

    function activateSelection() {
        if (tabs.currentIndex !== 0 || selectedIndex < 0 || !selectedItem.id) {
            return false
        }
        clipboardVm.copyItem(String(selectedItem.id || ""))
        return true
    }

    function toggleSelectedPin() {
        if (tabs.currentIndex !== 0 || selectedIndex < 0 || !selectedItem.id) {
            return false
        }
        clipboardVm.togglePin(String(selectedItem.id || ""))
        return true
    }

    function deleteSelection() {
        if (tabs.currentIndex !== 0 || selectedIndex < 0 || !selectedItem.id) {
            return false
        }
        clipboardVm.deleteItem(String(selectedItem.id || ""))
        return true
    }

    function setFilter(filterType) {
        activeFilter = filterType || "all"
        clipboardVm.setFilterType(activeFilter)
        Qt.callLater(root.focusForKeyboard)
    }

    function showLatestHistory() {
        applyOpenState({
            "panel": "history",
            "query": "",
            "filter": "all",
            "latestItemId": clipboardVm.latestItemId()
        })
        clipboardVm.resetToLatest()
    }

    function setSearchQuery(text) {
        suppressSearchRefresh = true
        searchInput.text = text || ""
        suppressSearchRefresh = false
    }

    function applyOpenState(state) {
        state = state || ({})
        if (String(state.panel || "history") === "settings") {
            activeFilter = "all"
            setSearchQuery("")
            tabs.currentIndex = 1
            return
        }
        activeFilter = "all"
        selectedItem = ({})
        selectedIndex = -1
        selectedItemId = String(state.latestItemId || "")
        forceLatestSelection = selectedItemId.length === 0
        setSearchQuery(String(state.query || ""))
        tabs.currentIndex = 0
        historyList.contentY = 0
        Qt.callLater(root.refreshSelection)
    }

    function maybeLoadMore() {
        if (!historyModel || !historyModel.hasMore) {
            return
        }
        var threshold = root.historyRowHeight * 6
        var remaining = (historyList.contentHeight - historyList.contentY) - historyList.height
        if (remaining <= threshold) {
            historyModel.loadMore()
        }
    }

    function filterNavigationBlocked() {
        return (searchInput.activeTextFocus && searchInput.text.length > 0)
            || ignorePatternsInput.activeTextFocus
            || maxCharsInput.activeTextFocus
            || hotkeyInput.activeTextFocus
    }

    function switchFilter(delta) {
        if (tabs.currentIndex !== 0) {
            return false
        }
        var filters = ["all", "pinned", "text", "image", "files"]
        var currentIndex = filters.indexOf(activeFilter)
        if (currentIndex < 0) {
            currentIndex = 0
        }
        var nextIndex = Math.max(0, Math.min(filters.length - 1, currentIndex + delta))
        if (nextIndex === currentIndex) {
            return false
        }
        root.setFilter(filters[nextIndex])
        return true
    }

    function handleListKey(event) {
        if (event.key === Qt.Key_Left) {
            event.accepted = root.switchFilter(-1)
            return
        }
        if (event.key === Qt.Key_Right) {
            event.accepted = root.switchFilter(1)
            return
        }
        if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
            event.accepted = root.deleteSelection()
            return
        }
        if (event.matches(StandardKey.Copy)) {
            event.accepted = root.activateSelection()
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_P) {
            event.accepted = root.toggleSelectedPin()
        }
    }

    function focusForKeyboard() {
        root.forceActiveFocus()
        if (tabs.currentIndex === 0) {
            searchInput.forceActiveFocus()
        }
    }

    function primaryShortcutPressed(event) {
        return !!(event.modifiers & Qt.ControlModifier) || !!(event.modifiers & Qt.MetaModifier)
    }

    function closeCurrentSurface() {
        var win = root.hostWindow
        if (win && (String(win.pluginId || "") === "clipboard" || String(win.objectName || "") !== "launcherWindow")) {
            win.close()
            return
        }
        launcherBridge.hideLauncher()
    }

    function itemIconName(item) {
        return String((item && item.icon) || "qta:mdi6.clipboard-text-outline").replace("qta:", "")
    }

    function itemMetaLine(item) {
        var label = String((item && (item.subtitle || item.typeLabel)) || "")
        var time = String((item && item.createdAt) || "")
        if (label.length > 0 && time.length > 0) {
            return label + " · " + time
        }
        return label || time
    }

    function selectedFooterText() {
        if (!selectedItem || !selectedItem.id) {
            return ""
        }
        var parts = []
        if (selectedItem.stats) {
            parts.push(String(selectedItem.stats))
        }
        if (selectedItem.preview || selectedItem.subtitle) {
            parts.push(String(selectedItem.preview || selectedItem.subtitle))
        }
        return parts.join(" · ")
    }

    Component.onCompleted: {
        var initialQuery = clipboardVm.initialQuery()
        searchInput.text = initialQuery
        clipboardVm.loadConfig()
        if (clipboardVm.initialPanel() === "settings") {
            clipboardVm.refreshHistory(initialQuery)
            tabs.currentIndex = 1
        } else {
            root.showLatestHistory()
        }
        Qt.callLater(root.focusForKeyboard)
    }

    onVisibleChanged: {
        if (visible) {
            if (clipboardVm.initialPanel() !== "settings") {
                root.showLatestHistory()
            }
            Qt.callLater(root.focusForKeyboard)
        }
    }

    Keys.priority: Keys.BeforeItem
    Keys.onUpPressed: function(event) {
        event.accepted = root.moveSelection(-1)
    }
    Keys.onDownPressed: function(event) {
        event.accepted = root.moveSelection(1)
    }
    Keys.onReturnPressed: function(event) {
        event.accepted = root.activateSelection()
    }
    Keys.onEnterPressed: function(event) {
        event.accepted = root.activateSelection()
    }
    Keys.onDeletePressed: function(event) {
        event.accepted = root.deleteSelection()
    }
    Keys.onPressed: function(event) {
        if (!root.filterNavigationBlocked() && event.key === Qt.Key_Left) {
            event.accepted = root.switchFilter(-1)
            return
        }
        if (!root.filterNavigationBlocked() && event.key === Qt.Key_Right) {
            event.accepted = root.switchFilter(1)
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_F) {
            tabs.currentIndex = 0
            searchInput.forceActiveFocus()
            searchInput.selectAll()
            event.accepted = true
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_P) {
            event.accepted = root.toggleSelectedPin()
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_1) {
            root.setFilter("all")
            event.accepted = true
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_2) {
            root.setFilter("pinned")
            event.accepted = true
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_3) {
            root.setFilter("text")
            event.accepted = true
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_4) {
            root.setFilter("image")
            event.accepted = true
            return
        }
        if (root.primaryShortcutPressed(event) && event.key === Qt.Key_5) {
            root.setFilter("files")
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                Layout.alignment: Qt.AlignVCenter
                radius: 8
                color: dark ? Qt.rgba(0.039, 0.518, 1, 0.22) : Qt.rgba(0.039, 0.518, 1, 0.12)

                UiIcon {
                    anchors.centerIn: parent
                    width: 18
                    height: 18
                    name: "mdi6.clipboard-text-outline"
                    color: selectedStrongBg
                    iconSize: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 1

                Label {
                    Layout.fillWidth: true
                    text: "剪贴板历史"
                    color: textMain
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    font.family: macFont
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    text: statusText || (historyCount + " 条记录")
                    color: textMuted
                    font.pixelSize: 12
                    font.family: macFont
                    elide: Text.ElideRight
                }
            }

            Rectangle {
                id: tabs
                property int currentIndex: 0

                Layout.preferredWidth: 176
                Layout.preferredHeight: 32
                radius: 8
                color: dark ? "#3A3A3C" : "#E2E2E7"
                border.width: 1
                border.color: hairlineColor

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 3

                    Repeater {
                        model: ["历史", "设置"]

                        Rectangle {
                            id: tabButton

                            required property int index
                            required property string modelData

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 6
                            color: tabs.currentIndex === tabButton.index ? surfaceBg : "transparent"

                            Label {
                                anchors.centerIn: parent
                                text: tabButton.modelData
                                color: tabs.currentIndex === tabButton.index ? textMain : textMuted
                                font.pixelSize: 12
                                font.weight: tabs.currentIndex === tabButton.index ? Font.DemiBold : Font.Normal
                                font.family: macFont
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: tabs.currentIndex = tabButton.index
                            }
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            RowLayout {
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 360
                    Layout.fillHeight: true
                    radius: 8
                    color: sidebarBg
                    border.width: 1
                    border.color: hairlineColor
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        PlainTextField {
                            id: searchInput
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            placeholderText: "搜索历史、链接、文件名"
                            onTextChanged: {
                                if (!root.suppressSearchRefresh)
                                    clipboardVm.refreshHistory(text)
                            }

                            Keys.priority: Keys.BeforeItem
                            Keys.onUpPressed: function(event) {
                                event.accepted = root.moveSelection(-1)
                            }
                            Keys.onDownPressed: function(event) {
                                event.accepted = root.moveSelection(1)
                            }
                            Keys.onReturnPressed: function(event) {
                                event.accepted = root.activateSelection()
                            }
                            Keys.onEnterPressed: function(event) {
                                event.accepted = root.activateSelection()
                            }
                            Keys.onDeletePressed: function(event) {
                                if (searchInput.text.length === 0) {
                                    event.accepted = root.deleteSelection()
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            Layout.minimumHeight: 30
                            Layout.maximumHeight: 30
                            spacing: 6

                            FilterChip {
                                Layout.preferredWidth: 60
                                filterType: "all"
                                label: "全部"
                                iconName: "mdi6.view-list-outline"
                            }

                            FilterChip {
                                Layout.preferredWidth: 60
                                filterType: "pinned"
                                label: "置顶"
                                iconName: "mdi6.pin-outline"
                            }

                            FilterChip {
                                Layout.preferredWidth: 60
                                filterType: "text"
                                label: "文本"
                                iconName: "mdi6.text-box-outline"
                            }

                            FilterChip {
                                Layout.preferredWidth: 60
                                filterType: "image"
                                label: "图片"
                                iconName: "mdi6.image-outline"
                            }

                            FilterChip {
                                Layout.preferredWidth: 60
                                filterType: "files"
                                label: "文件"
                                iconName: "mdi6.file-multiple-outline"
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 22

                            Label {
                                Layout.fillWidth: true
                                text: activeFilter === "all" ? "最近项目" : "筛选结果"
                                color: textMuted
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.family: macFont
                            }

                            Label {
                                text: String(historyCount)
                                color: textFaint
                                font.pixelSize: 11
                                font.family: macFont
                            }
                        }

                        ListView {
                            id: historyList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 4
                            model: root.historyModel
                            currentIndex: selectedIndex
                            activeFocusOnTab: true
                            reuseItems: true
                            cacheBuffer: root.historyRowHeight * 8

                            Keys.priority: Keys.BeforeItem
                            Keys.onUpPressed: function(event) {
                                event.accepted = root.moveSelection(-1)
                            }
                            Keys.onDownPressed: function(event) {
                                event.accepted = root.moveSelection(1)
                            }
                            Keys.onReturnPressed: function(event) {
                                event.accepted = root.activateSelection()
                            }
                            Keys.onEnterPressed: function(event) {
                                event.accepted = root.activateSelection()
                            }
                            Keys.onPressed: function(event) {
                                root.handleListKey(event)
                            }

                            onContentYChanged: root.maybeLoadMore()
                            onCountChanged: root.refreshSelection()

                            delegate: Rectangle {
                                id: row

                                required property int index
                                required property var item

                                property bool hovered: false

                                width: historyList.width
                                height: root.historyRowHeight
                                radius: 8
                                color: row.index === root.selectedIndex ? selectedBg : (hovered ? hoverBg : "transparent")

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 9
                                    anchors.rightMargin: 9
                                    spacing: 10

                                    Rectangle {
                                        Layout.preferredWidth: 44
                                        Layout.preferredHeight: 44
                                        Layout.alignment: Qt.AlignVCenter
                                        radius: 8
                                        color: row.item.itemType === "image" && row.item.imageUrl
                                            ? "#000000"
                                            : (dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(1, 1, 1, 0.72))
                                        border.width: 1
                                        border.color: hairlineColor
                                        clip: true

                                        UiIcon {
                                            visible: row.item.itemType !== "image" || !row.item.imageUrl
                                            anchors.centerIn: parent
                                            width: 20
                                            height: 20
                                            name: root.itemIconName(row.item)
                                            color: selectedStrongBg
                                            iconSize: 20
                                        }

                                        Image {
                                            visible: row.item.itemType === "image" && !!row.item.imageUrl
                                            anchors.fill: parent
                                            source: row.item.imageUrl || ""
                                            sourceSize.width: 88
                                            sourceSize.height: 88
                                            fillMode: Image.PreserveAspectCrop
                                            smooth: true
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Label {
                                                Layout.fillWidth: true
                                                text: row.item.title || ""
                                                color: textMain
                                                font.pixelSize: 13
                                                font.weight: Font.Medium
                                                font.family: macFont
                                                elide: Text.ElideRight
                                            }

                                            UiIcon {
                                                visible: !!row.item.pinned
                                                Layout.preferredWidth: 13
                                                Layout.preferredHeight: 13
                                                name: "mdi6.pin"
                                                color: selectedStrongBg
                                                iconSize: 13
                                            }
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: root.itemMetaLine(row.item)
                                            color: textMuted
                                            font.pixelSize: 11
                                            font.family: macFont
                                            elide: Text.ElideRight
                                        }

                                        RowLayout {
                                            visible: row.item.badges && row.item.badges.length > 0
                                            Layout.fillWidth: true
                                            spacing: 5

                                            Repeater {
                                                model: row.item.badges || []

                                                MiniBadge {
                                                    required property string modelData
                                                    label: modelData
                                                }
                                            }
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onEntered: row.hovered = true
                                    onExited: row.hovered = false
                                    onClicked: {
                                        root.selectItem(row.item, row.index)
                                        historyList.forceActiveFocus()
                                    }
                                    onDoubleClicked: root.activateSelection()
                                }
                            }

                            ScrollBar.vertical: ScrollBar {
                                policy: ScrollBar.AsNeeded
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: historyList.count === 0
                                text: "暂无历史"
                                color: textFaint
                                font.pixelSize: 13
                                font.family: macFont
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: surfaceBg
                    border.width: 1
                    border.color: hairlineColor
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: 3

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Label {
                                        Layout.fillWidth: true
                                        text: selectedItem.title || "未选择"
                                        color: textMain
                                        font.pixelSize: 16
                                        font.weight: Font.DemiBold
                                        font.family: macFont
                                        elide: Text.ElideRight
                                    }

                                    TypePill {
                                        visible: !!selectedItem.typeLabel
                                        label: selectedItem.typeLabel || ""
                                    }

                                    Repeater {
                                        model: selectedItem.badges || []

                                        MiniBadge {
                                            required property string modelData
                                            label: modelData
                                        }
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: selectedItem.createdAt
                                        ? (selectedItem.createdAt + (selectedItem.stats ? " · " + selectedItem.stats : ""))
                                        : "选择记录后查看内容"
                                    color: textMuted
                                    font.pixelSize: 12
                                    font.family: macFont
                                    elide: Text.ElideRight
                                }
                            }

                            IconButton {
                                iconName: selectedItem.pinned ? "mdi6.pin-off-outline" : "mdi6.pin-outline"
                                tooltip: selectedItem.pinned ? "取消置顶" : "置顶"
                                enabled: selectedIndex >= 0
                                onClicked: clipboardVm.togglePin(String(selectedItem.id || ""))
                            }

                            IconButton {
                                iconName: "mdi6.content-copy"
                                tooltip: "复制"
                                accent: true
                                enabled: selectedIndex >= 0
                                onClicked: clipboardVm.copyItem(String(selectedItem.id || ""))
                            }

                            IconButton {
                                iconName: "mdi6.trash-can-outline"
                                tooltip: "删除"
                                dangerRole: true
                                enabled: selectedIndex >= 0
                                onClicked: clipboardVm.deleteItem(String(selectedItem.id || ""))
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 8
                            color: raisedBg
                            border.width: 1
                            border.color: hairlineColor
                            clip: true

                            Item {
                                anchors.fill: parent
                                anchors.margins: 14

                                TextArea {
                                    visible: selectedItem.itemType !== "image"
                                    anchors.fill: parent
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    text: selectedItem.detail || ""
                                    color: textMain
                                    selectedTextColor: "#FFFFFF"
                                    selectionColor: selectedStrongBg
                                    font.pixelSize: 13
                                    font.family: selectedItem.itemType === "text" ? monoFont : macFont
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
                            Layout.preferredHeight: 34

                            Label {
                                Layout.fillWidth: true
                                text: root.selectedFooterText()
                                color: textFaint
                                font.pixelSize: 11
                                font.family: macFont
                                elide: Text.ElideRight
                            }

                            IconButton {
                                iconName: "mdi6.pin-off-outline"
                                tooltip: "清空未置顶"
                                dangerRole: true
                                onClicked: clipboardVm.clearUnpinned()
                            }

                            IconButton {
                                iconName: "mdi6.delete-sweep-outline"
                                tooltip: "清空历史"
                                dangerRole: true
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
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 174
                        radius: 8
                        color: surfaceBg
                        border.width: 1
                        border.color: hairlineColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            SectionTitle {
                                title: "记录类型"
                                subtitle: "选择进入历史的内容"
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
                        Layout.preferredHeight: 264
                        radius: 8
                        color: surfaceBg
                        border.width: 1
                        border.color: hairlineColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            SectionTitle {
                                title: "过滤与限制"
                                subtitle: "控制保存范围"
                            }

                            Label {
                                text: "过滤规则"
                                color: textMuted
                                font.pixelSize: 12
                                font.family: macFont
                            }

                            PlainTextArea {
                                id: ignorePatternsInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 88
                                placeholderText: "关键词或正则，用 | 或换行分隔"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Label {
                                    text: "文本长度上限"
                                    color: textMuted
                                    font.pixelSize: 12
                                    font.family: macFont
                                }

                                PlainTextField {
                                    id: maxCharsInput
                                    Layout.preferredWidth: 150
                                    placeholderText: "20000"
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: "0 表示不限制"
                                    color: textFaint
                                    font.pixelSize: 11
                                    font.family: macFont
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                PushButton {
                                    label: "保存过滤"
                                    accent: true
                                    onClicked: {
                                        clipboardVm.saveIgnorePatterns(ignorePatternsInput.text)
                                        clipboardVm.saveMaxTextChars(maxCharsInput.text)
                                    }
                                }

                                PushButton {
                                    label: "清空过滤"
                                    onClicked: clipboardVm.clearIgnorePatterns()
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 118
                        radius: 8
                        color: surfaceBg
                        border.width: 1
                        border.color: hairlineColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            SectionTitle {
                                title: "快捷键"
                                subtitle: "打开剪贴板窗口"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                PlainTextField {
                                    id: hotkeyInput
                                    Layout.preferredWidth: 190
                                    placeholderText: "Alt+V"
                                }

                                Item {
                                    Layout.fillWidth: true
                                }

                                PushButton {
                                    label: "保存"
                                    accent: true
                                    onClicked: clipboardVm.saveHotkey(hotkeyInput.text)
                                }
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
            }
        }
    }

    component TypePill: Rectangle {
        property string label: ""

        implicitWidth: pillText.implicitWidth + 16
        implicitHeight: 22
        radius: 8
        color: dark ? Qt.rgba(0.039, 0.518, 1, 0.22) : Qt.rgba(0.039, 0.518, 1, 0.12)

        Label {
            id: pillText
            anchors.centerIn: parent
            text: parent.label
            color: selectedStrongBg
            font.pixelSize: 11
            font.weight: Font.DemiBold
            font.family: macFont
        }
    }

    component MiniBadge: Rectangle {
        property string label: ""

        implicitWidth: badgeText.implicitWidth + 12
        implicitHeight: 18
        radius: 6
        color: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.055)
        border.width: 1
        border.color: hairlineColor

        Label {
            id: badgeText
            anchors.centerIn: parent
            text: parent.label
            color: textMuted
            font.pixelSize: 10
            font.weight: Font.Medium
            font.family: macFont
        }
    }

    component FilterChip: Rectangle {
        id: control

        property string filterType: "all"
        property string label: ""
        property string iconName: ""
        readonly property bool selected: root.activeFilter === filterType

        Layout.fillWidth: true
        Layout.preferredHeight: 30
        Layout.minimumHeight: 30
        Layout.maximumHeight: 30
        implicitHeight: 30
        radius: 8
        color: control.selected
            ? (dark ? Qt.rgba(0.039, 0.518, 1, 0.24) : Qt.rgba(0.039, 0.518, 1, 0.13))
            : (chipMouse.containsMouse || chipMouse.pressed ? hoverBg : "transparent")
        border.width: control.selected || chipMouse.containsMouse ? 1 : 0
        border.color: control.selected ? selectedStrongBg : hairlineColor

        RowLayout {
            anchors.fill: parent
            spacing: 4

            Item {
                Layout.fillWidth: true
            }

            UiIcon {
                Layout.preferredWidth: 13
                Layout.preferredHeight: 13
                name: control.iconName
                color: control.selected ? selectedStrongBg : textMuted
                iconSize: 13
            }

            Label {
                text: control.label
                color: control.selected ? selectedStrongBg : textMuted
                font.pixelSize: 11
                font.weight: control.selected ? Font.DemiBold : Font.Normal
                font.family: macFont
                elide: Text.ElideRight
            }

            Item {
                Layout.fillWidth: true
            }
        }

        MouseArea {
            id: chipMouse

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.setFilter(control.filterType)
        }

        ToolTip.visible: chipMouse.containsMouse
        ToolTip.text: control.label
        ToolTip.delay: 550
    }

    component PlainTextField: Rectangle {
        id: fieldRoot

        property alias text: input.text
        property alias placeholderText: placeholder.text
        readonly property bool activeTextFocus: input.activeFocus

        implicitHeight: 34
        radius: 8
        color: fieldBg
        border.width: 1
        border.color: input.activeFocus ? selectedStrongBg : hairlineColor
        Keys.forwardTo: [input]

        TextInput {
            id: input

            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            focus: true
            color: textMain
            selectedTextColor: "#FFFFFF"
            selectionColor: selectedStrongBg
            font.pixelSize: 13
            font.family: macFont
            verticalAlignment: TextInput.AlignVCenter
            clip: true
            selectByMouse: true
        }

        Label {
            id: placeholder

            anchors.fill: input
            visible: input.text.length === 0
            color: textFaint
            font.pixelSize: 13
            font.family: macFont
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        function forceActiveFocus() {
            input.forceActiveFocus()
        }

        function selectAll() {
            input.selectAll()
        }
    }

    component PlainTextArea: Rectangle {
        id: areaRoot

        property alias text: edit.text
        property alias placeholderText: placeholder.text
        readonly property bool activeTextFocus: edit.activeFocus

        radius: 8
        color: fieldBg
        border.width: 1
        border.color: edit.activeFocus ? selectedStrongBg : hairlineColor
        clip: true
        Keys.forwardTo: [edit]

        TextEdit {
            id: edit

            anchors.fill: parent
            anchors.margins: 10
            focus: true
            wrapMode: TextEdit.Wrap
            color: textMain
            selectedTextColor: "#FFFFFF"
            selectionColor: selectedStrongBg
            font.pixelSize: 12
            font.family: macFont
            clip: true
            selectByMouse: true
        }

        Label {
            id: placeholder

            anchors.fill: edit
            visible: edit.text.length === 0
            text: ""
            color: textFaint
            font.pixelSize: 12
            font.family: macFont
            wrapMode: Text.Wrap
        }
    }

    component SectionTitle: ColumnLayout {
        property string title: ""
        property string subtitle: ""

        Layout.fillWidth: true
        spacing: 2

        Label {
            Layout.fillWidth: true
            text: parent.title
            color: textMain
            font.pixelSize: 15
            font.weight: Font.DemiBold
            font.family: macFont
        }

        Label {
            Layout.fillWidth: true
            text: parent.subtitle
            color: textMuted
            font.pixelSize: 12
            font.family: macFont
            elide: Text.ElideRight
        }
    }

    component IconButton: Rectangle {
        id: control

        property string iconName: ""
        property string tooltip: ""
        property bool accent: false
        property bool dangerRole: false
        signal clicked()

        implicitWidth: 34
        implicitHeight: 30
        radius: 8
        color: {
            if (!control.enabled)
                return "transparent"
            if (control.accent)
                return iconMouse.pressed ? Qt.darker(selectedStrongBg, 1.15) : selectedStrongBg
            if (iconMouse.containsMouse || iconMouse.pressed)
                return hoverBg
            return "transparent"
        }
        border.width: control.accent ? 0 : 1
        border.color: iconMouse.containsMouse && !control.accent ? hairlineColor : "transparent"

        UiIcon {
            anchors.centerIn: parent
            width: 16
            height: 16
            name: control.iconName
            color: {
                if (!control.enabled)
                    return textFaint
                if (control.accent)
                    return "#FFFFFF"
                if (control.dangerRole)
                    return danger
                return textMuted
            }
            iconSize: 16
        }

        MouseArea {
            id: iconMouse

            anchors.fill: parent
            enabled: control.enabled
            hoverEnabled: true
            cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: control.clicked()
        }

        ToolTip.visible: iconMouse.containsMouse && control.tooltip.length > 0
        ToolTip.text: control.tooltip
        ToolTip.delay: 450
    }

    component PushButton: Rectangle {
        id: control

        property string label: ""
        property bool accent: false
        signal clicked()

        implicitWidth: Math.max(86, buttonText.implicitWidth + 28)
        implicitHeight: 32
        radius: 8
        color: control.accent
            ? (pushMouse.pressed ? Qt.darker(selectedStrongBg, 1.15) : selectedStrongBg)
            : (pushMouse.pressed ? Qt.rgba(0, 0, 0, root.dark ? 0.22 : 0.08) : (pushMouse.containsMouse ? hoverBg : raisedBg))
        border.width: control.accent ? 0 : 1
        border.color: hairlineColor

        Label {
            id: buttonText
            anchors.fill: parent
            text: control.label
            color: control.accent ? "#FFFFFF" : textMain
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 13
            font.weight: Font.Medium
            font.family: macFont
        }

        MouseArea {
            id: pushMouse

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: control.clicked()
        }
    }

    component SettingSwitch: RowLayout {
        id: switchRoot

        property string label: ""
        property bool checked: false
        signal toggled(bool value)

        Layout.fillWidth: true

        Label {
            Layout.fillWidth: true
            text: label
            color: textMain
            font.pixelSize: 13
            font.family: macFont
        }

        Rectangle {
            Layout.preferredWidth: 42
            Layout.preferredHeight: 24
            radius: 12
            color: switchRoot.checked ? root.success : (root.dark ? "#48484A" : "#D1D1D6")

            Rectangle {
                width: 20
                height: 20
                radius: 10
                y: 2
                x: switchRoot.checked ? parent.width - width - 2 : 2
                color: "#FFFFFF"
                border.width: 1
                border.color: Qt.rgba(0, 0, 0, 0.08)

                Behavior on x {
                    NumberAnimation {
                        duration: 140
                        easing.type: Easing.OutCubic
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: switchRoot.toggled(!switchRoot.checked)
            }
        }
    }

    Connections {
        target: clipboardVm

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
            if (message === "已写回系统剪贴板") {
                root.closeCurrentSurface()
            }
        }

        function onOpenStateChanged(state) {
            root.applyOpenState(state)
        }
    }

    Connections {
        target: root.hostWindow

        function onVisibleChanged() {
            if (root.hostWindow && root.hostWindow.visible) {
                Qt.callLater(root.focusForKeyboard)
            }
        }

        function onActiveChanged() {
            if (root.hostWindow && root.hostWindow.active) {
                Qt.callLater(root.focusForKeyboard)
            }
        }
    }
}
