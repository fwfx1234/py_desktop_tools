import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    property bool dark: false
    property int cornerRadius: 6
    property bool flat: false
    property color fillColor: control.dark
        ? Theme.token("color-bg-subtle", true)
        : Theme.token("color-bg-surface", false)
    property color hoverFillColor: control.dark
        ? Theme.token("color-bg-subtle-2", true)
        : Theme.token("color-bg-subtle", false)
    property color textColor: Theme.token("color-text-primary", control.dark)
    property color mutedColor: Theme.token("color-text-regular", control.dark)
    property color accentColor: "#0A84FF"
    property var itemColorFn: null

    implicitHeight: 28
    leftPadding: 10
    rightPadding: control.flat ? 22 : 32
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
            : (control.dark ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(0, 0, 0, 0.18))
        antialiasing: true
    }

    indicator: Item {
        width: control.flat ? 14 : 20
        height: control.height - 6
        x: control.width - width - 4
        y: 3

        Rectangle {
            id: accentBox
            visible: !control.flat
            anchors.fill: parent
            radius: 4
            color: control.accentColor
            opacity: control.down ? 0.85 : 1.0
        }

        Canvas {
            id: chevron
            anchors.fill: parent
            contextType: "2d"

            Connections {
                target: control
                function onPressedChanged() { chevron.requestPaint() }
                function onHoveredChanged() { chevron.requestPaint() }
            }

            onPaint: {
                var ctx = context
                ctx.reset()
                ctx.lineWidth = 1.5
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.strokeStyle = control.flat ? control.mutedColor : "#FFFFFF"

                var w = width
                var h = height
                var cx = w / 2
                if (control.flat) {
                    var pad = 3
                    ctx.beginPath()
                    ctx.moveTo(pad, h / 2 - 2)
                    ctx.lineTo(cx, h / 2 + 3)
                    ctx.lineTo(w - pad, h / 2 - 2)
                    ctx.stroke()
                    return
                }
                var armX = 4
                var topY = h / 2 - 5
                var midY1 = h / 2 - 2
                var bottomY = h / 2 + 5
                var midY2 = h / 2 + 2
                ctx.beginPath()
                ctx.moveTo(armX, midY1)
                ctx.lineTo(cx, topY)
                ctx.lineTo(w - armX, midY1)
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(armX, midY2)
                ctx.lineTo(cx, bottomY)
                ctx.lineTo(w - armX, midY2)
                ctx.stroke()
            }
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
