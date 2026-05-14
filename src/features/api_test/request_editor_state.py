from __future__ import annotations

import json


def parse_kv(text: str) -> list[dict]:
    out: list[dict] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        sep = line.find(":") if ":" in line else line.find("=")
        if sep < 0:
            continue
        k, v = line[:sep].strip(), line[sep + 1 :].strip()
        if k:
            out.append({"enabled": True, "key": k, "value": v, "type": "string", "desc": ""})
    return out


def parse_header_rows(text: str) -> list[dict]:
    out: list[dict] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        sep = line.find(":") if ":" in line else line.find("=")
        if sep < 0:
            continue
        k, v = line[:sep].strip(), line[sep + 1 :].strip()
        if k:
            out.append({"enabled": True, "key": k, "value": v, "type": "string", "desc": ""})
    return out


def parse_cookie_rows(text: str) -> list[dict]:
    out: list[dict] = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        sep = part.find("=")
        k = part[:sep].strip() if sep >= 0 else part
        v = part[sep + 1 :].strip() if sep >= 0 else ""
        if k:
            out.append({"enabled": True, "key": k, "value": v, "type": "string", "desc": ""})
    return out


def normalize_rows(rows: list[dict], empty_template: dict) -> list[dict]:
    out = [dict(r) for r in (rows or [])]
    for row in out:
        if "enabled" not in row:
            row["enabled"] = bool(row.get("key") or row.get("value"))
    if not out:
        out.append(dict(empty_template))
        return out
    while len(out) > 1 and not out[-1].get("key") and not out[-1].get("value") and not out[-2].get("key") and not out[-2].get("value"):
        out.pop()
    if out[-1].get("key") or out[-1].get("value"):
        out.append(dict(empty_template))
    return out


def build_kv_text(items: list[dict]) -> str:
    lines = []
    for item in items or []:
        if item.get("enabled") is False:
            continue
        key = str(item.get("key") or "")
        if key:
            lines.append(f"{key}:{item.get('value') or ''}")
    return "\n".join(lines)


def build_header_text(items: list[dict]) -> str:
    lines = []
    for item in items or []:
        if item.get("enabled") is False:
            continue
        key = str(item.get("key") or "")
        if key:
            lines.append(f"{key}: {item.get('value') or ''}")
    return "\n".join(lines)


def build_cookie_text(items: list[dict]) -> str:
    parts = []
    for item in items or []:
        if item.get("enabled") is False:
            continue
        key = str(item.get("key") or "")
        if key:
            parts.append(f"{key}={item.get('value') or ''}")
    return "; ".join(parts)


def empty_kv_row() -> dict:
    return {"enabled": False, "key": "", "value": "", "type": "string", "desc": ""}


def empty_form_row() -> dict:
    return {"enabled": False, "key": "", "value": ""}


def snapshot_from_tab(tab: dict) -> dict:
    return {
        "name": tab.get("name", "新场景"),
        "method": tab.get("method", "GET"),
        "url": tab.get("url", "/"),
        "requestMode": tab.get("requestMode", "http"),
        "bodyMode": tab.get("bodyMode", "none"),
        "authType": tab.get("authType", "none"),
        "authValue": tab.get("authValue", ""),
        "headersText": tab.get("headersText", ""),
        "cookiesText": tab.get("cookiesText", ""),
        "bodyText": tab.get("bodyText", "{}"),
        "paramsText": tab.get("paramsText", ""),
        "pathParamsText": tab.get("pathParamsText", ""),
        "envBaseUrl": tab.get("envBaseUrl", ""),
        "preOpsText": tab.get("preOpsText", ""),
        "postOpsText": tab.get("postOpsText", ""),
        "mockMode": bool(tab.get("mockMode")),
    }


