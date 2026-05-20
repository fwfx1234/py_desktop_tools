from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWebSocketSessionService:
    @pytest.fixture
    def ws_svc(self, variable_service, api_database):
        from features.api_test.ws_service import WebSocketSessionService

        return WebSocketSessionService(api_database.storage, variable_service)

    def test_initial_state_not_connected(self, ws_svc) -> None:
        assert ws_svc.is_connected("tab-nonexistent") is False

    def test_connect_and_disconnect(self, ws_svc) -> None:
        mock_ws = MagicMock()
        with patch("websocket.create_connection", return_value=mock_ws):
            final_url = ws_svc.connect(
                tab_id="tab-ws-1",
                url="ws://echo.example.com/chat",
                params={},
                headers={},
                cookies="",
                env_name="",
                env_base_url="",
            )
        assert "echo.example.com" in final_url
        assert ws_svc.is_connected("tab-ws-1") is True

        ws_svc.disconnect("tab-ws-1")
        assert ws_svc.is_connected("tab-ws-1") is False
        mock_ws.close.assert_called_once()

    def test_connect_replaces_previous_connection(self, ws_svc) -> None:
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        with patch("websocket.create_connection", side_effect=[mock_ws1, mock_ws2]):
            ws_svc.connect(
                tab_id="tab-ws-2", url="ws://first.example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
            ws_svc.connect(
                tab_id="tab-ws-2", url="ws://second.example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
        mock_ws1.close.assert_called_once()
        assert ws_svc.is_connected("tab-ws-2") is True

    def test_send_message_when_not_connected_raises(self, ws_svc) -> None:
        with pytest.raises(RuntimeError, match="未连接"):
            ws_svc.send_message(tab_id="nonexistent", content="hello", encoding="text")

    def test_send_message_text(self, ws_svc) -> None:
        mock_ws = MagicMock()
        with patch("websocket.create_connection", return_value=mock_ws):
            ws_svc.connect(
                tab_id="tab-send", url="ws://example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
        result = ws_svc.send_message(tab_id="tab-send", content="hello", encoding="text")
        assert result == "hello"
        mock_ws.send.assert_called_once_with("hello")

    def test_send_message_base64(self, ws_svc) -> None:
        import base64

        mock_ws = MagicMock()
        with patch("websocket.create_connection", return_value=mock_ws):
            ws_svc.connect(
                tab_id="tab-b64", url="ws://example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )

        payload = "hello binary"
        ws_svc.send_message(tab_id="tab-b64", content=base64.b64encode(payload.encode()).decode(), encoding="base64")
        mock_ws.send.assert_called_once()

    def test_receive_once(self, ws_svc) -> None:
        mock_ws = MagicMock()
        mock_ws.recv.return_value = "server message"
        with patch("websocket.create_connection", return_value=mock_ws):
            ws_svc.connect(
                tab_id="tab-recv", url="ws://example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
        result = ws_svc.receive_once("tab-recv")
        assert result == "server message"

    def test_receive_binary(self, ws_svc) -> None:
        mock_ws = MagicMock()
        mock_ws.recv.return_value = b"\x00\x01\x02"
        with patch("websocket.create_connection", return_value=mock_ws):
            ws_svc.connect(
                tab_id="tab-bin", url="ws://example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
        result = ws_svc.receive_once("tab-bin")
        assert isinstance(result, str)

    def test_disconnect_all(self, ws_svc) -> None:
        mock1 = MagicMock()
        mock2 = MagicMock()
        with patch("websocket.create_connection", side_effect=[mock1, mock2]):
            ws_svc.connect(tab_id="a", url="ws://a.com", params={}, headers={}, cookies="", env_name="", env_base_url="")
            ws_svc.connect(tab_id="b", url="ws://b.com", params={}, headers={}, cookies="", env_name="", env_base_url="")
        ws_svc.disconnect_all()
        assert ws_svc.is_connected("a") is False
        assert ws_svc.is_connected("b") is False

    def test_timeline_records_messages(self, ws_svc) -> None:
        mock_ws = MagicMock()
        with patch("websocket.create_connection", return_value=mock_ws):
            ws_svc.connect(
                tab_id="tab-tl", url="ws://example.com",
                params={}, headers={}, cookies="", env_name="", env_base_url="",
            )
        timeline = ws_svc.list_timeline("tab-tl")
        assert len(timeline) >= 1
        assert timeline[0]["direction"] == "system"

    def test_resolve_ws_url(self, ws_svc) -> None:
        result = ws_svc._resolve_url("ws://abs.example.com/chat", "http://base.example.com")
        assert result == "ws://abs.example.com/chat"

        result = ws_svc._resolve_url("/chat", "http://base.example.com")
        assert result == "http://base.example.com/chat"
