from __future__ import annotations

import json
import pyperclip

from PySide6.QtCore import QObject, Signal, Slot


class JsonParserViewModel(QObject):
    """Simple feature: pure string processing fits inside the ViewModel.

    No service layer is needed because the logic has no IO, no threading and
    is unlikely to be reused by other features.
    """

    jsonProcessed = Signal(str, str)
    jsonCopied = Signal(bool, str)
    inputTextChanged = Signal(str)

    def __init__(self, initial_text: str = "") -> None:
        super().__init__()
        self._input_text = initial_text

    @Slot(result=str)
    def initialText(self) -> str:
        return self._input_text

    @Slot(str)
    def setInputText(self, text: str) -> None:
        if self._input_text == text:
            return
        self._input_text = text
        self.inputTextChanged.emit(text)

    @Slot(str, str)
    def processJson(self, jsonText: str, query: str) -> None:
        text, error = self._process(jsonText, query)
        self.jsonProcessed.emit(text, error)

    @Slot(str)
    def copyText(self, text: str) -> None:
        try:
            pyperclip.copy(text or "")
            self.jsonCopied.emit(True, "已复制到剪贴板")
        except Exception as exc:
            self.jsonCopied.emit(False, f"复制失败: {exc}")

    def _process(self, json_text: str, query: str) -> tuple[str, str]:
        try:
            parsed = json.loads(json_text) if json_text.strip() else None
        except Exception as exc:
            return "", f"JSON 解析错误: {exc}"
        if parsed is None:
            return "", ""
        if not query.strip():
            return json.dumps(parsed, ensure_ascii=False, indent=2), ""
        try:
            value = self._query_json(parsed, query.strip())
            return json.dumps(value, ensure_ascii=False, indent=2), ""
        except Exception as exc:
            return "", f"查询错误: {exc}"

    def _query_json(self, data, query: str):
        if not query.startswith("$"):
            raise ValueError("查询语法必须以 $ 开头")
        if query == "$":
            return data
        # 解析路径段，支持 .key 和 [index] 以及 key[0][1] 组合
        path = query[1:]  # 去掉开头的 $
        cur = data
        i = 0
        while i < len(path):
            if path[i] == ".":
                i += 1
                continue
            if path[i] == "[":
                # 数组索引 [...]
                j = path.index("]", i)
                idx = int(path[i + 1:j])
                cur = cur[idx]
                i = j + 1
            else:
                # 对象键
                j = i
                while j < len(path) and path[j] not in (".", "["):
                    j += 1
                key = path[i:j]
                if j < len(path) and path[j] == "[":
                    # key 后跟 [index]，如 key[0]
                    i = j
                    while i < len(path) and path[i] == "[":
                        k = path.index("]", i)
                        idx = int(path[i + 1:k])
                        cur = cur[key][idx]
                        i = k + 1
                        # 跳过连续的 ]... 之间的 .
                        if i < len(path) and path[i] == ".":
                            i += 1
                else:
                    cur = cur[key]
                    i = j
        return cur
