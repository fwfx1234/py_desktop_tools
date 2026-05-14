import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"
import "pages"

Item {
    id: root

    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color border: Theme.token("color-border-default", dark)
    readonly property color primary: Theme.token("color-primary-active", dark)

    property int currentPage: 0
    property var pages: [
        { title: "基础元素",     source: "BasicElementsPage.qml" },
        { title: "布局系统",     source: "LayoutPage.qml" },
        { title: "属性绑定",     source: "BindingPage.qml" },
        { title: "信号与槽",     source: "SignalsPage.qml" },
        { title: "控件大全",     source: "ControlsPage.qml" },
        { title: "自定义组件",   source: "ComponentsPage.qml" },
        { title: "ListView",     source: "ListViewPage.qml" },
        { title: "主题系统",     source: "ThemePage.qml" },
        { title: "动画效果",     source: "AnimationPage.qml" },
        { title: "Dialog 弹窗",  source: "DialogPage.qml" },
        { title: "Loader 加载",  source: "LoaderPage.qml" },
        { title: "TabBar 选项卡",source: "TabBarPage.qml" },
        { title: "Timer + 状态", source: "TimerStatePage.qml" },
        { title: "Slider 滑块",  source: "InputWidgetsPage.qml" },
        { title: "ToolTip/Menu", source: "TooltipMenuPage.qml" },
        { title: "Gradient/Flow",source: "GradientFlowPage.qml" },
        { title: "Keys/Shortcut",source: "KeysShortcutPage.qml" },
    ]

    Component.onCompleted: {
        qmlDemoVm.filterItems("")
    }

    Rectangle { anchors.fill: parent; color: Theme.token("color-bg-page", dark) }

    RowLayout {
        anchors.fill: parent; anchors.margins: 8; spacing: 8

        // ---- Sidebar ----
        Rectangle {
            Layout.preferredWidth: 180; Layout.fillHeight: true; radius: 10; color: root.panelBg
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 4

                Label {
                    text: "QML 学习演示"
                    font.pixelSize: 15; font.bold: true; color: root.textMain
                    Layout.fillWidth: true; Layout.bottomMargin: 8
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.border }

                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2
                    model: root.pages
                    delegate: Rectangle {
                        width: ListView.view.width; height: 34; radius: 6
                        color: index === root.currentPage ? Theme.token("color-primary-bg", root.dark) : "transparent"
                        Label {
                            anchors.centerIn: parent
                            text: modelData.title
                            font.pixelSize: 13
                            color: index === root.currentPage
                                ? Theme.token("color-primary-active", root.dark) : root.textMain
                        }
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.currentPage = index
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.border }

                Label {
                    text: "提示：按下 Alt+Space\n打开启动器搜索"
                    font.pixelSize: 10; color: root.textSubtle
                    Layout.fillWidth: true
                }
            }
        }

        // ---- Main content ----
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: root.panelBg
            border.color: root.border

            StackLayout {
                anchors.fill: parent; anchors.margins: 12
                currentIndex: root.currentPage

                BasicElementsPage { dark: root.dark; primary: root.primary }
                LayoutPage { dark: root.dark; primary: root.primary }
                BindingPage { dark: root.dark; primary: root.primary }
                SignalsPage { dark: root.dark; primary: root.primary }
                ControlsPage { dark: root.dark; primary: root.primary }
                ComponentsPage { dark: root.dark; primary: root.primary }
                ListViewPage { dark: root.dark; primary: root.primary }
                ThemePage { dark: root.dark; primary: root.primary }
                AnimationPage { dark: root.dark; primary: root.primary }
                DialogPage { dark: root.dark; primary: root.primary }
                LoaderPage { dark: root.dark; primary: root.primary }
                TabBarPage { dark: root.dark; primary: root.primary }
                TimerStatePage { dark: root.dark; primary: root.primary }
                InputWidgetsPage { dark: root.dark; primary: root.primary }
                TooltipMenuPage { dark: root.dark; primary: root.primary }
                GradientFlowPage { dark: root.dark; primary: root.primary }
                KeysShortcutPage { dark: root.dark; primary: root.primary }
            }
        }
    }
}
