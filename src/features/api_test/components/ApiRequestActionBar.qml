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

    signal methodTextChanged(string value)
    signal urlTextChanged(string value)
    signal sendClicked()

    color: root.panelBg

    function setMethodText(value) {
        var idx = methodCombo.model.indexOf(value)
        if (idx >= 0)
            methodCombo.currentIndex = idx
    }

    function setUrlText(value) {
        urlField.text = value
    }

    function getMethodText() {
        return methodCombo.currentText
    }

    function getUrlText() {
        return urlField.text
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.s3
        anchors.rightMargin: Theme.spacing.s3
        spacing: Theme.spacing.s2

        UiComboBox {
            id: methodCombo
            dark: root.dark
            model: root.methodModel
            Layout.preferredWidth: 66
            Layout.preferredHeight: 28
            cornerRadius: Theme.radius.xs
            fillColor: root.panelBg
            font.pixelSize: Theme.typeScale.caption
            font.family: "JetBrains Mono"
            font.bold: false
            itemColorFn: function(index, modelData) {
                return root.methodColorFn ? root.methodColorFn(modelData) : undefined
            }
            Component.onCompleted: currentIndex = 1
            onCurrentTextChanged: root.methodTextChanged(currentText)
        }

        UiTextField {
            id: urlField
            dark: root.dark
            Layout.fillWidth: true
            placeholderText: "http://example.com/path 或 /path"
            text: "/admin/list"
            onTextChanged: root.urlTextChanged(text)
        }

        UiButton {
            text: root.sending ? "发送中" : "发送"
            dark: root.dark
            variant: "primary"
            enabled: !root.sending
            implicitWidth: 76
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
                    font.pixelSize: Theme.typeScale.body
                    font.family: "IBM Plex Sans"
                }
            }
        }
    }
}
