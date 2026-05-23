.pragma library


function envTag(name) {
    if (!name || name.length === 0)
        return "测"
    return name.slice(0, 1)
}


function parseKvText(textValue) {
    var out = []
    var text = textValue || ""
    var queryText = queryPart(text)
    if (queryText.length > 0)
        text = queryText.replace(/&/g, "\n")
    var lines = text.split("\n")
    for (var i = 0; i < lines.length; i++) {
        var line = (lines[i] || "").trim()
        if (!line)
            continue
        var sep = line.indexOf(":")
        if (sep < 0)
            sep = line.indexOf("=")
        var key = sep >= 0 ? line.slice(0, sep).trim() : line
        var value = sep >= 0 ? line.slice(sep + 1).trim() : ""
        if (key.length > 0)
            out.push({ enabled: true, key: key, value: value, type: "string", desc: "" })
    }
    return normalizeQueryRows(out)
}


function queryPart(textValue) {
    var text = (textValue || "").trim()
    var question = text.indexOf("?")
    if (question >= 0)
        text = text.slice(question + 1)
    var hash = text.indexOf("#")
    if (hash >= 0)
        text = text.slice(0, hash)
    if (text.indexOf("=") >= 0 && text.indexOf("&") >= 0)
        return text
    return ""
}


function decodePart(value) {
    var text = (value || "").replace(/\+/g, " ")
    try {
        return decodeURIComponent(text)
    } catch (e) {
        return text
    }
}


function parseQueryRowsText(textValue) {
    var out = []
    var text = queryPart(textValue)
    if (text.length === 0)
        text = textValue || ""
    var pairs = text.split(/[&\n]/)
    for (var i = 0; i < pairs.length; i++) {
        var line = (pairs[i] || "").trim()
        if (!line)
            continue
        var sep = line.indexOf("=")
        if (sep < 0)
            sep = line.indexOf(":")
        var key = sep >= 0 ? decodePart(line.slice(0, sep).trim()) : decodePart(line)
        var value = sep >= 0 ? decodePart(line.slice(sep + 1).trim()) : ""
        if (key.length > 0)
            out.push({ enabled: true, key: key, value: value, type: "string", desc: "" })
    }
    return normalizeQueryRows(out)
}


function normalizeRowsBySection(sectionName, rows) {
    if (sectionName === "query")
        return normalizeQueryRows(rows)
    if (sectionName === "path")
        return normalizePathRows(rows)
    if (sectionName === "body")
        return normalizeBodyRows(rows)
    if (sectionName === "headers")
        return normalizeHeaderRows(rows)
    if (sectionName === "cookies")
        return normalizeCookieRows(rows)
    return rows
}


function parseRowsBySection(sectionName, textValue) {
    if (sectionName === "query" || sectionName === "path")
        return sectionName === "query" ? parseQueryRowsText(textValue) : normalizePathRows(parseKvText(textValue))
    if (sectionName === "headers")
        return parseHeaderRowsText(textValue)
    if (sectionName === "cookies")
        return parseCookieRowsText(textValue)
    if (sectionName === "body")
        return normalizeBodyRows(parseKvText(textValue))
    return parseKvText(textValue)
}


function mergeImportedRows(sectionName, currentRows, importedRows, replaceExisting) {
    var emptyFactory = makeQueryParamRow
    if (sectionName === "path")
        emptyFactory = makePathParamRow
    else if (sectionName === "headers")
        emptyFactory = makeHeaderRow
    else if (sectionName === "cookies")
        emptyFactory = makeCookieRow
    else if (sectionName === "body")
        emptyFactory = makeBodyFormRow

    var out = []
    if (!replaceExisting) {
        var current = currentRows || []
        for (var i = 0; i < current.length; i++) {
            if (!isParamRowEmpty(current[i]))
                out.push(current[i])
        }
    }
    var imported = importedRows || []
    for (var j = 0; j < imported.length; j++) {
        if (!isParamRowEmpty(imported[j]))
            out.push(imported[j])
    }
    return normalizeParamRows(out, emptyFactory)
}


