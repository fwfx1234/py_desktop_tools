import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    property bool dark: false
    property int cornerRadius: 6
    property bool compact: false
    property color fillColor: control.dark
        ? Theme.token("color-nav-icon-idle-bg", true)
        : Theme.token("color-bg-surface", false)
    property color hoverFillColor: control.dark
        ? Theme.token("color-bg-subtle", true)
        : Theme.token("color-bg-subtle-2", false)
    property color textColor: Theme.token("color-text-primary", control.dark)
    property color mutedColor: Theme.token("color-text-regular", control.dark)
    property color accentColor: "#0A84FF"
    property color borderColor: control.dark
        ? Qt.rgba(1, 1, 1, 0.18)
        : Qt.rgba(0, 0, 0, 0.20)
    property color hoverBorderColor: control.dark
        ? Qt.rgba(1, 1, 1, 0.28)
        : Qt.rgba(0, 0, 0, 0.28)
    property var itemColorFn: null

    implicitHeight: 28
    leftPadding: 10
    rightPadding: control.compact ? 24 : 30
    hoverEnabled: true
    font.family: Theme.fontFamily.ui
    font.pixelSize: 13

    palette.buttonText: control.textColor
    palette.text: control.textColor

    contentItem: Text {
        text: control.displayText
        color: control.textColor
        font: control.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.cornerRadius
        color: control.down || control.hovered ? control.hoverFillColor : control.fillColor
        border.width: 1
        border.color: control.activeFocus
            ? control.accentColor
            : (control.hovered ? control.hoverBorderColor : control.borderColor)
        antialiasing: true
    }

    indicator: Item {
        width: 16
        height: 16
        x: control.width - width - (control.compact ? 8 : 10)
        y: Math.round((control.height - height) / 2)

        UiIcon {
            anchors.fill: parent
            useQta: true
            name: "mdi6.chevron-down"
            color: control.mutedColor
            iconSize: 16
        }
    }

    popup: Popup {
        y: control.height + 4
        width: Math.max(control.width, 140)
        padding: 4
        implicitHeight: Math.min(popupList.contentHeight + 8, 320)

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            }
        }

        contentItem: ListView {
            id: popupList
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            spacing: 0
        }

        background: UiMenuSurface {
            dark: control.dark
            radius: 8
        }
    }

    delegate: UiMenuItem {
        id: optionDelegate
        required property int index
        required property var modelData

        width: (control.popup ? control.popup.width : control.width) - 8
        dark: control.dark
        reserveCheckSpace: true
        checked: control.currentIndex === index
        highlighted: control.highlightedIndex === index
        text: typeof modelData === "object" && modelData !== null && control.textRole.length > 0
            ? ("" + (modelData[control.textRole] ?? ""))
            : ("" + modelData)
        textColorOverride: {
            if (!control.itemColorFn) return "transparent"
            var c = control.itemColorFn(optionDelegate.index, optionDelegate.modelData)
            return c ? c : "transparent"
        }
        onTriggered: {
            control.currentIndex = index
            control.popup.close()
        }
    }
}
