import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"
import "components"

Dialog {
    id: dialog

    property bool dark: false
    property var environments: []
    property int currentEnvIndex: 0
    property var draftEnvironments: []
    property int selectedIndex: 0
    property int detailTab: 0
    property var activeRowEditor: null
    property var activeFieldEditor: null
    property bool autoSaveEnabled: false
    property color surface: Theme.token("color-bg-surface", dark)
    property color subtle: Theme.token("color-bg-subtle-2", dark)
    property color panel: Theme.token("color-bg-subtle", dark)
    property color borderColor: Theme.token("color-border-default", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color textSubtle: Theme.token("color-text-secondary", dark)
    property var detailTabs: [
        { title: "变量", kind: "variables", addText: "新增变量", keyTitle: "变量名", valueTitle: "变量值", emptyText: "暂无环境变量" },
        { title: "Headers", kind: "headers", addText: "新增 Header", keyTitle: "Header 名", valueTitle: "Header 值", emptyText: "暂无公共 Header" }
    ]

    signal environmentsSaved(var envs, int selectedIndex)

    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    width: Math.min(980, Overlay.overlay ? Overlay.overlay.width * 0.78 : 980)
    height: Math.min(640, Overlay.overlay ? Overlay.overlay.height * 0.84 : 640)
    padding: 0

    function clone(value) {
        return JSON.parse(JSON.stringify(value || []))
    }

    function blankEnvironment(index) {
        return {
            id: "",
            name: index === 0 ? "默认环境" : ("新环境 " + index),
            baseUrl: "",
            variables: [],
            headers: []
        }
    }

    function normalizeRow(row) {
        return {
            enabled: row && row.enabled !== false,
            key: row ? (row.key || row.name || "") : "",
            value: row ? (row.value || row.localValue || "") : ""
        }
    }

    function normalizeRows(rows) {
        var out = []
        var list = rows || []
        for (var i = 0; i < list.length; i++) {
            var row = normalizeRow(list[i])
            if (row.key.length > 0 || row.value.length > 0)
                out.push(row)
        }
        return out
    }

    function normalizeEnvironment(env, index) {
        var item = env || blankEnvironment(index + 1)
        var name = (item.name === undefined || item.name === null) ? "" : ("" + item.name).trim()
        return {
            id: item.id || "",
            name: name,
            baseUrl: item.baseUrl || "",
            variables: normalizeRows(item.variables || []),
            headers: normalizeRows(item.headers || [])
        }
    }

    function resetDraft() {
        var source = clone(dialog.environments)
        var next = []
        for (var i = 0; i < source.length; i++)
            next.push(normalizeEnvironment(source[i], i))
        if (next.length === 0)
            next.push({
                id: "",
                name: "默认环境",
                baseUrl: "http://127.0.0.1:8000",
                variables: [],
                headers: []
            })
        dialog.draftEnvironments = next
        dialog.selectedIndex = Math.max(0, Math.min(dialog.currentEnvIndex, next.length - 1))
    }

    function currentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return blankEnvironment(0)
        var idx = Math.max(0, Math.min(dialog.selectedIndex, dialog.draftEnvironments.length - 1))
        return dialog.draftEnvironments[idx]
    }

    function currentRows() {
        var tab = dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]
        return currentEnvironment()[tab.kind] || []
    }

    function updateCurrentEnvironment(field, value) {
        if (dialog.draftEnvironments.length === 0)
            return
        var list = clone(dialog.draftEnvironments)
        var env = list[dialog.selectedIndex]
        env[field] = value
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function setActiveField(field, editor) {
        dialog.activeFieldEditor = {
            field: field,
            editor: editor
        }
    }

    function clearActiveField(editor) {
        if (dialog.activeFieldEditor && dialog.activeFieldEditor.editor === editor) {
            dialog.commitActiveField()
            dialog.activeFieldEditor = null
        }
    }

    function commitActiveField() {
        var item = dialog.activeFieldEditor
        if (!item || !item.editor)
            return
        if (item.field === "name")
            dialog.updateCurrentEnvironment("name", item.editor.text.trim())
        else if (item.field === "baseUrl")
            dialog.updateCurrentEnvironment("baseUrl", item.editor.text.trim())
    }

    function addEnvironment() {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        list.push(blankEnvironment(list.length + 1))
        dialog.draftEnvironments = list
        dialog.selectedIndex = list.length - 1
    }

    function duplicateCurrentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return
        dialog.commitActiveField()
        var list = clone(dialog.draftEnvironments)
        var env = normalizeEnvironment(list[dialog.selectedIndex], dialog.selectedIndex)
        env.id = ""
        env.name = env.name + " 副本"
        list.splice(dialog.selectedIndex + 1, 0, env)
        dialog.draftEnvironments = list
        dialog.selectedIndex = dialog.selectedIndex + 1
    }

    function deleteCurrentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        list.splice(dialog.selectedIndex, 1)
        if (list.length === 0)
            list.push(blankEnvironment(0))
        dialog.draftEnvironments = list
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, list.length - 1))
    }

    function addRow(kind) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        rows.push({ enabled: true, key: "", value: "" })
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function updateRow(kind, rowIndex, field, value) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        if (rowIndex < 0 || rowIndex >= rows.length)
            return
        rows[rowIndex][field] = value
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function deleteRow(kind, rowIndex) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        if (rowIndex < 0 || rowIndex >= rows.length)
            return
        rows.splice(rowIndex, 1)
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function setActiveEditor(kind, rowIndex, field, editor) {
        dialog.activeRowEditor = {
            kind: kind,
            rowIndex: rowIndex,
            field: field,
            editor: editor
        }
    }

    function clearActiveEditor(editor) {
        if (dialog.activeRowEditor && dialog.activeRowEditor.editor === editor) {
            dialog.commitActiveEditor()
            dialog.activeRowEditor = null
        }
    }

    function commitActiveEditor() {
        var item = dialog.activeRowEditor
        if (!item || !item.editor)
            return
        var value = item.field === "key" ? item.editor.text.trim() : item.editor.text
        dialog.updateRow(item.kind, item.rowIndex, item.field, value)
    }

    function cleanDraft() {
        var list = clone(dialog.draftEnvironments)
        var out = []
        for (var i = 0; i < list.length; i++)
            out.push(normalizeEnvironment(list[i], i))
        if (out.length === 0)
            out.push(blankEnvironment(0))
        return out
    }

    function save(closeAfter) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var envs = cleanDraft()
        dialog.draftEnvironments = envs
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, envs.length - 1))
        dialog.environmentsSaved(envs, dialog.selectedIndex)
        if (closeAfter)
            dialog.close()
    }

    function scheduleAutoSave() {
        if (!dialog.autoSaveEnabled || !dialog.opened)
            return
        autoSaveTimer.restart()
    }

    onOpened: resetDraft()
    Component.onCompleted: resetDraft()
    onEnvironmentsChanged: {
        if (!dialog.opened)
            resetDraft()
    }

    Timer {
        id: autoSaveTimer
        interval: 300
        repeat: false
        onTriggered: dialog.save(false)
    }

    background: Rectangle {
        color: dialog.surface
        radius: Theme.radii.md
        border.width: 1
        border.color: dialog.borderColor
    }

    contentItem: Rectangle {
        color: dialog.surface
        radius: Theme.radii.md
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                color: dialog.surface
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["4"]
                    anchors.rightMargin: Theme.space["2"]
                    spacing: Theme.space["2"]

                    Label {
                        text: "环境管理"
                        Layout.fillWidth: true
                        color: dialog.textMain
                        font.pixelSize: Theme.fontSize.heading
                        font.bold: true
                    }

                    Label {
                        text: dialog.draftEnvironments.length + " 个环境"
                        color: dialog.textSubtle
                        font.pixelSize: Theme.fontSize.caption
                    }

                    UiButton {
                        text: "关闭"
                        dark: dialog.dark
                        variant: "ghost"
                        implicitWidth: 56
                        implicitHeight: 28
                        onClicked: dialog.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.subtle }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 250
                    Layout.fillHeight: true
                    color: dialog.subtle

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.space["2"]
                        spacing: Theme.space["2"]

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: "环境"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                Layout.fillWidth: true
                            }
                            UiButton {
                                text: "新建"
                                dark: dialog.dark
                                variant: "secondary"
                                implicitWidth: 58
                                implicitHeight: 28
                                onClicked: dialog.addEnvironment()
                            }
                        }

                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentHeight: envList.implicitHeight

                            ColumnLayout {
                                id: envList
                                width: parent.width
                                spacing: Theme.space["1"]

                                Repeater {
                                    model: dialog.draftEnvironments
                                    delegate: Rectangle {
                                        id: envItem
                                        required property int index
                                        required property var modelData
                                        property bool active: index === dialog.selectedIndex

                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 50
                                        radius: Theme.radii.xs
                                        color: active
                                            ? Theme.token("color-primary-bg", dialog.dark)
                                            : (envMouse.containsMouse ? Theme.token("color-bg-subtle", dialog.dark) : "transparent")
                                        border.width: active ? 1 : 0
                                        border.color: active ? Qt.rgba(Theme.token("color-primary-active", dialog.dark).r, Theme.token("color-primary-active", dialog.dark).g, Theme.token("color-primary-active", dialog.dark).b, 0.35) : "transparent"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.space["2"]
                                            anchors.rightMargin: Theme.space["2"]
                                            spacing: Theme.space["2"]

                                            Rectangle {
                                                Layout.preferredWidth: 24
                                                Layout.preferredHeight: 24
                                                radius: 12
                                                color: envItem.active ? Theme.token("color-primary-active", dialog.dark) : Theme.token("color-bg-surface", dialog.dark)
                                                border.width: envItem.active ? 0 : 1
                                                border.color: dialog.borderColor
                                                Label {
                                                    anchors.centerIn: parent
                                                    text: (modelData.name || "环").slice(0, 1)
                                                    color: envItem.active ? "white" : dialog.textMuted
                                                    font.pixelSize: Theme.fontSize.caption
                                                    font.bold: true
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 0
                                                Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.name || "未命名环境"
                                                    color: envItem.active ? Theme.token("color-primary-active", dialog.dark) : dialog.textMain
                                                    font.pixelSize: Theme.fontSize.body
                                                    elide: Text.ElideRight
                                                }
                                                Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.baseUrl || "未设置 Base URL"
                                                    color: dialog.textSubtle
                                                    font.pixelSize: Theme.fontSize.caption
                                                    elide: Text.ElideMiddle
                                                }
                                            }
                                        }

                                        MouseArea {
                                            id: envMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                dialog.commitActiveField()
                                                dialog.commitActiveEditor()
                                                dialog.selectedIndex = index
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: dialog.borderColor }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        color: dialog.surface
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["4"]
                            anchors.rightMargin: Theme.space["3"]
                            spacing: Theme.space["2"]

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Label {
                                    Layout.fillWidth: true
                                    text: dialog.currentEnvironment().name || "环境"
                                    color: dialog.textMain
                                    font.pixelSize: Theme.fontSize.heading
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: dialog.currentEnvironment().baseUrl || "未设置 Base URL"
                                    color: dialog.textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    elide: Text.ElideMiddle
                                }
                            }

                            UiButton {
                                text: "复制"
                                dark: dialog.dark
                                variant: "secondary"
                                implicitWidth: 58
                                implicitHeight: 28
                                onClicked: dialog.duplicateCurrentEnvironment()
                            }

                            UiButton {
                                text: "删除"
                                dark: dialog.dark
                                variant: "secondary"
                                implicitWidth: 58
                                implicitHeight: 28
                                onClicked: dialog.deleteCurrentEnvironment()
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.subtle }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: Theme.space["3"]
                        spacing: Theme.space["3"]

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: Theme.space["3"]
                            rowSpacing: Theme.space["2"]

                            Label {
                                text: "名称"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                            }
                            UiTextField {
                                id: envNameInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30
                                dark: dialog.dark
                                text: dialog.currentEnvironment().name || ""
                                placeholderText: "未命名环境"
                                onTextEdited: {
                                    dialog.updateCurrentEnvironment("name", text.trim())
                                    dialog.scheduleAutoSave()
                                }
                                onEditingFinished: dialog.updateCurrentEnvironment("name", text.trim())
                                onActiveFocusChanged: {
                                    if (activeFocus)
                                        dialog.setActiveField("name", envNameInput)
                                    else
                                        dialog.clearActiveField(envNameInput)
                                }
                            }

                            Label {
                                text: "Base URL"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                            }
                            UiTextField {
                                id: envBaseUrlInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30
                                dark: dialog.dark
                                text: dialog.currentEnvironment().baseUrl || ""
                                placeholderText: "http://127.0.0.1:8000"
                                onTextEdited: {
                                    dialog.updateCurrentEnvironment("baseUrl", text.trim())
                                    dialog.scheduleAutoSave()
                                }
                                onEditingFinished: dialog.updateCurrentEnvironment("baseUrl", text.trim())
                                onActiveFocusChanged: {
                                    if (activeFocus)
                                        dialog.setActiveField("baseUrl", envBaseUrlInput)
                                    else
                                        dialog.clearActiveField(envBaseUrlInput)
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: dialog.subtle
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["1"]

                            Repeater {
                                model: dialog.detailTabs
                                delegate: Rectangle {
                                    id: sectionTab
                                    required property int index
                                    required property var modelData
                                    property bool active: index === dialog.detailTab

                                    Layout.preferredWidth: Math.max(92, sectionTabLabel.implicitWidth + Theme.space["4"])
                                    Layout.preferredHeight: 28
                                    radius: Theme.radii.xs
                                    color: active ? Theme.token("color-bg-subtle", dialog.dark) : (sectionTabMouse.containsMouse ? dialog.subtle : "transparent")

                                    Label {
                                        id: sectionTabLabel
                                        anchors.centerIn: parent
                                        text: modelData.title + " " + (dialog.currentEnvironment()[modelData.kind] || []).length
                                        color: sectionTab.active ? Theme.token("color-primary-active", dialog.dark) : dialog.textMain
                                        font.pixelSize: Theme.fontSize.caption
                                        font.bold: sectionTab.active
                                    }

                                    MouseArea {
                                        id: sectionTabMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: dialog.detailTab = index
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            UiButton {
                                text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).addText
                                dark: dialog.dark
                                variant: "secondary"
                                implicitWidth: 104
                                implicitHeight: 28
                                onClicked: dialog.addRow((dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).kind)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: Theme.radii.xs
                            color: dialog.subtle
                            border.width: 1
                            border.color: dialog.borderColor
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                spacing: 0

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    color: Theme.token("color-table-header", dialog.dark)

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: Theme.space["2"]
                                        anchors.rightMargin: Theme.space["2"]
                                        spacing: Theme.space["2"]

                                        Label { text: "启用"; Layout.preferredWidth: 38; color: dialog.textMuted; font.pixelSize: Theme.fontSize.caption }
                                        Label { text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).keyTitle; Layout.preferredWidth: 190; color: dialog.textMuted; font.pixelSize: Theme.fontSize.caption }
                                        Label { text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).valueTitle; Layout.fillWidth: true; color: dialog.textMuted; font.pixelSize: Theme.fontSize.caption }
                                        Label { text: ""; Layout.preferredWidth: 38 }
                                    }
                                }

                                Flickable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    contentHeight: rowsColumn.implicitHeight

                                    ColumnLayout {
                                        id: rowsColumn
                                        width: parent.width
                                        spacing: 0

                                        Repeater {
                                            model: dialog.currentRows()
                                            delegate: Rectangle {
                                                required property int index
                                                required property var modelData
                                                property string kind: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).kind

                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 36
                                                color: rowMouse.containsMouse ? Theme.token("color-row-hover", dialog.dark) : "transparent"

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: Theme.space["1"]
                                                    anchors.rightMargin: Theme.space["1"]
                                                    spacing: Theme.space["2"]

                                                    UiCheckBox {
                                                        dark: dialog.dark
                                                        checked: modelData.enabled !== false
                                                        Layout.preferredWidth: 40
                                                        Layout.preferredHeight: 30
                                                        onToggled: dialog.updateRow(kind, index, "enabled", checked)
                                                    }

                                                    TextField {
                                                        Layout.preferredWidth: 190
                                                        Layout.preferredHeight: 30
                                                        text: modelData.key || ""
                                                        color: dialog.textMain
                                                        placeholderText: kind === "headers" ? "Authorization" : "token"
                                                        placeholderTextColor: dialog.textSubtle
                                                        font.family: Theme.fontFamily.mono
                                                        font.pixelSize: Theme.fontSize.mono
                                                        selectByMouse: true
                                                        background: Rectangle {
                                                            radius: Theme.radii.xs
                                                            color: keyInput.activeFocus ? dialog.surface : "transparent"
                                                            border.width: keyInput.activeFocus ? 1 : 0
                                                            border.color: Theme.token("color-primary-active", dialog.dark)
                                                        }
                                                        id: keyInput
                                                        onEditingFinished: dialog.updateRow(kind, index, "key", text.trim())
                                                        onActiveFocusChanged: {
                                                            if (activeFocus)
                                                                dialog.setActiveEditor(kind, index, "key", keyInput)
                                                            else
                                                                dialog.clearActiveEditor(keyInput)
                                                        }
                                                    }

                                                    TextField {
                                                        id: valueInput
                                                        Layout.fillWidth: true
                                                        Layout.preferredHeight: 30
                                                        text: modelData.value || ""
                                                        color: dialog.textMain
                                                        placeholderText: kind === "headers" ? "Bearer {{token}}" : "value"
                                                        placeholderTextColor: dialog.textSubtle
                                                        font.family: Theme.fontFamily.mono
                                                        font.pixelSize: Theme.fontSize.mono
                                                        selectByMouse: true
                                                        background: Rectangle {
                                                            radius: Theme.radii.xs
                                                            color: valueInput.activeFocus ? dialog.surface : "transparent"
                                                            border.width: valueInput.activeFocus ? 1 : 0
                                                            border.color: Theme.token("color-primary-active", dialog.dark)
                                                        }
                                                        onEditingFinished: dialog.updateRow(kind, index, "value", text)
                                                        onActiveFocusChanged: {
                                                            if (activeFocus)
                                                                dialog.setActiveEditor(kind, index, "value", valueInput)
                                                            else
                                                                dialog.clearActiveEditor(valueInput)
                                                        }
                                                    }

                                                    ApiDeleteButton {
                                                        dark: dialog.dark
                                                        Layout.preferredWidth: 38
                                                        Layout.preferredHeight: 30
                                                        iconColor: dialog.textMuted
                                                        dangerColor: Theme.token("color-danger", dialog.dark)
                                                        onDeleteRequested: dialog.deleteRow(kind, index)
                                                    }
                                                }

                                                MouseArea {
                                                    id: rowMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    acceptedButtons: Qt.NoButton
                                                }

                                                Rectangle {
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.bottom: parent.bottom
                                                    height: 1
                                                    color: Theme.token("color-bg-subtle-2", dialog.dark)
                                                }
                                            }
                                        }

                                        Rectangle {
                                            visible: dialog.currentRows().length === 0
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 88
                                            color: "transparent"
                                            Label {
                                                anchors.centerIn: parent
                                                text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).emptyText
                                                color: dialog.textSubtle
                                                font.pixelSize: Theme.fontSize.body
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.subtle }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        Layout.leftMargin: Theme.space["3"]
                        Layout.rightMargin: Theme.space["3"]
                        spacing: Theme.space["2"]

                        UiButton {
                            text: "取消"
                            dark: dialog.dark
                            variant: "ghost"
                            implicitWidth: 72
                            implicitHeight: 30
                            onClicked: dialog.close()
                        }

                        Item { Layout.fillWidth: true }

                        UiButton {
                            text: "保存并关闭"
                            dark: dialog.dark
                            variant: "secondary"
                            implicitWidth: 112
                            implicitHeight: 30
                            onClicked: dialog.save(true)
                        }

                        UiButton {
                            text: "保存"
                            dark: dialog.dark
                            variant: "primary"
                            implicitWidth: 80
                            implicitHeight: 30
                            onClicked: dialog.save(false)
                        }
                    }
                }
            }
        }
    }
}
