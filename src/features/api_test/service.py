from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4
from base64 import b64encode
from urllib.parse import quote

import yaml
from app.storage import SQLiteDatabase

from .case_service import DebugCaseService
from .db import ApiDatabase
from .http_service import HttpRequestService
from .repositories.collection_repo import CollectionRepository
from .repositories.environment_repo import EnvironmentRepository
from .repositories.tab_repo import TabRepository
from .script_service import ScriptService
from .variable_service import VariableService
from .ws_service import WebSocketSessionService


class ApiTestService:
    def __init__(self, database: SQLiteDatabase | Path | None = None) -> None:
        self._history: list[dict] = []
        self._database = ApiDatabase(database)
        self._db_path = self._database.path
        self._collections = CollectionRepository(self._database.storage)
        self._environments = EnvironmentRepository(self._database.storage)
        self._tabs = TabRepository(self._database.storage)
        self._variables = VariableService(self._database.storage)
        self._scripts = ScriptService()
        self._http = HttpRequestService(self._variables, self._scripts)
        self._ws = WebSocketSessionService(self._database.storage, self._variables)
        self._cases = DebugCaseService(self._database.storage)

    def list_tabs(self) -> list[dict]:
        return self._tabs.list_tabs()

    def list_environments(self) -> list[dict]:
        return self._environments.list_environments()

    def save_environments(self, environments: list[dict]) -> None:
        self._environments.save_environments(environments)

    def _environment_for_base_url(self, env_base_url: str) -> dict:
        base_url = (env_base_url or "").strip()
        for env in self.list_environments():
            if (env.get("baseUrl") or "").strip() == base_url:
                return env
        return {}

    @staticmethod
    def _environment_vars(env: dict) -> dict[str, str]:
        values: dict[str, str] = {}
        for row in env.get("variables") or []:
            if not isinstance(row, dict) or row.get("enabled") is False:
                continue
            key = str(row.get("key") or "").strip()
            if not key:
                continue
            values[key] = str(row.get("value") or "")
        return values

    def load_collection_tree(self) -> list[dict]:
        return self._collections.load_tree()

    def create_collection_node(
        self,
        *,
        parent_id: str,
        kind: str,
        name: str,
        method: str = "GET",
        url: str = "/new-endpoint",
        request_snapshot: dict | None = None,
    ) -> str:
        return self._collections.create_node(
            parent_id=parent_id,
            kind=kind,
            name=name,
            method=method,
            url=url,
            request_snapshot=request_snapshot,
        )

    def duplicate_collection_node(self, node_id: str) -> str:
        return self._collections.duplicate_node(node_id)

    def rename_collection_node(self, node_id: str, name: str) -> None:
        self._collections.rename_node(node_id, name)

    def update_collection_endpoint(self, node_id: str, method: str, url: str) -> None:
        self._collections.update_endpoint(node_id, method, url)

    def set_collection_node_expanded(self, node_id: str, expanded: bool) -> None:
        self._collections.set_expanded(node_id, expanded)

    def save_case_snapshot(self, node_id: str, snapshot: dict) -> None:
        self._collections.save_case_snapshot(node_id, snapshot)

    def set_all_collection_nodes_expanded(self, expanded: bool) -> None:
        self._collections.set_all_expanded(expanded)

    def delete_collection_node(self, node_id: str) -> None:
        self._collections.delete_node(node_id)

    def move_collection_node(self, node_id: str, target_parent_id: str, index_delta: int | None = None) -> None:
        self._collections.move_node(node_id, target_parent_id, index_delta)

    def replace_collection_tree(self, tree: list[dict]) -> None:
        self._collections.replace_tree(tree)

    def upsert_tab(
        self,
        tab_id: str,
        name: str,
        method: str,
        url: str,
        request_mode: str,
        body_mode: str,
        auth_type: str,
        auth_value: str,
        headers_text: str,
        cookies_text: str,
        body_text: str,
        params_text: str,
        path_params_text: str,
        env_base_url: str,
        pre_ops_text: str,
        post_ops_text: str,
        node_id: str,
        mock_mode: bool,
    ) -> None:
        self._tabs.upsert_tab(
            tab_id,
            name,
            method,
            url,
            request_mode,
            body_mode,
            auth_type,
            auth_value,
            headers_text,
            cookies_text,
            body_text,
            params_text,
            path_params_text,
            env_base_url,
            pre_ops_text,
            post_ops_text,
            node_id,
            mock_mode,
        )

    def delete_tab(self, tab_id: str) -> None:
        self._tabs.delete_tab(tab_id)

    def import_openapi(self, path: str) -> tuple[list[dict], list[dict]]:
        content = Path(path).read_text(encoding="utf-8")
        spec = yaml.safe_load(content) if path.lower().endswith((".yml", ".yaml")) else json.loads(content)
        paths = spec.get("paths", {}) or {}
        items: list[dict] = []
        for p, meta in paths.items():
            if not isinstance(meta, dict):
                continue
            for m in ("get", "post", "put", "delete", "patch", "head", "options"):
                op = meta.get(m)
                if not isinstance(op, dict):
                    continue
                name = op.get("summary") or op.get("operationId") or p
                items.append({"method": m.upper(), "path": p, "summary": name})
        environments: list[dict] = []
        for i, server in enumerate(spec.get("servers", []) or []):
            if not isinstance(server, dict):
                continue
            server_url = (server.get("url") or "").strip()
            if not server_url:
                continue
            server_name = server.get("description") or f"导入环境{i + 1}"
            environments.append({"name": server_name, "baseUrl": server_url})
        return items, environments

    @staticmethod
    def _environment_headers(env: dict) -> dict[str, str]:
        values: dict[str, str] = {}
        for row in env.get("headers") or []:
            if not isinstance(row, dict) or row.get("enabled") is False:
                continue
            key = str(row.get("key") or "").strip()
            if not key:
                continue
            values[key] = str(row.get("value") or "")
        return values

    def send_api(
        self,
        method: str,
        url: str,
        params_text: str,
        headers_text: str,
        body_text: str,
        env_base_url: str = "",
        auth_type: str = "none",
        auth_value: str = "",
        request_mode: str = "http",
        graphql_query: str = "",
        graphql_variables: str = "",
        global_params_text: str = "",
        assertions_text: str = "",
        mock_response_text: str = "",
        tab_id: str = "",
    ) -> tuple[str, str, dict]:
        del graphql_query, graphql_variables  # keep stable signature; GraphQL UI is not exposed yet.
        params = self._parse_key_value_text(params_text)
        final_url = self._apply_path_params(url, params)
        for key in self._path_param_keys(url):
            params.pop(key, None)
        headers = self._apply_auth(self._parse_key_value_text(headers_text), auth_type, auth_value)
        if request_mode == "mock":
            return self._send_mock(
                method,
                final_url,
                params,
                headers,
                body_text,
                mock_response_text,
                assertions_text,
                tab_id,
            )
        if request_mode == "websocket":
            details = self._http.build_request_details(
                method=method,
                url=final_url,
                params=params,
                headers=headers,
                body_text=body_text,
                log_note="WebSocket 模式未通过 HTTP 发送；这里只展示当前输入解析后的请求信息。",
            )
            return "状态: WS", "请使用 WebSocket 操作按钮进行连接、发送和接收。", details

        environment = self._environment_for_base_url(env_base_url)
        env_name = str(environment.get("name") or "")
        env_vars = self._environment_vars(environment)
        env_headers = self._environment_headers(environment)
        merged_headers = {**env_headers, **headers} if env_headers else headers
        title, body, status_code, final_url, details = self._http.send(
            method=method,
            url=final_url,
            params=params,
            headers=merged_headers,
            body_text=body_text,
            env_name=env_name,
            env_base_url=env_base_url,
            pre_ops_text=global_params_text,
            assertions_text=assertions_text,
            env_vars=env_vars,
        )
        response_body = body.split("\n\n--- Assertions ---", 1)[0]
        extracted = self._scripts.extract_variables(response_body, assertions_text)
        now = int(time.time() * 1000)
        for k, v in extracted.items():
            self._variables.set_variable("environment", k, v, env_name=env_name, updated_at=now)
        self._history = [{"method": method, "url": final_url, "status": status_code}] + self._history[:100]
        self._tabs.record_history(
            tab_id=tab_id,
            method=method,
            url=final_url,
            status=status_code,
            title=title,
            response=body,
            created_at=now,
        )
        return title, body, details

    def _send_mock(
        self,
        method: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        request_body_text: str,
        mock_response_text: str,
        assertions_text: str,
        tab_id: str,
    ) -> tuple[str, str, dict]:
        body = (mock_response_text or "").strip()
        if not body:
            body = json.dumps(
                {
                    "ok": True,
                    "mock": True,
                    "method": method,
                    "url": url,
                },
                ensure_ascii=False,
                indent=2,
            )
        now = int(time.time() * 1000)
        title = f"状态: MOCK | 大小: {len(body.encode('utf-8'))}B"
        assertion_result = self._scripts.run_assertions(200, body, assertions_text)
        if assertion_result:
            body = f"{body}\n\n--- Assertions ---\n{assertion_result}"
        details = self._http.build_request_details(
            method=method,
            url=url,
            params=params,
            headers=headers,
            body_text=request_body_text,
            log_note="Mock 模式未发起网络请求；以下是 Mock 前解析出的请求信息。",
        )
        details["responseHeadersText"] = "Content-Type: application/json\nX-Mock: true"
        self._history = [{"method": method, "url": url, "status": 0, "mock": True}] + self._history[:100]
        self._tabs.record_history(
            tab_id=tab_id,
            method=method,
            url=url,
            status=0,
            title=title,
            response=body,
            created_at=now,
        )
        return title, body, details

    def send_api_file(
        self,
        method: str,
        url: str,
        params_text: str,
        headers_text: str,
        file_path: str,
        file_param: str,
        env_base_url: str = "",
        auth_type: str = "none",
        auth_value: str = "",
        global_params_text: str = "",
        assertions_text: str = "",
        tab_id: str = "",
    ) -> tuple[str, str, dict]:
        params = self._parse_key_value_text(params_text)
        final_url = self._apply_path_params(url, params)
        for key in self._path_param_keys(url):
            params.pop(key, None)
        headers = self._apply_auth(self._parse_key_value_text(headers_text), auth_type, auth_value)
        environment = self._environment_for_base_url(env_base_url)
        env_name = str(environment.get("name") or "")
        env_vars = self._environment_vars(environment)
        env_headers = self._environment_headers(environment)
        merged_headers = {**env_headers, **headers} if env_headers else headers
        title, body, _, final_url, details = self._http.send_file(
            method=method,
            url=final_url,
            params=params,
            headers=merged_headers,
            file_path=file_path,
            file_param=file_param,
            env_name=env_name,
            env_base_url=env_base_url,
            pre_ops_text=global_params_text,
            assertions_text=assertions_text,
            env_vars=env_vars,
        )
        now = int(time.time() * 1000)
        self._history = [{"method": method, "url": final_url, "status": 0, "file": True}] + self._history[:100]
        self._tabs.record_history(
            tab_id=tab_id,
            method=method,
            url=final_url,
            status=0,
            title=title,
            response=body,
            created_at=now,
        )
        return title, body, details

    def ws_connect(self, tab_id: str, url: str, params_text: str, headers_text: str, cookies_text: str, env_base_url: str = "") -> tuple[str, str]:
        final_url = self._ws.connect(
            tab_id=tab_id,
            url=url,
            params=self._parse_key_value_text(params_text),
            headers=self._parse_key_value_text(headers_text),
            cookies=cookies_text,
            env_name="",
            env_base_url=env_base_url,
        )
        return "状态: WS_CONNECTED", f"已连接: {final_url}"

    def ws_send(self, tab_id: str, content: str, encoding: str) -> tuple[str, str]:
        sent = self._ws.send_message(tab_id=tab_id, content=content, encoding=encoding)
        return "状态: WS_SENT", sent

    def ws_receive(self, tab_id: str) -> tuple[str, str]:
        msg = self._ws.receive_once(tab_id)
        return "状态: WS_RECV", msg

    def ws_disconnect(self, tab_id: str) -> tuple[str, str]:
        self._ws.disconnect(tab_id)
        return "状态: WS_DISCONNECTED", "连接已关闭"

    def ws_timeline(self, tab_id: str) -> list[dict]:
        return self._ws.list_timeline(tab_id)

    def ws_connected(self, tab_id: str) -> bool:
        return self._ws.is_connected(tab_id)

    def save_debug_case(self, endpoint_key: str, payload: dict) -> None:
        case_id = payload.get("id") or f"case_{uuid4().hex}"
        self._cases.save_case(case_id=case_id, endpoint_key=endpoint_key, payload=payload)

    def list_debug_cases(self, endpoint_key: str) -> list[dict]:
        return self._cases.list_cases(endpoint_key)

    def run_debug_cases(self, endpoint_key: str, case_ids: list[str]) -> list[dict]:
        def sender(case: dict) -> tuple[str, str, dict]:
            return self.send_api(
                method=case.get("method", "GET"),
                url=case.get("url", "/"),
                params_text="\n".join(
                    part
                    for part in (
                        case.get("pathParamsText", ""),
                        case.get("paramsText", ""),
                    )
                    if part
                ),
                headers_text=case.get("headersText", ""),
                body_text=case.get("bodyText", ""),
                env_base_url=case.get("envBaseUrl", ""),
                auth_type=case.get("authType", "none"),
                auth_value=case.get("authValue", ""),
                request_mode="mock" if case.get("mockMode") else case.get("requestMode", "http"),
                global_params_text=case.get("preOpsText", ""),
                assertions_text=case.get("postOpsText", ""),
                mock_response_text=case.get("bodyText", ""),
            )

        return self._cases.run_batch(endpoint_key, case_ids, sender)

    def get_history(self) -> list[dict]:
        return self._history

    def list_history(self, limit: int = 100) -> list[dict]:
        history = self._tabs.list_history(limit)
        if history:
            return history
        return [dict(item) for item in self._history[:limit]]

    def close(self) -> None:
        self._ws.disconnect_all()

    @staticmethod
    def _parse_key_value_text(text: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for line in (text or "").splitlines():
            raw = line.strip()
            if not raw:
                continue
            sep = raw.find(":")
            if sep < 0:
                sep = raw.find("=")
            if sep < 0:
                continue
            k, v = raw[:sep], raw[sep + 1 :]
            if k.strip():
                out[k.strip()] = v.strip()
        return out

    @staticmethod
    def _apply_auth(headers: dict[str, str], auth_type: str, auth_value: str) -> dict[str, str]:
        out = dict(headers)
        t = (auth_type or "none").lower()
        value = (auth_value or "").strip()
        if t == "bearer" and value:
            out["Authorization"] = f"Bearer {value}"
        elif t == "basic" and value:
            if ":" in value:
                value = b64encode(value.encode("utf-8")).decode("ascii")
            out["Authorization"] = f"Basic {value}"
        elif t == "apikey" and value:
            out["X-API-Key"] = value
        return out

    @staticmethod
    def _path_param_keys(url: str) -> set[str]:
        keys: set[str] = set()
        text = url or ""
        start = 0
        while True:
            left = text.find("{", start)
            if left < 0:
                break
            right = text.find("}", left + 1)
            if right < 0:
                break
            key = text[left + 1 : right].strip()
            if key:
                keys.add(key)
            start = right + 1
        return keys

    @classmethod
    def _apply_path_params(cls, url: str, params: dict[str, str]) -> str:
        result = url or ""
        # sort longest key first to avoid partial replacements (e.g. {id} inside {user_id})
        for key in sorted(cls._path_param_keys(result), key=len, reverse=True):
            if key in params:
                result = result.replace("{" + key + "}", quote(str(params[key]), safe=""))
        return result
