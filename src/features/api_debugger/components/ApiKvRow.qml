import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color panelBorder: Theme.token("color-bg-subtle-2", dark)
    property var rowData: ({})
    property int checkWidth: 22
    property int keyWidth: 180
    property int valueWeight: 4
    property int typeWidth: 86
    property int descWidth: 112
    property int magicWidth: 30
    property int deleteWidth: 26
    property int rowHeight: 36
    property bool magicEnabled: true
    property string sectionName: "query"
    property bool showTypeSelector: false
    property bool showTypeColumn: true
    property var typeOptions: ["string", "number", "boolean", "array", "object"]
    property var commonHeaderKeys: [
        "Accept",
        "Authorization",
        "Content-Type",
        "User-Agent",
        "Cache-Control",
        "Cookie",
        "Referer",
        "Origin",
        "X-Requested-With",
        "Accept-Language",
        "Accept-Encoding"
    ]
    property var commonHeaderValues: ({
        "accept": ["application/json", "*/*", "text/plain", "application/xml"],
        "authorization": ["Bearer {{token}}", "Basic "],
        "content-type": ["application/json", "application/x-www-form-urlencoded", "multipart/form-data", "text/plain", "application/xml"],
        "cache-control": ["no-cache", "no-store", "max-age=0"],
        "user-agent": ["Mozilla/5.0", "PyDesktopTools"],
        "x-requested-with": ["XMLHttpRequest"],
        "accept-language": ["zh-CN,zh;q=0.9", "en-US,en;q=0.9"],
        "accept-encoding": ["gzip, deflate, br"],
        "origin": ["{{baseUrl}}"],
        "referer": ["{{baseUrl}}"]
    })
    property string fixedTypeText: "string"
    property color fieldHoverBg: Theme.token("color-bg-subtle-2", dark)
    property color fieldFocusBg: Theme.token("color-bg-surface", dark)
    property bool valuePressed: false

    signal enabledToggled(bool checked)
    signal keyCommitted(string keyText, bool focusValueAfterCommit)
    signal keyEdited(string keyText)
    signal valueCommitted(string valueText)
    signal valueEdited(string valueText)
    signal typeCommitted(string typeText)
    signal descCommitted(string descText)
    signal deleteRequested()
    signal valueFocused()
    signal magicInsertRequested(string valueText)

    Layout.fillWidth: true
    Layout.preferredHeight: root.rowHeight
    color: "transparent"

    function forceValueFocus() {
        valueField.forceActiveFocus()
        valueField.cursorPosition = valueField.text.length
    }

    function filteredHeaderKeys(textValue) {
        return filteredCandidates(root.commonHeaderKeys, textValue)
    }

    function headerValueCandidates() {
        var key = (keyField.text || root.rowData.key || "").toLowerCase()
        return root.commonHeaderValues[key] || []
    }

    function filteredHeaderValues(textValue) {
        return filteredCandidates(headerValueCandidates(), textValue)
    }

    function filteredCandidates(candidates, textValue) {
        var query = (textValue || "").toLowerCase()
        var out = []
        for (var i = 0; candidates && i < candidates.length; i++) {
            var candidate = candidates[i]
            if (query.length === 0 || candidate.toLowerCase().indexOf(query) >= 0)
                out.push(candidate)
        }
        return out.slice(0, 6)
    }

    function openHeaderKeyPopup() {
        if (root.sectionName !== "headers")
            return
        headerKeyPopup.model = filteredHeaderKeys(keyField.text)
        if (headerKeyPopup.model.length > 0)
            headerKeyPopup.open()
        else
            headerKeyPopup.close()
    }

    function openHeaderValuePopup() {
        if (root.sectionName !== "headers")
            return
        headerValuePopup.model = filteredHeaderValues(valueField.text)
        if (headerValuePopup.model.length > 0)
            headerValuePopup.open()
        else
            headerValuePopup.close()
    }

    Timer {
        id: clearValuePressedTimer
        interval: 500
        repeat: false
        onTriggered: root.valuePressed = false
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["3"]
        anchors.rightMargin: Theme.space["3"]
        spacing: Theme.space["2.5"]

        UiCheckBox {
            dark: root.dark
            checked: root.rowData.enabled !== false
            Layout.preferredWidth: root.checkWidth
            onToggled: root.enabledToggled(checked)
        }

        TextField {
            id: keyField
            Layout.preferredWidth: root.keyWidth
            text: root.rowData.key || ""
            hoverEnabled: true
            leftPadding: Theme.space["2"]
            rightPadding: Theme.space["2"]
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radii.xs
                color: keyField.activeFocus
                    ? root.fieldFocusBg
                    : (keyField.hovered ? root.fieldHoverBg : "transparent")
                border.width: keyField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: Theme.fontFamily.mono
            placeholderText: "Key"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.keyCommitted(text, root.valuePressed || valueField.activeFocus)
            onTextEdited: {
                root.keyEdited(text)
                root.openHeaderKeyPopup()
            }
            onActiveFocusChanged: {
                if (activeFocus)
                    root.openHeaderKeyPopup()
            }

            Popup {
                id: headerKeyPopup
                y: parent.height + 2
                width: parent.width
                padding: 0
                modal: false
                focus: false
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                property var model: []
                background: Rectangle {
                    radius: Theme.radii.xs
                    color: root.fieldFocusBg
                    border.width: 1
                    border.color: root.panelBorder
                }
                contentItem: Column {
                    width: headerKeyPopup.width
                    Repeater {
                        model: headerKeyPopup.model
                        delegate: Rectangle {
                            required property string modelData
                            width: headerKeyPopup.width
                            height: 28
                            color: keySuggestionMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                            Label {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space["2"]
                                anchors.rightMargin: Theme.space["2"]
                                text: modelData
                                color: root.textMain
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                id: keySuggestionMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onPressed: function(mouse) {
                                    keyField.text = modelData
                                    keyField.cursorPosition = keyField.text.length
                                    root.keyEdited(keyField.text)
                                    root.keyCommitted(keyField.text, false)
                                    headerKeyPopup.close()
                                    mouse.accepted = true
                                }
                            }
                        }
                    }
                }
            }
        }

        TextField {
            id: valueField
            Layout.fillWidth: true
            Layout.horizontalStretchFactor: root.valueWeight
            text: root.rowData.value || ""
            hoverEnabled: true
            leftPadding: Theme.space["2"]
            rightPadding: Theme.space["2"]
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radii.xs
                color: valueField.activeFocus
                    ? root.fieldFocusBg
                    : (valueField.hovered ? root.fieldHoverBg : "transparent")
                border.width: valueField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: Theme.fontFamily.mono
            placeholderText: "Value"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.valueCommitted(text)
            onTextEdited: {
                root.valueEdited(text)
                root.openHeaderValuePopup()
            }
            onActiveFocusChanged: {
                if (activeFocus) {
                    root.valueFocused()
                    root.openHeaderValuePopup()
                }
            }

            TapHandler {
                acceptedButtons: Qt.LeftButton
                onPressedChanged: if (pressed) {
                    root.valuePressed = true
                    clearValuePressedTimer.restart()
                }
            }

            function insertMagicValue(valueText) {
                var start = Math.min(selectionStart, selectionEnd)
                var end = Math.max(selectionStart, selectionEnd)
                if (isNaN(start) || isNaN(end) || start < 0 || end < 0) {
                    start = cursorPosition
                    end = cursorPosition
                }
                text = text.slice(0, start) + valueText + text.slice(end)
                cursorPosition = start + valueText.length
                forceActiveFocus()
                root.valueCommitted(text)
                root.magicInsertRequested(valueText)
            }

            Popup {
                id: headerValuePopup
                y: parent.height + 2
                width: parent.width
                padding: 0
                modal: false
                focus: false
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                property var model: []
                background: Rectangle {
                    radius: Theme.radii.xs
                    color: root.fieldFocusBg
                    border.width: 1
                    border.color: root.panelBorder
                }
                contentItem: Column {
                    width: headerValuePopup.width
                    Repeater {
                        model: headerValuePopup.model
                        delegate: Rectangle {
                            required property string modelData
                            width: headerValuePopup.width
                            height: 28
                            color: valueSuggestionMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                            Label {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space["2"]
                                anchors.rightMargin: Theme.space["2"]
                                text: modelData
                                color: root.textMain
                                font.pixelSize: Theme.fontSize.caption
                                font.family: Theme.fontFamily.mono
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                id: valueSuggestionMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onPressed: function(mouse) {
                                    valueField.text = modelData
                                    valueField.cursorPosition = valueField.text.length
                                    root.valueEdited(valueField.text)
                                    root.valueCommitted(valueField.text)
                                    headerValuePopup.close()
                                    mouse.accepted = true
                                }
                            }
                        }
                    }
                }
            }
        }

        ApiMagicInsertButton {
            visible: root.magicEnabled
            Layout.preferredWidth: root.magicEnabled ? root.magicWidth : 0
            dark: root.dark
            panelBg: root.fieldFocusBg
            panelBorder: root.panelBorder
            textMain: root.textMain
            textMuted: root.textMuted
            onInsertRequested: function(valueText) { valueField.insertMagicValue(valueText) }
        }

        Loader {
            visible: root.showTypeColumn
            Layout.preferredWidth: root.showTypeColumn ? root.typeWidth : 0
            sourceComponent: root.showTypeColumn ? (root.showTypeSelector ? typeEditor : typeLabel) : null
        }

        Component {
            id: typeLabel
            Label {
                text: root.fixedTypeText
                color: root.textMuted
                font.family: Theme.fontFamily.mono
                font.pixelSize: Theme.fontSize.caption
                verticalAlignment: Text.AlignVCenter
            }
        }

        Component {
            id: typeEditor
            ApiTypeSelector {
                dark: root.dark
                model: root.typeOptions
                value: root.rowData.type || "string"
                textMain: root.textMain
                textMuted: root.textMuted
                width: root.typeWidth
                height: 26
                onValueCommitted: function(valueText) { root.typeCommitted(valueText) }
            }
        }

        TextField {
            id: descField
            Layout.preferredWidth: root.descWidth
            text: root.rowData.desc || ""
            hoverEnabled: true
            leftPadding: Theme.space["2"]
            rightPadding: Theme.space["2"]
            selectedTextColor: root.textMain
            selectionColor: Theme.token("color-primary-active", root.dark)
            background: Rectangle {
                radius: Theme.radii.xs
                color: descField.activeFocus
                    ? root.fieldFocusBg
                    : (descField.hovered ? root.fieldHoverBg : "transparent")
                border.width: descField.activeFocus ? 1 : 0
                border.color: Theme.token("color-primary-active", root.dark)
            }
            color: root.textMain
            font.family: Theme.fontFamily.mono
            placeholderText: "Description"
            placeholderTextColor: Theme.token("color-text-secondary", root.dark)
            onEditingFinished: root.descCommitted(text)
        }

        ApiDeleteButton {
            dark: root.dark
            iconColor: root.textMuted
            dangerColor: Theme.token("color-danger", root.dark)
            Layout.preferredWidth: root.deleteWidth
            onDeleteRequested: root.deleteRequested()
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: root.panelBorder
    }
}
