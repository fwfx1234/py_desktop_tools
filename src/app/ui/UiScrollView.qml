import QtQuick
import QtQuick.Controls

ScrollView {
    id: control

    property int wheelStep: 72
    property int keyStep: 48
    property int pageStep: Math.max(80, height - 48)
    property bool shiftWheelScrollsHorizontally: true

    clip: true
    focusPolicy: Qt.StrongFocus
    Keys.priority: Keys.AfterItem
    ScrollBar.vertical.policy: ScrollBar.AsNeeded
    ScrollBar.horizontal.policy: ScrollBar.AsNeeded

    function flickableItem() {
        return control.contentItem
    }

    function maxContentX() {
        var item = flickableItem()
        if (!item || typeof item.contentWidth === "undefined")
            return 0
        return Math.max(0, item.contentWidth - item.width)
    }

    function maxContentY() {
        var item = flickableItem()
        if (!item || typeof item.contentHeight === "undefined")
            return 0
        return Math.max(0, item.contentHeight - item.height)
    }

    function setContentX(value) {
        var item = flickableItem()
        if (!item || typeof item.contentX === "undefined")
            return false
        var next = Math.max(0, Math.min(maxContentX(), value))
        if (Math.abs(next - item.contentX) < 0.5)
            return false
        item.contentX = next
        return true
    }

    function setContentY(value) {
        var item = flickableItem()
        if (!item || typeof item.contentY === "undefined")
            return false
        var next = Math.max(0, Math.min(maxContentY(), value))
        if (Math.abs(next - item.contentY) < 0.5)
            return false
        item.contentY = next
        return true
    }

    function scrollBy(dx, dy) {
        var item = flickableItem()
        if (!item)
            return false
        var changed = false
        if (dx !== 0)
            changed = setContentX(item.contentX + dx) || changed
        if (dy !== 0)
            changed = setContentY(item.contentY + dy) || changed
        return changed
    }

    WheelHandler {
        target: control
        enabled: control.shiftWheelScrollsHorizontally
        acceptedModifiers: Qt.ShiftModifier
        onWheel: function(event) {
            var dx = 0
            if (event.pixelDelta.y !== 0)
                dx = -event.pixelDelta.y
            else if (event.angleDelta.y !== 0)
                dx = -event.angleDelta.y / 120 * control.wheelStep
            else if (event.pixelDelta.x !== 0)
                dx = -event.pixelDelta.x
            else if (event.angleDelta.x !== 0)
                dx = -event.angleDelta.x / 120 * control.wheelStep
            if (dx !== 0)
                event.accepted = control.scrollBy(dx, 0)
        }
    }

    Keys.onPressed: function(event) {
        var handled = false
        var horizontal = (event.modifiers & Qt.ShiftModifier) !== 0
        var controlPressed = (event.modifiers & Qt.ControlModifier) !== 0
        if (event.key === Qt.Key_PageDown)
            handled = horizontal ? scrollBy(pageStep, 0) : scrollBy(0, pageStep)
        else if (event.key === Qt.Key_PageUp)
            handled = horizontal ? scrollBy(-pageStep, 0) : scrollBy(0, -pageStep)
        else if (event.key === Qt.Key_Home)
            handled = controlPressed ? setContentY(0) : setContentX(0)
        else if (event.key === Qt.Key_End)
            handled = controlPressed ? setContentY(maxContentY()) : setContentX(maxContentX())
        else if (horizontal && event.key === Qt.Key_Left)
            handled = scrollBy(-keyStep, 0)
        else if (horizontal && event.key === Qt.Key_Right)
            handled = scrollBy(keyStep, 0)
        if (handled)
            event.accepted = true
    }
}