function parseCookieRowsText(textValue) {
    var out = []
    var text = textValue || ""
    var pairs = text.split(";")
    for (var i = 0; i < pairs.length; i++) {
        var line = (pairs[i] || "").trim()
        if (!line)
            continue
        var sep = line.indexOf("=")
        var key = sep >= 0 ? line.slice(0, sep).trim() : line
        var value = sep >= 0 ? line.slice(sep + 1).trim() : ""
        if (key.length > 0)
            out.push({ enabled: true, key: key, value: value, type: "string", desc: "" })
    }
    return normalizeCookieRows(out)
}


function parseHeaderRowsText(textValue) {
    var out = []
    var text = textValue || ""
    var lines = text.split("\n")
    for (var i = 0; i < lines.length; i++) {
        var line = (lines[i] || "").trim()
        if (!line)
            continue
        var sep = line.indexOf(":")
        var key = sep >= 0 ? line.slice(0, sep).trim() : line
        var value = sep >= 0 ? line.slice(sep + 1).trim() : ""
        if (key.length > 0)
            out.push({ enabled: true, key: key, value: value, type: "string", desc: "" })
    }
    return normalizeHeaderRows(out)
}


function buildCookieText(items) {
    var pairs = []
    for (var i = 0; i < items.length; i++) {
        var it = items[i]
        if (it.enabled === false)
            continue
        if (it.key && it.key.length > 0)
            pairs.push(it.key + "=" + (it.value || ""))
    }
    return pairs.join("; ")
}


function buildHeaderText(items) {
    var lines = []
    for (var i = 0; i < items.length; i++) {
        var it = items[i]
        if (it.enabled === false)
            continue
        if (it.key && it.key.length > 0)
            lines.push(it.key + ": " + (it.value || ""))
    }
    return lines.join("\n")
}


function normalizeCookieRows(rows) {
    return normalizeParamRows(rows, makeCookieRow)
}


function normalizeHeaderRows(rows) {
    return normalizeParamRows(rows, makeHeaderRow)
}


function normalizeBodyRows(rows) {
    var source = rows || []
    var compact = []
    for (var i = 0; i < source.length; i++) {
        var row = source[i]
        if (row.enabled === undefined)
            row.enabled = !isParamRowEmpty(row)
        if (!isParamRowEmpty(row))
            compact.push(row)
    }
    if (compact.length === 0)
        compact.push(makeBodyFormRow())
    compact.push(makeBodyFormRow())
    return compact
}


function normalizePathRows(rows) {
    return normalizeParamRows(rows, makePathParamRow)
}


function normalizeQueryRows(rows) {
    return normalizeParamRows(rows, makeQueryParamRow)
}


function normalizeParamRows(rows, emptyFactory) {
    var out = (rows || []).slice()
    for (var i = 0; i < out.length; i++) {
        if (out[i].enabled === undefined)
            out[i].enabled = !isParamRowEmpty(out[i])
    }
    if (out.length === 0) {
        out.push(emptyFactory())
        return out
    }
    while (out.length > 1 && isParamRowEmpty(out[out.length - 1]) && isParamRowEmpty(out[out.length - 2]))
        out.pop()
    if (!isParamRowEmpty(out[out.length - 1]))
        out.push(emptyFactory())
    return out
}


function isParamRowEmpty(row) {
    if (!row)
        return true
    var keyText = row.key || ""
    var valueText = row.value || ""
    return keyText.length === 0 && valueText.length === 0
}


function makeCookieRow() {
    return { enabled: false, key: "", value: "", type: "string", desc: "" }
}


function makeHeaderRow() {
    return { enabled: false, key: "", value: "", type: "string", desc: "" }
}


function makeBodyFormRow() {
    return { enabled: false, key: "", value: "" }
}


function makePathParamRow() {
    return { enabled: false, key: "", value: "", type: "string", desc: "" }
}


function makeQueryParamRow() {
    return { enabled: false, key: "", value: "", type: "string", desc: "" }
}


function buildKvText(items) {
    var lines = []
    for (var i = 0; i < items.length; i++) {
        var it = items[i]
        if (it.enabled === false)
            continue
        if (it.key && it.key.length > 0)
            lines.push(it.key + ":" + (it.value || ""))
    }
    return lines.join("\n")
}


function normalizeMethod(methodText) {
    if (!methodText)
        return "GET"
    var m = ("" + methodText).toUpperCase()
    return m === "DEL" ? "DELETE" : m
}


function requestModeForMethod(methodText) {
    return methodText === "WS" ? "websocket" : "http"
}
