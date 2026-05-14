import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    property bool dark: false
    property int cornerRadius: Theme.radius.md
    property color fillColor: Theme.token("color-bg-subtle", control.dark)
    property color hoverFillColor: Theme.token("color-bg-subtle-2", control.dark)
    property color textColor: Theme.token("color-text-primary", control.dark)
    property color mutedColor: Theme.token("color-text-regular", control.dark)
    property var itemColorFn: null

    implicitHeight: Theme.spacing.s4 * 3
    hoverEnabled: true
    font.family: "IBM Plex Sans"
    font.pixelSize: Theme.typeScale.body

    palette.buttonText: control.textColor
    palette.text: control.textColor

    contentItem: Text {
        text: control.displayText
        color: control.textColor
        font: control.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        leftPadding: Theme.spacing.s2
        rightPadding: Theme.spacing.s4
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.cornerRadius
        color: control.down || control.hovered ? control.hoverFillColor : control.fillColor
        border.width: 1
        border.color: control.visualFocus
            ? Theme.token("color-primary-active", control.dark)
            : Theme.token("color-border-default", control.dark)
    }

    indicator: Canvas {
        id: arrowCanvas
        x: control.width - width - Theme.spacing.s2
        y: (control.height - height) / 2
        width: 10
        height: 6
        contextType: "2d"

        Connections {
            target: control
            function onPressedChanged() { arrowCanvas.requestPaint() }
            function onHoveredChanged() { arrowCanvas.requestPaint() }
        }

        onPaint: {
            context.reset()
            context.moveTo(0, 0)
            context.lineTo(width, 0)
            context.lineTo(width / 2, height)
            context.closePath()
            context.fillStyle = control.mutedColor
            context.fill()
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 280)

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            spacing: 2
        }

        background: UiPopupSurface {
            dark: control.dark
            radius: control.cornerRadius
            fillColor: Theme.token("color-bg-surface", control.dark)
        }
    }

    delegate: ItemDelegate {
        id: optionDelegate
        required property int index
        required property var modelData

        width: control.width - 8
        height: 34
        text: typeof modelData === "object" && modelData !== null && control.textRole.length > 0
            ? (modelData[control.textRole] ?? "")
            : ("" + modelData)
        font: control.font
        padding: Theme.spacing.s2
        highlighted: control.highlightedIndex === index

        background: Rectangle {
            radius: Theme.radius.sm
            color: optionDelegate.highlighted || optionDelegate.hovered
                ? Theme.token("color-bg-subtle", control.dark)
                : "transparent"
        }

        contentItem: Text {
            text: parent.text
            color: control.itemColorFn
                ? control.itemColorFn(optionDelegate.index, optionDelegate.modelData)
                : control.textColor
            font: parent.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }
}