class RequestEditorState:
    def __init__(self) -> None:
        self.query_params: list[dict] = [empty_kv_row()]
        self.path_params: list[dict] = [empty_kv_row()]
        self.body_modes: list[str] = ["none", "x-www-form-urlencoded", "JSON", "XML", "Text", "file"]
        self.current_body_mode: int = 0
        self.body_per_mode: dict = {}
        self.body_form_rows: list[dict] = [empty_form_row()]
        self.body_file_path: str = ""
        self.body_file_param_name: str = "file"
        self.body_text: str = ""
        self.headers_rows: list[dict] = [empty_kv_row()]
        self.cookie_rows: list[dict] = [empty_kv_row()]
        self.auth_type_value: str = "none"
        self.auth_value_text: str = ""
        self.cookies_text: str = ""
        self.pre_ops_text: str = ""
        self.post_ops_text: str = ""
        self.ws_encoding: str = "text"
        self.mock_mode: bool = False
        self.assertions_enabled: bool = True

    def current_body_mode_name(self) -> str:
        if 0 <= self.current_body_mode < len(self.body_modes):
            return self.body_modes[self.current_body_mode]
        return "none"

    def body_text_for_request(self) -> str:
        if self.current_body_mode in {1, 5}:
            return ""
        return self.body_text

    def save_body_to_mode(self) -> None:
        mode = self.current_body_mode_name()
        if self.current_body_mode == 1:
            self.body_per_mode[mode] = list(self.body_form_rows)
        elif self.current_body_mode == 5:
            self.body_per_mode[mode] = {"path": self.body_file_path, "paramName": self.body_file_param_name}
        else:
            self.body_per_mode[mode] = self.body_text

    def load_body_from_mode(self) -> None:
        mode = self.current_body_mode_name()
        saved = self.body_per_mode.get(mode)
        if self.current_body_mode == 1:
            self.body_form_rows = list(saved) if isinstance(saved, list) and saved else [empty_form_row()]
        elif self.current_body_mode == 5:
            if isinstance(saved, dict):
                self.body_file_path = str(saved.get("path") or "")
                self.body_file_param_name = str(saved.get("paramName") or "file")
        else:
            self.body_text = str(saved or "")

    def set_current_body_mode(self, index: int) -> None:
        if index != self.current_body_mode:
            self.save_body_to_mode()
            self.current_body_mode = index
            self.load_body_from_mode()

    def normalize_section(self, section: str) -> list[dict]:
        if section == "query":
            return normalize_rows(self.query_params, empty_kv_row())
        if section == "path":
            return normalize_rows(self.path_params, empty_kv_row())
        if section == "headers":
            return normalize_rows(self.headers_rows, empty_kv_row())
        if section == "cookies":
            return normalize_rows(self.cookie_rows, empty_kv_row())
        if section == "body":
            return normalize_rows(self.body_form_rows, empty_form_row())
        return []

    def get_rows(self, section: str) -> list[dict]:
        mapping = {
            "query": self.query_params,
            "path": self.path_params,
            "headers": self.headers_rows,
            "cookies": self.cookie_rows,
            "body": self.body_form_rows,
        }
        return mapping.get(section, [])

    def set_rows(self, section: str, rows: list[dict]) -> None:
        if section == "query":
            self.query_params = rows
        elif section == "path":
            self.path_params = rows
        elif section == "headers":
            self.headers_rows = rows
        elif section == "cookies":
            self.cookie_rows = rows
        elif section == "body":
            self.body_form_rows = rows

    def toggle_row_enabled(self, section: str, row_index: int, checked: bool) -> bool:
        rows = self.get_rows(section)
        if not (0 <= row_index < len(rows)):
            return False
        rows[row_index]["enabled"] = checked
        self.set_rows(section, rows)
        return True

    def edit_row_key(self, section: str, row_index: int, key_text: str) -> bool:
        rows = self.get_rows(section)
        if not (0 <= row_index < len(rows)):
            return False
        rows[row_index]["key"] = key_text
        if key_text:
            rows[row_index]["enabled"] = True
        template = empty_form_row() if section == "body" else empty_kv_row()
        self.set_rows(section, normalize_rows(rows, template))
        return True

    def edit_row_value(self, section: str, row_index: int, value_text: str) -> bool:
        rows = self.get_rows(section)
        if not (0 <= row_index < len(rows)):
            return False
        rows[row_index]["value"] = value_text
        self.set_rows(section, rows)
        return True

    def delete_row(self, section: str, row_index: int) -> bool:
        rows = self.get_rows(section)
        if not (0 <= row_index < len(rows)):
            return False
        rows.pop(row_index)
        template = empty_form_row() if section == "body" else empty_kv_row()
        self.set_rows(section, normalize_rows(rows, template))
        return True

    def apply_tab(self, tab: dict, environments: list[dict]) -> int | None:
        self.auth_type_value = str(tab.get("authType") or "none")
        self.auth_value_text = str(tab.get("authValue") or "")
        self.headers_rows = parse_header_rows(str(tab.get("headersText") or ""))
        self.cookies_text = str(tab.get("cookiesText") or "")
        self.cookie_rows = parse_cookie_rows(self.cookies_text)
        try:
            body_per_mode = json.loads(str(tab.get("bodyText") or "{}"))
        except Exception:
            body_per_mode = {}
        self.body_per_mode = body_per_mode if isinstance(body_per_mode, dict) else {}
        self.current_body_mode = next((i for i, mode in enumerate(self.body_modes) if mode == str(tab.get("bodyMode") or "")), 0)
        self.load_body_from_mode()
        self.pre_ops_text = str(tab.get("preOpsText") or "")
        self.post_ops_text = str(tab.get("postOpsText") or "")
        self.query_params = parse_kv(str(tab.get("paramsText") or ""))
        self.path_params = parse_kv(str(tab.get("pathParamsText") or ""))
        self.mock_mode = bool(tab.get("mockMode"))
        env_base = str(tab.get("envBaseUrl") or "")
        for index, env in enumerate(environments):
            if env.get("baseUrl") == env_base:
                return index
        return None

    def update_tab_from_state(self, tab: dict, env_base_url: str) -> dict:
        self.save_body_to_mode()
        next_tab = dict(tab)
        next_tab["bodyText"] = json.dumps(self.body_per_mode)
        next_tab["bodyMode"] = self.current_body_mode_name()
        next_tab["authType"] = self.auth_type_value
        next_tab["authValue"] = self.auth_value_text
        next_tab["headersText"] = build_header_text(self.headers_rows)
        next_tab["cookiesText"] = build_cookie_text(self.cookie_rows)
        next_tab["paramsText"] = build_kv_text(self.query_params)
        next_tab["pathParamsText"] = build_kv_text(self.path_params)
        next_tab["envBaseUrl"] = env_base_url
        next_tab["preOpsText"] = self.pre_ops_text
        next_tab["postOpsText"] = self.post_ops_text
        next_tab["mockMode"] = self.mock_mode
        return next_tab
