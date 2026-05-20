from __future__ import annotations

"""Contract tests that verify the ViewModel Slot signatures.

These tests ensure QML-to-Python binding stability. If a Slot signature
changes, QML callers can break silently at runtime.
"""

import inspect

import pytest


class TestApiTestViewModelSlots:
    """Verify that every @Slot method expected by QML exists with correct signature."""

    # Expected Slot methods and their parameter counts
    # (method_name, min_params) — at least this many positional params
    EXPECTED_SLOTS = [
        ("importOpenApi", 1),
        ("sendApi", 13),
        ("sendApiFile", 12),
        ("loadTabs", 0),
        ("loadInitialData", 0),
        ("loadApiHistory", 0),
        ("loadEnvironments", 0),
        ("saveEnvironments", 1),
        ("loadCollectionTree", 0),
        ("saveCollectionTree", 1),
        ("createCollectionNode", 5),
        ("duplicateCollectionNode", 1),
        ("renameCollectionNode", 2),
        ("deleteCollectionNode", 1),
        ("moveCollectionNode", 2),
        ("reorderCollectionNode", 2),
        ("setCollectionNodeExpanded", 2),
        ("saveCaseSnapshot", 2),
        ("setAllCollectionNodesExpanded", 1),
        ("updateCollectionEndpoint", 3),
        ("saveTabDraft", 18),
        ("removeTab", 1),
        ("wsConnect", 6),
        ("wsSend", 3),
        ("wsReceive", 1),
        ("wsDisconnect", 1),
        ("loadWsTimeline", 1),
        ("saveDebugCase", 18),
        ("loadDebugCases", 1),
        ("runDebugCases", 2),
        ("applyImportedApiItems", 1),
        ("sendRequest", 1),
        ("saveDebugCaseData", 1),
        ("applyResponseDetails", 3),
        ("normalizeRows", 1),
        ("toggleSectionRowEnabled", 3),
        ("editSectionRowKeyLive", 3),
        ("editSectionRowKey", 3),
        ("editSectionRowValueLive", 3),
        ("editSectionRowValue", 3),
        ("deleteSectionRow", 2),
        ("persistCurrentTabDraft", 0),
        ("updateCurrentTabRequest", 2),
        ("openEndpointTab", 4),
        ("openCaseTab", 5),
        ("replaceCollectionTree", 1),
        ("sendCurrentRequest", 0),
        ("saveCurrentAsDebugCase", 0),
        ("toggleCaseSelection", 1),
        ("toggleCaseSelectionById", 1),
        ("toggleMockMode", 0),
        ("setCurrentBodyMode", 1),
        ("closeCurrentTab", 0),
    ]

    @pytest.fixture
    def vm_class(self):
        from features.api_test.view_model import ApiTestViewModel
        return ApiTestViewModel

    def test_all_slot_methods_exist(self, vm_class) -> None:
        for method_name, _ in self.EXPECTED_SLOTS:
            assert hasattr(vm_class, method_name), f"Missing Slot: {method_name}"

    def test_slot_parameter_counts(self, vm_class) -> None:
        for method_name, min_params in self.EXPECTED_SLOTS:
            method = getattr(vm_class, method_name)
            sig = inspect.signature(method)
            # Exclude 'self'
            params = [p for p in sig.parameters.values() if p.name != "self"]
            assert len(params) >= min_params, (
                f"Slot {method_name} expects at least {min_params} params, got {len(params)}"
            )


class TestApiTestViewModelProperties:
    """Verify QML-exposed Property getters/setters exist."""

    # Actual getter names in the ViewModel (snake_case convention)
    EXPECTED_GETTERS = [
        "_get_endpoint_tabs", "_set_endpoint_tabs",
        "_get_current_endpoint_tab", "_set_current_endpoint_tab",
        "_get_query_params",
        "_get_path_params",
        "_get_current_body_mode", "_set_current_body_mode",
        "_get_body_form_rows",
        "_get_body_file_path",
        "_get_body_file_param_name",
        "_get_body_text",
        "_get_body_per_mode",
        "_get_headers_rows",
        "_get_cookie_rows",
        "_get_auth_type_value",
        "_get_auth_value_text",
        "_get_pre_ops_text",
        "_get_post_ops_text",
        "_get_cookies_text",
        "_get_ws_encoding",
        "_get_mock_mode",
        "_get_assertions_enabled",
        "_get_request_sending",
        "_get_ws_timeline",
        "_get_ws_status",
        "_get_ws_status_text",
        "_get_debug_cases",
        "_get_selected_debug_case_ids",
        "_get_collection_tree",
        "_get_environments",
        "_get_current_env_index",
        "_get_api_history",
        "_get_response_title",
        "_get_response_body",
        "_get_response_headers",
        "_get_response_request",
        "_get_response_curl",
        "_get_response_log",
        "_get_response_logs",
    ]

    @pytest.fixture
    def vm_class(self):
        from features.api_test.view_model import ApiTestViewModel
        return ApiTestViewModel

    def test_all_property_getters_exist(self, vm_class) -> None:
        for getter_name in self.EXPECTED_GETTERS:
            assert hasattr(vm_class, getter_name), f"Missing property getter: {getter_name}"

    def test_signals_exist(self, vm_class) -> None:
        expected_signals = [
            "apiImported",
            "apiEnvironmentsImported",
            "apiResponseReady",
            "apiSendingChanged",
            "apiHistoryUpdated",
            "tabsLoaded",
            "environmentsLoaded",
            "collectionTreeLoaded",
            "wsTimelineLoaded",
            "debugCasesLoaded",
            "debugCasesRunCompleted",
            "tabsChanged",
            "editorChanged",
            "wsTimelineChanged",
            "debugCasesChanged",
            "collectionDataChanged",
            "environmentsChanged",
            "apiHistoryChanged",
            "responseChanged",
            "wsStatusChanged",
        ]
        for signal_name in expected_signals:
            assert hasattr(vm_class, signal_name), f"Missing Signal: {signal_name}"
