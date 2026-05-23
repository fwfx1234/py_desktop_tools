from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class RequestDraft:
    method: str
    url: str
    params: dict[str, str]
    headers: dict[str, str]
    body: str


class ScriptService:
    """Lightweight pre/post operation interpreter for desktop MVP."""

    def apply_pre_ops(self, draft: RequestDraft, pre_ops_text: str) -> tuple[RequestDraft, dict[str, Any]]:
        temp_vars: dict[str, Any] = {}
        for raw in (pre_ops_text or "").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("set "):
                payload = line[4:].strip()
                if "=" in payload:
                    k, v = payload.split("=", 1)
                    temp_vars[k.strip()] = v.strip()
                continue
            if line.startswith("header "):
                payload = line[7:].strip()
                if ":" in payload:
                    k, v = payload.split(":", 1)
                    draft.headers[k.strip()] = v.strip()
                continue
            if line.startswith("query "):
                payload = line[6:].strip()
                if "=" in payload:
                    k, v = payload.split("=", 1)
                    draft.params[k.strip()] = v.strip()
                continue
            if line.startswith("body.append "):
                draft.body = (draft.body or "") + line[len("body.append ") :]
        return draft, temp_vars

    def run_assertions(self, status_code: int, body_text: str, assertions_text: str) -> str:
        lines = [line.strip() for line in (assertions_text or "").splitlines() if line.strip()]
        if not lines:
            return ""
        results: list[str] = []
        parsed_json = self._safe_json(body_text)
        for line in lines:
            if line.startswith("status =="):
                expected = int(line.split("==", 1)[1].strip())
                results.append(f"{'PASS' if status_code == expected else 'FAIL'} {line}")
                continue
            if line.startswith("body contains"):
                expected_text = line.split("body contains", 1)[1].strip().strip("'\"")
                results.append(f"{'PASS' if expected_text in body_text else 'FAIL'} {line}")
                continue
            if line.startswith("json "):
                result = self._run_json_assertion(parsed_json, line)
                results.append(result)
                continue
            results.append(f"SKIP {line}")
        return "\n".join(results)

    def extract_variables(self, body_text: str, post_ops_text: str) -> dict[str, str]:
        parsed_json = self._safe_json(body_text)
        if parsed_json is None:
            return {}
        extracted: dict[str, str] = {}
        for raw in (post_ops_text or "").splitlines():
            line = raw.strip()
            if not line.startswith("extract "):
                continue
            # syntax: extract token=$.data.token
            payload = line[len("extract ") :]
            if "=" not in payload:
                continue
            key, expr = payload.split("=", 1)
            value = self._json_path_get(parsed_json, expr.strip())
            if value is not None:
                extracted[key.strip()] = str(value)
        return extracted

    @staticmethod
    def _safe_json(body_text: str) -> Any | None:
        try:
            return json.loads(body_text)
        except Exception:
            return None

    def _run_json_assertion(self, parsed_json: Any | None, line: str) -> str:
        # syntax: json $.code == 200
        if parsed_json is None:
            return f"FAIL {line}"
        payload = line[len("json ") :].strip()
        if "==" not in payload:
            return f"SKIP {line}"
        left, right = payload.split("==", 1)
        value = self._json_path_get(parsed_json, left.strip())
        expected = right.strip().strip("'\"")
        return f"{'PASS' if str(value) == expected else 'FAIL'} {line}"

    def _json_path_get(self, parsed_json: Any, path: str) -> Any | None:
        # Minimal JSONPath: $.a.b.c and array indexes like $.items.0.id
        if not path.startswith("$."):
            return None
        cur: Any = parsed_json
        for part in path[2:].split("."):
            part = part.strip()
            if part == "":
                return None
            if isinstance(cur, list):
                if not part.isdigit():
                    return None
                idx = int(part)
                if idx < 0 or idx >= len(cur):
                    return None
                cur = cur[idx]
                continue
            if isinstance(cur, dict):
                if part not in cur:
                    return None
                cur = cur[part]
                continue
            return None
        return cur
