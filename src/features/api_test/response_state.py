from __future__ import annotations

from datetime import datetime


class ResponseState:
    def __init__(self) -> None:
        self.title_text = "返回响应"
        self.body_text = ""
        self.headers_text = ""
        self.request_text = ""
        self.curl_text = ""
        self.request_log_text = ""
        self.log_entries: list[dict] = []

    def apply(self, title: str, body_text: str, details: dict | None = None) -> None:
        meta = details or {}
        self.title_text = title
        self.body_text = body_text or ""
        self.headers_text = str(meta.get("responseHeadersText") or "")
        self.request_text = str(meta.get("requestText") or "")
        self.curl_text = self._format_curl(str(meta.get("curlText") or ""))
        self.request_log_text = str(meta.get("requestLogText") or "")
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
    def _format_curl(curl_text: str) -> str:
        if not curl_text:
            return ""
        return curl_text.replace(" -", " \\\n -")
