import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebEngine
import QtWebChannel
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    property var selectedProfile: null
    property var selectedRemoteItems: []
    property var editingProfile: ({})
    property var contextItem: null
    property var contextProfile: null
    readonly property bool dark: app.theme === "dark"
    readonly property bool connected: (remoteFilesVm.connectionState.status || "") === "connected"
    readonly property bool connecting: (remoteFilesVm.connectionState.status || "") === "connecting"
    readonly property bool errored: (remoteFilesVm.connectionState.status || "") === "error"
    readonly property bool sftpConnected: connected && (remoteFilesVm.connectionState.protocol || "") === "sftp"
    readonly property color pageBg: dark ? "#0E1117" : "#F2F3F7"
    readonly property color sidebarBg: dark ? "#1B2029" : "#E4E7EE"
    readonly property color surface: dark ? "#1F242E" : "#FFFFFF"
    readonly property color surfaceSubtle: dark ? "#252B36" : "#F5F6FA"
    readonly property color surfaceElevated: dark ? "#2A303C" : "#FFFFFF"
    readonly property color toolbarBg: dark ? "#1B2029" : "#F8F9FC"
    readonly property color border: dark ? "#363D4B" : "#D6D8E1"
    readonly property color separator: dark ? "#2F3644" : "#E0E2EA"
    readonly property color rowHover: dark ? "#2A3140" : "#E9EBF1"
    readonly property color selectedBg: "#0A84FF"
    readonly property color selectedSoftBg: dark ? "#1B3D6B" : "#D6E7FF"
    readonly property color textMain: dark ? "#FAFBFC" : "#15171B"
    readonly property color textMuted: dark ? "#B8BDC7" : "#5A5E66"
    readonly property color textFaint: dark ? "#8A909C" : "#878A91"
    readonly property color danger: "#FF453A"
    readonly property color success: "#30D158"
    readonly property color warning: "#FFD60A"
    readonly property color tagBg: dark ? "#33394A" : "#E3E5EE"
    readonly property color tagText: dark ? "#C7CBD3" : "#4B4E55"

    function emptyProfile() {
        return {
            id: "",
            name: "",
            protocol: "sftp",
            host: "",
            port: 22,
            username: "",
            password: "",
            remoteRoot: "",
            localRoot: "",
            encoding: "utf-8",
            passiveMode: true,
            authKind: "password",
            privateKeyPath: "",
            privateKeyPassphrase: "",
            connectTimeout: 15,
            jumpEnabled: false,
            jumpHost: "",
            jumpPort: 22,
            jumpUsername: "",
            jumpPassword: "",
            jumpPrivateKeyPath: "",
            jumpPrivateKeyPassphrase: ""
        }
    }

    function copyProfile(source) {
        var profile = emptyProfile()
        if (!source)
            return profile
        for (var key in profile) {
            if (source[key] !== undefined)
                profile[key] = source[key]
        }
        if (source.rawName !== undefined)
            profile.name = source.rawName
        return profile
    }

    function profileSubtitle(profile) {
        if (!profile)
            return "未选择"
        var user = profile.username ? profile.username + "@" : ""
        var host = profile.host || ""
        var port = profile.port ? ":" + profile.port : ""
        return user + host + port
    }

    function selectedProfileName() {
        if (selectedProfile)
            return selectedProfile.name || "未命名连接"
        if (connecting)
            return "连接中"
        if (connected)
            return (remoteFilesVm.connectionState.protocol || "").toUpperCase() + " " + (remoteFilesVm.connectionState.host || "")
        return "未选择连接"
    }

    function selectedProfileSubtitle() {
        if (selectedProfile)
            return profileSubtitle(selectedProfile)
        if (remoteFilesVm.connectionState.host)
            return remoteFilesVm.connectionState.host
        return "SFTP / FTP / FTPS"
    }

    function statusColor() {
        if (connected)
            return success
        if (connecting)
            return warning
        if (errored)
            return danger
        return textFaint
    }

    function statusText() {
        if (remoteFilesVm.statusMessage)
            return remoteFilesVm.statusMessage
        if (connected)
            return "已连接"
        if (connecting)
            return "连接中"
        if (errored)
            return "连接失败"
        return "未连接"
    }

    function formatSize(size) {
        var value = Number(size || 0)
        if (value >= 1024 * 1024 * 1024)
            return (value / 1024 / 1024 / 1024).toFixed(1) + " GB"
        if (value >= 1024 * 1024)
            return (value / 1024 / 1024).toFixed(1) + " MB"
        if (value >= 1024)
            return (value / 1024).toFixed(1) + " KB"
        return value + " B"
    }

    function shortenPath(path, maxLen) {
        var text = String(path || "")
        if (text.length <= maxLen)
            return text
        return "…" + text.substring(text.length - maxLen + 1)
    }

    function ensureSelectedProfile() {
        var profiles = remoteFilesVm.profiles || []
        if (profiles.length === 0) {
            selectedProfile = null
            return
        }
        if (selectedProfile) {
            for (var i = 0; i < profiles.length; i++) {
                if (profiles[i].id === selectedProfile.id) {
                    selectedProfile = profiles[i]
                    return
                }
            }
        }
        selectedProfile = profiles[0]
    }

    function openProfileEditor(source) {
        editingProfile = source ? copyProfile(source) : emptyProfile()
        profileDialog.showAdvanced = false
        profileDialog.open()
    }

    function duplicateProfile(source) {
        if (!source)
            return
        var copy = copyProfile(source)
        copy.id = ""
        copy.name = (source.name || "未命名连接") + " 副本"
        editingProfile = copy
        profileDialog.showAdvanced = false
        profileDialog.open()
    }

    Component.onCompleted: ensureSelectedProfile()

    Connections {
        target: remoteFilesVm
        function onProfilesChanged() { root.ensureSelectedProfile() }
        function onConnectionStateChanged() {
            if (root.sftpConnected)
                remoteFilesVm.openTerminal()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // ============ Sidebar ============
            Rectangle {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                color: sidebarBg

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            Layout.fillWidth: true
                            text: "连接管理"
                            color: textMain
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        IconButton {
                            iconName: "mdi6.plus"
                            tooltip: "新建连接"
                            accent: true
                            onClicked: openProfileEditor(null)
                        }
                    }

                    UiTextField {
                        id: sidebarFilter
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "搜索连接"
                    }

                    ListView {
                        id: profileList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: remoteFilesVm.profiles
                        delegate: Rectangle {
                            id: profileRow

                            required property var modelData
                            required property int index
                            readonly property bool selected: root.selectedProfile && root.selectedProfile.id === modelData.id
                            readonly property string filterText: (sidebarFilter.text || "").toLowerCase()
                            readonly property bool matchesFilter: filterText.length === 0
                                || String(modelData.name || "").toLowerCase().indexOf(filterText) >= 0
                                || String(modelData.host || "").toLowerCase().indexOf(filterText) >= 0
                                || String(modelData.username || "").toLowerCase().indexOf(filterText) >= 0

                            width: ListView.view.width
                            height: matchesFilter ? 50 : 0
                            visible: matchesFilter
                            radius: 7
                            color: selected ? selectedBg : (profileMouse.containsMouse ? rowHover : "transparent")

                            MouseArea {
                                id: profileMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                cursorShape: Qt.PointingHandCursor
                                onClicked: function(mouse) {
                                    root.selectedProfile = modelData
                                    if (mouse.button === Qt.RightButton) {
                                        root.contextProfile = modelData
                                        root.openPopupAtMouse(profileMenu, profileMouse, mouse)
                                    }
                                }
                                onDoubleClicked: remoteFilesVm.connectProfile(modelData.id || "")
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                Rectangle {
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    radius: 7
                                    color: profileRow.selected
                                        ? Qt.rgba(1, 1, 1, 0.22)
                                        : (root.dark ? "#323A4A" : "#FFFFFF")
                                    border.width: profileRow.selected ? 0 : 1
                                    border.color: root.dark ? "#3F4759" : "#D5D8E0"

                                    UiIcon {
                                        anchors.centerIn: parent
                                        width: 16
                                        height: 16
                                        iconSize: 16
                                        name: "mdi6.server-network"
                                        color: profileRow.selected ? "#FFFFFF" : selectedBg
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6

                                        Label {
                                            Layout.fillWidth: true
                                            text: modelData.name || "未命名连接"
                                            color: profileRow.selected ? "#FFFFFF" : textMain
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            Layout.preferredHeight: 15
                                            implicitWidth: protoLabel.implicitWidth + 10
                                            radius: 4
                                            color: profileRow.selected ? Qt.rgba(1, 1, 1, 0.26) : tagBg
                                            Label {
                                                id: protoLabel
                                                anchors.centerIn: parent
                                                text: (modelData.protocol || "").toUpperCase()
                                                color: profileRow.selected ? "#FFFFFF" : tagText
                                                font.pixelSize: 9
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: root.profileSubtitle(modelData)
                                        color: profileRow.selected ? Qt.rgba(1, 1, 1, 0.92) : textMuted
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: (remoteFilesVm.profiles || []).length + " 个连接  ·  右键查看操作"
                        color: textFaint
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: separator
            }

            // ============ Right area ============
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                // Toolbar
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    color: toolbarBg

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.statusColor()
                        }

                        Label {
                            text: root.selectedProfileName()
                            color: textMain
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.selectedProfileSubtitle() + "  ·  " + root.statusText()
                            color: errored ? danger : textMuted
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }

                        PushButton {
                            label: root.connecting ? "连接中" : (root.connected ? "已连接" : "连接")
                            accent: !root.connected
                            enabled: root.selectedProfile !== null && !root.connected && !root.connecting
                            iconName: "mdi6.connection"
                            onClicked: remoteFilesVm.connectProfile(root.selectedProfile ? root.selectedProfile.id || "" : "")
                        }

                        IconButton {
                            iconName: "mdi6.refresh"
                            tooltip: "刷新"
                            enabled: root.connected
                            onClicked: remoteFilesVm.refreshAll()
                        }

                        IconButton {
                            iconName: "mdi6.power"
                            tooltip: "断开"
                            dangerRole: true
                            enabled: root.connected || root.connecting
                            onClicked: remoteFilesVm.disconnect()
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: separator
                    }
                }

                // Main split: remote | terminal
                SplitView {
                    id: mainSplit
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: Qt.Horizontal
                    handle: Rectangle {
                        implicitWidth: 1
                        implicitHeight: 1
                        color: separator
                    }

                    RemoteFilePane {
                        id: remotePane
                        SplitView.preferredWidth: 380
                        SplitView.minimumWidth: 260
                        enabled: root.connected
                    }

                    TerminalPane {
                        id: terminalPane
                        SplitView.fillWidth: true
                        SplitView.minimumWidth: 280
                    }
                }

                // Transfers panel
                Rectangle {
                    id: transfersBar
                    property bool collapsed: false

                    Layout.fillWidth: true
                    Layout.preferredHeight: collapsed ? 36 : 210
                    color: surface

                    Behavior on Layout.preferredHeight { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: 1
                        color: separator
                    }

                    Rectangle {
                        id: transfersHeader
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 1
                        height: 35
                        color: toolbarBg

                        MouseArea {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 240
                            cursorShape: Qt.PointingHandCursor
                            onClicked: transfersBar.collapsed = !transfersBar.collapsed
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 10
                            spacing: 10

                            UiIcon {
                                Layout.preferredWidth: 14
                                Layout.preferredHeight: 14
                                iconSize: 14
                                name: transfersBar.collapsed ? "mdi6.chevron-right" : "mdi6.chevron-down"
                                color: textMuted
                            }

                            Label {
                                text: "传输队列"
                                color: textMain
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }

                            Label {
                                text: (remoteFilesVm.transfers || []).length > 0
                                    ? "(" + (remoteFilesVm.transfers || []).length + ")"
                                    : ""
                                color: textFaint
                                font.pixelSize: 12
                            }

                            Item { Layout.fillWidth: true }

                            IconButton {
                                iconName: "mdi6.broom"
                                tooltip: "清理已完成"
                                onClicked: remoteFilesVm.clearFinishedTransfers()
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: separator
                            visible: !transfersBar.collapsed
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: transfersHeader.bottom
                        height: 22
                        color: surface
                        visible: !transfersBar.collapsed && (remoteFilesVm.transfers || []).length > 0

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 10
                            Label { Layout.preferredWidth: 18; text: "" }
                            Label { Layout.preferredWidth: 130; text: "文件"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.fillWidth: true; text: "本地路径"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.fillWidth: true; text: "远程路径"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 160; text: "进度"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 60; text: "状态"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 28; text: "" }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: separator
                        }
                    }

                    ListView {
                        id: transferList
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: transfersHeader.bottom
                        anchors.topMargin: (remoteFilesVm.transfers || []).length > 0 ? 22 : 0
                        anchors.bottom: parent.bottom
                        clip: true
                        visible: !transfersBar.collapsed
                        model: remoteFilesVm.transfers
                        delegate: Rectangle {
                            required property var modelData
                            required property int index

                            width: ListView.view.width
                            height: 32
                            color: index % 2 === 0 ? surface : surfaceSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 10

                                UiIcon {
                                    Layout.preferredWidth: 14
                                    Layout.preferredHeight: 14
                                    iconSize: 14
                                    name: modelData.direction === "upload" ? "mdi6.arrow-up-bold" : "mdi6.arrow-down-bold"
                                    color: modelData.direction === "upload" ? success : selectedBg
                                }

                                Label {
                                    Layout.preferredWidth: 130
                                    text: modelData.name || ""
                                    color: textMain
                                    font.pixelSize: 12
                                    elide: Text.ElideMiddle
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: root.shortenPath(modelData.localPath || "", 60)
                                    color: textMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideLeft
                                    ToolTip.visible: localPathHover.containsMouse && (modelData.localPath || "").length > 0
                                    ToolTip.text: modelData.localPath || ""
                                    ToolTip.delay: 600
                                    MouseArea {
                                        id: localPathHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        acceptedButtons: Qt.NoButton
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: root.shortenPath(modelData.remotePath || "", 60)
                                    color: textMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideLeft
                                    ToolTip.visible: remotePathHover.containsMouse && (modelData.remotePath || "").length > 0
                                    ToolTip.text: modelData.remotePath || ""
                                    ToolTip.delay: 600
                                    MouseArea {
                                        id: remotePathHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        acceptedButtons: Qt.NoButton
                                    }
                                }

                                ProgressBar {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 6
                                    from: 0
                                    to: 100
                                    value: modelData.progress || 0
                                }

                                Label {
                                    text: {
                                        var status = modelData.status || ""
                                        if (status === "queued") return "等待"
                                        if (status === "running") return (modelData.progress || 0) + "%"
                                        if (status === "completed") return "完成"
                                        if (status === "cancelled") return "已取消"
                                        if (status === "failed") return "失败"
                                        return status
                                    }
                                    color: {
                                        var status = modelData.status || ""
                                        if (status === "failed") return danger
                                        if (status === "completed") return success
                                        return textMuted
                                    }
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 60
                                }

                                IconButton {
                                    iconName: "mdi6.close"
                                    tooltip: "取消"
                                    enabled: modelData.status === "queued" || modelData.status === "running"
                                    onClicked: remoteFilesVm.cancelTransfer(modelData.id || "")
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: (remoteFilesVm.transfers || []).length === 0
                            text: "暂无传输任务  ·  右键远程文件下载，或拖拽文件夹到目录上传"
                            color: textFaint
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
    }

    // ============ Menus ============
    function openPopupAtMouse(popup, srcItem, mouse) {
        var p = srcItem.mapToItem(Overlay.overlay, mouse.x, mouse.y)
        popup.x = p.x
        popup.y = p.y
        popup.open()
    }

    Popup {
        id: profileMenu
        parent: Overlay.overlay
        width: 200
        height: profileMenuColumn.implicitHeight + 8
        padding: 4
        modal: false
        focus: true
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            }
        }
        background: UiMenuSurface { dark: root.dark; radius: 8 }
        contentItem: Column {
            id: profileMenuColumn
            spacing: 0

            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "连接"
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.connectProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "编辑…"
                onTriggered: { openProfileEditor(root.contextProfile); profileMenu.close() }
            }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "复制连接"
                onTriggered: { duplicateProfile(root.contextProfile); profileMenu.close() }
            }
            UiMenuSeparator { width: profileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                destructive: true
                text: "删除"
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.deleteProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
        }
    }

    Popup {
        id: remoteFileMenu
        parent: Overlay.overlay
        width: 220
        height: remoteFileMenuColumn.implicitHeight + 8
        padding: 4
        modal: false
        focus: true
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        property bool itemIsDir: root.contextItem ? !!root.contextItem.isDir : false
        property bool hasItem: root.contextItem !== null
        property bool itemIsParent: root.contextItem && root.contextItem.name === ".."
        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            }
        }
        background: UiMenuSurface { dark: root.dark; radius: 8 }
        contentItem: Column {
            id: remoteFileMenuColumn
            spacing: 0

            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem
                text: remoteFileMenu.itemIsDir ? "打开目录" : "下载到默认目录"
                onTriggered: {
                    if (!root.contextItem) return
                    if (root.contextItem.isDir)
                        remoteFilesVm.changeRemotePath(root.contextItem.path || "")
                    else
                        remoteFilesVm.downloadFiles([root.contextItem])
                    remoteFileMenu.close()
                }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsDir
                text: "下载到…"
                onTriggered: { downloadFolderDialog.open(); remoteFileMenu.close() }
            }
            UiMenuSeparator { width: remoteFileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: root.connected
                text: "新建目录…"
                onTriggered: { mkdirDialog.open(); remoteFileMenu.close() }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsParent
                text: "重命名…"
                onTriggered: {
                    if (!root.contextItem) return
                    renameDialog.targetPath = root.contextItem.path || ""
                    renameField.text = root.contextItem.name || ""
                    renameDialog.open()
                    remoteFileMenu.close()
                }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: root.connected
                text: "刷新"
                onTriggered: { remoteFilesVm.changeRemotePath(remoteFilesVm.remotePath); remoteFileMenu.close() }
            }
            UiMenuSeparator { width: remoteFileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                destructive: true
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsParent
                text: "删除"
                onTriggered: {
                    if (!root.contextItem) return
                    root.selectedRemoteItems = [root.contextItem]
                    deleteDialog.open()
                    remoteFileMenu.close()
                }
            }
        }
    }

    // ============ Dialogs ============
    Dialog {
        id: profileDialog
        modal: true
        title: ""
        width: 620
        height: 600
        anchors.centerIn: Overlay.overlay
        padding: 0

        property bool showAdvanced: false

        background: Rectangle {
            color: surface
            radius: 14
            border.width: 1
            border.color: dark ? "#3D4555" : "#D8DAE2"
        }

        header: Rectangle {
            color: "transparent"
            implicitHeight: 72
            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 28
                anchors.rightMargin: 28
                anchors.topMargin: 18
                anchors.bottomMargin: 14
                spacing: 4

                Label {
                    text: editingProfile.id ? "编辑连接" : "新建连接"
                    color: textMain
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }
                Label {
                    text: "为 SFTP / FTP / FTPS 服务器配置访问凭据。"
                    color: textMuted
                    font.pixelSize: 12
                }
            }
        }

        footer: Rectangle {
            color: surfaceSubtle
            implicitHeight: 58
            radius: 14

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: separator
            }

            // mask bottom rounded corners against bg
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 14
                color: surfaceSubtle
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: "敏感信息以明文方式保存到本地数据库。"
                    color: textFaint
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                PushButton {
                    label: "取消"
                    onClicked: profileDialog.close()
                }

                PushButton {
                    label: "保存"
                    accent: true
                    onClicked: profileDialog.accept()
                }
            }
        }

        onAccepted: {
            var p = copyProfile(editingProfile)
            p.name = nameField.text
            p.protocol = ["sftp", "ftp", "ftps"][protocolBox.currentIndex]
            p.host = hostField.text
            p.port = parseInt(portField.text || "0")
            p.username = usernameField.text
            p.password = passwordField.text
            p.remoteRoot = remoteRootField.text
            p.localRoot = localRootField.text
            p.encoding = encodingField.text || "utf-8"
            p.passiveMode = passiveSwitch.checked
            p.authKind = ["password", "private_key", "agent"][authBox.currentIndex]
            p.privateKeyPath = keyPathField.text
            p.privateKeyPassphrase = keyPassField.text
            p.connectTimeout = parseInt(timeoutField.text || "15")
            p.jumpEnabled = jumpSwitch.checked
            p.jumpHost = jumpHostField.text
            p.jumpPort = parseInt(jumpPortField.text || "22")
            p.jumpUsername = jumpUserField.text
            p.jumpPassword = jumpPasswordField.text
            p.jumpPrivateKeyPath = jumpKeyField.text
            p.jumpPrivateKeyPassphrase = jumpKeyPassField.text
            remoteFilesVm.saveProfile(p)
        }

        contentItem: ScrollView {
            id: dialogScroll
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: dialogScroll.availableWidth
                spacing: 18

                // Section: 通用
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "通用"

                    MacFormItem {
                        label: "名称"
                        UiTextField {
                            id: nameField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.name || ""
                            placeholderText: "例如：生产环境跳板"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "协议"
                        UiComboBox {
                            id: protocolBox
                            dark: root.dark
                            Layout.preferredWidth: 200
                            model: ["SFTP", "FTP", "FTPS"]
                            currentIndex: (editingProfile.protocol || "sftp") === "ftp"
                                ? 1
                                : (editingProfile.protocol || "sftp") === "ftps" ? 2 : 0
                            onCurrentIndexChanged: {
                                if (portField.text === "" || portField.text === "22" || portField.text === "21")
                                    portField.text = currentIndex === 0 ? "22" : "21"
                            }
                        }
                    }
                }

                // Section: 服务器
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "服务器"

                    MacFormItem {
                        label: "主机"
                        UiTextField {
                            id: hostField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.host || ""
                            placeholderText: "host 或 IP"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "端口"
                        UiTextField {
                            id: portField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.port || ((editingProfile.protocol || "sftp") === "sftp" ? 22 : 21))
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "用户名"
                        UiTextField {
                            id: usernameField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.username || ""
                            placeholderText: "登录账号"
                        }
                    }
                }

                // Section: 认证
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "身份认证"

                    MacFormItem {
                        label: "方式"
                        UiComboBox {
                            id: authBox
                            dark: root.dark
                            Layout.preferredWidth: 200
                            model: ["密码", "私钥", "SSH Agent"]
                            currentIndex: (editingProfile.authKind || "password") === "private_key"
                                ? 1
                                : (editingProfile.authKind || "password") === "agent" ? 2 : 0
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 0 }
                    MacFormItem {
                        visible: authBox.currentIndex === 0
                        label: "密码"
                        UiTextField {
                            id: passwordField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.password || ""
                            echoMode: TextInput.Password
                            placeholderText: "登录密码"
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 1 }
                    MacFormItem {
                        visible: authBox.currentIndex === 1
                        label: "私钥"
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            UiTextField {
                                id: keyPathField
                                dark: root.dark
                                Layout.fillWidth: true
                                text: editingProfile.privateKeyPath || ""
                                placeholderText: "~/.ssh/id_rsa"
                            }
                            PushButton {
                                label: "选择…"
                                onClicked: keyFileDialog.open()
                            }
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 1 }
                    MacFormItem {
                        visible: authBox.currentIndex === 1
                        label: "口令"
                        UiTextField {
                            id: keyPassField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.privateKeyPassphrase || ""
                            echoMode: TextInput.Password
                            placeholderText: "可选"
                        }
                    }
                }

                // Advanced toggle
                Rectangle {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 9
                    color: surfaceSubtle
                    border.width: 1
                    border.color: separator

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        UiIcon {
                            Layout.preferredWidth: 14
                            Layout.preferredHeight: 14
                            iconSize: 14
                            name: profileDialog.showAdvanced ? "mdi6.chevron-down" : "mdi6.chevron-right"
                            color: textMuted
                        }

                        Label {
                            Layout.fillWidth: true
                            text: "高级选项"
                            color: textMain
                            font.pixelSize: 12
                            font.weight: Font.Medium
                        }

                        Label {
                            text: "默认目录 · 编码 · 超时 · 跳板机"
                            color: textFaint
                            font.pixelSize: 11
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: profileDialog.showAdvanced = !profileDialog.showAdvanced
                    }
                }

                // Section: advanced
                MacCard {
                    visible: profileDialog.showAdvanced
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "高级"

                    MacFormItem {
                        label: "远程默认目录"
                        UiTextField {
                            id: remoteRootField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.remoteRoot || ""
                            placeholderText: "留空则使用远程家目录"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "本地默认目录"
                        UiTextField {
                            id: localRootField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.localRoot || ""
                            placeholderText: "留空则使用本机家目录"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "编码"
                        UiTextField {
                            id: encodingField
                            dark: root.dark
                            Layout.preferredWidth: 160
                            text: editingProfile.encoding || "utf-8"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "连接超时 (秒)"
                        UiTextField {
                            id: timeoutField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.connectTimeout || 15)
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "FTP 被动模式"
                        UiSwitch {
                            id: passiveSwitch
                            dark: root.dark
                            checked: editingProfile.passiveMode !== false
                        }
                    }
                }

                MacCard {
                    visible: profileDialog.showAdvanced
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "跳板机"

                    MacFormItem {
                        label: "启用"
                        UiSwitch {
                            id: jumpSwitch
                            dark: root.dark
                            checked: editingProfile.jumpEnabled || false
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "主机"
                        UiTextField {
                            id: jumpHostField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpHost || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "端口"
                        UiTextField {
                            id: jumpPortField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.jumpPort || 22)
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "用户名"
                        UiTextField {
                            id: jumpUserField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpUsername || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "密码"
                        UiTextField {
                            id: jumpPasswordField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPassword || ""
                            echoMode: TextInput.Password
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "私钥"
                        UiTextField {
                            id: jumpKeyField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPrivateKeyPath || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "私钥口令"
                        UiTextField {
                            id: jumpKeyPassField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPrivateKeyPassphrase || ""
                            echoMode: TextInput.Password
                        }
                    }
                }

                Item { Layout.preferredHeight: 8 }
            }
        }
    }

    FileDialog {
        id: keyFileDialog
        title: "选择私钥文件"
        onAccepted: {
            var url = selectedFile.toString()
            if (url.indexOf("file://") === 0)
                url = decodeURIComponent(url.substring(7))
            keyPathField.text = url
        }
    }

    FileDialog {
        id: uploadFileDialog
        title: "选择要上传的文件"
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            var paths = []
            var files = selectedFiles
            for (var i = 0; i < files.length; i++)
                paths.push(files[i].toString())
            if (paths.length > 0)
                remoteFilesVm.uploadPaths(paths)
        }
    }

    FolderDialog {
        id: downloadFolderDialog
        title: "选择下载到的目录"
        onAccepted: {
            if (!root.contextItem)
                return
            var url = selectedFolder.toString()
            remoteFilesVm.downloadFilesTo([root.contextItem], url)
        }
    }

    Dialog {
        id: mkdirDialog
        modal: true
        title: "新建远程目录"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        onAccepted: {
            remoteFilesVm.mkdirRemote(mkdirField.text)
            mkdirField.text = ""
        }
        UiTextField { id: mkdirField; dark: root.dark; width: 320; placeholderText: "目录名" }
    }

    Dialog {
        id: renameDialog
        property string targetPath: ""
        modal: true
        title: "重命名"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        onAccepted: remoteFilesVm.renameRemote(targetPath, renameField.text)
        UiTextField { id: renameField; dark: root.dark; width: 320; placeholderText: "新名称" }
    }

    MessageDialog {
        id: deleteDialog
        title: "确认删除"
        text: "删除选中的远程文件或空目录？"
        buttons: MessageDialog.Yes | MessageDialog.No
        onAccepted: remoteFilesVm.deleteRemote(root.selectedRemoteItems)
    }

    // ============ Components ============

    component MacCard: ColumnLayout {
        property string title: ""
        default property alias content: cardCol.data
        Layout.fillWidth: true
        spacing: 6

        children: [
            Label {
                visible: title.length > 0
                text: title
                color: textFaint
                font.pixelSize: 11
                font.weight: Font.Medium
                font.capitalization: Font.AllUppercase
                Layout.leftMargin: 2
            },
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: cardCol.implicitHeight + 4
                radius: 10
                color: surfaceElevated
                border.width: 1
                border.color: dark ? "#3D4555" : "#E2E4EB"

                ColumnLayout {
                    id: cardCol
                    anchors.fill: parent
                    anchors.margins: 2
                    spacing: 0
                }
            }
        ]
    }

    component MacFormDivider: Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        Layout.leftMargin: 14
        color: separator
    }

    component MacFormItem: RowLayout {
        property string label: ""
        spacing: 14
        Layout.fillWidth: true
        Layout.minimumHeight: 38

        Label {
            text: parent.label
            color: textMain
            font.pixelSize: 12
            Layout.preferredWidth: 110
            Layout.leftMargin: 14
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    component RemoteFilePane: Rectangle {
        id: pane

        color: surface
        border.width: 0

        function currentItem() {
            if (fileList.currentIndex < 0 || fileList.currentIndex >= (remoteFilesVm.remoteItems || []).length)
                return null
            return remoteFilesVm.remoteItems[fileList.currentIndex]
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Title bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 10

                    UiIcon {
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconSize: 14
                        name: "mdi6.folder-network-outline"
                        color: selectedBg
                    }

                    Label {
                        text: "远程目录"
                        color: textMain
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Item { Layout.fillWidth: true }

                    IconButton {
                        iconName: "mdi6.console-network-outline"
                        tooltip: "同步至终端目录"
                        enabled: pane.enabled && root.sftpConnected
                        onClicked: remoteFilesVm.syncRemoteFromTerminal()
                    }

                    Label {
                        text: (remoteFilesVm.remoteItems || []).length + " 项"
                        color: textFaint
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // Path bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: surface

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 6

                    IconButton {
                        iconName: "mdi6.arrow-up"
                        tooltip: "返回上级"
                        enabled: pane.enabled && remoteFilesVm.remotePath !== "/"
                        onClicked: {
                            var p = String(remoteFilesVm.remotePath || "/")
                            var idx = p.lastIndexOf("/")
                            var parent = idx <= 0 ? "/" : p.substring(0, idx)
                            remoteFilesVm.changeRemotePath(parent || "/")
                        }
                    }

                    IconButton {
                        iconName: "mdi6.home-outline"
                        tooltip: "家目录"
                        enabled: pane.enabled
                        onClicked: remoteFilesVm.changeRemotePath("")
                    }

                    UiTextField {
                        id: pathField
                        dark: root.dark
                        text: remoteFilesVm.remotePath
                        Layout.fillWidth: true
                        onAccepted: remoteFilesVm.changeRemotePath(text)
                    }

                    IconButton {
                        iconName: "mdi6.arrow-right"
                        tooltip: "跳转"
                        enabled: pane.enabled
                        onClicked: remoteFilesVm.changeRemotePath(pathField.text)
                    }

                    IconButton {
                        iconName: "mdi6.upload"
                        tooltip: "上传文件"
                        enabled: pane.enabled
                        onClicked: uploadFileDialog.open()
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // Column header
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 26
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 8

                    Label { text: ""; Layout.preferredWidth: 20 }
                    Label { text: "名称"; color: textMuted; font.pixelSize: 11; Layout.fillWidth: true }
                    Label { text: "大小"; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 86; horizontalAlignment: Text.AlignRight }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // File list + drop
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: fileList
                    anchors.fill: parent
                    clip: true
                    model: remoteFilesVm.remoteItems
                    delegate: Rectangle {
                        id: fileRow

                        required property var modelData
                        required property int index

                        width: ListView.view.width
                        height: 30
                        color: ListView.isCurrentItem ? selectedSoftBg : (fileMouse.containsMouse ? rowHover : (index % 2 === 0 ? surface : surfaceSubtle))

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 8

                            UiIcon {
                                Layout.preferredWidth: 17
                                Layout.preferredHeight: 17
                                iconSize: 17
                                name: modelData.isDir ? "mdi6.folder" : "mdi6.file-outline"
                                color: modelData.isDir ? "#0A84FF" : textMuted
                            }

                            Label {
                                text: modelData.name || ""
                                color: textMain
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Label {
                                text: modelData.isDir ? "" : root.formatSize(modelData.size || 0)
                                color: textMuted
                                font.pixelSize: 12
                                Layout.preferredWidth: 86
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        MouseArea {
                            id: fileMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            cursorShape: Qt.PointingHandCursor
                            onClicked: function(mouse) {
                                fileList.currentIndex = index
                                if (mouse.button === Qt.RightButton) {
                                    root.contextItem = modelData
                                    root.openPopupAtMouse(remoteFileMenu, fileMouse, mouse)
                                }
                            }
                            onDoubleClicked: {
                                if (modelData.isDir)
                                    remoteFilesVm.changeRemotePath(modelData.path || "")
                                else
                                    remoteFilesVm.downloadFiles([modelData])
                            }
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: pane.enabled && (remoteFilesVm.remoteItems || []).length === 0
                        text: "目录为空  ·  拖拽文件夹到此处即可上传"
                        color: textFaint
                        font.pixelSize: 12
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: !pane.enabled
                        text: "请选择并连接远程主机"
                        color: textFaint
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    id: emptyAreaMouse
                    anchors.fill: parent
                    acceptedButtons: Qt.RightButton
                    propagateComposedEvents: true
                    onClicked: function(mouse) {
                        // empty-area right click -> menu without selection
                        var ix = fileList.indexAt(mouse.x, mouse.y + fileList.contentY)
                        if (ix < 0) {
                            root.contextItem = null
                            root.openPopupAtMouse(remoteFileMenu, emptyAreaMouse, mouse)
                        } else {
                            mouse.accepted = false
                        }
                    }
                }

                DropArea {
                    anchors.fill: parent
                    enabled: pane.enabled
                    onEntered: function(event) {
                        if (event.hasUrls)
                            dropOverlay.visible = true
                        else
                            event.accepted = false
                    }
                    onExited: dropOverlay.visible = false
                    onDropped: function(event) {
                        dropOverlay.visible = false
                        if (!event.hasUrls)
                            return
                        var paths = []
                        var urls = event.urls || []
                        for (var i = 0; i < urls.length; i++)
                            paths.push(urls[i].toString())
                        if (paths.length > 0)
                            remoteFilesVm.uploadPaths(paths)
                    }
                }

                Rectangle {
                    id: dropOverlay
                    anchors.fill: parent
                    anchors.margins: 6
                    visible: false
                    radius: 10
                    color: dark ? Qt.rgba(0.04, 0.52, 1.0, 0.18) : Qt.rgba(0.04, 0.52, 1.0, 0.12)
                    border.width: 2
                    border.color: selectedBg

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        UiIcon {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 36
                            Layout.preferredHeight: 36
                            iconSize: 36
                            name: "mdi6.cloud-upload-outline"
                            color: selectedBg
                        }
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: "释放以上传到 " + remoteFilesVm.remotePath
                            color: selectedBg
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }
        }
    }

    component TerminalPane: Rectangle {
        id: terminalPane
        color: dark ? "#101014" : "#FFFFFF"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 10

                    UiIcon {
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconSize: 14
                        name: "mdi6.console-line"
                        color: root.sftpConnected ? success : textMuted
                    }

                    Label {
                        text: "SSH 终端"
                        color: textMain
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Label {
                        text: root.sftpConnected ? "就绪" : "未连接 SFTP"
                        color: root.sftpConnected ? success : textFaint
                        font.pixelSize: 11
                    }

                    Item { Layout.fillWidth: true }

                    IconButton {
                        iconName: "mdi6.play"
                        tooltip: "打开终端"
                        enabled: root.sftpConnected
                        onClicked: remoteFilesVm.openTerminal()
                    }

                    IconButton {
                        iconName: "mdi6.stop"
                        tooltip: "关闭终端"
                        enabled: root.sftpConnected
                        onClicked: remoteFilesVm.closeTerminal()
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            QtObject {
                id: terminalProxy
                WebChannel.id: "remoteTerminalBridge"
                signal output(string text)
                signal closed(string message)
                function sendInput(text) {
                    remoteFilesVm.terminalBridge.sendInput(text)
                }
                function resize(cols, rows) {
                    remoteFilesVm.terminalBridge.resize(cols, rows)
                }
            }

            Connections {
                target: remoteFilesVm.terminalBridge
                function onOutput(text) { terminalProxy.output(text) }
                function onClosed(message) { terminalProxy.closed(message) }
            }

            WebChannel {
                id: terminalChannel
                registeredObjects: [terminalProxy]
            }

            WebEngineView {
                id: terminalView
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: Qt.resolvedUrl("assets/terminal.html")
                webChannel: terminalChannel
                onNavigationRequested: function(request) {
                    if (request.url.toString().indexOf(Qt.resolvedUrl("assets/terminal.html").toString()) !== 0)
                        request.action = WebEngineNavigationRequest.IgnoreRequest
                }
                onContextMenuRequested: function(request) {
                    request.accepted = true
                    webContextMenu.editFlags = request.editFlags
                    webContextMenu.hasSelection = (request.selectedText || "").length > 0
                    var p = terminalView.mapToItem(Overlay.overlay, request.position.x, request.position.y)
                    webContextMenu.x = p.x
                    webContextMenu.y = p.y
                    webContextMenu.open()
                }
            }

            Popup {
                id: webContextMenu
                parent: Overlay.overlay
                width: 200
                height: webContextMenuColumn.implicitHeight + 8
                padding: 4
                modal: false
                focus: true
                closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
                property int editFlags: 0
                property bool hasSelection: false
                // bit constants matching Qt's WebEngineContextMenuRequest::EditFlag
                readonly property int flagCanUndo: 0x1
                readonly property int flagCanRedo: 0x2
                readonly property int flagCanCut: 0x4
                readonly property int flagCanCopy: 0x8
                readonly property int flagCanPaste: 0x10
                readonly property int flagCanSelectAll: 0x40
                enter: Transition {
                    ParallelAnimation {
                        NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                        NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                    }
                }
                background: UiMenuSurface { dark: root.dark; radius: 8 }
                contentItem: Column {
                    id: webContextMenuColumn
                    spacing: 0

                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "撤销"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanUndo) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Undo); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "重做"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanRedo) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Redo); webContextMenu.close() }
                    }
                    UiMenuSeparator { width: webContextMenu.width - 8; dark: root.dark }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "剪切"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanCut) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Cut); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "复制"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanCopy) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Copy); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "粘贴"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanPaste) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Paste); webContextMenu.close() }
                    }
                    UiMenuSeparator { width: webContextMenu.width - 8; dark: root.dark }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "全选"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanSelectAll) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.SelectAll); webContextMenu.close() }
                    }
                }
            }
        }
    }

    component IconButton: Rectangle {
        id: control

        property string iconName: ""
        property string tooltip: ""
        property bool accent: false
        property bool dangerRole: false
        signal clicked()

        implicitWidth: 30
        implicitHeight: 28
        radius: 7
        opacity: enabled ? 1.0 : 0.45
        color: {
            if (control.accent)
                return iconMouse.pressed ? Qt.darker(selectedBg, 1.15) : selectedBg
            if (iconMouse.containsMouse || iconMouse.pressed)
                return rowHover
            return "transparent"
        }
        border.width: control.accent ? 0 : 1
        border.color: iconMouse.containsMouse && !control.accent ? separator : "transparent"

        UiIcon {
            anchors.centerIn: parent
            width: 16
            height: 16
            iconSize: 16
            name: control.iconName
            color: {
                if (control.accent)
                    return "#FFFFFF"
                if (control.dangerRole)
                    return danger
                return textMuted
            }
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
        property string iconName: ""
        property bool accent: false
        signal clicked()

        implicitWidth: Math.max(accent ? 92 : 76, contentRow.implicitWidth + 24)
        implicitHeight: 30
        radius: 7
        opacity: enabled ? 1.0 : 0.45
        color: {
            if (control.accent)
                return buttonMouse.pressed ? Qt.darker(selectedBg, 1.15) : selectedBg
            if (buttonMouse.containsMouse || buttonMouse.pressed)
                return rowHover
            return root.dark ? "#2A303C" : "#FFFFFF"
        }
        border.width: control.accent ? 0 : 1
        border.color: separator

        RowLayout {
            id: contentRow
            anchors.centerIn: parent
            spacing: 6

            UiIcon {
                visible: control.iconName.length > 0
                Layout.preferredWidth: 15
                Layout.preferredHeight: 15
                iconSize: 15
                name: control.iconName
                color: control.accent ? "#FFFFFF" : textMuted
            }

            Label {
                text: control.label
                color: control.accent ? "#FFFFFF" : textMain
                font.pixelSize: 12
                font.weight: Font.Medium
            }
        }

        MouseArea {
            id: buttonMouse

            anchors.fill: parent
            enabled: control.enabled
            hoverEnabled: true
            cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: control.clicked()
        }
    }
}
