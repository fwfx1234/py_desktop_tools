from __future__ import annotations

import json
import os
import time
from datetime import datetime
from collections.abc import Mapping
from urllib.parse import urlencode
from typing import TYPE_CHECKING

from .script_service import RequestDraft, ScriptService
from .variable_service import VariableService

if TYPE_CHECKING:
    import requests
    from requests.models import PreparedRequest


class HttpRequestService:
    def __init__(self, variable_service: VariableService, script_service: ScriptService) -> None:
        self._variable_service = variable_service
        self._script_service = script_service

    def build_request_details(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        body_text: str,
        env_name: str = "",
        env_vars: dict[str, str] | None = None,
        env_base_url: str = "",
        pre_ops_text: str = "",
        log_note: str = "未发起网络请求，仅生成请求详情。",
    ) -> dict[str, str]:
        import requests

        env_vars = env_vars or {}
        final_url = self._resolve_url(url, env_base_url)
        draft = RequestDraft(
            method=method,
            url=self._variable_service.resolve_text(final_url, env_name=env_name, env_vars=env_vars),
            params=self._variable_service.resolve_mapping(params, env_name=env_name, env_vars=env_vars),
            headers=self._variable_service.resolve_mapping(headers, env_name=env_name, env_vars=env_vars),
            body=self._variable_service.resolve_text(body_text or "", env_name=env_name, env_vars=env_vars),
        )
        draft, temporary_vars = self._script_service.apply_pre_ops(draft, pre_ops_text)
        draft.url = self._variable_service.resolve_text(draft.url, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.body = self._variable_service.resolve_text(draft.body, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.params = self._variable_service.resolve_mapping(draft.params, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.headers = self._variable_service.resolve_mapping(draft.headers, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        prepared = None
        error = None
        try:
            prepared = self._prepare_request(draft)
            details = self._request_details(prepared)
        except requests.RequestException as exc:
            error = exc
            details = self._request_details_from_draft(draft)
        details["requestLogText"] = self._build_request_log(
            raw_url=url,
            env_base_url=env_base_url,
            resolved_url=final_url,
            draft=draft,
            prepared=prepared,
            response=None,
            error=error,
            elapsed_ms=None,
            temporary_vars=temporary_vars,
            note=log_note,
        )
        return details

    def send(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        body_text: str,
        env_name: str,
        env_base_url: str,
        pre_ops_text: str,
        assertions_text: str,
        env_vars: dict[str, str] | None = None,
    ) -> tuple[str, str, int, str, dict[str, str]]:
        import requests

        env_vars = env_vars or {}
        final_url = self._resolve_url(url, env_base_url)
        draft = RequestDraft(
            method=method,
            url=self._variable_service.resolve_text(final_url, env_name=env_name, env_vars=env_vars),
            params=self._variable_service.resolve_mapping(params, env_name=env_name, env_vars=env_vars),
            headers=self._variable_service.resolve_mapping(headers, env_name=env_name, env_vars=env_vars),
            body=self._variable_service.resolve_text(body_text or "", env_name=env_name, env_vars=env_vars),
        )
        draft, temporary_vars = self._script_service.apply_pre_ops(draft, pre_ops_text)
        draft.url = self._variable_service.resolve_text(draft.url, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.body = self._variable_service.resolve_text(draft.body, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.params = self._variable_service.resolve_mapping(draft.params, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.headers = self._variable_service.resolve_mapping(draft.headers, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        prepared = None
        request_details = self._request_details_from_draft(draft)
        started_at = time.perf_counter()

        try:
            prepared = self._prepare_request(draft)
            request_details = self._request_details(prepared)
            resp = requests.request(
                method=draft.method,
                url=draft.url,
                params=draft.params,
                headers=draft.headers,
                data=draft.body or None,
                timeout=20,
            )
        except requests.ConnectionError as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            request_details["requestLogText"] = self._build_request_log(
                raw_url=url,
                env_base_url=env_base_url,
                resolved_url=final_url,
                draft=draft,
                prepared=prepared,
                response=None,
                error=exc,
                elapsed_ms=elapsed_ms,
                temporary_vars=temporary_vars,
            )
            return "状态: ERR | 连接失败", f"无法连接到服务器: {draft.url}", 0, self._prepared_url(prepared, draft), request_details
        except requests.Timeout as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            request_details["requestLogText"] = self._build_request_log(
                raw_url=url,
                env_base_url=env_base_url,
                resolved_url=final_url,
                draft=draft,
                prepared=prepared,
                response=None,
                error=exc,
                elapsed_ms=elapsed_ms,
                temporary_vars=temporary_vars,
            )
            return "状态: ERR | 请求超时", f"请求超时 (20s): {draft.url}", 0, self._prepared_url(prepared, draft), request_details
        except requests.RequestException as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            request_details["requestLogText"] = self._build_request_log(
                raw_url=url,
                env_base_url=env_base_url,
                resolved_url=final_url,
                draft=draft,
                prepared=prepared,
                response=None,
                error=exc,
                elapsed_ms=elapsed_ms,
                temporary_vars=temporary_vars,
            )
            return "状态: ERR | 请求异常", str(exc), 0, self._prepared_url(prepared, draft), request_details
        title = f"状态: {resp.status_code} | 大小: {len(resp.content)}B | 耗时: {resp.elapsed.total_seconds():.3f}s"
        body = resp.text
        try:
            body = json.dumps(resp.json(), ensure_ascii=False, indent=2)
        except Exception:
            pass
        assertion_result = self._script_service.run_assertions(resp.status_code, body, assertions_text)
        if assertion_result:
            body = f"{body}\n\n--- Assertions ---\n{assertion_result}"
        response_headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
        details = self._request_details(resp.request)
        details.update(
            {
                "responseHeadersText": response_headers,
                "finalUrl": resp.url,
                "statusCode": str(resp.status_code),
                "elapsedMs": str(int(resp.elapsed.total_seconds() * 1000)),
                "requestLogText": self._build_request_log(
                    raw_url=url,
                    env_base_url=env_base_url,
                    resolved_url=final_url,
                    draft=draft,
                    prepared=resp.request,
                    response=resp,
                    error=None,
                    elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
                    temporary_vars=temporary_vars,
                ),
            }
        )
        return title, body, resp.status_code, resp.url, details

    def send_file(  # noqa: PLR0913
        self,
        *,
        method: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        file_path: str,
        file_param: str,
        env_name: str,
        env_base_url: str,
        pre_ops_text: str,
        assertions_text: str,
        env_vars: dict[str, str] | None = None,
    ) -> tuple[str, str, int, str, dict[str, str]]:
        import requests

        env_vars = env_vars or {}
        final_url = self._resolve_url(url, env_base_url)
        if not file_path or not os.path.isfile(file_path):
            return "状态: ERR", f"文件不存在: {file_path}", 0, final_url, {"requestText": "文件不存在"}
        headers.pop("Content-Type", None)
        draft = RequestDraft(
            method=method,
            url=self._variable_service.resolve_text(final_url, env_name=env_name, env_vars=env_vars),
            params=self._variable_service.resolve_mapping(params, env_name=env_name, env_vars=env_vars),
            headers=self._variable_service.resolve_mapping(headers, env_name=env_name, env_vars=env_vars),
            body="",
        )
        draft, temporary_vars = self._script_service.apply_pre_ops(draft, pre_ops_text)
        draft.url = self._variable_service.resolve_text(draft.url, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.params = self._variable_service.resolve_mapping(draft.params, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        draft.headers = self._variable_service.resolve_mapping(draft.headers, env_name=env_name, temporary=temporary_vars, env_vars=env_vars)
        request_details = self._request_details_from_draft(draft)
        started_at = time.perf_counter()
        try:
            with open(file_path, "rb") as fh:
                resp = requests.request(
                    method=draft.method,
                    url=draft.url,
                    params=draft.params,
                    headers=draft.headers,
                    files={file_param: (os.path.basename(file_path), fh)},
                    timeout=30,
                )
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            request_details["requestLogText"] = self._build_request_log(
                raw_url=url, env_base_url=env_base_url, resolved_url=final_url,
                draft=draft, prepared=None, response=None, error=exc,
                elapsed_ms=elapsed_ms, temporary_vars=temporary_vars,
            )
            return f"状态: ERR | {exc.__class__.__name__}", str(exc), 0, self._prepared_url(None, draft), request_details
        title = f"状态: {resp.status_code} | 大小: {len(resp.content)}B | 耗时: {resp.elapsed.total_seconds():.3f}s"
        body = resp.text
        try:
            body = json.dumps(resp.json(), ensure_ascii=False, indent=2)
        except Exception:
            pass
        assertion_result = self._script_service.run_assertions(resp.status_code, body, assertions_text)
        if assertion_result:
            body = f"{body}\n\n--- Assertions ---\n{assertion_result}"
        response_headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
        details = self._request_details(resp.request) if resp.request is not None else request_details
        details.update({
            "responseHeadersText": response_headers,
            "finalUrl": resp.url,
            "statusCode": str(resp.status_code),
            "elapsedMs": str(int(resp.elapsed.total_seconds() * 1000)),
            "requestLogText": self._build_request_log(
                raw_url=url, env_base_url=env_base_url, resolved_url=final_url,
                draft=draft, prepared=resp.request, response=resp, error=None,
                elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
                temporary_vars=temporary_vars,
            ),
        })
        return title, body, resp.status_code, resp.url, details

    @staticmethod
    def _resolve_url(url: str, base_url: str) -> str:
        u = (url or "").strip()
        base = (base_url or "").strip().rstrip("/")
        if not u:
            return base
        if u.startswith("http://") or u.startswith("https://") or not base:
            return u
        if u.startswith("/"):
            return f"{base}{u}"
        return f"{base}/{u}"

    @staticmethod
    def _prepare_request(draft: RequestDraft) -> "PreparedRequest":
        import requests

        return requests.Request(
            method=draft.method,
            url=draft.url,
            params=draft.params,
            headers=draft.headers,
            data=draft.body or None,
        ).prepare()

    @classmethod
    def _request_details(cls, request: "PreparedRequest") -> dict[str, str]:
        body = cls._body_to_text(request.body)
        headers_text = "\n".join(f"{k}: {v}" for k, v in request.headers.items())
        request_text = "\n".join(
            part
            for part in (
                f"{request.method} {request.url}",
                "",
                "Headers:",
                headers_text or "(none)",
                "",
                "Body:",
                body or "(empty)",
            )
            if part is not None
        )
        return {
            "requestText": request_text,
            "curlText": cls._to_curl(request.method or "GET", request.url or "", request.headers, body),
            "responseHeadersText": "",
            "finalUrl": request.url or "",
        }

    @classmethod
    def _request_details_from_draft(cls, draft: RequestDraft) -> dict[str, str]:
        body = draft.body or ""
        url = cls._append_query(draft.url, draft.params)
        headers_text = "\n".join(f"{k}: {v}" for k, v in draft.headers.items())
        request_text = "\n".join(
            (
                f"{draft.method} {url}",
                "",
                "Headers:",
                headers_text or "(none)",
                "",
                "Body:",
                body or "(empty)",
            )
        )
        return {
            "requestText": request_text,
            "curlText": cls._to_curl(draft.method or "GET", url, draft.headers, body),
            "responseHeadersText": "",
            "finalUrl": url,
        }

    @staticmethod
    def _body_to_text(body: object) -> str:
        if body is None:
            return ""
        if isinstance(body, bytes):
            try:
                return body.decode("utf-8")
            except UnicodeDecodeError:
                return body.decode("utf-8", errors="replace")
        return str(body)

    @staticmethod
    def _append_query(url: str, params: dict[str, str]) -> str:
        if not params:
            return url or ""
        query = urlencode(params)
        if not query:
            return url or ""
        separator = "&" if "?" in (url or "") else "?"
        return f"{url or ''}{separator}{query}"

    @classmethod
    def _to_curl(cls, method: str, url: str, headers: dict, body: str) -> str:
        parts = [
            "curl",
            "-X",
            cls._shell_quote(method or "GET"),
            cls._shell_quote(url or ""),
        ]
        for key, value in headers.items():
            if key.lower() == "content-length":
                continue
            parts.extend(["-H", cls._shell_quote(f"{key}: {value}")])
        if body:
            parts.extend(["--data-raw", cls._shell_quote(body)])
        return " ".join(parts)

    @staticmethod
    def _prepared_url(prepared: "PreparedRequest | None", draft: RequestDraft) -> str:
        if prepared and prepared.url:
            return prepared.url
        return draft.url

    @classmethod
    def _build_request_log(
        cls,
        *,
        raw_url: str,
        env_base_url: str,
        resolved_url: str,
        draft: RequestDraft,
        prepared: "PreparedRequest | None",
        response: "requests.Response | None",
        error: "requests.RequestException | None",
        elapsed_ms: int | None,
        temporary_vars: Mapping[str, object],
        note: str = "",
    ) -> str:
        lines = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] API request log",
            f"Method: {draft.method or 'GET'}",
            f"Input URL: {raw_url or '(empty)'}",
            f"Environment base URL: {env_base_url or '(none)'}",
            f"URL after environment: {resolved_url or '(empty)'}",
            f"Final draft URL: {draft.url or '(empty)'}",
        ]
        if note:
            lines.append(f"Note: {note}")
        if temporary_vars:
            lines.extend(("", "Temporary variables:", cls._format_mapping(temporary_vars)))

        lines.extend(
            (
                "",
                "Resolved query params:",
                cls._format_mapping(draft.params),
                "",
                "Resolved request headers:",
                cls._format_mapping(draft.headers),
                "",
                "Resolved request body:",
                draft.body or "(empty)",
            )
        )

        if prepared is None:
            lines.extend(
                (
                    "",
                    "Draft cURL:",
                    cls._to_curl(draft.method or "GET", cls._append_query(draft.url, draft.params), draft.headers, draft.body or ""),
                )
            )

        if prepared is not None:
            prepared_body = cls._body_to_text(prepared.body)
            lines.extend(
                (
                    "",
                    "PreparedRequest:",
                    f"{prepared.method} {prepared.url}",
                    "",
                    "Prepared headers:",
                    cls._format_mapping(prepared.headers),
                    "",
                    f"Prepared body bytes: {len(prepared_body.encode('utf-8'))}",
                    "Prepared body:",
                    prepared_body or "(empty)",
                    "",
                    "cURL:",
                    cls._to_curl(prepared.method or "GET", prepared.url or "", prepared.headers, prepared_body),
                )
            )

        if response is not None:
            lines.extend(
                (
                    "",
                    "Response:",
                    f"Status: {response.status_code} {response.reason}",
                    f"Final URL: {response.url}",
                    f"Elapsed: {elapsed_ms if elapsed_ms is not None else int(response.elapsed.total_seconds() * 1000)}ms",
                    f"Response bytes: {len(response.content)}",
                    "",
                    "Response headers:",
                    cls._format_mapping(response.headers),
                )
            )
        elif elapsed_ms is not None:
            lines.extend(("", f"Elapsed before failure: {elapsed_ms}ms"))

        if error is not None:
            lines.extend(
                (
                    "",
                    "Error:",
                    f"Type: {error.__class__.__name__}",
                    f"Message: {error}",
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _format_mapping(values: Mapping[str, object]) -> str:
        if not values:
            return "(none)"
        return "\n".join(f"{key}: {value}" for key, value in values.items())

    @staticmethod
    def _shell_quote(value: str) -> str:
        text = str(value)
        if text == "":
            return "''"
        return "'" + text.replace("'", "'\"'\"'") + "'"
