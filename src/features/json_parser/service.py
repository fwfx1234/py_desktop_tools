from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class JsonParseResult:
    output: str
    error: str
    error_line: int = 0
    error_column: int = 0
    error_phase: str = ""
    char_count: int = 0
    line_count: int = 0
    kind: str = ""
    size: int = 0
    depth: int = 0


class JsonService:
    def parse(self, text: str) -> tuple[Any, JsonParseResult]:
        result = JsonParseResult(output="", error="")
        stripped = text.strip()
        if not stripped:
            return None, result
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            result.error = str(exc.msg) if hasattr(exc, "msg") else str(exc)
            result.error_line = exc.lineno
            result.error_column = exc.colno
            result.error_phase = "parse"
            return None, result
        return value, result

    def format(self, text: str) -> JsonParseResult:
        value, result = self.parse(text)
        if result.error or value is None:
            return result
        output = json.dumps(value, ensure_ascii=False, indent=2)
        return self._with_stats(output, value)

    def compress(self, text: str) -> JsonParseResult:
        value, result = self.parse(text)
        if result.error or value is None:
            return result
        output = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return self._with_stats(output, value)

    def query(self, text: str, expression: str) -> JsonParseResult:
        value, result = self.parse(text)
        if result.error:
            return result
        if value is None:
            result.error = "无输入 JSON"
            result.error_phase = "query"
            return result
        expression = expression.strip()
        if not expression:
            return self.format(text)
        try:
            picked = _resolve_path(value, expression)
        except Exception as exc:
            result.error = f"查询错误: {exc}"
            result.error_phase = "query"
            return result
        output = json.dumps(picked, ensure_ascii=False, indent=2)
        return self._with_stats(output, picked)

    def _with_stats(self, output: str, value: Any) -> JsonParseResult:
        kind = _value_kind(value)
        size = _value_size(value)
        depth = _value_depth(value)
        line_count = output.count("\n") + 1 if output else 0
        return JsonParseResult(
            output=output,
            error="",
            char_count=len(output),
            line_count=line_count,
            kind=kind,
            size=size,
            depth=depth,
        )


def _value_kind(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def _value_size(value: Any) -> int:
    if isinstance(value, (dict, list)):
        return len(value)
    if isinstance(value, str):
        return len(value)
    return 0


def _value_depth(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + max((_value_depth(v) for v in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_value_depth(v) for v in value), default=0)
    return 0


def _resolve_path(data: Any, expression: str) -> Any:
    if not expression.startswith("$"):
        raise ValueError("查询语法必须以 $ 开头")
    if expression == "$":
        return data
    path = expression[1:]
    cur = data
    i = 0
    while i < len(path):
        if path[i] == ".":
            i += 1
            continue
        if path[i] == "[":
            j = path.index("]", i)
            idx = int(path[i + 1:j])
            cur = cur[idx]
            i = j + 1
            continue
        j = i
        while j < len(path) and path[j] not in (".", "["):
            j += 1
        key = path[i:j]
        if j < len(path) and path[j] == "[":
            i = j
            cur = cur[key]
            while i < len(path) and path[i] == "[":
                k = path.index("]", i)
                idx = int(path[i + 1:k])
                cur = cur[idx]
                i = k + 1
                if i < len(path) and path[i] == ".":
                    i += 1
        else:
            cur = cur[key]
            i = j
    return cur
