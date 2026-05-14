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

    signal environmentsSaved(var envs, int selectedIndex)

    modal: true
    title: "环境管理"
    standardButtons: Dialog.NoButton
    width: Math.min(900, Overlay.overlay ? Overlay.overlay.width * 0.75 : 900)
    height: Math.min(620, Overlay.overlay ? Overlay.overlay.height * 0.82 : 620)
    padding: 0

    function clone(value) {
        return JSON.parse(JSON.stringify(value || []))
    }

    function blankEnvironment(index) {
        return {
            name: index === 0 ? "默认环境" : ("新环境 " + index),
            baseUrl: "",
            variables: [],
            headers: []
        }
    }

    function normalizeVariable(row) {
        return {
            enabled: row && row.enabled !== false,
            key: row ? (row.key || row.name || "") : "",
            value: row ? (row.value || row.localValue || "") : ""
        }
    }

    function normalizeVariables(rows) {
        var out = []
        var list = rows || []
        for (var i = 0; i < list.length; i++) {
            var row = normalizeVariable(list[i])
            if (row.key.length > 0 || row.value.length > 0)
                out.push(row)
        }
        return out
    }

    function normalizeHeader(row) {
        return {
            enabled: row && row.enabled !== false,
            key: row ? (row.key || row.name || "") : "",
            value: row ? (row.value || "") : ""
        }
    }

    function normalizeHeaders(rows) {
        var out = []
        var list = rows || []
        for (var i = 0; i < list.length; i++) {
            var row = normalizeHeader(list[i])
            if (row.key.length > 0 || row.value.length > 0)
                out.push(row)
        }
        return out
    }

    function normalizeEnvironment(env, index) {
        var item = env || blankEnvironment(index + 1)
        var name = (item.name || "").trim()
        if (name.length === 0)
            name = "环境 " + (index + 1)
        return {
            name: name,
            baseUrl: item.baseUrl || "",
            variables: normalizeVariables(item.variables || []),
            headers: normalizeHeaders(item.headers || [])
        }
    }

    function resetDraft() {
        var source = clone(dialog.environments)
        var next = []
        for (var i = 0; i < source.length; i++)
            next.push(normalizeEnvironment(source[i], i))
        if (next.length === 0)
            next.push({
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

    function currentVariables() {
        return currentEnvironment().variables || []
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

    function addEnvironment() {
        var list = clone(dialog.draftEnvironments)
        list.push(blankEnvironment(list.length + 1))
        dialog.draftEnvironments = list
        dialog.selectedIndex = list.length - 1
    }

    function deleteCurrentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return
        var list = clone(dialog.draftEnvironments)
        list.splice(dialog.selectedIndex, 1)
        if (list.length === 0)
            list.push(blankEnvironment(0))
        dialog.draftEnvironments = list
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, list.length - 1))
    }

    function addVariable() {
        var list = clone(dialog.draftEnvironments)
        var env = list[dialog.selectedIndex]
        var vars = env.variables || []
        vars.push({ enabled: true, key: "", value: "" })
        env.variables = vars
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function updateVariable(rowIndex, field, value) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var vars = env.variables || []
        if (rowIndex < 0 || rowIndex >= vars.length)
            return
        vars[rowIndex][field] = value
        env.variables = vars
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function deleteVariable(rowIndex) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var vars = env.variables || []
        if (rowIndex < 0 || rowIndex >= vars.length)
            return
        vars.splice(rowIndex, 1)
        env.variables = vars
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function currentHeaders() {
        return currentEnvironment().headers || []
    }

    function addHeader() {
        var list = clone(dialog.draftEnvironments)
        var env = list[dialog.selectedIndex]
        var headers = env.headers || []
        headers.push({ enabled: true, key: "", value: "" })
        env.headers = headers
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function updateHeader(rowIndex, field, value) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var headers = env.headers || []
        if (rowIndex < 0 || rowIndex >= headers.length)
            return
        headers[rowIndex][field] = value
        env.headers = headers
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function deleteHeader(rowIndex) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var headers = env.headers || []
        if (rowIndex < 0 || rowIndex >= headers.length)
            return
        headers.splice(rowIndex, 1)
        env.headers = headers
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
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
        var envs = cleanDraft()
        dialog.draftEnvironments = envs
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, envs.length - 1))
        dialog.environmentsSaved(envs, dialog.selectedIndex)
        if (closeAfter)
            dialog.close()
    }

    onOpened: resetDraft()
    Component.onCompleted: resetDraft()
    onEnvironmentsChanged: {
        if (!dialog.opened)
            resetDraft()
    }

    background: Rectangle {
        color: Theme.token("color-bg-surface", dialog.dark)
        radius: Theme.radius.md
        border.color: Theme.token("color-border-default", dialog.dark)
    }

    contentItem: Rectangle {
        color: Theme.token("color-bg-surface", dialog.dark)
        radius: Theme.radius.md

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 12
                    Label {
                        text: "环境管理"
                        Layout.fillWidth: true
                        color: Theme.token("color-text-primary", dialog.dark)
                        font.bold: true
                        font.pixelSize: 15
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
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.token("color-bg-subtle-2", dialog.dark)
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 220
                    Layout.fillHeight: true
                    color: Theme.token("color-bg-subtle-2", dialog.dark)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacing.s3
                        spacing: Theme.spacing.s2

                        Label {
                            text: "环境"
                            color: Theme.token("color-text-regular", dialog.dark)
                            font.pixelSize: Theme.typeScale.caption
                        }

                        Repeater {
                            model: dialog.draftEnvironments
                            delegate: Rectangle {
                                required property int index
                                required property var modelData

                                Layout.fillWidth: true
                                Layout.preferredHeight: 34
                                radius: Theme.radius.xs
                                color: envMouse.containsMouse || index === dialog.selectedIndex
                                    ? Theme.token("color-nav-item-active-bg", dialog.dark)
                                    : "transparent"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.spacing.s2
                                    anchors.rightMargin: Theme.spacing.s2
                                    spacing: Theme.spacing.s2

                                    Label {
                                        text: (modelData.name || "环").slice(0, 1)
                                        Layout.preferredWidth: 20
                                        color: index === dialog.selectedIndex
                                            ? Theme.token("color-primary-active", dialog.dark)
                                            : Theme.token("color-text-regular", dialog.dark)
                                        font.bold: true
                                    }
                                    Label {
                                        text: modelData.name || "未命名环境"
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        color: index === dialog.selectedIndex
                                            ? Theme.token("color-primary-active", dialog.dark)
                                            : Theme.token("color-text-primary", dialog.dark)
                                        font.pixelSize: Theme.typeScale.body
                                    }
                                }

                                MouseArea {
                                    id: envMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: dialog.selectedIndex = index
                                }
                            }
                        }

                        UiButton {
                            text: "新建环境"
                            dark: dialog.dark
                            variant: "secondary"
                            Layout.fillWidth: true
                            implicitHeight: 30
                            onClicked: dialog.addEnvironment()
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.fillHeight: true
                    color: Theme.token("color-border-default", dialog.dark)
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    // ---- fixed header ----
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        color: "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 20
                            anchors.rightMargin: 16
                            Label {
                                text: dialog.currentEnvironment().name || "环境"
                                Layout.fillWidth: true
                                color: Theme.token("color-text-primary", dialog.dark)
                                font.bold: true
                                font.pixelSize: 14
                            }
                            UiButton {
                                text: "删除环境"
                                dark: dialog.dark
                                variant: "secondary"
                                implicitWidth: 80
                                implicitHeight: 28
                                onClicked: dialog.deleteCurrentEnvironment()
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.token("color-bg-subtle-2", dialog.dark)
                    }

                    // ---- scrollable content ----
                    UiScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ColumnLayout {
                            width: parent.width
                            spacing: 12
                            anchors.leftMargin: 20
                            anchors.rightMargin: 16
                            anchors.margins: 16

                    // ---- name & baseUrl ----
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6

                        Label {
                            text: "名称"
                            color: Theme.token("color-text-regular", dialog.dark)
                            font.pixelSize: 12
                        }
                        UiTextField {
                            Layout.fillWidth: true
                            dark: dialog.dark
                            text: dialog.currentEnvironment().name || ""
                            onEditingFinished: dialog.updateCurrentEnvironment("name", text.trim().length > 0 ? text.trim() : "未命名环境")
                        }
                        Label {
                            text: "Base URL"
                            color: Theme.token("color-text-regular", dialog.dark)
                            font.pixelSize: 12
                        }
                        UiTextField {
                            Layout.fillWidth: true
                            dark: dialog.dark
                            text: dialog.currentEnvironment().baseUrl || ""
                            placeholderText: "http://127.0.0.1:8000"
                            onEditingFinished: dialog.updateCurrentEnvironment("baseUrl", text.trim())
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.token("color-border-default", dialog.dark)
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "环境变量"
                            Layout.fillWidth: true
                            color: Theme.token("color-text-primary", dialog.dark)
                            font.bold: true
                            font.pixelSize: Theme.typeScale.body
                        }

                        UiButton {
                            text: "新增变量"
                            dark: dialog.dark
                            variant: "secondary"
                            implicitWidth: 88
                            implicitHeight: 30
                            onClicked: dialog.addVariable()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: Math.min(200, varCol.implicitHeight + 34)
                        radius: 6
                        color: "transparent"
                        border.color: Theme.token("color-border-default", dialog.dark)
                        border.width: 1
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
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 12

                                    Label { text: "启用"; Layout.preferredWidth: 40; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: 10 }
                                    Label { text: "变量名"; Layout.preferredWidth: 160; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: 10 }
                                    Label { text: "变量值"; Layout.fillWidth: true; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: 10 }
                                    Label { text: ""; Layout.preferredWidth: 32; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: 10 }
                                }
                            }

                            ColumnLayout {
                                id: varCol
                                width: parent.width
                                spacing: 0

                                Repeater {
                                    model: dialog.currentVariables()
                                        delegate: Rectangle {
                                            required property int index
                                            required property var modelData

                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 38
                                            color: "transparent"

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: Theme.spacing.s3
                                                anchors.rightMargin: Theme.spacing.s3
                                                spacing: Theme.spacing.s3

                                                UiCheckBox {
                                                    dark: dialog.dark
                                                    checked: modelData.enabled !== false
                                                    onToggled: dialog.updateVariable(index, "enabled", checked)
                                                }

                                                TextField {
                                                    Layout.preferredWidth: 180
                                                    text: modelData.key || ""
                                                    color: Theme.token("color-text-primary", dialog.dark)
                                                    font.family: "JetBrains Mono"
                                                    background: Rectangle { color: "transparent" }
                                                    onEditingFinished: dialog.updateVariable(index, "key", text.trim())
                                                }

                                                TextField {
                                                    Layout.fillWidth: true
                                                    text: modelData.value || ""
                                                    color: Theme.token("color-text-primary", dialog.dark)
                                                    font.family: "JetBrains Mono"
                                                    background: Rectangle { color: "transparent" }
                                                    onEditingFinished: dialog.updateVariable(index, "value", text)
                                                }

                                                ApiDeleteButton {
                                                    dark: dialog.dark
                                                    iconColor: Theme.token("color-text-regular", dialog.dark)
                                                    dangerColor: Theme.token("color-danger", dialog.dark)
                                                    onDeleteRequested: dialog.deleteVariable(index)
                                                }
                                            }

                                            Rectangle {
                                                anchors.bottom: parent.bottom
                                                width: parent.width
                                                height: 1
                                                color: Theme.token("color-bg-subtle-2", dialog.dark)
                                            }
                                        }
                                    }

                                    Rectangle {
                                        visible: dialog.currentVariables().length === 0
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 54
                                        color: "transparent"

                                        Label {
                                            anchors.centerIn: parent
                                            text: "暂无变量"
                                            color: Theme.token("color-text-secondary", dialog.dark)
                                            font.pixelSize: Theme.typeScale.body
                                        }
                                    }
                                }
                            }
                        }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.token("color-border-default", dialog.dark)
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "公共Headers"
                            Layout.fillWidth: true
                            color: Theme.token("color-text-primary", dialog.dark)
                            font.bold: true
                            font.pixelSize: Theme.typeScale.body
                        }

                        UiButton {
                            text: "新增Header"
                            dark: dialog.dark
                            variant: "secondary"
                            implicitWidth: 96
                            implicitHeight: 30
                            onClicked: dialog.addHeader()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radius.xs
                        color: "transparent"
                        border.color: Theme.token("color-border-default", dialog.dark)
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 32
                                color: Theme.token("color-table-header", dialog.dark)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.spacing.s3
                                    anchors.rightMargin: Theme.spacing.s3
                                    spacing: Theme.spacing.s3

                                    Label { text: "启用"; Layout.preferredWidth: 44; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: Theme.typeScale.caption }
                                    Label { text: "Header名"; Layout.preferredWidth: 180; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: Theme.typeScale.caption }
                                    Label { text: "Header值"; Layout.fillWidth: true; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: Theme.typeScale.caption }
                                    Label { text: "删除"; Layout.preferredWidth: 48; color: Theme.token("color-text-regular", dialog.dark); font.pixelSize: Theme.typeScale.caption; horizontalAlignment: Text.AlignRight }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: Theme.token("color-border-default", dialog.dark)
                            }

                            ColumnLayout {
                                id: headersColumn
                                width: parent.width
                                spacing: 0

                                Repeater {
                                    model: dialog.currentHeaders()
                                    delegate: Rectangle {
                                            required property int index
                                            required property var modelData

                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 38
                                            color: "transparent"

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: Theme.spacing.s3
                                                anchors.rightMargin: Theme.spacing.s3
                                                spacing: Theme.spacing.s3

                                                UiCheckBox {
                                                    dark: dialog.dark
                                                    checked: modelData.enabled !== false
                                                    onToggled: dialog.updateHeader(index, "enabled", checked)
                                                }

                                                TextField {
                                                    Layout.preferredWidth: 180
                                                    text: modelData.key || ""
                                                    color: Theme.token("color-text-primary", dialog.dark)
                                                    font.family: "JetBrains Mono"
                                                    placeholderText: "Header-Name"
                                                    placeholderTextColor: Theme.token("color-text-secondary", dialog.dark)
                                                    background: Rectangle { color: "transparent" }
                                                    onEditingFinished: dialog.updateHeader(index, "key", text.trim())
                                                }

                                                TextField {
                                                    Layout.fillWidth: true
                                                    text: modelData.value || ""
                                                    color: Theme.token("color-text-primary", dialog.dark)
                                                    font.family: "JetBrains Mono"
                                                    placeholderText: "Header-Value"
                                                    placeholderTextColor: Theme.token("color-text-secondary", dialog.dark)
                                                    background: Rectangle { color: "transparent" }
                                                    onEditingFinished: dialog.updateHeader(index, "value", text)
                                                }

                                                ApiDeleteButton {
                                                    dark: dialog.dark
                                                    iconColor: Theme.token("color-text-regular", dialog.dark)
                                                    dangerColor: Theme.token("color-danger", dialog.dark)
                                                    onDeleteRequested: dialog.deleteHeader(index)
                                                }
                                            }

                                            Rectangle {
                                                anchors.bottom: parent.bottom
                                                width: parent.width
                                                height: 1
                                                color: Theme.token("color-bg-subtle-2", dialog.dark)
                                            }
                                        }
                                    }

                                    Rectangle {
                                        visible: dialog.currentHeaders().length === 0
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 54
                                        color: "transparent"

                                        Label {
                                            anchors.centerIn: parent
                                            text: "暂无公共Header"
                                            color: Theme.token("color-text-secondary", dialog.dark)
                                            font.pixelSize: Theme.typeScale.body
                                        }
                                    }
                                }
                            }
                        }

                        }  // inner ColumnLayout
                    }  // UiScrollView

                    // ---- fixed footer ----
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.token("color-bg-subtle-2", dialog.dark)
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        Layout.bottomMargin: 4
                        Layout.leftMargin: 16
                        Layout.rightMargin: 16

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
