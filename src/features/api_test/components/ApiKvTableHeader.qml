import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/theme"

ColumnLayout {
    id: root

    property bool dark: false
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property color tableHeaderBg: Theme.token("color-table-header", dark)
    property int checkWidth: 22
    property int keyWidth: 210
    property int valueWeight: 2
    property int typeWidth: 86
    property int descWidth: 180
    property int deleteWidth: 26
    property bool showTypeColumn: true
    property string keyTitle: "参数"
    property string valueTitle: "参数值"
    property string typeTitle: "类型"
    property string descTitle: "说明"

    spacing: 0
    Layout.fillWidth: true

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 32
        color: root.tableHeaderBg

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacing.s4
            anchors.rightMargin: Theme.spacing.s4
            spacing: Theme.spacing.s3

            Item { Layout.preferredWidth: root.checkWidth }
            Label {
                text: root.keyTitle
                color: root.textMuted
                Layout.preferredWidth: root.keyWidth
                font.pixelSize: Theme.typeScale.caption
                elide: Text.ElideRight
            }
            Label {
                text: root.valueTitle
                color: root.textMuted
                Layout.fillWidth: true
                Layout.horizontalStretchFactor: root.valueWeight
                font.pixelSize: Theme.typeScale.caption
                elide: Text.ElideRight
            }
            Label {
                text: root.typeTitle
                visible: root.showTypeColumn
                color: root.textMuted
                Layout.preferredWidth: root.showTypeColumn ? root.typeWidth : 0
                font.pixelSize: Theme.typeScale.caption
                elide: Text.ElideRight
            }
            Label {
                text: root.descTitle
                color: root.textMuted
                Layout.preferredWidth: root.descWidth
                font.pixelSize: Theme.typeScale.caption
                elide: Text.ElideRight
            }
            Item { Layout.preferredWidth: root.deleteWidth }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: root.panelBorder
    }
}
