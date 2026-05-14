from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.commands.command_index_db import CommandIndexDb, compute_pinyin
from app.commands.context import LauncherContext, build_launcher_context
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.platform.services import PlatformServices
from app.plugins.manifest import ContextMatcher, PluginManifest


class CommandService:
    """Search and launch service for plugins, system tools, and applications."""

    def __init__(
        self,
        manifests: list[PluginManifest],
        index_db: CommandIndexDb,
        dynamic_commands: DynamicCommandRegistry | None = None,
        *,
        platform_services: PlatformServices,
    ) -> None:
        self._manifests = sorted(manifests, key=lambda item: item.order)
        self._index_db = index_db
        self._dynamic_commands = dynamic_commands or DynamicCommandRegistry()
        self._platform = platform_services
        self._apps_scanned = False

    def search(self, query: str, context: LauncherContext | None = None) -> list[dict]:
        q = query.strip()
        context = context or build_launcher_context(q, self.known_prefixes())
        score_query = context.input_body.strip() if context.prefix else q
        if (
            not self._apps_scanned
            and self._index_db.count_apps() == 0
        ):
            apps = self._platform.app_indexer.scan_apps(self._index_db.get_icon_dir())
            self._index_db.sync_apps([app.to_db_dict() for app in apps])
            self._apps_scanned = True

        items = (
            self._plugin_items(score_query, context)
            + self._dynamic_items(score_query, context)
            + self._system_items(score_query)
            + self._app_items(score_query)
        )
        usage = self._index_db.usage_map()
        for item in items:
            use_count, last_used = usage.get(item["usageKey"], (0, ""))
            item["useCount"] = use_count
            item["lastUsedAt"] = last_used

        if q:
            items = [item for item in items if item["score"] > 0]
            items.sort(key=lambda item: (-item["score"], -item["useCount"], item["name"]))
        else:
            items.sort(
                key=lambda item: (
                    -item["score"],
                    -item["useCount"],
                    item.get("order", 99),
                    item["name"],
                )
            )
        return items[:50]

    def all_plugin_items(self) -> list[dict]:
        return self._plugin_items("", build_launcher_context("", self.known_prefixes()))

    def known_prefixes(self) -> set[str]:
        prefixes: set[str] = set()
        for manifest in self._manifests:
            for command in manifest.commands or [manifest.primary_command]:
                prefixes.update(self._normalize_tokens(command.prefixes))
        for command in self._dynamic_commands.all():
            prefixes.update(self._normalize_tokens(command.prefixes))
        return prefixes

    def record_plugin_launch(self, plugin_id: str) -> None:
        self._index_db.record_launch(f"plugin:{plugin_id}")

    def record_item_launch(self, item: dict) -> None:
        usage_key = item.get("usageKey")
        if usage_key:
            self._index_db.record_launch(str(usage_key))

    def launch_external_item(self, item_id: str, source: str, payload: dict | None = None) -> str | None:
        payload = payload or {}
        if source == "system":
            action = str(payload.get("action") or "")
            if not action:
                return None
            self._index_db.record_launch(f"system:{item_id}")
            result = self._platform.external_launcher.launch_system_action(action)
            if result.ok:
                return str(payload.get("name") or item_id)
            print(f"[WARN] system action failed: {action} - {result.code} {result.message}")
            return None

        if source == "app":
            launch_path = str(payload.get("launchPath") or payload.get("lnkPath") or "")
            if not launch_path:
                return None
            self._index_db.record_launch_by_app_path(launch_path)
            result = self._platform.external_launcher.launch_app(payload)
            if result.ok:
                return str(payload.get("name") or launch_path)
            print(f"[WARN] app launch failed: {launch_path} - {result.code} {result.message}")
            return None

        return None

    def _plugin_items(self, query: str, context: LauncherContext) -> list[dict]:
        out: list[dict] = []
        for manifest in self._manifests:
            command = manifest.primary_command
            score, start, length = self._score(
                query,
                manifest.name,
                command.keywords,
                manifest.description,
            )
            base_score = score
            score, reasons = self._apply_command_context(
                score,
                context,
                command.prefixes,
                command.matchers,
            )
            input_text, input_source, clear_input = self._launch_input_policy(
                base_score,
                context,
                command.prefixes,
                reasons,
            )
            out.append(
                {
                    "id": manifest.id,
                    "name": command.title,
                    "description": command.subtitle or manifest.description,
                    "source": "plugin",
                    "mode": command.launch_mode,
                    "pluginId": manifest.id,
                    "commandId": command.id,
                    "qmlPage": manifest.qml_page,
                    "contextProperty": manifest.context_property,
                    "category": manifest.category,
                    "icon": command.icon or manifest.icon,
                    "pluginIcon": manifest.icon,
                    "window": manifest.window_options,
                    "payload": command.payload,
                    "inputMode": command.input_mode,
                    "hotkey": command.hotkey,
                    "usageKey": f"plugin:{manifest.id}",
                    "order": manifest.order,
                    "score": score,
                    "highlightStart": start,
                    "highlightLen": length,
                    "recommendReasons": reasons,
                    "inputText": input_text,
                    "inputSource": input_source,
                    "clearInputOnEnter": clear_input,
                }
            )
        return out

    def _dynamic_items(self, query: str, context: LauncherContext) -> list[dict]:
        out: list[dict] = []
        for command in self._dynamic_commands.all():
            score, start, length = self._score(
                query,
                command.title,
                command.keywords,
                command.subtitle,
            )
            base_score = score
            score, reasons = self._apply_command_context(
                score,
                context,
                command.prefixes,
                command.matchers,
            )
            input_text, input_source, clear_input = self._launch_input_policy(
                base_score,
                context,
                command.prefixes,
                reasons,
            )
            item_id = f"dynamic:{command.plugin_id}:{command.command_id}"
            out.append(
                {
                    "id": item_id,
                    "name": command.title,
                    "description": command.subtitle,
                    "icon": command.icon,
                    "source": "plugin",
                    "mode": command.launch_mode,
                    "pluginId": command.plugin_id,
                    "commandId": command.command_id,
                    "qmlPage": "",
                    "contextProperty": "",
                    "category": "dynamic",
                    "pluginIcon": command.icon,
                    "window": {},
                    "payload": command.payload,
                    "inputMode": "global",
                    "hotkey": "",
                    "usageKey": item_id,
                    "order": command.order,
                    "score": score,
                    "highlightStart": start,
                    "highlightLen": length,
                    "recommendReasons": reasons,
                    "inputText": input_text,
                    "inputSource": input_source,
                    "clearInputOnEnter": clear_input,
                }
            )
        return out

    def _system_items(self, query: str) -> list[dict]:
        out: list[dict] = []
        for index, command in enumerate(self._platform.system_commands.commands()):
            item = command.to_item_dict()
            score, start, length = self._score(
                query,
                item["name"],
                item["keywords"],
                item["description"],
            )
            item_id = f"system:{item['id']}"
            out.append(
                {
                    "id": item_id,
                    "name": item["name"],
                    "description": item["description"],
                    "icon": item["icon"],
                    "source": "system",
                    "mode": "none",
                    "pluginId": "",
                    "commandId": item["id"],
                    "qmlPage": "",
                    "contextProperty": "",
                    "category": "system",
                    "payload": {"action": item["action"], "name": item["name"]},
                    "usageKey": item_id,
                    "order": 100 + index,
                    "score": score,
                    "highlightStart": start,
                    "highlightLen": length,
                }
            )
        return out

    def _apply_command_context(
        self,
        base_score: int,
        context: LauncherContext,
        prefixes: list[str],
        matchers: list[ContextMatcher] | list[object],
    ) -> tuple[int, list[str]]:
        score = base_score
        reasons: list[str] = []

        normalized_prefixes = self._normalize_tokens(prefixes)
        if context.prefix and context.prefix in normalized_prefixes:
            score += 240
            reasons.append(f"prefix:{context.prefix}")

        has_explicit_text = bool(context.input_body.strip() if context.prefix else context.input_text.strip())
        for matcher in matchers:
            source = str(getattr(matcher, "source", "")).strip().lower()
            kind = str(getattr(matcher, "kind", "")).strip().lower()
            boost = int(getattr(matcher, "boost", 0) or 0)
            pattern = str(getattr(matcher, "pattern", "") or "")
            if not source or not kind:
                continue

            if source == "input":
                haystack = context.input_body if context.prefix else context.input_text
                kinds = context.detected_input_kinds
            elif source == "clipboard":
                if has_explicit_text and base_score <= 0 and not (
                    context.prefix and context.prefix in normalized_prefixes
                ):
                    continue
                haystack = context.clipboard_text or context.clipboard_preview
                kinds = context.detected_clipboard_kinds
            else:
                continue

            if self._matcher_hits(kind, pattern, kinds, haystack):
                score += boost
                reasons.append(f"{source}:{kind}")

        return score, reasons

    def _launch_input_policy(
        self,
        base_score: int,
        context: LauncherContext,
        prefixes: list[str],
        reasons: list[str],
    ) -> tuple[str, str, bool]:
        has_query = bool(context.input_text.strip())
        normalized_prefixes = self._normalize_tokens(prefixes)
        prefix_hit = bool(context.prefix and context.prefix in normalized_prefixes)
        input_match = any(reason.startswith("input:") for reason in reasons)

        if prefix_hit:
            return "", "command", has_query
        if input_match and base_score <= 0:
            return context.input_text, "content", has_query
        return "", "command", has_query

    @staticmethod
    def _matcher_hits(
        kind: str,
        pattern: str,
        detected_kinds: frozenset[str],
        haystack: str,
    ) -> bool:
        if kind == "regex":
            if not pattern:
                return False
            try:
                return re.search(pattern, haystack, re.IGNORECASE) is not None
            except re.error:
                return pattern.lower() in haystack.lower()
        return kind in detected_kinds

    @staticmethod
    def _normalize_tokens(tokens: list[str]) -> set[str]:
        return {str(token).strip().lower() for token in tokens if str(token).strip()}

    def _app_items(self, query: str) -> list[dict]:
        apps = self._index_db.search_apps(query, limit=30 if query else 20)
        out: list[dict] = []
        for app in apps:
            score, start, length = self._score(query, app["name"], [app["initials"]], "")
            icon = (
                "file:///" + app["iconPath"].replace("\\", "/")
                if app["iconPath"]
                else "qta:mdi6.application-outline"
            )
            launch_path = str(app.get("launchPath") or "")
            item_id = f"app:{app['id']}"
            out.append(
                {
                    "id": item_id,
                    "name": app["name"],
                    "description": launch_path,
                    "icon": icon,
                    "source": "app",
                    "mode": "none",
                    "pluginId": "",
                    "commandId": item_id,
                    "qmlPage": "",
                    "contextProperty": "",
                    "category": "app",
                    "payload": {"launchPath": launch_path, "name": app["name"]},
                    "usageKey": f"app:{launch_path}",
                    "order": 200,
                    "score": score,
                    "highlightStart": start,
                    "highlightLen": length,
                }
            )
        return out

    @staticmethod
    def _score(query: str, title: str, keywords: list[str], description: str) -> tuple[int, int, int]:
        q = query.strip().lower()
        if not q:
            return 1, -1, 0

        title_lower = title.lower()
        if q == title_lower:
            return 100, 0, len(query)
        if title_lower.startswith(q):
            return 90, 0, len(query)
        pos = title_lower.find(q)
        if pos >= 0:
            return 70, pos, len(query)

        for keyword in keywords:
            keyword_lower = str(keyword).lower()
            if q == keyword_lower:
                return 85, -1, 0
            if keyword_lower.startswith(q):
                return 75, -1, 0
            if q in keyword_lower:
                return 55, -1, 0

        pinyin, initials = compute_pinyin(title)
        if pinyin.startswith(q):
            return 74, -1, 0
        if q in pinyin:
            return 54, -1, 0
        if initials.startswith(q):
            return 72, -1, 0

        ratio = SequenceMatcher(None, q, title_lower).ratio()
        if ratio > 0.62:
            return int(ratio * 50), -1, 0
        if q in description.lower():
            return 20, -1, 0
        return 0, -1, 0
