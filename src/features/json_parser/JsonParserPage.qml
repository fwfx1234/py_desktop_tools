import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    property string tipText: ""

    function runParse() {
        jsonParserVm.processJson(input.text, query.text)
    }

    Component.onCompleted: {
        input.text = jsonParserVm.initialText()
        runParse()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4
        spacing: Theme.spacing.s2
        Label { text: "JSON 解析"; font.bold: true; font.pixelSize: Theme.typeScale.title; color: textMain; font.family: "IBM Plex Sans" }
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 10
                color: "transparent"
            }

            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.5
                Label { text: "JSON 输入"; color: textMain }
                UiScrollView {
                    id: inputScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded

                    UiTextArea {
                        id: input
                        dark: dark
                        width: Math.max(inputScroll.availableWidth, contentWidth + leftPadding + rightPadding)
                        height: Math.max(inputScroll.availableHeight, contentHeight + topPadding + bottomPadding)
                    placeholderText: "输入 JSON..."
                        wrapMode: TextEdit.NoWrap
                        onTextChanged: runParse()
                    }
                }
                Label { text: "JSONPath 查询"; color: textMain }
                UiTextField {
                    id: query
                    dark: dark
                    Layout.fillWidth: true
                    placeholderText: "$.foo.bar"
                    onTextChanged: runParse()
                }
                RowLayout {
                    Layout.fillWidth: true
                    UiButton { text: "执行"; dark: dark; variant: "primary"; onClicked: runParse() }
                    UiButton { text: "清空"; dark: dark; variant: "secondary"; onClicked: { input.text = ""; query.text = ""; output.text = ""; err.text = ""; tipText = "" } }
                    UiButton { text: "复制输出"; dark: dark; variant: "secondary"; onClicked: jsonParserVm.copyText(output.text) }
                }
                Label { id: err; color: Theme.token("color-danger", dark) }
                Label { text: tipText; color: Theme.token("color-success", dark); visible: tipText.length > 0 }
            }

            ColumnLayout {
                Label { text: "输出"; color: textMain }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Theme.token("color-bg-subtle", dark)
                    radius: Theme.radius.lg
                    UiScrollView {
                        id: outputScroll
                        anchors.fill: parent
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AsNeeded

                        UiTextArea {
                            id: output
                            dark: dark
                            width: Math.max(outputScroll.availableWidth, contentWidth + leftPadding + rightPadding)
                            height: Math.max(outputScroll.availableHeight, contentHeight + topPadding + bottomPadding)
                            readOnly: true
                            wrapMode: TextEdit.NoWrap
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: jsonParserVm
        function onJsonProcessed(text, errorText) {
            output.text = text
            err.text = errorText
            if (errorText.length > 0)
                tipText = ""
        }
        function onJsonCopied(ok, message) {
            tipText = ok ? message : ""
            if (!ok)
                err.text = message
        }
        function onInputTextChanged(text) {
            if (input.text !== text)
                input.text = text
            runParse()
        }
    }
}
