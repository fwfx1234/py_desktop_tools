from __future__ import annotations

from collections.abc import Callable

from app.commands.app_index_service import AppIndexService
from app.commands.command_context import CommandContextMatcher
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_launcher import CommandLauncher
from app.commands.context import LauncherContext, build_launcher_context
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.commands.ranker import CommandRanker
from app.commands.usage_service import CommandUsageService
from app.platform.services import PlatformServices
from app.plugins.manifest import PluginManifest


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
        self._app_index = AppIndexService(index_db, platform_services)
        self._launcher = CommandLauncher(index_db, platform_services)
        self._usage = CommandUsageService(index_db)

    @property
    def app_scan_running(self) -> bool:
        return self._app_index.scan_running

    def search(self, query: str, context: LauncherContext | None = None) -> list[dict]:
        q = query.strip()
        context = context or build_launcher_context(q, self.known_prefixes())
        score_query = context.input_body.strip() if context.prefix else q
        self._app_index.ensure_scan_started()

        items = (
            self._plugin_items(score_query, context)
            + self._dynamic_items(score_query, context)
            + self._system_items(score_query)
        )
        items += self._app_items(score_query)
        usage = self._usage.usage_map()
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

    def on_app_scan_completed(self, callback: Callable[[], None]) -> None:
        self._app_index.on_scan_completed(callback)

    def start_app_scan(self, *, force: bool = False) -> bool:
        return self._app_index.start_scan(force=force)

    def check_app_index_changes(self, *, force: bool = False) -> bool:
        return self._app_index.start_change_check(force=force)

    def search_apps(self, query: str, *, limit: int = 50) -> list[dict]:
        self._app_index.ensure_scan_started()
        return self._index_db.search_apps(query, limit=limit)

    def count_apps(self) -> int:
        return self._index_db.count_apps()

    def shutdown(self) -> None:
        self._app_index.shutdown()

    def known_prefixes(self) -> set[str]:
        prefixes: set[str] = set()
        for manifest in self._manifests:
            for command in manifest.commands or [manifest.primary_command]:
                prefixes.update(CommandContextMatcher.normalize_tokens(command.prefixes))
        for command in self._dynamic_commands.all():
            prefixes.update(CommandContextMatcher.normalize_tokens(command.prefixes))
        return prefixes

    def record_plugin_launch(self, plugin_id: str) -> None:
        self._usage.record_plugin_launch(plugin_id)

    def record_item_launch(self, item: dict) -> None:
        self._usage.record_item_launch(item)

    def launch_external_item(self, item_id: str, source: str, payload: dict | None = None) -> str | None:
        return self._launcher.launch_external_item(item_id, source, payload)

    def _plugin_items(self, query: str, context: LauncherContext) -> list[dict]:
        out: list[dict] = []
        for manifest in self._manifests:
            command = manifest.primary_command
            score, start, length = CommandRanker.score(
                query,
                manifest.name,
                command.keywords,
                manifest.description,
            )
            base_score = score
            score, reasons = CommandContextMatcher.apply_context(
                score,
                context,
                command.prefixes,
                command.matchers,
            )
            input_text, input_source, clear_input = CommandContextMatcher.launch_input_policy(
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
            score, start, length = CommandRanker.score(
                query,
                command.title,
                command.keywords,
                command.subtitle,
            )
            base_score = score
            score, reasons = CommandContextMatcher.apply_context(
                score,
                context,
                command.prefixes,
                command.matchers,
            )
            input_text, input_source, clear_input = CommandContextMatcher.launch_input_policy(
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
            score, start, length = CommandRanker.score(
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

    def _app_items(self, query: str) -> list[dict]:
        apps = self._index_db.search_apps(query, limit=30 if query else 20)
        out: list[dict] = []
        for app in apps:
            aliases = [str(alias) for alias in app.get("aliases", [])]
            keywords = [
                str(app.get("initials") or ""),
                *aliases,
                str(app.get("searchText") or ""),
            ]
            score, start, length = CommandRanker.score(query, app["name"], keywords, "")
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
