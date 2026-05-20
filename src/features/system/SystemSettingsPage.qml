import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    readonly property bool hasSettingsVm: typeof systemSettingsVm !== "undefined" && systemSettingsVm
    readonly property bool hasApp: typeof app !== "undefined" && app
    readonly property bool dark: hasApp ? app.theme === "dark" : false
    readonly property bool isMacos: hasApp ? app.isMacos : false
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property string appIndexStatus: !hasSettingsVm ? "应用索引不可用" : (systemSettingsVm.appScanRunning ? "正在后台重扫描应用" : ("已缓存应用：" + systemSettingsVm.appCount))

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2.5"]
        Label { text: "系统设置"; font.bold: true; font.pixelSize: Theme.fontSize.title; color: textMain; font.family: Theme.fontFamily.ui }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 9
            radius: Theme.radii.xl
            color: panelBg
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                Label { text: "主题模式"; font.bold: true; color: textMain }
                RowLayout {
                    RadioButton { text: "浅色"; checked: hasApp && app.themeMode === "light"; onClicked: if (hasApp) app.setTheme("light") }
                    RadioButton { text: "深色"; checked: hasApp && app.themeMode === "dark"; onClicked: if (hasApp) app.setTheme("dark") }
                    RadioButton { text: "跟随系统"; checked: hasApp && app.themeMode === "auto"; onClicked: if (hasApp) app.setTheme("auto") }
                }
                Label { text: "已启用本地数据存储"; color: textMuted }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 10
            radius: Theme.radii.xl
            color: panelBg
            border.width: 1
            border.color: panelBorder

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                spacing: Theme.space["3"]

                Rectangle {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    Layout.alignment: Qt.AlignVCenter
                    radius: Theme.radii.md
                    color: Theme.token("color-primary-bg", dark)

                    UiIcon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        name: "mdi6.application-cog-outline"
                        color: Theme.token("color-primary", dark)
                        iconSize: 22
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 4

                    Label { text: "应用索引"; font.bold: true; color: textMain; font.family: Theme.fontFamily.ui }
                    Label { text: appIndexStatus; color: textMuted; font.pixelSize: Theme.fontSize.body; font.family: Theme.fontFamily.ui }
                }

                Button {
                    id: rescanButton
                    Layout.preferredWidth: 128
                    Layout.preferredHeight: 34
                    enabled: hasSettingsVm && !systemSettingsVm.appScanRunning
                    hoverEnabled: true
                    readonly property color contentColor: enabled ? Theme.token("color-bg-surface", false) : textMuted

                    background: Rectangle {
                        radius: Theme.radii.md
                        color: !rescanButton.enabled ? Theme.token("color-bg-subtle", dark) : (rescanButton.down ? Theme.token("color-primary-active", dark) : (rescanButton.hovered ? Theme.token("color-primary", dark) : Theme.token("color-primary-active", dark)))
                    }

                    contentItem: RowLayout {
                        spacing: 6

                        UiIcon {
                            Layout.preferredWidth: 16
                            Layout.preferredHeight: 16
                            name: "mdi6.refresh"
                            color: rescanButton.contentColor
                            iconSize: 16
                        }

                        Label {
                            Layout.fillWidth: true
                            text: hasSettingsVm && systemSettingsVm.appScanRunning ? "扫描中" : "重扫描"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color: rescanButton.contentColor
                            font.pixelSize: Theme.fontSize.body
                            font.family: Theme.fontFamily.ui
                        }
                    }

                    onClicked: {
                        if (hasSettingsVm)
                            systemSettingsVm.rescanApplications()
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 10
            radius: Theme.radii.xl
            color: panelBg
            border.width: 1
            border.color: panelBorder

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                spacing: Theme.space["3"]

                Rectangle {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    Layout.alignment: Qt.AlignVCenter
                    radius: Theme.radii.md
                    color: Theme.token("color-primary-bg", dark)

                    UiIcon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        name: "mdi6.shield-key-outline"
                        color: Theme.token("color-primary", dark)
                        iconSize: 22
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 4

                    Label { text: "macOS 权限"; font.bold: true; color: textMain; font.family: Theme.fontFamily.ui }
                    Label {
                        text: hasSettingsVm ? systemSettingsVm.accessibilityStatusText : "辅助功能权限：未知"
                        color: textMuted
                        font.pixelSize: Theme.fontSize.body
                        font.family: Theme.fontFamily.ui
                    }
                }

                Button {
                    id: accessibilityButton
                    Layout.preferredWidth: 128
                    Layout.preferredHeight: 34
                    visible: isMacos
                    enabled: hasSettingsVm
                    hoverEnabled: true
                    readonly property color contentColor: enabled ? Theme.token("color-bg-surface", false) : textMuted

                    background: Rectangle {
                        radius: Theme.radii.md
                        color: !accessibilityButton.enabled ? Theme.token("color-bg-subtle", dark) : (accessibilityButton.down ? Theme.token("color-primary-active", dark) : (accessibilityButton.hovered ? Theme.token("color-primary", dark) : Theme.token("color-primary-active", dark)))
                    }

                    contentItem: Label {
                        text: hasSettingsVm && systemSettingsVm.accessibilityAuthorized ? "已授权" : "去授权"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: accessibilityButton.contentColor
                        font.pixelSize: Theme.fontSize.body
                        font.family: Theme.fontFamily.ui
                    }

                    onClicked: {
                        if (hasSettingsVm)
                            systemSettingsVm.openAccessibilitySettings()
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 12
            radius: Theme.radii.xl
            color: panelBg
            border.width: 1
            border.color: panelBorder
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                spacing: Theme.space["2"]
                Label { text: "开发诊断"; font.bold: true; color: textMain }
                Label { text: "数据目录：" + diagnostics.dataDir; color: textMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: "日志目录：" + diagnostics.logDir; color: textMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: "插件数量：" + diagnostics.pluginCount; color: textMuted }
                Label { text: "后台插件：" + diagnostics.backgroundPlugins; color: textMuted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
    }

    property var diagnostics: (hasSettingsVm ? systemSettingsVm.diagnostics() : ({}))
}
