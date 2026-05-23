from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from .request_editor_state import RequestEditorState, snapshot_from_tab


SaveTabDraft = Callable[[dict], None]
SaveCaseSnapshot = Callable[[str, dict], None]


class TabsController:
    def __init__(
        self,
        editor: RequestEditorState,
        *,
        env_base_url: Callable[[], str],
        save_tab_draft: SaveTabDraft,
        save_case_snapshot: SaveCaseSnapshot,
        delete_tab: Callable[[str], None],
    ) -> None:
        self._editor = editor
        self._env_base_url = env_base_url
        self._save_tab_draft = save_tab_draft
        self._save_case_snapshot = save_case_snapshot
        self._delete_tab = delete_tab
        self.items: list[dict] = []
        self.current_index: int = -1
        self.applying: bool = False

    def current_tab(self) -> dict:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return {}

    def current_tab_id(self) -> str:
        return str(self.current_tab().get("id") or "")

    def set_items(self, items: list[dict]) -> None:
        self.items = list(items)
        if self.items and self.current_index < 0:
            self.current_index = 0
        elif not self.items:
            self.current_index = -1
        elif self.current_index >= len(self.items):
            self.current_index = len(self.items) - 1

    def set_current_index(self, index: int, environments: list[dict]) -> int | None:
        if index == self.current_index:
            return None
        self.persist_current()
        self.current_index = int(index)
        return self.apply_current_to_editor(environments)

    def apply_current_to_editor(self, environments: list[dict]) -> int | None:
        if not (0 <= self.current_index < len(self.items)):
            return None
        self.applying = True
        try:
            return self._editor.apply_tab(self.items[self.current_index], environments)
        finally:
            self.applying = False

    def persist_current(self) -> bool:
        if self.applying:
            return False
        if not (0 <= self.current_index < len(self.items)):
            return False
        tab = self._editor.update_tab_from_state(self.items[self.current_index], self._env_base_url())
        self.items[self.current_index] = tab
        self.items = list(self.items)
        if tab.get("kind") == "case":
            self._save_case_snapshot(str(tab.get("nodeId") or ""), snapshot_from_tab(tab))
        else:
            self._save_tab_draft(tab)
        return True

    def update_current_request(self, method: str, url: str) -> bool:
        if not (0 <= self.current_index < len(self.items)):
            return False
        tab = dict(self.items[self.current_index])
        clean_method = str(method or "GET")
        clean_url = str(url or "/")
        if tab.get("method") == clean_method and tab.get("url") == clean_url:
            return False
        tab["method"] = clean_method
        tab["url"] = clean_url
        self.items[self.current_index] = tab
        self.items = list(self.items)
        return True

    def update_current_active_request_tab(self, index: int) -> bool:
        if not (0 <= self.current_index < len(self.items)):
            return False
        tab = dict(self.items[self.current_index])
        normalized = max(0, int(index or 0))
        if int(tab.get("activeRequestTab") or 0) == normalized:
            return False
        tab["activeRequestTab"] = normalized
        self.items[self.current_index] = tab
        self.items = list(self.items)
        if tab.get("kind") == "case":
            self._save_case_snapshot(str(tab.get("nodeId") or ""), snapshot_from_tab(tab))
        else:
            self._save_tab_draft(tab)
        return True

    def rename_node_tabs(self, node_id: str, name: str) -> bool:
        clean_node_id = str(node_id or "")
        clean_name = str(name or "").strip()
        if not clean_node_id or not clean_name:
            return False
        changed = False
        for index, item in enumerate(self.items):
            if item.get("nodeId") != clean_node_id or item.get("name") == clean_name:
                continue
            tab = dict(item)
            tab["name"] = clean_name
            self.items[index] = tab
            if tab.get("kind") == "case":
                self._save_case_snapshot(str(tab.get("nodeId") or ""), snapshot_from_tab(tab))
            else:
                self._save_tab_draft(tab)
            changed = True
        if changed:
            self.items = list(self.items)
        return changed

    def sync_node_tab(self, node_id: str, name: str, method: str, url: str) -> bool:
        clean_node_id = str(node_id or "")
        if not clean_node_id:
            return False
        changed = False
        for index, item in enumerate(self.items):
            if item.get("nodeId") != clean_node_id:
                continue
            tab = dict(item)
            if str(name or "").strip() and tab.get("name") != str(name or "").strip():
                tab["name"] = str(name or "").strip()
            if method and tab.get("method") != method:
                tab["method"] = method
            if url and tab.get("url") != url:
                tab["url"] = url
            if tab == item:
                continue
            self.items[index] = tab
            if tab.get("kind") == "case":
                self._save_case_snapshot(str(tab.get("nodeId") or ""), snapshot_from_tab(tab))
            else:
                self._save_tab_draft(tab)
            changed = True
        if changed:
            self.items = list(self.items)
        return changed

    def open_endpoint(self, name: str, method: str, url: str, node_id: str, environments: list[dict]) -> bool:
        return self.open_request(name, method, url, node_id, "endpoint", {}, environments)

    def open_case(
        self,
        name: str,
        method: str,
        url: str,
        node_id: str,
        request_snapshot: dict,
        environments: list[dict],
    ) -> bool:
        return self.open_request(name, method, url, node_id, "case", request_snapshot, environments)

    def open_request(
        self,
        name: str,
        method: str,
        url: str,
        node_id: str,
        kind: str,
        request_snapshot: dict | None,
        environments: list[dict],
    ) -> bool:
        for index, tab in enumerate(self.items):
            if node_id and tab.get("nodeId") == node_id:
                self.persist_current()
                self.current_index = index
                self.sync_node_tab(node_id, name, method, url)
                self.apply_current_to_editor(environments)
                return False
        snapshot = request_snapshot or {}
        self.items.append(
            {
                "id": _new_tab_id(),
                "name": snapshot.get("name") or name,
                "method": snapshot.get("method") or method,
                "url": snapshot.get("url") or url,
                "requestMode": snapshot.get("requestMode") or "http",
                "bodyMode": snapshot.get("bodyMode") or "none",
                "authType": snapshot.get("authType") or "none",
                "authValue": snapshot.get("authValue") or "",
                "headersText": snapshot.get("headersText") or "",
                "cookiesText": snapshot.get("cookiesText") or "",
                "bodyText": snapshot.get("bodyText") or "{}",
                "paramsText": snapshot.get("paramsText") or "",
                "pathParamsText": snapshot.get("pathParamsText") or "",
                "envBaseUrl": snapshot.get("envBaseUrl") or "",
                "preOpsText": snapshot.get("preOpsText") or "",
                "postOpsText": snapshot.get("postOpsText") or "",
                "nodeId": node_id,
                "kind": kind,
                "mockMode": bool(snapshot.get("mockMode")),
            }
        )
        self.current_index = len(self.items) - 1
        self.apply_current_to_editor(environments)
        if kind != "case":
            self.persist_current()
        return True

    def close_current(self, environments: list[dict]) -> bool:
        if not (0 <= self.current_index < len(self.items)):
            return False
        tab_id = str(self.items[self.current_index].get("id") or "")
        if tab_id:
            self._delete_tab(tab_id)
        self.items.pop(self.current_index)
        if self.items:
            self.current_index = max(0, min(self.current_index, len(self.items) - 1))
            self.apply_current_to_editor(environments)
        else:
            self.current_index = -1
        return True


def _new_tab_id() -> str:
    return f"tab_{uuid4().hex[:12]}"
