import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    property bool dark: false
    property int cornerRadius: Theme.radii.md
    property color fillColor: Theme.token("color-bg-subtle", control.dark)
    property color hoverFillColor: Theme.token("color-bg-subtle-2", control.dark)
    property color textColor: Theme.token("color-text-primary", control.dark)
    property color mutedColor: Theme.token("color-text-regular", control.dark)
    property var itemColorFn: null

    implicitHeight: Theme.space["3"] * 3
    hoverEnabled: true
    font.family: Theme.fontFamily.ui
    font.pixelSize: Theme.fontSize.body

    palette.buttonText: control.textColor
    palette.text: control.textColor

    contentItem: Text {
        text: control.displayText
        color: control.textColor
        font: control.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        leftPadding: Theme.space["2"]
        rightPadding: Theme.space["3"]
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
        x: control.width - width - Theme.space["2"]
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
            // mac-style chevron-down (stroked V)
            context.lineWidth = 1.5
            context.lineCap = "round"
            context.lineJoin = "round"
            context.strokeStyle = control.mutedColor
            context.beginPath()
            context.moveTo(1, 1)
            context.lineTo(width / 2, height - 1)
            context.lineTo(width - 1, 1)
            context.stroke()
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 280)

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            }
        }

        contentItem: ListView {
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

        width: control.width - 8
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
