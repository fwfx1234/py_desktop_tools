import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBorder: "#D0D7DE"
    property color textMain: "#333333"
    property color textMuted: "#666666"
    property var collectionTree: []
    property var qtaFn: null
    property var methodColorFn: null
    property int treeRevision: 0
    property string selectedPath: ""
    property string selectedNodeId: ""

    signal importRequested()
    signal endpointSelected(string name, string method, string path, string nodeId)
    signal caseSelected(string name, string method, string path, string nodeId, var requestSnapshot)
    signal nodeCreated(string parentId, string kind, string name, string method, string path)
    signal nodeRenamed(string nodeId, string name)
    signal nodeDeleted(string nodeId)
    signal nodeDuplicated(string nodeId)
    signal nodeMoved(string nodeId, string targetParentId)
    signal nodeReordered(string nodeId, int delta)
    signal nodeExpandedChanged(string nodeId, bool expanded)
    signal allNodesExpandedChanged(bool expanded)

    function visibleBoundsInRoot() {
        var margin = 8
        var overlay = Overlay.overlay
        if (overlay)
            return {
                left: margin,
                top: margin,
                right: Math.max(margin, overlay.width - margin),
                bottom: Math.max(margin, overlay.height - margin)
            }
        var win = root.Window.window
        if (!win)
            return {
                left: margin,
                top: margin,
                right: Math.max(margin, root.width - margin),
                bottom: Math.max(margin, root.height - margin)
            }
        var topLeft = root.mapFromItem(null, 0, 0)
        var bottomRight = root.mapFromItem(null, win.width, win.height)
        return {
            left: topLeft.x + margin,
            top: topLeft.y + margin,
            right: bottomRight.x - margin,
            bottom: bottomRight.y - margin
        }
    }

    function clampPopupPosition(popup, preferredX, preferredY) {
        var bounds = visibleBoundsInRoot()
        var popupWidth = popup.width || popup.implicitWidth || 0
        var popupHeight = popup.height || popup.implicitHeight || 0
        var x = preferredX
        var y = preferredY
        if (x + popupWidth > bounds.right)
            x = bounds.right - popupWidth
        if (y + popupHeight > bounds.bottom)
            y = bounds.bottom - popupHeight
        x = Math.max(bounds.left, x)
        y = Math.max(bounds.top, y)
        return { x: x, y: y }
    }

    function positionPopupAt(popup, preferredX, preferredY) {
        var overlay = Overlay.overlay
        var localPos = overlay ? root.mapToItem(overlay, preferredX, preferredY) : { x: preferredX, y: preferredY }
        var pos = clampPopupPosition(popup, localPos.x, localPos.y)
        popup.x = pos.x
        popup.y = pos.y
    }

    function openPopupAt(popup, preferredX, preferredY) {
        popup._preferredX = preferredX
        popup._preferredY = preferredY
        positionPopupAt(popup, preferredX, preferredY)
        popup.open()
        Qt.callLater(function() {
            if (popup.opened)
                root.positionPopupAt(popup, popup._preferredX, popup._preferredY)
        })
    }

    function refreshVisibleRows() {
        if (treeFlick)
            treeFlick.visibleRows = root.flattenVisibleTree()
    }

    function ensureNodeId(node) {
        if (!node)
            return ""
        if (node.id && ("" + node.id).length > 0)
            return "" + node.id
        return ""
    }

    function nodePathById(nodeId) {
        if (!nodeId)
            return ""
        var found = ""
        function visit(list, parentPath) {
            var current = list || []
            for (var i = 0; i < current.length; i++) {
                var node = current[i]
                var path = parentPath ? (parentPath + "/" + i) : ("" + i)
                if (root.ensureNodeId(node) === nodeId) {
                    found = path
                    return true
                }
                if (node && node.children && visit(node.children, path))
                    return true
            }
            return false
        }
        visit(root.collectionTree || [], "")
        return found
    }

    function nodePathByObject(targetNode) {
        if (!targetNode)
            return ""
        var found = ""
        function visit(list, parentPath) {
            var current = list || []
            for (var i = 0; i < current.length; i++) {
                var node = current[i]
                var path = parentPath ? (parentPath + "/" + i) : ("" + i)
                if (node === targetNode) {
                    found = path
                    return true
                }
                if (node && node.children && visit(node.children, path))
                    return true
            }
            return false
        }
        visit(root.collectionTree || [], "")
        return found
    }

    function nodeById(nodeId) {
        var path = nodePathById(nodeId)
        return path.length > 0 ? nodeByPath(path) : null
    }

    function pathForNode(node, nodeId) {
        var objectPath = nodePathByObject(node)
        if (objectPath.length > 0)
            return objectPath
        if (nodeId && nodeId.length > 0)
            return nodePathById(nodeId)
        return nodePathById(root.ensureNodeId(node))
    }

    function currentContextPath() {
        if (root.contextPath && root.contextPath.length > 0) {
            var node = nodeByPath(root.contextPath)
            if (node && (!root.contextNodeId || root.contextNodeId.length === 0 || root.ensureNodeId(node) === root.contextNodeId))
                return root.contextPath
        }
        if (root.contextNodeId && root.contextNodeId.length > 0)
            return nodePathById(root.contextNodeId)
        return root.contextPath || ""
    }

    function contextNodeNow() {
        if (root.contextNodeId && root.contextNodeId.length > 0)
            return nodeById(root.contextNodeId)
        return null
    }

    function syncContextFromId() {
        root.contextPath = currentContextPath()
        root.contextNode = root.contextPath.length > 0 ? nodeByPath(root.contextPath) : null
        return root.contextNode
    }

    function openContextMenu(node, nodeId, preferredX, preferredY) {
        root.openContextMenuAtPath(node, nodeId, pathForNode(node, nodeId || root.ensureNodeId(node)), preferredX, preferredY)
    }

    function openContextMenuAtPath(node, nodeId, path, preferredX, preferredY) {
        var resolvedPath = path || ""
        var resolvedNode = resolvedPath.length > 0 ? nodeByPath(resolvedPath) : node
        var resolvedId = nodeId || root.ensureNodeId(resolvedNode)
        if (resolvedPath.length > 0)
            resolvedId = root.ensureNodeId(nodeByPath(resolvedPath))
        root.contextNodeId = resolvedId
        root.contextPath = resolvedPath
        root.contextNode = resolvedPath.length > 0 ? resolvedNode : null
        if (root.contextNode) {
            root.selectNodeByPath(resolvedPath)
            root.selectedNodeId = resolvedId
        } else {
            root.selectNodeByPath("")
        }
        root.openPopupAt(contextMenu, preferredX, preferredY)
    }

    function openRootContextMenu(preferredX, preferredY) {
        root.contextNodeId = ""
        root.contextPath = ""
        root.contextNode = null
        root.openPopupAt(contextMenu, preferredX, preferredY)
    }

    function openMoveMenuBesideContext() {
        root.syncContextFromId()
        var bounds = visibleBoundsInRoot()
        var gap = 6
        var preferredX = contextMenu.x + contextMenu.width + gap
        if (preferredX + moveMenu.width > bounds.right)
            preferredX = contextMenu.x - moveMenu.width - gap
        var pos = clampPopupPosition(moveMenu, preferredX, contextMenu.y)
        moveMenu.x = pos.x
        moveMenu.y = pos.y
        moveMenu.open()
    }

    function toggleNodeExpandedByPath(path) {
        var node = nodeByPath(path)
        if (!node || !canHaveChildrenNode(node))
            return
        root.nodeExpandedChanged(root.ensureNodeId(node), !node.expanded)
    }

    function toggleNodeExpandedById(nodeId) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        toggleNodeExpandedByPath(path)
    }

    function toggleNodeExpandedForNode(node, nodeId) {
        var path = pathForNode(node, nodeId)
        if (path.length === 0)
            return
        toggleNodeExpandedByPath(path)
    }

    function isFolderNode(node) {
        if (!node)
            return false
        if (node.kind === "folder")
            return true
        return node.children !== undefined && !isEndpointNode(node) && !isCaseNode(node)
    }

    function isEndpointNode(node) {
        if (!node)
            return false
        if (node.kind === "endpoint")
            return true
        return node.method !== undefined && normalizeMethod(node.method) !== "CASE" && node.kind !== "case"
    }

    function isCaseNode(node) {
        if (!node)
            return false
        return node.kind === "case" || normalizeMethod(node.method) === "CASE"
    }

    function canHaveChildrenNode(node) {
        return isFolderNode(node) || isEndpointNode(node)
    }

    function hasChildNodes(node) {
        return !!(node && node.children && node.children.length > 0)
    }

    function canContainNode(parentNode, childNode) {
        if (!parentNode || !childNode)
            return false
        var kind = isFolderNode(childNode) ? "folder" : (isEndpointNode(childNode) ? "endpoint" : (isCaseNode(childNode) ? "case" : ""))
        return canContainKind(parentNode, kind)
    }

    function canContainKind(parentNode, childKind) {
        if (!parentNode || !childKind)
            return false
        if (isFolderNode(parentNode))
            return childKind === "folder" || childKind === "endpoint"
        if (isEndpointNode(parentNode))
            return childKind === "case"
        return false
    }

    function nodeByPath(path) {
        if (path === "")
            return null
        var parts = path.split("/")
        var list = root.collectionTree || []
        var node = null
        for (var i = 0; i < parts.length; i++) {
            var index = parseInt(parts[i], 10)
            if (isNaN(index) || index < 0 || index >= list.length)
                return null
            node = list[index]
            list = (i < parts.length - 1) ? (node.children || []) : []
        }
        return node
    }

    function containerByPath(path) {
        if (!path)
            return null
        var parts = path.split("/")
        var list = root.collectionTree || []
        var parentNode = null
        for (var i = 0; i < parts.length - 1; i++) {
            var parentIndex = parseInt(parts[i], 10)
            if (isNaN(parentIndex) || parentIndex < 0 || parentIndex >= list.length)
                return null
            parentNode = list[parentIndex]
            list = parentNode.children || []
        }
        var index = parseInt(parts[parts.length - 1], 10)
        if (isNaN(index) || index < 0 || index >= list.length)
            return null
        return { list: list, index: index, node: list[index], parent: parentNode }
    }

    function isDescendantPath(parentPath, childPath) {
        return parentPath.length > 0 && (childPath === parentPath || childPath.indexOf(parentPath + "/") === 0)
    }

    function walkNodes(nodes, callback) {
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            callback(list[i])
            if (list[i].children)
                walkNodes(list[i].children, callback)
        }
    }

    function nextName(baseName) {
        var used = {}
        walkNodes(root.collectionTree, function(node) {
            used[node.name || ""] = true
        })
        if (!used[baseName])
            return baseName
        var index = 2
        while (used[baseName + " " + index])
            index += 1
        return baseName + " " + index
    }

    function nextEndpointPath(basePath) {
        var base = basePath || "/new-endpoint"
        var used = {}
        walkNodes(root.collectionTree, function(node) {
            if (root.isEndpointNode(node))
                used[node.path || "/"] = true
        })
        if (!used[base])
            return base
        var index = 2
        while (used[base + "-" + index])
            index += 1
        return base + "-" + index
    }

    function endpointAncestorByPath(path) {
        if (!path)
            return null
        var parts = path.split("/")
        if (parts.length <= 1)
            return null
        parts.pop()
        while (parts.length > 0) {
            var node = nodeByPath(parts.join("/"))
            if (isEndpointNode(node))
                return node
            parts.pop()
        }
        return null
    }

    function clearSelection() {
        root.selectedPath = ""
        root.selectedNodeId = ""
    }

    function selectNodeByPath(path) {
        var targetPath = path || ""
        clearSelection()
        var node = nodeByPath(targetPath)
        if (node) {
            root.selectedPath = targetPath
            root.selectedNodeId = root.ensureNodeId(node)
        }
        root.treeRevision += 1
        root.refreshVisibleRows()
    }

    function selectNodeById(nodeId) {
        var path = nodePathById(nodeId)
        if (path.length === 0) {
            root.selectNodeByPath("")
            return
        }
        root.selectNodeByPath(path)
        root.selectedNodeId = nodeId
    }

    function openEndpoint(node, path) {
        if (!root.isEndpointNode(node))
            return
        root.selectedPath = path || ""
        root.selectedNodeId = root.ensureNodeId(node)
        root.treeRevision += 1
        root.refreshVisibleRows()
        root.endpointSelected(node.name || "新接口", node.method || "GET", node.path || "/", root.selectedNodeId)
    }

    function openEndpointById(nodeId) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        openEndpoint(nodeByPath(path), path)
    }

    function openEndpointForNode(node, nodeId) {
        var path = pathForNode(node, nodeId)
        if (path.length === 0)
            return
        openEndpoint(nodeByPath(path), path)
    }

    function openCase(node, path) {
        if (!root.isCaseNode(node))
            return
        var endpoint = endpointAncestorByPath(path)
        if (!endpoint)
            return
        root.selectedPath = path || ""
        root.selectedNodeId = root.ensureNodeId(node)
        root.treeRevision += 1
        root.refreshVisibleRows()
        var snapshot = node.requestSnapshot || {}
        root.caseSelected(
            snapshot.name || node.name || "新场景",
            snapshot.method || endpoint.method || "GET",
            snapshot.url || endpoint.path || "/",
            root.ensureNodeId(node),
            snapshot
        )
    }

    function openCaseById(nodeId) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        openCase(nodeByPath(path), path)
    }

    function openCaseForNode(node, nodeId) {
        var path = pathForNode(node, nodeId)
        if (path.length === 0)
            return
        openCase(nodeByPath(path), path)
    }

    function createNodeAtPath(path, kind, asChild) {
        var parentId = ""
        var name = kind === "folder" ? nextName("新分组") : (kind === "case" ? nextName("新场景") : nextName("新接口"))
        var methodText = "GET"
        var pathText = kind === "endpoint" ? nextEndpointPath("/new-endpoint") : "/"
        if (!path) {
            if (kind === "case")
                return false
        } else if (asChild && canContainKind(nodeByPath(path), kind)) {
            var parentNode = nodeByPath(path)
            parentId = root.ensureNodeId(parentNode)
        } else {
            var hit = containerByPath(path)
            if (!hit)
                return false
            parentId = hit.parent ? root.ensureNodeId(hit.parent) : ""
        }
        if (kind === "case") {
            var endpoint = asChild ? nodeByPath(path) : endpointAncestorByPath(path)
            methodText = endpoint ? (endpoint.method || "GET") : "GET"
            pathText = endpoint ? (endpoint.path || "/") : "/"
        }
        root.nodeCreated(parentId, kind, name, methodText, pathText)
        return true
    }

    function addFolderAtPath(path, asChild) {
        createNodeAtPath(path || "", "folder", asChild)
    }

    function addEndpointAtPath(path, asChild) {
        createNodeAtPath(path || "", "endpoint", asChild)
    }

    function addCaseAtPath(path, asChild) {
        createNodeAtPath(path || "", "case", asChild)
    }

    function addRootFolder() {
        createNodeAtPath("", "folder", false)
    }

    function addRootEndpoint() {
        createNodeAtPath("", "endpoint", false)
    }

    function deleteNodeByPath(path) {
        var hit = containerByPath(path)
        if (!hit)
            return
        var deletedId = root.ensureNodeId(hit.node)
        if (root.selectedNodeId === deletedId) {
            root.selectedNodeId = ""
            root.selectedPath = ""
        }
        if (root.contextNodeId === deletedId) {
            root.contextNodeId = ""
            root.contextPath = ""
            root.contextNode = null
        }
        root.treeRevision += 1
        root.refreshVisibleRows()
        root.nodeDeleted(deletedId)
    }

    function renameNodeByPath(path, newName) {
        var text = (newName || "").trim()
        if (text.length === 0)
            return
        var node = nodeByPath(path)
        if (!node)
            return
        var targetId = root.ensureNodeId(node)
        root.selectedPath = path || root.selectedPath
        root.selectedNodeId = targetId
        root.editingPath = ""
        root.editingNodeId = ""
        root.pendingRenamePath = ""
        root.pendingRenameNodeId = ""
        root.treeRevision += 1
        root.refreshVisibleRows()
        root.nodeRenamed(targetId, text)
    }

    function cancelInlineRename(keepCommitGuard) {
        root.pendingRenamePath = ""
        root.pendingRenameNodeId = ""
        root.editingPath = ""
        root.editingNodeId = ""
        if (!keepCommitGuard)
            root.committingRename = false
        root.treeRevision += 1
    }

    function beginInlineRename(path) {
        root.pendingRenamePath = path || ""
        var node = nodeByPath(root.pendingRenamePath)
        root.pendingRenameNodeId = root.ensureNodeId(node)
        root.selectNodeByPath(root.pendingRenamePath)
        Qt.callLater(function() {
            if (root.pendingRenameNodeId.length === 0)
                return
            root.editingNodeId = root.pendingRenameNodeId
            root.editingPath = nodePathById(root.editingNodeId)
            root.pendingRenamePath = ""
            root.pendingRenameNodeId = ""
            root.treeRevision += 1
        })
    }

    function beginInlineRenameById(nodeId) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        root.pendingRenameNodeId = nodeId
        root.pendingRenamePath = path
        root.selectNodeById(nodeId)
        Qt.callLater(function() {
            if (root.pendingRenameNodeId.length === 0)
                return
            root.editingNodeId = root.pendingRenameNodeId
            root.editingPath = nodePathById(root.editingNodeId)
            root.pendingRenamePath = ""
            root.pendingRenameNodeId = ""
            root.treeRevision += 1
        })
    }

    function commitInlineRename(value) {
        if (root.committingRename)
            return
        root.committingRename = true
        var text = (value || "").trim()
        var targetPath = root.editingNodeId ? nodePathById(root.editingNodeId) : ""
        if (targetPath.length === 0)
            targetPath = root.editingPath || root.pendingRenamePath || root.selectedPath
        if (text.length > 0 && targetPath.length > 0)
            renameNodeByPath(targetPath, text)
        else
            root.cancelInlineRename(true)
        Qt.callLater(function() {
            root.committingRename = false
        })
    }

    function duplicateNodeByPath(path) {
        var hit = containerByPath(path)
        if (!hit)
            return
        root.nodeDuplicated(root.ensureNodeId(hit.node))
    }

    function moveNodeByPath(path, targetFolderPath) {
        var source = containerByPath(path)
        if (!source)
            return
        if (targetFolderPath && isDescendantPath(path, targetFolderPath))
            return
        var target = targetFolderPath ? nodeByPath(targetFolderPath) : null
        var moving = source.node
        if (targetFolderPath && !canContainNode(target, moving))
            return
        var movingNodeId = root.ensureNodeId(moving)
        root.contextNodeId = movingNodeId
        root.contextPath = path
        root.contextNode = moving
        root.nodeMoved(movingNodeId, targetFolderPath ? root.ensureNodeId(target) : "")
    }

    function moveNodeById(nodeId, targetFolderId) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        var targetPath = targetFolderId ? nodePathById(targetFolderId) : ""
        moveNodeByPath(path, targetPath)
    }

    function moveNodeUpDown(path, delta) {
        var hit = containerByPath(path)
        if (!hit)
            return
        var targetIndex = hit.index + delta
        if (targetIndex < 0 || targetIndex >= hit.list.length)
            return
        var movingNodeId = root.ensureNodeId(hit.node)
        root.contextNodeId = movingNodeId
        root.contextPath = path
        root.contextNode = hit.node
        root.nodeReordered(movingNodeId, delta)
    }

    function canMoveNodeByPath(path, delta) {
        var hit = containerByPath(path)
        if (!hit)
            return false
        var targetIndex = hit.index + delta
        return targetIndex >= 0 && targetIndex < hit.list.length
    }

    function setNodeExpandedByPath(path, expanded) {
        var node = nodeByPath(path)
        if (!root.canHaveChildrenNode(node))
            return
        root.nodeExpandedChanged(root.ensureNodeId(node), expanded)
    }

    function setNodeExpandedById(nodeId, expanded) {
        var path = nodePathById(nodeId)
        if (path.length === 0)
            return
        setNodeExpandedByPath(path, expanded)
    }

    function setContextNodeExpanded(expanded) {
        var path = currentContextPath()
        if (path.length === 0)
            return
        setNodeExpandedByPath(path, expanded)
    }

    function setAllExpanded(expanded) {
        root.allNodesExpandedChanged(expanded)
    }

    function normalizeMethod(methodText) {
        if (!methodText)
            return ""
        var m = ("" + methodText).toUpperCase()
        return m === "DEL" ? "DELETE" : m
    }

    function nodeVisible(node) {
        if (!node)
            return false
        var keyword = searchInput.text ? searchInput.text.trim().toLowerCase() : ""
        var filterMethod = methodFilterText
        var nameHit = !keyword || ((node.name || "").toLowerCase().indexOf(keyword) !== -1)
        var pathHit = !keyword || ((node.path || "").toLowerCase().indexOf(keyword) !== -1)
        var methodHit = filterMethod === "ALL"
            || root.isFolderNode(node)
            || root.isCaseNode(node)
            || normalizeMethod(node.method) === filterMethod
        var selfVisible = (nameHit || pathHit) && methodHit
        var children = node.children || []
        for (var i = 0; i < children.length; i++) {
            if (nodeVisible(children[i]))
                return true
        }
        return selfVisible
    }

    function flattenVisibleTree() {
        var rows = []
        function visit(list, depth, parentPath) {
            var current = list || []
            for (var i = 0; i < current.length; i++) {
                var node = current[i]
                var path = parentPath ? (parentPath + "/" + i) : ("" + i)
                if (!root.nodeVisible(node))
                    continue
                rows.push({
                    node: node,
                    nodeId: root.ensureNodeId(node),
                    path: path,
                    depth: depth
                })
                if (node && node.expanded && node.children)
                    visit(node.children, depth + 1, path)
            }
        }
        visit(root.collectionTree || [], 0, "")
        return rows
    }

    Layout.preferredWidth: 200
    Layout.fillHeight: true
    color: "transparent"

    function qta(name, colorValue, iconSize) {
        return root.qtaFn ? root.qtaFn(name, colorValue, iconSize) : ""
    }

    onCollectionTreeChanged: {
        root.treeRevision += 1
        root.refreshVisibleRows()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2.5"]
                anchors.rightMargin: Theme.space["2"]
                Label {
                    text: "接口"
                    Layout.fillWidth: true
                    color: root.textMain
                    font.bold: false
                    font.pixelSize: Theme.fontSize.heading
                }

                Rectangle {
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    radius: Theme.radii.xs
                    color: expandAllMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                    Image {
                        anchors.centerIn: parent
                        source: root.qta("mdi6.unfold-more-horizontal", root.textMuted, 14)
                        width: 14
                        height: 14
                        fillMode: Image.PreserveAspectFit
                    }
                    MouseArea {
                        id: expandAllMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.commitActiveRename()
                            root.setAllExpanded(true)
                        }
                    }
                    ToolTip.visible: expandAllMouse.containsMouse
                    ToolTip.text: "全部展开"
                }

                Rectangle {
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    radius: Theme.radii.xs
                    color: collapseAllMouse.containsMouse ? Theme.token("color-bg-subtle", root.dark) : "transparent"
                    Image {
                        anchors.centerIn: parent
                        source: root.qta("mdi6.unfold-less-horizontal", root.textMuted, 14)
                        width: 14
                        height: 14
                        fillMode: Image.PreserveAspectFit
                    }
                    MouseArea {
                        id: collapseAllMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.commitActiveRename()
                            root.setAllExpanded(false)
                        }
                    }
                    ToolTip.visible: collapseAllMouse.containsMouse
                    ToolTip.text: "全部收起"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space["2.5"]
            Layout.rightMargin: Theme.space["2.5"]
            Layout.bottomMargin: Theme.space["1"]
            spacing: Theme.space["1"]
            UiTextField {
                id: searchInput
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                dark: root.dark
                placeholderText: "搜索接口"
            }
            Rectangle {
                id: filterButton
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: Theme.radii.xs
                color: "transparent"
                border.color: root.panelBorder
                Image {
                    anchors.centerIn: parent
                    source: root.qta("mdi6.filter-variant", root.textMuted, 14)
                    width: 14
                    height: 14
                    fillMode: Image.PreserveAspectFit
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var p = filterButton.mapToItem(root, 0, filterButton.height + 4)
                        root.openPopupAt(filterMenu, p.x, p.y)
                    }
                }
            }
            UiIconButton {
                id: addButton
                dark: root.dark
                controlSize: 28
                iconSize: 14
                iconName: "mdi6.plus"
                tooltip: "新增"
                onClicked: {
                    var p = addButton.mapToItem(root, 0, addButton.height + 4)
                    root.openPopupAt(addMenu, p.x, p.y)
                }
            }
        }

        Flickable {
            id: treeFlick
            Layout.fillWidth: true
            Layout.fillHeight: true
            property var visibleRows: root.flattenVisibleTree()
            contentHeight: Math.max(height, treeColumn.implicitHeight)
            clip: true

            Connections {
                target: root
                function onTreeRevisionChanged() {
                    treeFlick.visibleRows = root.flattenVisibleTree()
                }
            }

            Connections {
                target: searchInput
                function onTextChanged() {
                    treeFlick.visibleRows = root.flattenVisibleTree()
                }
            }

            MouseArea {
                width: treeFlick.width
                height: Math.max(treeFlick.height, treeColumn.implicitHeight)
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onPressed: function(mouse) {
                    if (mouse.button === Qt.LeftButton && root.editingNodeId.length > 0)
                        root.commitActiveRename()
                }
                onClicked: function(mouse) {
                    if (mouse.button === Qt.RightButton) {
                        var p = mapToItem(root, mouse.x, mouse.y)
                        root.openRootContextMenu(p.x, p.y)
                    }
                }
            }

            ColumnLayout {
                id: treeColumn
                width: parent.width
                z: 1
                spacing: 0

                Repeater {
                    model: treeFlick.visibleRows
                    delegate: nodeComponent
                }
            }
        }
    }

    property string methodFilterText: "ALL"

    Component {
        id: nodeComponent
        Item {
            id: nodeRoot
            required property var modelData

            property var node: modelData.node
            property int depth: modelData.depth || 0
            property string nodePath: modelData.path || ""
            property string nodeId: modelData.nodeId || root.ensureNodeId(nodeRoot.node)
            property int revision: root.treeRevision

            Layout.fillWidth: true
            implicitWidth: parent ? parent.width : 0
            visible: root.nodeVisible(nodeRoot.node)
            implicitHeight: visible ? 28 : 0

            Rectangle {
                id: nodeRow
                anchors.fill: parent
                height: 28
                property bool active: root.selectedNodeId.length > 0 && root.selectedNodeId === nodeRoot.nodeId
                color: active
                    ? Theme.token("color-primary-bg", root.dark)
                    : (nodeMouse.containsMouse
                    ? Theme.token("color-bg-subtle-2", root.dark)
                    : "transparent")
                border.width: 0
                border.color: "transparent"

                Rectangle {
                    visible: nodeRow.active
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 2
                    color: Theme.token("color-primary-active", root.dark)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["2.5"] + nodeRoot.depth * 14
                    anchors.rightMargin: Theme.space["2"]
                    spacing: 6
                    property bool isCase: !!root.isCaseNode(nodeRoot.node)

                    Item {
                        visible: !!(root.canHaveChildrenNode(nodeRoot.node) && root.hasChildNodes(nodeRoot.node))
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 12
                        Image {
                            anchors.centerIn: parent
                            source: root.qta(
                                (nodeRoot.node && nodeRoot.node.expanded) ? "mdi6.chevron-down" : "mdi6.chevron-right",
                                root.textMuted,
                                12
                            )
                            width: 12
                            height: 12
                            fillMode: Image.PreserveAspectFit
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleNodeExpandedByPath(nodeRoot.nodePath)
                        }
                    }

                    Item {
                        visible: !(root.canHaveChildrenNode(nodeRoot.node) && root.hasChildNodes(nodeRoot.node))
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 12
                    }

                    Label {
                        visible: !!(root.isEndpointNode(nodeRoot.node) && nodeRoot.node.method !== undefined)
                        text: (nodeRoot.node && nodeRoot.node.method) ? nodeRoot.node.method : ""
                        color: root.methodColorFn ? root.methodColorFn(nodeRoot.node ? nodeRoot.node.method : "") : root.textMuted
                        font.bold: false
                        font.family: Theme.fontFamily.mono
                        font.pixelSize: Theme.fontSize.caption
                        Layout.preferredWidth: 36
                    }

                    Image {
                        visible: parent.isCase
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        source: root.qta("mdi6.lightning-bolt-outline", Theme.token("color-primary-active", root.dark), 14)
                        fillMode: Image.PreserveAspectFit
                    }

                    Label {
                        visible: root.editingNodeId !== nodeRoot.nodeId
                        text: (nodeRoot.node ? nodeRoot.node.name : "") + ((nodeRoot.node && nodeRoot.node.count) ? " (" + nodeRoot.node.count + ")" : "")
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: nodeRow.active ? Theme.token("color-primary-active", root.dark) : root.textMain
                        font.pixelSize: Theme.fontSize.body
                        font.bold: false
                    }

                    Rectangle {
                        visible: false
                        Layout.preferredWidth: 8
                        Layout.preferredHeight: 8
                        radius: 4
                        color: Theme.token("color-primary-active", root.dark)
                        opacity: 0.45
                    }
                }

                UiTextField {
                    id: inlineRenameInput
                    dark: root.dark
                    visible: root.editingNodeId === nodeRoot.nodeId
                    z: 4
                    x: {
                        var base = Theme.space["2.5"] + nodeRoot.depth * 14 + 10 + 6
                        if (root.isEndpointNode(nodeRoot.node) && nodeRoot.node.method !== undefined)
                            base += 32 + 6
                        if (root.isCaseNode(nodeRoot.node))
                            base += 14 + 6
                        return base
                    }
                    y: 3
                    width: Math.max(80, nodeRow.width - x - Theme.space["2"])
                    height: 22
                    text: nodeRoot.node ? (nodeRoot.node.name || "") : ""
                    selectByMouse: true
                    leftPadding: 6
                    rightPadding: 6
                    topPadding: 0
                    bottomPadding: 0
                    color: root.textMain
                    font.pixelSize: Theme.fontSize.body
                    font.family: Theme.fontFamily.ui
                    background: Rectangle {
                        radius: 3
                        border.width: 1
                        border.color: Theme.token("color-primary-active", root.dark)
                        color: Theme.token("color-bg-surface", root.dark)
                    }
                    onVisibleChanged: {
                        if (visible) {
                            forceActiveFocus()
                            selectAll()
                            root.activeRenameText = text
                        }
                    }
                    onTextChanged: {
                        if (visible && root.editingNodeId === nodeRoot.nodeId)
                            root.activeRenameText = text
                    }
                    onAccepted: root.commitInlineRename(inlineRenameInput.text)
                    Keys.onReturnPressed: root.commitInlineRename(inlineRenameInput.text)
                    Keys.onEnterPressed: root.commitInlineRename(inlineRenameInput.text)
                    Keys.onEscapePressed: root.cancelInlineRename()
                    onActiveFocusChanged: {
                        if (!activeFocus && visible)
                            root.commitInlineRename(inlineRenameInput.text)
                    }
                }

                MouseArea {
                    id: nodeMouse
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    enabled: root.editingNodeId !== nodeRoot.nodeId
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    z: 2
                    onPressed: function(mouse) {
                        if (root.editingNodeId.length > 0 && root.editingNodeId !== nodeRoot.nodeId)
                            root.commitActiveRename()
                    }
                    onClicked: function(mouse) {
                        if (mouse.button === Qt.RightButton) {
                            var p = parent.mapToItem(root, mouse.x, mouse.y)
                            root.openContextMenuAtPath(nodeRoot.node, nodeRoot.nodeId, nodeRoot.nodePath, p.x, p.y)
                            return
                        }
                        var toggleLeft = Theme.space["2.5"] + nodeRoot.depth * 14
                        var toggleRight = toggleLeft + 16
                        if (root.canHaveChildrenNode(nodeRoot.node) && root.hasChildNodes(nodeRoot.node)
                                && mouse.x >= toggleLeft && mouse.x <= toggleRight) {
                            root.toggleNodeExpandedByPath(nodeRoot.nodePath)
                            return
                        }
                        if (root.isFolderNode(nodeRoot.node)) {
                            root.toggleNodeExpandedByPath(nodeRoot.nodePath)
                        } else if (root.isEndpointNode(nodeRoot.node)) {
                            root.openEndpoint(root.nodeByPath(nodeRoot.nodePath), nodeRoot.nodePath)
                        } else if (root.isCaseNode(nodeRoot.node)) {
                            root.openCase(root.nodeByPath(nodeRoot.nodePath), nodeRoot.nodePath)
                        }
                    }
                }
            }
        }
    }


    UiMenuPopup {
        id: addMenu
        width: 148
        padding: 4
        dark: root.dark
        property real _preferredX: 0
        property real _preferredY: 0

        contentItem: Column {
            spacing: 0

            UiMenuItem {
                width: addMenu.width - 8
                dark: root.dark
                text: "新建接口"
                onTriggered: {
                    root.addRootEndpoint()
                    addMenu.close()
                }
            }
            UiMenuItem {
                width: addMenu.width - 8
                dark: root.dark
                text: "新建分组"
                onTriggered: {
                    root.addRootFolder()
                    addMenu.close()
                }
            }
            UiMenuItem {
                width: addMenu.width - 8
                dark: root.dark
                text: "导入 OpenAPI"
                onTriggered: {
                    root.importRequested()
                    addMenu.close()
                }
            }
        }
    }

    UiMenuPopup {
        id: filterMenu
        width: 120
        padding: 4
        dark: root.dark
        property real _preferredX: 0
        property real _preferredY: 0

        contentItem: Column {
            spacing: 0
            Repeater {
                model: ["ALL", "GET", "POST", "PUT", "DELETE", "PATCH"]
                delegate: UiMenuItem {
                    required property var modelData
                    width: filterMenu.width - 8
                    dark: root.dark
                    text: modelData === "ALL" ? "全部方法" : modelData
                    checked: root.methodFilterText === modelData
                    reserveCheckSpace: true
                    onTriggered: {
                        root.methodFilterText = modelData
                        filterMenu.close()
                    }
                }
            }
        }
    }

    property var contextNode: null
    property string contextNodeId: ""
    property string contextPath: ""
    property var moveGroupTargets: []
    property string moveSourcePath: ""
    property string moveSourceNodeId: ""
    property string editingNodeId: ""
    property string editingPath: ""
    property string pendingRenameNodeId: ""
    property string pendingRenamePath: ""
    property bool committingRename: false
    property string activeRenameText: ""

    function commitActiveRename() {
        if (root.editingNodeId.length === 0)
            return
        root.commitInlineRename(root.activeRenameText)
    }

    function collectFolderTargets(nodes, out, parentPath) {
        var list = nodes || []
        var prefix = parentPath || ""
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            var path = prefix ? (prefix + "/" + i) : ("" + i)
            if (isFolderNode(n))
                out.push({ name: n.name || "未命名分组", path: path, nodeId: root.ensureNodeId(n) })
            if (n && n.children)
                collectFolderTargets(n.children, out, path)
        }
    }

    UiMenuPopup {
        id: contextMenu
        width: 180
        dark: root.dark
        property real _preferredX: 0
        property real _preferredY: 0

        contentItem: Column {
            id: contextMenuColumn
            spacing: 0

            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !root.contextNode
                text: "新建接口"
                onTriggered: { root.addRootEndpoint(); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !root.contextNode
                text: "新建分组"
                onTriggered: { root.addRootFolder(); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !root.contextNode
                text: "导入 OpenAPI"
                onTriggered: { root.importRequested(); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !root.contextNode
                text: "全部展开"
                onTriggered: { root.setAllExpanded(true); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !root.contextNode
                text: "全部收起"
                onTriggered: { root.setAllExpanded(false); contextMenu.close() }
            }

            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && root.isEndpointNode(root.contextNode))
                text: "新建场景"
                onTriggered: { root.addCaseAtPath(root.currentContextPath(), true); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && root.isCaseNode(root.contextNode))
                text: "新建同级场景"
                onTriggered: { root.addCaseAtPath(root.currentContextPath(), false); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && root.isFolderNode(root.contextNode))
                text: "新建子接口"
                onTriggered: { root.addEndpointAtPath(root.currentContextPath(), true); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && !root.isCaseNode(root.contextNode))
                text: "新建同级接口"
                onTriggered: { root.addEndpointAtPath(root.currentContextPath(), false); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && root.isFolderNode(root.contextNode))
                text: "新建子分组"
                onTriggered: { root.addFolderAtPath(root.currentContextPath(), true); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && !root.isCaseNode(root.contextNode))
                text: "新建同级分组"
                onTriggered: { root.addFolderAtPath(root.currentContextPath(), false); contextMenu.close() }
            }

            UiMenuSeparator {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
            }

            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && root.canHaveChildrenNode(root.contextNode) && root.hasChildNodes(root.contextNode))
                text: root.contextNode && root.contextNode.expanded ? "收起" : "展开"
                onTriggered: {
                    root.setContextNodeExpanded(!(root.contextNode && root.contextNode.expanded))
                    contextMenu.close()
                }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!(root.contextNode && !root.isCaseNode(root.contextNode))
                text: "移动到分组"
                onTriggered: {
                    var groups = []
                    root.collectFolderTargets(root.collectionTree, groups, "")
                    groups = groups.filter(function(group) {
                        var sourcePath = root.currentContextPath()
                        return group.path !== sourcePath && !root.isDescendantPath(sourcePath, group.path)
                    })
                    groups.unshift({ name: "根目录", path: "" })
                    root.moveSourcePath = root.currentContextPath()
                    root.moveSourceNodeId = root.contextNodeId
                    root.moveGroupTargets = groups
                    root.openMoveMenuBesideContext()
                }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
                itemEnabled: root.canMoveNodeByPath(root.currentContextPath(), -1)
                text: "上移"
                onTriggered: {
                    root.moveNodeUpDown(root.currentContextPath(), -1)
                    contextMenu.close()
                }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
                itemEnabled: root.canMoveNodeByPath(root.currentContextPath(), 1)
                text: "下移"
                onTriggered: {
                    root.moveNodeUpDown(root.currentContextPath(), 1)
                    contextMenu.close()
                }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
                text: "复制"
                onTriggered: { root.duplicateNodeByPath(root.currentContextPath()); contextMenu.close() }
            }

            UiMenuSeparator {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
            }

            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
                text: "重命名"
                onTriggered: { root.beginInlineRenameById(root.contextNodeId); contextMenu.close() }
            }
            UiMenuItem {
                width: contextMenu.width - 8
                dark: root.dark
                visible: !!root.contextNode
                destructive: true
                text: "删除"
                onTriggered: { root.deleteNodeByPath(root.currentContextPath()); contextMenu.close() }
            }
        }
    }

    UiMenuPopup {
        id: moveMenu
        width: 200
        maxPopupHeight: 300
        dark: root.dark
        property real _preferredX: 0
        property real _preferredY: 0

        contentItem: Column {
            spacing: 0
            Repeater {
                model: root.moveGroupTargets
                delegate: UiMenuItem {
                    required property var modelData
                    width: moveMenu.width - 8
                    dark: root.dark
                    text: modelData.name || "未命名分组"
                    onTriggered: {
                        if (root.moveSourceNodeId)
                            root.moveNodeById(root.moveSourceNodeId, modelData.nodeId || "")
                        else
                            root.moveNodeByPath(root.moveSourcePath, modelData.path)
                        moveMenu.close()
                        contextMenu.close()
                    }
                }
            }
        }
    }

}
