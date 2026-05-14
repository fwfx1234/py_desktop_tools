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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4
        spacing: Theme.spacing.s3
        Label { text: "系统设置"; font.bold: true; font.pixelSize: Theme.typeScale.title; color: textMain; font.family: "IBM Plex Sans" }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.spacing.s4 * 9
            radius: Theme.radius.xl
            color: panelBg
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.s4
                Label { text: "主题模式"; font.bold: true; color: textMain }
                RowLayout {
                    RadioButton { text: "浅色"; checked: app.theme === "light"; onClicked: app.setTheme("light") }
                    RadioButton { text: "深色"; checked: app.theme === "dark"; onClicked: app.setTheme("dark") }
                }
                Label { text: "已启用本地数据存储"; color: textMuted }
            }
        }
    }
}
