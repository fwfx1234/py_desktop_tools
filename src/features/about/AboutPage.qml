import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/theme"

Item {
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    ColumnLayout {
        anchors.centerIn: parent
        spacing: Theme.space["2"]
        Rectangle {
            width: 72
            height: 72
            radius: Theme.radii.xl + Theme.space["1"]
            color: Theme.token("color-nav-active-bg", dark)
            Label { anchors.centerIn: parent; text: "DT"; font.pixelSize: Theme.fontSize.title + 2; font.bold: true; color: Theme.token("color-primary-active", dark) }
        }
        Label { text: "桌面工具箱"; font.bold: true; font.pixelSize: Theme.fontSize.title + 2; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; color: textMain; font.family: Theme.fontFamily.ui }
        Label { text: "版本 1.0.0"; color: textMuted; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
        Label { text: "QML + PySide6"; color: textMuted; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
        Rectangle {
            width: 420
            height: 44
            radius: Theme.radii.lg
            color: panelBg
            Label {
                anchors.centerIn: parent
                text: "集成 API 调试、下载、抓包、图片压缩与 JSON 处理"
                color: textMuted
            }
        }
    }
}
