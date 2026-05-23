from __future__ import annotations


class EnvironmentState:
    def __init__(self) -> None:
        self.items: list[dict] = [
            {
                "name": "默认环境",
                "baseUrl": "http://127.0.0.1:8000",
                "variables": [],
                "headers": [],
            }
        ]
        self.current_index: int = 0

    def set_items(self, items: list[dict]) -> None:
        self.items = list(items)
        if not self.items:
            self.current_index = -1
        elif self.current_index < 0:
            self.current_index = 0
        elif self.current_index >= len(self.items):
            self.current_index = len(self.items) - 1

    def set_current_index(self, index: int) -> None:
        self.current_index = int(index)

    def current_base_url(self) -> str:
        if 0 <= self.current_index < len(self.items):
            return str(self.items[self.current_index].get("baseUrl") or "")
        return ""
