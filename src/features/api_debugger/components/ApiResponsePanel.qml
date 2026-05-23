import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

ColumnLayout {
    id: root

    spacing: 0

    property bool dark: false
    property color panelBg
    property color panelBorder
    property color textMain
    property color textMuted
    property color textSubtle
    property color softBorder
    property bool mockMode: false
    property bool assertionsEnabled: true
    property int detailTab: 0
    property var detailTabs: [
        { title: "Body", icon: "mdi6.code-json" },
        { title: "Headers", icon: "mdi6.format-header-pound" },
        { title: "Request", icon: "mdi6.send-outline" },
        { title: "cURL", icon: "mdi6.console-line" },
        { title: "日志", icon: "mdi6.text-box-search-outline" }
    ]
    property string bodyText: ""
    property string bodyHtml: ""
    property string headersText: ""
    property string requestText: ""
    property string curlText: ""
    property string requestLogText: ""
    property var logEntries: []
    property string titleText: "返回响应"
    property string statusCode: ""
    property string elapsedMs: ""
    property string finalUrl: ""
    property string outcome: "idle"

    signal mockModeToggled(bool checked)
    signal assertionsToggled(bool checked)

    function responseHasContent() {
        return bodyText.length > 0
            || headersText.length > 0
            || requestText.length > 0
            || curlText.length > 0
            || requestLogText.length > 0
    }

    function currentResponseText() {
        if (detailTab === 1) return headersText || "暂无响应头"
        if (detailTab === 2) return requestText || "暂无实际请求"
        if (detailTab === 3) return curlText || "暂无 cURL"
        if (detailTab === 4) return requestLogText || "暂无请求日志"
        return bodyText || ""
    }

    function outcomeColor() {
        if (outcome === "success")
            return Theme.token("color-success", root.dark)
        if (outcome === "error")
            return Theme.token("color-danger", root.dark)
        if (outcome === "mock")
            return Theme.token("color-warning", root.dark)
        if (outcome === "ws" || outcome === "redirect")
            return Theme.token("color-info", root.dark)
        return root.textSubtle
    }

    function statusText() {
        if (statusCode.length > 0)
            return statusCode
        if (titleText.indexOf("MOCK") >= 0)
            return "MOCK"
        if (titleText.indexOf("WS") >= 0)
            return "WS"
        if (titleText.indexOf("ERR") >= 0)
            return "ERR"
        return responseHasContent() ? "DONE" : "IDLE"
    }

    function metricText() {
        var items = []
        if (elapsedMs.length > 0)
            items.push(elapsedMs + " ms")
        if (bodyText.length > 0)
            items.push(bodyText.length + " chars")
        return items.join("  ")
    }

    function summaryText() {
        var t = (titleText || "").trim()
        if (!t)
            return ""
        var cleaned = t.replace(/^状态:\s*\S+\s*\|?\s*/, "")
        if (cleaned === t)
            return cleaned
        if (cleaned.length === 0)
            return "已完成"
        return cleaned
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: root.panelBg

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: root.panelBg
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["2"]
                    anchors.rightMargin: Theme.space["2"]
                    spacing: Theme.space["2"]

                    Rectangle {
                        Layout.preferredWidth: Math.max(54, statusLabel.implicitWidth + Theme.space["3"])
                        Layout.preferredHeight: 24
                        radius: Theme.radii.xs
                        color: Qt.rgba(root.outcomeColor().r, root.outcomeColor().g, root.outcomeColor().b, root.dark ? 0.24 : 0.12)
                        border.width: 1
                        border.color: Qt.rgba(root.outcomeColor().r, root.outcomeColor().g, root.outcomeColor().b, 0.36)
                        Label {
                            id: statusLabel
                            anchors.centerIn: parent
                            text: root.statusText()
                            color: root.outcomeColor()
                            font.pixelSize: Theme.fontSize.caption
                            font.family: Theme.fontFamily.mono
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label {
                            Layout.fillWidth: true
                            text: root.summaryText()
                            color: root.textMain
                            font.pixelSize: Theme.fontSize.body
                            elide: Text.ElideRight
                            visible: text.length > 0
                        }
                        Label {
                            Layout.fillWidth: true
                            text: root.metricText()
                            color: root.textSubtle
                            font.pixelSize: Theme.fontSize.caption
                            elide: Text.ElideRight
                            visible: text.length > 0
                        }
                    }

                    Row {
                        spacing: 6
                        Layout.alignment: Qt.AlignVCenter
                        Label {
                            text: "Mock"
                            color: root.textMuted
                            font.pixelSize: Theme.fontSize.caption
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        UiSwitch {
                            dark: root.dark
                            checked: root.mockMode
                            anchors.verticalCenter: parent.verticalCenter
                            onToggled: root.mockModeToggled(checked)
                        }
                    }

                    Row {
                        spacing: 6
                        Layout.alignment: Qt.AlignVCenter
                        Label {
                            text: "断言"
                            color: root.textMuted
                            font.pixelSize: Theme.fontSize.caption
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        UiSwitch {
                            dark: root.dark
                            checked: root.assertionsEnabled
                            anchors.verticalCenter: parent.verticalCenter
                            onToggled: root.assertionsToggled(checked)
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.panelBorder }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                color: root.panelBg
                visible: root.responseHasContent()

                Flickable {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["2"]
                    anchors.rightMargin: Theme.space["2"]
                    clip: true
                    interactive: contentWidth > width
                    boundsBehavior: Flickable.StopAtBounds
                    contentWidth: responseTabRow.implicitWidth
                    contentHeight: height

                    Row {
                        id: responseTabRow
                        height: parent.height
                        spacing: Theme.space["1"]

                        Repeater {
                            model: root.detailTabs
                            delegate: Rectangle {
                                id: responseTabItem
                                required property int index
                                required property var modelData
                                property bool active: index === root.detailTab
                                width: Math.max(70, responseTabContent.implicitWidth + Theme.space["3"])
                                height: 26
                                anchors.verticalCenter: parent.verticalCenter
                                radius: Theme.radii.xs
                                color: active
                                    ? Theme.token("color-bg-subtle", root.dark)
                                    : (responseTabMouse.containsMouse ? Theme.token("color-bg-subtle-2", root.dark) : "transparent")
                                Row {
                                    id: responseTabContent
                                    anchors.centerIn: parent
                                    spacing: 5
                                    Image {
                                        width: 13
                                        height: 13
                                        anchors.verticalCenter: parent.verticalCenter
                                        source: "image://qta/" + modelData.icon + ";color=" + ("" + (responseTabItem.active ? Theme.token("color-primary-active", root.dark) : root.textMain)).replace("#", "") + ";size=13"
                                        sourceSize.width: 13
                                        sourceSize.height: 13
                                        fillMode: Image.PreserveAspectFit
                                    }
                                    Label {
                                        text: modelData.title
                                        color: responseTabItem.active
                                            ? Theme.token("color-primary-active", root.dark)
                                            : root.textMain
                                        font.pixelSize: Theme.fontSize.caption
                                        font.bold: responseTabItem.active
                                    }
                                }
                                MouseArea {
                                    id: responseTabMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.detailTab = index
                                }
                            }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: root.responseHasContent() ? 1 : 0; color: root.panelBorder }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: Theme.space["2"]
                    visible: !root.responseHasContent()
                    UiIcon {
                        Layout.alignment: Qt.AlignHCenter
                        width: 34
                        height: 34
                        useQta: true
                        name: "mdi6.send-clock-outline"
                        color: root.textSubtle
                        iconSize: 34
                    }
                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: "等待响应"
                        color: root.textSubtle
                        font.pixelSize: Theme.fontSize.body
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Theme.space["2"]
                    radius: Theme.radii.xs
                    color: Theme.token("color-bg-subtle-2", root.dark)
                    border.width: 1
                    border.color: root.softBorder
                    visible: root.responseHasContent()
                    clip: true

                    UiScrollView {
                        id: responseScroll
                        anchors.fill: parent
                        anchors.margins: 1
                        clip: true
                        visible: root.detailTab !== 4
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: root.detailTab === 0 ? ScrollBar.AlwaysOff : ScrollBar.AsNeeded

                        TextArea {
                            id: responseTextArea
                            width: root.detailTab === 0
                                ? responseScroll.availableWidth
                                : Math.max(responseScroll.availableWidth, contentWidth + leftPadding + rightPadding)
                            height: Math.max(responseScroll.availableHeight, contentHeight + topPadding + bottomPadding)
                            readOnly: true
                            wrapMode: root.detailTab === 0 ? TextEdit.Wrap : TextEdit.NoWrap
                            selectByMouse: true
                            persistentSelection: true
                            color: Theme.token("color-text-primary", root.dark)
                            font.family: Theme.fontFamily.mono
                            font.pixelSize: Theme.fontSize.mono
                            leftPadding: Theme.space["2.5"]
                            rightPadding: Theme.space["2.5"]
                            topPadding: Theme.space["2.5"]
                            bottomPadding: Theme.space["2.5"]
                            textFormat: root.detailTab === 0 && root.bodyHtml.length > 0 ? TextEdit.RichText : TextEdit.PlainText
                            text: root.detailTab === 0 && root.bodyHtml.length > 0 ? root.bodyHtml : root.currentResponseText()
                            background: null
                        }
                    }

                    Connections {
                        target: root
                        function onDetailTabChanged() {
                            responseScroll.setContentX(0)
                            responseScroll.setContentY(0)
                        }
                    }

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: Theme.space["2"]
                        clip: true
                        visible: root.detailTab === 4
                        contentWidth: width
                        contentHeight: responseLogColumn.implicitHeight

                        ColumnLayout {
                            id: responseLogColumn
                            width: parent.width
                            spacing: Theme.space["2"]

                            Repeater {
                                model: root.logEntries
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: logBlock.implicitHeight + Theme.space["3"]
                                    radius: Theme.radii.xs
                                    color: Theme.token("color-bg-surface", root.dark)
                                    border.width: 1
                                    border.color: root.softBorder

                                    ColumnLayout {
                                        id: logBlock
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.space["2"]
                                        spacing: Theme.space["1"]
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                text: modelData.title || "请求日志"
                                                color: root.textMain
                                                font.pixelSize: Theme.fontSize.body
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                            Label {
                                                text: modelData.time || ""
                                                color: root.textSubtle
                                                font.pixelSize: Theme.fontSize.caption
                                            }
                                        }
                                        TextArea {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: Math.max(86, implicitHeight + Theme.space["2"])
                                            text: modelData.text || ""
                                            readOnly: true
                                            wrapMode: TextEdit.NoWrap
                                            selectByMouse: true
                                            color: root.textMain
                                            font.family: Theme.fontFamily.mono
                                            font.pixelSize: Theme.fontSize.mono
                                            padding: Theme.space["2"]
                                            background: Rectangle {
                                                radius: Theme.radii.xs
                                                color: Theme.token("color-bg-subtle", root.dark)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
