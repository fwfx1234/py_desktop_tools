from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from app.storage import SQLiteConnection, SQLiteDatabase


class CollectionRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._db_path = self._database.path

    def load_tree(self) -> list[dict]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, parent_id, kind, name, method, url, request_json, sort_order, expanded
                FROM api_collection_nodes
                ORDER BY parent_id, sort_order, created_at
                """
            ).fetchall()
        nodes_by_id: dict[str, dict] = {}
        roots: list[dict] = []
        children_by_parent: dict[str, list[dict]] = {}
        for row in rows:
            node_id, parent_id, kind, name, method, url, request_json, _, expanded = row
            node: dict = {
                "id": node_id,
                "parentId": parent_id or "",
                "kind": kind,
                "name": name,
            }
            if kind == "folder":
                node["expanded"] = bool(expanded)
                node["children"] = []
            elif kind == "endpoint":
                node["method"] = method or "GET"
                node["path"] = url or "/"
                node["expanded"] = bool(expanded)
                node["children"] = []
            elif kind == "case":
                node["requestSnapshot"] = _loads_json_object(request_json)
            nodes_by_id[node_id] = node
            children_by_parent.setdefault(parent_id or "", []).append(node)
        for node in nodes_by_id.values():
            node["children"] = children_by_parent.get(node["id"], node.get("children", []))
        roots.extend(children_by_parent.get("", []))
        return roots

    def create_node(
        self,
        *,
        parent_id: str,
        kind: str,
        name: str,
        method: str = "GET",
        url: str = "/new-endpoint",
        request_snapshot: dict | None = None,
    ) -> str:
        now = int(time.time() * 1000)
        node_id = str(uuid4())
        parent = parent_id or ""
        clean_kind = kind if kind in {"folder", "endpoint", "case"} else "folder"
        clean_method = method if clean_kind == "endpoint" else ""
        clean_url = url if clean_kind == "endpoint" else ""
        expanded = 1 if clean_kind in {"folder", "endpoint"} else 0
        request_json = json.dumps(request_snapshot or {}, ensure_ascii=False)
        with self._database.connection() as conn:
            if not _can_create_child(conn, parent, clean_kind):
                return ""
            sort_order = _next_sort_order(conn, parent)
            conn.execute(
                """
                INSERT INTO api_collection_nodes (
                    id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    parent,
                    clean_kind,
                    name.strip() or "未命名",
                    clean_method,
                    clean_url,
                    request_json,
                    sort_order,
                    expanded,
                    now,
                    now,
                ),
            )
            if parent:
                conn.execute(
                    "UPDATE api_collection_nodes SET expanded = 1, updated_at = ? WHERE id = ?",
                    (now, parent),
                )
        return node_id

    def duplicate_node(self, node_id: str) -> str:
        if not node_id:
            return ""
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, parent_id, kind, name, method, url, request_json, sort_order, expanded
                FROM api_collection_nodes
                ORDER BY parent_id, sort_order, created_at
                """
            ).fetchall()
            by_parent: dict[str, list[Any]] = {}
            source = None
            for row in rows:
                by_parent.setdefault(row[1] or "", []).append(row)
                if row[0] == node_id:
                    source = row
            if source is None:
                return ""

            def copy_branch(row, parent_id: str, sibling_offset: int = 0) -> str:
                old_id, _, kind, name, method, url, request_json, _, expanded = row
                new_id = str(uuid4())
                sort_order = sibling_offset if parent_id != (source[1] or "") else _next_sort_order(conn, parent_id)
                new_name = f"{name} 副本" if old_id == node_id else name
                conn.execute(
                    """
                    INSERT INTO api_collection_nodes (
                        id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        parent_id,
                        kind,
                        new_name,
                        method,
                        url,
                        request_json,
                        sort_order,
                        expanded,
                        now,
                        now,
                    ),
                )
                for index, child in enumerate(by_parent.get(old_id, [])):
                    copy_branch(child, new_id, index)
                return new_id

            return copy_branch(source, source[1] or "")

    def rename_node(self, node_id: str, name: str) -> None:
        text = name.strip()
        if not node_id or not text:
            return
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                "UPDATE api_collection_nodes SET name = ?, updated_at = ? WHERE id = ?",
                (text, now, node_id),
            )

    def update_endpoint(self, node_id: str, method: str, url: str) -> None:
        if not node_id:
            return
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE api_collection_nodes
                SET method = ?, url = ?, updated_at = ?
                WHERE id = ? AND kind = 'endpoint'
                """,
                (method or "GET", url or "/", now, node_id),
            )

    def set_expanded(self, node_id: str, expanded: bool) -> None:
        if not node_id:
            return
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE api_collection_nodes
                SET expanded = ?, updated_at = ?
                WHERE id = ? AND kind IN ('folder', 'endpoint')
                """,
                (1 if expanded else 0, now, node_id),
            )

    def save_case_snapshot(self, node_id: str, snapshot: dict) -> None:
        if not node_id:
            return
        now = int(time.time() * 1000)
        request_json = json.dumps(snapshot or {}, ensure_ascii=False)
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE api_collection_nodes
                SET request_json = ?, updated_at = ?
                WHERE id = ? AND kind = 'case'
                """,
                (request_json, now, node_id),
            )

    def set_all_expanded(self, expanded: bool) -> None:
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE api_collection_nodes
                SET expanded = ?, updated_at = ?
                WHERE kind IN ('folder', 'endpoint')
                """,
                (1 if expanded else 0, now),
            )

    def delete_node(self, node_id: str) -> None:
        if not node_id:
            return
        with self._database.connection() as conn:
            rows = conn.execute("SELECT id, parent_id FROM api_collection_nodes").fetchall()
            children: dict[str, list[str]] = {}
            for child_id, parent_id in rows:
                children.setdefault(parent_id or "", []).append(child_id)
            to_delete: list[str] = []
            stack = [node_id]
            while stack:
                current = stack.pop()
                to_delete.append(current)
                stack.extend(children.get(current, []))
            conn.executemany("DELETE FROM api_collection_nodes WHERE id = ?", [(item,) for item in to_delete])
            conn.executemany(
                "UPDATE http_tabs SET node_id = '' WHERE node_id = ?",
                [(item,) for item in to_delete],
            )

    def move_node(self, node_id: str, target_parent_id: str, index_delta: int | None = None) -> None:
        if not node_id:
            return
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT parent_id, sort_order, kind FROM api_collection_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()
            if row is None:
                return
            parent_id, _, node_kind = row[0] or "", int(row[1] or 0), str(row[2] or "")
            if index_delta is not None:
                _reorder_node(conn, parent_id, node_id, index_delta, now)
                return
            target_parent = target_parent_id or ""
            if target_parent == node_id or _is_descendant(conn, target_parent, node_id):
                return
            if not _can_create_child(conn, target_parent, node_kind):
                return
            new_order = _next_sort_order(conn, target_parent)
            conn.execute(
                """
                UPDATE api_collection_nodes
                SET parent_id = ?, sort_order = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_parent, new_order, now, node_id),
            )
            if target_parent:
                conn.execute(
                    "UPDATE api_collection_nodes SET expanded = 1, updated_at = ? WHERE id = ?",
                    (now, target_parent),
                )

    def replace_tree(self, tree: list[dict]) -> None:
        now = int(time.time() * 1000)
        rows: list[tuple] = []

        def visit(nodes: list[dict], parent_id: str) -> None:
            for index, node in enumerate(nodes or []):
                if not isinstance(node, dict):
                    continue
                kind = node.get("kind") or node.get("type") or "folder"
                if kind not in {"folder", "endpoint", "case"}:
                    method_text = str(node.get("method") or "").upper()
                    if method_text == "CASE":
                        kind = "case"
                    elif node.get("method") or node.get("path") or node.get("url"):
                        kind = "endpoint"
                    else:
                        kind = "folder"
                node_id = str(node.get("id") or uuid4())
                name = str(node.get("name") or "未命名")
                method = str(node.get("method") or ("GET" if kind == "endpoint" else ""))
                url = str(node.get("path") or node.get("url") or ("/" if kind == "endpoint" else ""))
                request_json = json.dumps(node.get("requestSnapshot") or {}, ensure_ascii=False)
                expanded = 1 if node.get("expanded") is True else 0
                rows.append((node_id, parent_id, kind, name, method, url, request_json, index, expanded, now, now))
                visit(node.get("children") or [], node_id)

        visit(tree or [], "")
        with self._database.connection() as conn:
            conn.execute("DELETE FROM api_collection_nodes")
            conn.executemany(
                """
                INSERT INTO api_collection_nodes (
                    id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )


def _loads_json_object(value: str) -> dict:
    try:
        loaded = json.loads(value or "{}")
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _next_sort_order(conn: SQLiteConnection, parent_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM api_collection_nodes WHERE parent_id = ?",
        (parent_id or "",),
    ).fetchone()
    return int(row[0] or 0)


def _can_create_child(conn: SQLiteConnection, parent_id: str, child_kind: str) -> bool:
    if not parent_id:
        return child_kind in {"folder", "endpoint"}
    row = conn.execute(
        "SELECT kind FROM api_collection_nodes WHERE id = ?",
        (parent_id,),
    ).fetchone()
    if row is None:
        return False
    parent_kind = str(row[0] or "")
    if parent_kind == "folder":
        return child_kind in {"folder", "endpoint"}
    if parent_kind == "endpoint":
        return child_kind == "case"
    return False


def _reorder_node(
    conn: SQLiteConnection,
    parent_id: str,
    node_id: str,
    index_delta: int,
    updated_at: int,
) -> None:
    siblings = conn.execute(
        """
        SELECT id, sort_order
        FROM api_collection_nodes
        WHERE parent_id = ?
        ORDER BY sort_order, created_at
        """,
        (parent_id,),
    ).fetchall()
    ids = [item[0] for item in siblings]
    try:
        current_index = ids.index(node_id)
    except ValueError:
        return
    target_index = current_index + index_delta
    if target_index < 0 or target_index >= len(ids):
        return
    ids[current_index], ids[target_index] = ids[target_index], ids[current_index]
    for order, item_id in enumerate(ids):
        conn.execute(
            "UPDATE api_collection_nodes SET sort_order = ?, updated_at = ? WHERE id = ?",
            (order, updated_at, item_id),
        )


def _is_descendant(conn: SQLiteConnection, node_id: str, ancestor_id: str) -> bool:
    current = node_id
    while current:
        if current == ancestor_id:
            return True
        row = conn.execute(
            "SELECT parent_id FROM api_collection_nodes WHERE id = ?",
            (current,),
        ).fetchone()
        current = (row[0] if row else "") or ""
    return False
