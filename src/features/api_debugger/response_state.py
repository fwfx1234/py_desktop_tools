from __future__ import annotations

from datetime import datetime
import html as html_mod
import json
import re


class ResponseState:
    def __init__(self) -> None:
        self.title_text = "返回响应"
        self.body_text = ""
        self.body_html = ""
        self.headers_text = ""
        self.request_text = ""
        self.curl_text = ""
        self.request_log_text = ""
        self.log_entries: list[dict] = []
        self.status_code = ""
        self.elapsed_ms = ""
        self.final_url = ""
        self.outcome = "idle"

    def apply(self, title: str, body_text: str, details: dict | None = None) -> None:
        meta = details or {}
        self.title_text = title
        self.body_text = body_text or ""
        self.body_html = self._format_json_to_html(body_text or "")
        self.headers_text = str(meta.get("responseHeadersText") or "")
        self.request_text = str(meta.get("requestText") or "")
        self.curl_text = self._format_curl(str(meta.get("curlText") or ""))
        self.request_log_text = str(meta.get("requestLogText") or "")
        self.status_code = self._status_code(title, meta)
        self.elapsed_ms = str(meta.get("elapsedMs") or "")
        self.final_url = str(meta.get("finalUrl") or "")
        self.outcome = self._outcome(title, self.status_code)
        if self.request_log_text:
            self.log_entries = [
                {
                    "title": title,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": self.request_log_text,
                },
                *self.log_entries,
            ][:20]

    @staticmethod
    def _format_json_to_html(text: str) -> str:
        if not text or not text.strip():
            return ""
        try:
            parsed = json.loads(text)
            formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, ValueError):
            return html_mod.escape(text)

        def _colorize(val: str) -> str:
            escaped = html_mod.escape(val)
            result = []
            i = 0
            while i < len(escaped):
                ch = escaped[i]
                if ch == '"' and (i == 0 or escaped[i - 1] != '\\'):
                    j = escaped.index('"', i + 1) if '"' in escaped[i + 1:] else len(escaped)
                    result.append(f'<span style="color:#6a8759">"{escaped[i + 1:j]}"</span>')
                    i = j + 1
                    continue
                result.append(ch)
                i += 1
            return "".join(result)

        lines = formatted.split("\n")
        colored_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                colored_lines.append("")
                continue
            # colorize keys (before colon in JSON)
            colon_idx = stripped.find(": ")
            if colon_idx > 0 and stripped[:colon_idx].strip().startswith('"'):
                key_end = colon_idx
                # Key is quoted
                indent = line[:len(line) - len(line.lstrip())]
                key = stripped[:key_end].strip()
                rest = stripped[key_end:]
                colored_lines.append(
                    f'{indent}<span style="color:#9cdcfe">{html_mod.escape(key)}</span>'
                    f'{_colorize(rest)}'
                )
            else:
                colored_lines.append(_colorize(line))
        inner = "<br/>".join(colored_lines)
        return (
            '<pre style="font-family:monospace;margin:0;white-space:pre-wrap;word-wrap:break-word">'
            f'{inner}'
            '</pre>'
        )

    @staticmethod
    def _format_curl(curl_text: str) -> str:
        if not curl_text:
            return ""
        return curl_text.replace(" -", " \\\n -")

    @staticmethod
    def _status_code(title: str, meta: dict) -> str:
        status_code = str(meta.get("statusCode") or "").strip()
        if status_code:
            return status_code
        match = re.search(r"状态:\s*(\d{3})", title or "")
        return match.group(1) if match else ""

    @staticmethod
    def _outcome(title: str, status_code: str) -> str:
        text = title or ""
        if "ERR" in text or "FAIL" in text or "WS_ERR" in text:
            return "error"
        if "MOCK" in text:
            return "mock"
        if text.startswith("状态: WS"):
            return "ws"
        if status_code:
            try:
                code = int(status_code)
            except ValueError:
                return "info"
            if 200 <= code < 300:
                return "success"
            if 300 <= code < 400:
                return "redirect"
            if code >= 400:
                return "error"
        return "info" if text and text != "返回响应" else "idle"
