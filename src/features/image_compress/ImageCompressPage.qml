import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../app/ui"
import "../../app/theme"

Item {
    property var selectedFiles: []
    property int quality: 80
    property string mode: "visual"
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    function setSelectedFiles(files) {
        selectedFiles = files || []
        result.text = selectedFiles.length > 0
            ? ("已选择 " + selectedFiles.length + " 个图片文件\n" + selectedFiles.join("\n"))
            : ""
    }

    Component.onCompleted: setSelectedFiles(imageCompressVm.initialFiles())

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4
        spacing: Theme.spacing.s3

        Label { text: "图片压缩"; font.bold: true; font.pixelSize: Theme.typeScale.title; color: textMain; font.family: "IBM Plex Sans" }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.spacing.s4 * 6 + Theme.spacing.s1
            radius: Theme.radius.xl
            color: panelBg
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.s4
                UiButton {
                    text: "视觉无损"
                    checkable: true
                    checked: mode === "visual"
                    dark: dark
                    variant: checked ? "primary" : "secondary"
                    onClicked: mode = "visual"
                }
                UiButton {
                    text: "普通压缩"
                    checkable: true
                    checked: mode === "normal"
                    dark: dark
                    variant: checked ? "primary" : "secondary"
                    onClicked: mode = "normal"
                }
                Label { text: "质量 " + quality + "%"; color: textMain; font.family: "JetBrains Mono"; font.pixelSize: Theme.typeScale.mono }
                UiSlider {
                    dark: dark
                    from: 10
                    to: 100
                    value: quality
                    onValueChanged: quality = Math.round(value)
                    Layout.fillWidth: true
                }
            }
        }
        RowLayout {
            UiButton {
                text: "选择图片"
                dark: dark
                variant: "secondary"
                onClicked: picker.open()
            }
            UiButton {
                text: "开始压缩"
                dark: dark
                variant: "primary"
                onClicked: imageCompressVm.compressImages(selectedFiles, quality, mode)
            }
        }
        UiTextArea {
            id: result
            dark: dark
            Layout.fillWidth: true
            Layout.fillHeight: true
            readOnly: true
            placeholderText: "压缩结果会显示在这里..."
            wrapMode: TextEdit.WrapAnywhere
        }
    }

    FileDialog {
        id: picker
        title: "选择图片文件"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"]
        onAccepted: {
            var paths = []
            for (var i = 0; i < picker.selectedFiles.length; i++)
                paths.push(String(picker.selectedFiles[i]).replace("file:///", ""))
            setSelectedFiles(selectedFiles.concat(paths))
        }
    }

    Connections {
        target: imageCompressVm
        function onImageCompressed(text) { result.text = text }
        function onFilesChanged(files) { setSelectedFiles(files) }
    }
}
