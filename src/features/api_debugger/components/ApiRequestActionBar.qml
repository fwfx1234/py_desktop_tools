import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color panelBorder: "#D0D7DE"
    property color textMuted: "#666666"
    property var methodModel: ["GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS","WS"]
    property var methodColorFn: null
    property bool sending: false
    property string modeText: getMethodText() === "WS" ? "WebSocket" : "HTTP"
    property string baseUrlText: ""
    property string pathText: "/"
    property bool pathFieldReady: false
    property bool _settingPath: false

    signal methodTextChanged(string value)
    signal requestPathEdited(string value)
    signal sendClicked()

    color: root.panelBg

    function setMethodText(value) {
        var idx = methodCombo.model.indexOf(value)
        if (idx >= 0)
            methodCombo.currentIndex = idx
    }

    function getMethodText() {
        return methodCombo.currentText
    }

    function setPathText(value) {
        if (!root.pathFieldReady || root._settingPath)
            return
        root._settingPath = true
        var next = value || "/"
        if (pathField.text !== next)
            pathField.text = next
        root._settingPath = false
    }

    function getPathText() {
        return pathField.text || "/"
    }

    function displayBaseUrl() {
        return root.baseUrlText || "未设置 Base URL"
    }

    function displayPath() {
        return root.pathText || "/"
    }

    onPathTextChanged: if (root.pathFieldReady) setPathText(root.displayPath())

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["2"]
        anchors.rightMargin: Theme.space["2"]
        spacing: Theme.space["1"]

        UiComboBox {
            id: methodCombo
            dark: root.dark
            compact: true
            model: root.methodModel
            Layout.preferredWidth: 82
            Layout.preferredHeight: 30
            cornerRadius: Theme.radii.xs
            fillColor: root.panelBg
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.mono
            font.bold: false
            itemColorFn: function(index, modelData) {
                return root.methodColorFn ? root.methodColorFn(modelData) : undefined
            }
            Component.onCompleted: currentIndex = 0
            onCurrentTextChanged: root.methodTextChanged(currentText)
        }

        Rectangle {
            id: urlField
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            radius: Theme.radii.md
            color: root.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-surface", false)
            border.width: pathField.activeFocus ? 2 : 0
            border.color: Theme.token("color-primary-active", root.dark)
            clip: true

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["1"]

                Label {
                    id: baseUrlLabel
                    Layout.maximumWidth: Math.max(120, Math.min(360, urlField.width * 0.42))
                    text: root.displayBaseUrl()
                    color: root.textMuted
                    font.pixelSize: Theme.fontSize.body
                    elide: Text.ElideMiddle
                    verticalAlignment: Text.AlignVCenter
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 18
                    color: Theme.token("color-border-default", root.dark)
                    opacity: 0.65
                }

                TextField {
                    id: pathField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    color: Theme.token("color-text-primary", root.dark)
                    placeholderText: "/path"
                    placeholderTextColor: root.textMuted
                    selectByMouse: true
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    verticalAlignment: TextInput.AlignVCenter
                    font.pixelSize: Theme.fontSize.body
                    font.family: Theme.fontFamily.mono
                    background: Item {}
                    onTextChanged: {
                        if (!root._settingPath && root.pathFieldReady)
                            root.requestPathEdited(text)
                    }
                }
            }

            Component.onCompleted: {
                root.pathFieldReady = true
                root.setPathText(root.displayPath())
            }
        }

        Rectangle {
            Layout.preferredWidth: modeLabel.implicitWidth + Theme.space["3"]
            Layout.preferredHeight: 24
            radius: Theme.radii.xs
            color: Theme.token("color-bg-subtle", root.dark)
            Label {
                id: modeLabel
                anchors.centerIn: parent
                text: root.modeText
                color: root.textMuted
                font.pixelSize: Theme.fontSize.caption
            }
        }

        UiButton {
            text: root.sending ? "发送中" : "发送"
            dark: root.dark
            variant: "primary"
            enabled: !root.sending
            implicitWidth: 84
            implicitHeight: 30
            onClicked: root.sendClicked()
            contentItem: Row {
                spacing: 6
                anchors.centerIn: parent
                width: implicitWidth
                height: parent.height

                Rectangle {
                    visible: root.sending
                    width: 12
                    height: 12
                    radius: 6
                    anchors.verticalCenter: parent.verticalCenter
                    color: "transparent"
                    border.width: 2
                    border.color: Theme.token("color-bg-surface", false)
                    opacity: 0.9

                    Rectangle {
                        width: 5
                        height: 5
                        radius: 2.5
                        color: Theme.token("color-bg-surface", false)
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    RotationAnimator on rotation {
                        running: root.sending
                        loops: Animation.Infinite
                        from: 0
                        to: 360
                        duration: 800
                    }
                }

                Text {
                    text: root.sending ? "发送中" : "发送"
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.token("color-bg-surface", false)
                    font.pixelSize: Theme.fontSize.body
                    font.family: Theme.fontFamily.ui
                }
            }
        }
    }
}
