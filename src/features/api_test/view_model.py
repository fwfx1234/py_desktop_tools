from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot
from app.storage import SQLiteDatabase

from .debug_case_state import DebugCaseState
from .environment_state import EnvironmentState
from .request_editor_state import (
    RequestEditorState,
    build_cookie_text,
    build_header_text,
    build_kv_text,
)
from .request_sender import RequestSenderCoordinator
from .response_state import ResponseState
from .service import ApiTestService
from .tabs_controller import TabsController


class ApiTestViewModel(QObject):
    # ---- signals ----
    apiImported = Signal("QVariantList")
    apiEnvironmentsImported = Signal("QVariantList")
    apiResponseReady = Signal(str, str, "QVariantMap")
    apiSendingChanged = Signal(bool)
    apiHistoryUpdated = Signal("QVariantList")
    tabsLoaded = Signal("QVariantList")
    environmentsLoaded = Signal("QVariantList")
    collectionTreeLoaded = Signal("QVariantList")
    wsTimelineLoaded = Signal("QVariantList")
    debugCasesLoaded = Signal("QVariantList")
    debugCasesRunCompleted = Signal("QVariantList")

    tabsChanged = Signal()
    editorChanged = Signal()
    wsTimelineChanged = Signal()
    debugCasesChanged = Signal()
    collectionDataChanged = Signal()
    environmentsChanged = Signal()
    apiHistoryChanged = Signal()
    responseChanged = Signal()
    wsStatusChanged = Signal()

    def __init__(self, database: SQLiteDatabase | Path | None = None) -> None:
        super().__init__()
        self._service = ApiTestService(database)
        self._disposed = False

        self._editor = RequestEditorState()
        self._sender = RequestSenderCoordinator(
            self._service,
            on_response=self._emit_api_response,
            on_history=self._emit_api_history,
            on_sending=self._emit_api_sending,
            on_ws_timeline=self._emit_ws_timeline,
            on_ws_status=self._emit_ws_status,
        )
        self._tabs = TabsController(
            self._editor,
            env_base_url=self._current_env_base_url,
            save_tab_draft=self._save_tab_draft_from_dict,
            save_case_snapshot=self._save_case_snapshot_from_dict,
            delete_tab=self._service.delete_tab,
        )
        self._request_sending: bool = False
        self._ws_status_by_tab: dict[str, dict] = {}
        self._ws_timeline: list[dict] = []
        self._debug_cases = DebugCaseState()
        self._response = ResponseState()
        self._collection_tree: list[dict] = []
        self._environments = EnvironmentState()
        self._api_history: list[dict] = []

    # ---- @Property ----
    # endpointTabs
    def _get_endpoint_tabs(self): return self._tabs.items
    def _set_endpoint_tabs(self, v):
        if self._tabs.items != v:
            self._tabs.set_items(list(v))
            if self._tabs.current_index >= 0:
                env_index = self._tabs.apply_current_to_editor(self._environments.items)
                if env_index is not None:
                    self._environments.current_index = env_index
            self.tabsChanged.emit()
            self.editorChanged.emit()
            self.environmentsChanged.emit()
    endpointTabs = Property("QVariantList", _get_endpoint_tabs, _set_endpoint_tabs, notify=tabsChanged)

    # currentEndpointTab
    def _get_current_endpoint_tab(self): return self._tabs.current_index
    def _set_current_endpoint_tab(self, v):
        if self._tabs.current_index != v:
            env_index = self._tabs.set_current_index(int(v), self._environments.items)
            if env_index is not None:
                self._environments.current_index = env_index
            self.tabsChanged.emit()
            self.editorChanged.emit()
            if env_index is not None:
                self.environmentsChanged.emit()
    currentEndpointTab = Property(int, _get_current_endpoint_tab, _set_current_endpoint_tab, notify=tabsChanged)

    # queryParams
    def _get_query_params(self): return self._editor.query_params
    def _set_query_params(self, v):
        if self._editor.query_params != v: self._editor.query_params = list(v); self.editorChanged.emit()
    queryParams = Property("QVariantList", _get_query_params, _set_query_params, notify=editorChanged)

    # pathParams
    def _get_path_params(self): return self._editor.path_params
    def _set_path_params(self, v):
        if self._editor.path_params != v: self._editor.path_params = list(v); self.editorChanged.emit()
    pathParams = Property("QVariantList", _get_path_params, _set_path_params, notify=editorChanged)

    # bodyModes
    bodyModes = Property("QVariantList", lambda self: self._editor.body_modes, constant=True)  # type: ignore[arg-type]

    # currentBodyMode
    def _get_current_body_mode(self): return self._editor.current_body_mode
    def _set_current_body_mode(self, v):
        if self._editor.current_body_mode != v: self._editor.current_body_mode = int(v); self.editorChanged.emit()
    currentBodyMode = Property(int, _get_current_body_mode, _set_current_body_mode, notify=editorChanged)

    # bodyFormRows
    def _get_body_form_rows(self): return self._editor.body_form_rows
    def _set_body_form_rows(self, v):
        if self._editor.body_form_rows != v: self._editor.body_form_rows = list(v); self.editorChanged.emit()
    bodyFormRows = Property("QVariantList", _get_body_form_rows, _set_body_form_rows, notify=editorChanged)

    # bodyFilePath
    def _get_body_file_path(self): return self._editor.body_file_path
    def _set_body_file_path(self, v):
        if self._editor.body_file_path != v: self._editor.body_file_path = str(v); self.editorChanged.emit()
    bodyFilePath = Property(str, _get_body_file_path, _set_body_file_path, notify=editorChanged)

    # bodyFileParamName
    def _get_body_file_param_name(self): return self._editor.body_file_param_name
    def _set_body_file_param_name(self, v):
        if self._editor.body_file_param_name != v: self._editor.body_file_param_name = str(v); self.editorChanged.emit()
    bodyFileParamName = Property(str, _get_body_file_param_name, _set_body_file_param_name, notify=editorChanged)

    # bodyText
    def _get_body_text(self): return self._editor.body_text
    def _set_body_text(self, v):
        if self._editor.body_text != v: self._editor.body_text = str(v); self.editorChanged.emit()
    bodyText = Property(str, _get_body_text, _set_body_text, notify=editorChanged)

    # bodyPerMode
    def _get_body_per_mode(self): return self._editor.body_per_mode
    def _set_body_per_mode(self, v):
        next_value = dict(v) if isinstance(v, dict) else {}
        if self._editor.body_per_mode != next_value: self._editor.body_per_mode = next_value; self.editorChanged.emit()
    bodyPerMode = Property("QVariantMap", _get_body_per_mode, _set_body_per_mode, notify=editorChanged)

    # headersRows
    def _get_headers_rows(self): return self._editor.headers_rows
    def _set_headers_rows(self, v):
        if self._editor.headers_rows != v: self._editor.headers_rows = list(v); self.editorChanged.emit()
    headersRows = Property("QVariantList", _get_headers_rows, _set_headers_rows, notify=editorChanged)

    # cookieRows
    def _get_cookie_rows(self): return self._editor.cookie_rows
    def _set_cookie_rows(self, v):
        if self._editor.cookie_rows != v: self._editor.cookie_rows = list(v); self.editorChanged.emit()
    cookieRows = Property("QVariantList", _get_cookie_rows, _set_cookie_rows, notify=editorChanged)

    # authTypeValue
    def _get_auth_type_value(self): return self._editor.auth_type_value
    def _set_auth_type_value(self, v):
        if self._editor.auth_type_value != v: self._editor.auth_type_value = str(v); self.editorChanged.emit()
    authTypeValue = Property(str, _get_auth_type_value, _set_auth_type_value, notify=editorChanged)

    # authValueText
    def _get_auth_value_text(self): return self._editor.auth_value_text
    def _set_auth_value_text(self, v):
        if self._editor.auth_value_text != v: self._editor.auth_value_text = str(v); self.editorChanged.emit()
    authValueText = Property(str, _get_auth_value_text, _set_auth_value_text, notify=editorChanged)

    # preOpsText
    def _get_pre_ops_text(self): return self._editor.pre_ops_text
    def _set_pre_ops_text(self, v):
        if self._editor.pre_ops_text != v: self._editor.pre_ops_text = str(v); self.editorChanged.emit()
    preOpsText = Property(str, _get_pre_ops_text, _set_pre_ops_text, notify=editorChanged)

    # postOpsText
    def _get_post_ops_text(self): return self._editor.post_ops_text
    def _set_post_ops_text(self, v):
        if self._editor.post_ops_text != v: self._editor.post_ops_text = str(v); self.editorChanged.emit()
    postOpsText = Property(str, _get_post_ops_text, _set_post_ops_text, notify=editorChanged)

    # cookiesText
    def _get_cookies_text(self): return self._editor.cookies_text
    def _set_cookies_text(self, v):
        if self._editor.cookies_text != v: self._editor.cookies_text = str(v); self.editorChanged.emit()
    cookiesText = Property(str, _get_cookies_text, _set_cookies_text, notify=editorChanged)

    # wsEncoding
    def _get_ws_encoding(self): return self._editor.ws_encoding
    def _set_ws_encoding(self, v):
        if self._editor.ws_encoding != v: self._editor.ws_encoding = str(v); self.editorChanged.emit()
    wsEncoding = Property(str, _get_ws_encoding, _set_ws_encoding, notify=editorChanged)

    # mockMode
    def _get_mock_mode(self): return self._editor.mock_mode
    def _set_mock_mode(self, v):
        if self._editor.mock_mode != v: self._editor.mock_mode = bool(v); self.editorChanged.emit()
    mockMode = Property(bool, _get_mock_mode, _set_mock_mode, notify=editorChanged)

    # assertionsEnabled
    def _get_assertions_enabled(self): return self._editor.assertions_enabled
    def _set_assertions_enabled(self, v):
        if self._editor.assertions_enabled != v: self._editor.assertions_enabled = bool(v); self.editorChanged.emit()
    assertionsEnabled = Property(bool, _get_assertions_enabled, _set_assertions_enabled, notify=editorChanged)

    # requestSending
    def _get_request_sending(self): return self._request_sending
    def _set_request_sending(self, v):
        if self._request_sending != v: self._request_sending = bool(v); self.apiSendingChanged.emit(v)
    requestSending = Property(bool, _get_request_sending, _set_request_sending, notify=apiSendingChanged)

    # wsTimeline
    def _get_ws_timeline(self): return self._ws_timeline
    def _set_ws_timeline(self, v):
        if self._ws_timeline != v: self._ws_timeline = list(v); self.wsTimelineChanged.emit()
    wsTimeline = Property("QVariantList", _get_ws_timeline, _set_ws_timeline, notify=wsTimelineChanged)

    def _get_ws_status(self): return self._current_ws_status().get("status", "idle")
    wsStatus = Property(str, _get_ws_status, notify=wsStatusChanged)

    def _get_ws_status_text(self): return self._current_ws_status().get("message", "未连接")
    wsStatusText = Property(str, _get_ws_status_text, notify=wsStatusChanged)

    # debugCases
    def _get_debug_cases(self): return self._debug_cases.items
    def _set_debug_cases(self, v):
        if self._debug_cases.items != v: self._debug_cases.set_items(list(v)); self.debugCasesChanged.emit()
    debugCases = Property("QVariantList", _get_debug_cases, _set_debug_cases, notify=debugCasesChanged)

    # selectedDebugCaseIds
    def _get_selected_debug_case_ids(self): return self._debug_cases.selected_ids
    def _set_selected_debug_case_ids(self, v):
        if self._debug_cases.selected_ids != v: self._debug_cases.set_selected_ids(list(v)); self.debugCasesChanged.emit()
    selectedDebugCaseIds = Property("QVariantList", _get_selected_debug_case_ids, _set_selected_debug_case_ids, notify=debugCasesChanged)

    # collectionTree
    def _get_collection_tree(self): return self._collection_tree
    def _set_collection_tree(self, v):
        if self._collection_tree != v: self._collection_tree = list(v); self.collectionDataChanged.emit()
    collectionTree = Property("QVariantList", _get_collection_tree, _set_collection_tree, notify=collectionDataChanged)

    # environments
    def _get_environments(self): return self._environments.items
    def _set_environments(self, v):
        if self._environments.items != v: self._environments.set_items(list(v)); self.environmentsChanged.emit()
    environments = Property("QVariantList", _get_environments, _set_environments, notify=environmentsChanged)

    # currentEnvIndex
    def _get_current_env_index(self): return self._environments.current_index
    def _set_current_env_index(self, v):
        if self._environments.current_index != v: self._environments.set_current_index(int(v)); self.environmentsChanged.emit()
    currentEnvIndex = Property(int, _get_current_env_index, _set_current_env_index, notify=environmentsChanged)

    # apiHistory
    def _get_api_history(self): return self._api_history
    def _set_api_history(self, v):
        if self._api_history != v: self._api_history = list(v); self.apiHistoryChanged.emit()
    apiHistory = Property("QVariantList", _get_api_history, _set_api_history, notify=apiHistoryChanged)

    def _get_response_title(self): return self._response.title_text
    responseTitle = Property(str, _get_response_title, notify=responseChanged)

    def _get_response_body(self): return self._response.body_text
    responseBody = Property(str, _get_response_body, notify=responseChanged)

    def _get_response_headers(self): return self._response.headers_text
    responseHeaders = Property(str, _get_response_headers, notify=responseChanged)

    def _get_response_request(self): return self._response.request_text
    responseRequest = Property(str, _get_response_request, notify=responseChanged)

    def _get_response_curl(self): return self._response.curl_text
    responseCurl = Property(str, _get_response_curl, notify=responseChanged)

    def _get_response_log(self): return self._response.request_log_text
    responseLog = Property(str, _get_response_log, notify=responseChanged)

    def _get_response_logs(self): return self._response.log_entries
    responseLogs = Property("QVariantList", _get_response_logs, notify=responseChanged)

    # ---- helpers ----
    def _current_tab_id(self) -> str:
        return self._tabs.current_tab_id()

    def _current_env_base_url(self) -> str:
        return self._environments.current_base_url()

    def _current_body_mode_name(self) -> str:
        return self._editor.current_body_mode_name()

    def _body_text_for_request(self) -> str:
        return self._editor.body_text_for_request()

    def _emit_api_response(self, title: str, body: str, details: dict) -> None:
        self._response.apply(title, body, details)
        self.responseChanged.emit()
        self.apiResponseReady.emit(title, body, details)

    def _emit_api_history(self, items: list[dict]) -> None:
        self.apiHistoryUpdated.emit(items)

    def _emit_api_sending(self, sending: bool) -> None:
        if self._request_sending != sending:
            self._request_sending = sending
        self.apiSendingChanged.emit(sending)

    def _emit_ws_timeline(self, tab_id: str) -> None:
        self.wsTimelineLoaded.emit(self._service.ws_timeline(tab_id))

    def _emit_ws_status(self, tab_id: str, status: str, message: str) -> None:
        self._ws_status_by_tab[str(tab_id or "")] = {"status": status or "idle", "message": message or ""}
        self.wsStatusChanged.emit()

    def _emit_editor_changed(self) -> None:
        self.editorChanged.emit()

    def _emit_tabs_and_editor_changed(self) -> None:
        self.tabsChanged.emit()
        self.editorChanged.emit()

    def _emit_tabs_editor_environment_changed(self) -> None:
        self.tabsChanged.emit()
        self.editorChanged.emit()
        self.environmentsChanged.emit()
        self.wsStatusChanged.emit()

    def _current_ws_status(self) -> dict:
        tab_id = self._current_tab_id()
        if tab_id in self._ws_status_by_tab:
            return self._ws_status_by_tab[tab_id]
        if not tab_id and "" in self._ws_status_by_tab:
            return self._ws_status_by_tab[""]
        return {"status": "idle", "message": "未连接"}

    # ---- existing @Slot methods (unchanged) ----

    @Slot(str)
    def importOpenApi(self, path: str) -> None:
        try:
            items, envs = self._service.import_openapi(path)
            self.applyImportedApiItems(items)
            self.apiEnvironmentsImported.emit(envs)
        except Exception:
            self.apiImported.emit([])
            self.apiEnvironmentsImported.emit([])

    @Slot(str, str, str, str, str, str, str, str, str, str, str, str)
    def sendApiFile(self, method, url, paramsText, headersText, filePath, fileParam,
                    envBaseUrl, authType, authValue, globalParamsText, assertionsText, tabId) -> None:
        self._sender.send_api_file(
            method,
            url,
            paramsText,
            headersText,
            filePath,
            fileParam,
            envBaseUrl,
            authType,
            authValue,
            globalParamsText,
            assertionsText,
            tabId,
        )

    @Slot(str, str, str, str, str, str, str, str, str, str, str, str, str, str, str)
    def sendApi(self, method, url, paramsText, headersText, bodyText, envBaseUrl,
                authType, authValue, requestMode, graphqlQuery, graphqlVariables,
                globalParamsText, assertionsText, mockResponseText, tabId) -> None:
        self._sender.send_api(
            method,
            url,
            paramsText,
            headersText,
            bodyText,
            envBaseUrl,
            authType,
            authValue,
            requestMode,
            graphqlQuery,
            graphqlVariables,
            globalParamsText,
            assertionsText,
            mockResponseText,
            tabId,
        )

    @Slot()
    def loadTabs(self) -> None:
        self.tabsLoaded.emit(self._service.list_tabs())

    @Slot()
    def loadApiHistory(self) -> None:
        self.apiHistoryUpdated.emit(self._service.list_history())

    @Slot()
    def loadEnvironments(self) -> None:
        self.environmentsLoaded.emit(self._service.list_environments())

    @Slot("QVariantList")
    def saveEnvironments(self, environments: list[dict]) -> None:
        self._service.save_environments(list(environments))
        self.environmentsLoaded.emit(self._service.list_environments())

    @Slot()
    def loadCollectionTree(self) -> None:
        self.collectionTreeLoaded.emit(self._service.load_collection_tree())

    @Slot("QVariantList")
    def saveCollectionTree(self, tree: list[dict]) -> None:
        self._service.replace_collection_tree(list(tree))

    @Slot(str, str, str, str, str, result=str)
    def createCollectionNode(self, parentId, kind, name, method, path) -> str:
        return self._service.create_collection_node(parent_id=parentId, kind=kind, name=name, method=method, url=path)

    @Slot(str, result=str)
    def duplicateCollectionNode(self, nodeId) -> str:
        return self._service.duplicate_collection_node(nodeId)

    @Slot(str, str)
    def renameCollectionNode(self, nodeId, name) -> None:
        self._service.rename_collection_node(nodeId, name)

    @Slot(str)
    def deleteCollectionNode(self, nodeId) -> None:
        self._service.delete_collection_node(nodeId)

    @Slot(str, str)
    def moveCollectionNode(self, nodeId, targetParentId) -> None:
        self._service.move_collection_node(nodeId, targetParentId)

    @Slot(str, int)
    def reorderCollectionNode(self, nodeId, delta) -> None:
        self._service.move_collection_node(nodeId, "", delta)

    @Slot(str, bool)
    def setCollectionNodeExpanded(self, nodeId, expanded) -> None:
        self._service.set_collection_node_expanded(nodeId, expanded)

    @Slot(str, "QVariantMap")
    def saveCaseSnapshot(self, nodeId, snapshot) -> None:
        self._service.save_case_snapshot(nodeId, snapshot)

    @Slot(bool)
    def setAllCollectionNodesExpanded(self, expanded) -> None:
        self._service.set_all_collection_nodes_expanded(expanded)

    @Slot(str, str, str)
    def updateCollectionEndpoint(self, nodeId, method, url) -> None:
        self._service.update_collection_endpoint(nodeId, method, url)

    @Slot(str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, bool)
    def saveTabDraft(self, tabId, name, method, url, requestMode, bodyMode, authType, authValue,
                     headersText, cookiesText, bodyText, paramsText, pathParamsText, envBaseUrl,
                     preOpsText, postOpsText, nodeId, mockMode) -> None:
        self._service.upsert_tab(
            tabId,
            name,
            method,
            url,
            requestMode,
            bodyMode,
            authType,
            authValue,
            headersText,
            cookiesText,
            bodyText,
            paramsText,
            pathParamsText,
            envBaseUrl,
            preOpsText,
            postOpsText,
            nodeId,
            mockMode,
        )

    def _save_tab_draft_from_dict(self, tab: dict) -> None:
        self._service.upsert_tab(
            str(tab.get("id") or ""),
            str(tab.get("name") or ""),
            str(tab.get("method") or "GET"),
            str(tab.get("url") or "/"),
            str(tab.get("requestMode") or "http"),
            str(tab.get("bodyMode") or "none"),
            str(tab.get("authType") or "none"),
            str(tab.get("authValue") or ""),
            str(tab.get("headersText") or ""),
            str(tab.get("cookiesText") or ""),
            str(tab.get("bodyText") or ""),
            str(tab.get("paramsText") or ""),
            str(tab.get("pathParamsText") or ""),
            str(tab.get("envBaseUrl") or ""),
            str(tab.get("preOpsText") or ""),
            str(tab.get("postOpsText") or ""),
            str(tab.get("nodeId") or ""),
            bool(tab.get("mockMode")),
        )

    def _save_case_snapshot_from_dict(self, node_id: str, snapshot: dict) -> None:
        self._service.save_case_snapshot(node_id, snapshot)

    @Slot(str)
    def removeTab(self, tabId) -> None:
        self._service.delete_tab(tabId)

    @Slot(str, str, str, str, str, str)
    def wsConnect(self, tabId, url, paramsText, headersText, cookiesText, envBaseUrl) -> None:
        self._sender.connect_ws(tabId, url, paramsText, headersText, cookiesText, envBaseUrl)

    @Slot(str, str, str)
    def wsSend(self, tabId, content, encoding) -> None:
        self._sender.send_ws(tabId, content, encoding)

    @Slot(str)
    def wsReceive(self, tabId) -> None:
        self._sender.receive_ws(tabId)

    @Slot(str)
    def wsDisconnect(self, tabId) -> None:
        self._sender.disconnect_ws(tabId)

    @Slot(str)
    def loadWsTimeline(self, tabId) -> None:
        self.wsTimelineLoaded.emit(self._service.ws_timeline(tabId))

    @Slot(str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, bool)
    def saveDebugCase(self, endpointKey, caseId, name, method, url, requestMode, bodyMode,
                      authType, authValue, headersText, cookiesText, bodyText, paramsText,
                      pathParamsText, envBaseUrl, preOpsText, postOpsText, mockMode) -> None:
        self._service.save_debug_case(endpointKey, {
            "id": caseId, "name": name, "method": method, "url": url,
            "requestMode": requestMode, "bodyMode": bodyMode, "authType": authType,
            "authValue": authValue, "headersText": headersText, "cookiesText": cookiesText,
            "bodyText": bodyText, "paramsText": paramsText, "pathParamsText": pathParamsText,
            "envBaseUrl": envBaseUrl, "preOpsText": preOpsText, "postOpsText": postOpsText,
            "mockMode": mockMode,
        })
        self.debugCasesLoaded.emit(self._service.list_debug_cases(endpointKey))

    @Slot(str)
    def loadDebugCases(self, endpointKey) -> None:
        self.debugCasesLoaded.emit(self._service.list_debug_cases(endpointKey))

    @Slot(str, "QVariantList")
    def runDebugCases(self, endpointKey, caseIds) -> None:
        results = self._service.run_debug_cases(endpointKey, list(caseIds))
        self.debugCasesRunCompleted.emit(results)

    @Slot("QVariantList")
    def applyImportedApiItems(self, items) -> None:
        grouped: list[dict] = []
        group_map: dict[str, dict] = {}
        import_time = datetime.now().timestamp() * 1000
        for i, it in enumerate(items or []):
            path = str(it.get("path") or "/").strip() or "/"
            parts = path.split("/")
            group_name = parts[1] if len(parts) > 1 and parts[1] else "默认分组"
            if group_name not in group_map:
                group_map[group_name] = {"name": group_name, "kind": "folder", "expanded": True, "children": []}
                grouped.append(group_map[group_name])
            method = str(it.get("method") or "GET").upper()
            if method == "DEL":
                method = "DELETE"
            summary = str(it.get("summary") or "")
            endpoint_name = summary if summary else f"{method} {path}"
            group_map[group_name]["children"].append({
                "id": f"import_endpoint_{i}_{int(import_time)}",
                "kind": "endpoint", "name": endpoint_name, "method": method, "path": path,
            })
        for gi, g in enumerate(grouped):
            g["id"] = f"import_folder_{gi}_{int(import_time)}"
            g["kind"] = "folder"
        self.apiImported.emit(grouped)

    @Slot("QVariantMap")
    def sendRequest(self, data: dict) -> None:
        self._editor.save_body_to_mode()
        self._sender.send_request(data)

    @Slot("QVariantMap")
    def saveDebugCaseData(self, data: dict) -> None:
        self.saveDebugCase(
            str(data.get("endpointKey") or ""), str(data.get("caseId") or ""),
            str(data.get("name") or ""), str(data.get("method") or "GET"),
            str(data.get("url") or "/"), str(data.get("requestMode") or "http"),
            str(data.get("bodyMode") or "none"), str(data.get("authType") or "none"),
            str(data.get("authValue") or ""), str(data.get("headersText") or ""),
            str(data.get("cookiesText") or ""), str(data.get("bodyText") or ""),
            str(data.get("paramsText") or ""), str(data.get("pathParamsText") or ""),
            str(data.get("envBaseUrl") or ""), str(data.get("preOpsText") or ""),
            str(data.get("postOpsText") or ""), bool(data.get("mockMode")),
        )

    @Slot(str, str, "QVariantMap")
    def applyResponseDetails(self, title: str, body_text: str, details: dict) -> None:
        self._emit_api_response(title, body_text, details or {})

    # ---- NEW @Slot: orchestration methods ----

    @Slot(str, result="QVariantMap")
    def normalizeRows(self, section: str) -> dict:
        return {"rows": self._editor.normalize_section(section)}

    @Slot(str, int, bool)
    def toggleSectionRowEnabled(self, section: str, row_index: int, checked: bool) -> None:
        if self._editor.toggle_row_enabled(section, row_index, checked):
            self._emit_editor_changed()

    @Slot(str, int, str)
    def editSectionRowKey(self, section: str, row_index: int, key_text: str) -> None:
        if self._editor.edit_row_key(section, row_index, key_text):
            self._emit_editor_changed()

    @Slot(str, int, str)
    def editSectionRowValue(self, section: str, row_index: int, value_text: str) -> None:
        if self._editor.edit_row_value(section, row_index, value_text):
            self._emit_editor_changed()

    @Slot(str, int)
    def deleteSectionRow(self, section: str, row_index: int) -> None:
        if self._editor.delete_row(section, row_index):
            self._emit_editor_changed()

    def _get_rows(self, section: str) -> list[dict]:
        return self._editor.get_rows(section)

    def _set_rows(self, section: str, rows: list[dict]) -> None:
        self._editor.set_rows(section, rows)
        self._emit_editor_changed()

    @Slot()
    def persistCurrentTabDraft(self) -> None:
        if self._tabs.persist_current():
            self.tabsChanged.emit()

    @Slot(str, str)
    def updateCurrentTabRequest(self, method: str, url: str) -> None:
        if self._tabs.update_current_request(method, url):
            self.tabsChanged.emit()

    @Slot(str, str, str, str)
    def openEndpointTab(self, name: str, method: str, url: str, nodeId: str) -> None:
        self._tabs.open_endpoint(name, method, url, nodeId, self._environments.items)
        self._emit_tabs_editor_environment_changed()

    @Slot(str, str, str, str, "QVariantMap")
    def openCaseTab(self, name: str, method: str, url: str, nodeId: str, requestSnapshot: dict) -> None:
        self._tabs.open_case(name, method, url, nodeId, requestSnapshot, self._environments.items)
        self._emit_tabs_editor_environment_changed()

    def openRequestTab(self, name: str, method: str, url: str, nodeId: str, kind: str, request_snapshot: dict | None = None) -> None:
        self._tabs.open_request(name, method, url, nodeId, kind, request_snapshot, self._environments.items)
        self._emit_tabs_editor_environment_changed()

    @Slot("QVariantList", bool)
    def replaceCollectionTree(self, tree: list[dict], should_save: bool = True) -> None:
        if should_save:
            self.saveCollectionTree(tree or [])
        self._collection_tree = self._service.load_collection_tree()
        self.collectionDataChanged.emit()

    @Slot()
    def sendCurrentRequest(self) -> None:
        self._emit_api_response("状态: ERR", "当前发送入口需要由 QML 提供 method 和 url。", {})

    @Slot()
    def saveCurrentAsDebugCase(self) -> None:
        self.persistCurrentTabDraft()
        tab = self._tabs.current_tab()
        endpoint_key = f"{tab.get('method', 'GET')} {tab.get('url', '/')}"
        case_name = self._debug_cases.next_case_name()
        self.saveDebugCaseData({
            "endpointKey": endpoint_key, "caseId": "", "name": case_name,
            "method": tab.get("method", "GET"), "url": tab.get("url", "/"),
            "requestMode": "mock" if self._editor.mock_mode else tab.get("requestMode", "http"),
            "bodyMode": self._current_body_mode_name(),
            "authType": self._editor.auth_type_value, "authValue": self._editor.auth_value_text,
            "headersText": build_header_text(self._editor.headers_rows),
            "cookiesText": build_cookie_text(self._editor.cookie_rows),
            "bodyText": self._body_text_for_request(),
            "paramsText": build_kv_text(self._editor.query_params),
            "pathParamsText": build_kv_text(self._editor.path_params),
            "envBaseUrl": self._current_env_base_url(),
            "preOpsText": self._editor.pre_ops_text, "postOpsText": self._editor.post_ops_text,
            "mockMode": self._editor.mock_mode,
        })
        self.loadDebugCases(endpoint_key)
        self.loadWsTimeline(tab.get("id", ""))

    @Slot(int)
    def toggleCaseSelection(self, index: int) -> None:
        if self._debug_cases.toggle_by_index(index):
            self.debugCasesChanged.emit()

    @Slot(str)
    def toggleCaseSelectionById(self, case_id: str) -> None:
        if self._debug_cases.toggle_by_id(case_id):
            self.debugCasesChanged.emit()

    @Slot()
    def toggleMockMode(self) -> None:
        self._editor.mock_mode = not self._editor.mock_mode
        self._emit_editor_changed()

    @Slot(int)
    def setCurrentBodyMode(self, index: int) -> None:
        self._editor.set_current_body_mode(index)
        self._emit_editor_changed()

    @Slot()
    def closeCurrentTab(self) -> None:
        if self._tabs.close_current(self._environments.items):
            self._emit_tabs_editor_environment_changed()

    def _apply_endpoint_tab(self) -> None:
        env_index = self._tabs.apply_current_to_editor(self._environments.items)
        if env_index is not None:
            self._environments.current_index = env_index
            self._emit_tabs_editor_environment_changed()
        else:
            self._emit_tabs_and_editor_changed()

    def dispose(self) -> None:
        self._disposed = True
        self._sender.dispose()
        if self._service:
            self._service.close()
