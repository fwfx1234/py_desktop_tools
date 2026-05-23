from __future__ import annotations


class DebugCaseState:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.selected_ids: list[str] = []

    def set_items(self, items: list[dict], *, clear_selection: bool = False) -> None:
        self.items = list(items)
        if clear_selection:
            self.selected_ids = []

    def set_selected_ids(self, ids: list[str]) -> None:
        self.selected_ids = list(ids)

    def next_case_name(self) -> str:
        return f"调试用例 {len(self.items) + 1}"

    def toggle_by_index(self, index: int) -> bool:
        if index < 0 or index >= len(self.items):
            return False
        case_id = str(self.items[index].get("id") or "")
        return self.toggle_by_id(case_id)

    def toggle_by_id(self, case_id: str) -> bool:
        case_id = str(case_id or "")
        if not case_id:
            return False
        if case_id in self.selected_ids:
            self.selected_ids.remove(case_id)
        else:
            self.selected_ids.append(case_id)
        return True
