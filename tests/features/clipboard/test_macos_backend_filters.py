from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.services.clipboard.backends.macos_backend import (
    MacOSClipboardBackend,
    NOISE_UTIS,
    SELF_COPY_UTI,
    SENSITIVE_UTIS,
    _is_all_noise,
    _is_self_copy,
    _is_sensitive,
    _pasteboard_types,
)
from app.services.clipboard.models import ClipboardItemDraft


class FakePasteboard:
    def __init__(self, types: list[str]) -> None:
        self._types = list(types)

    def types(self) -> list[str]:
        return list(self._types)


class PureFilterTests(unittest.TestCase):
    def test_sensitive_uti_detected(self) -> None:
        for uti in SENSITIVE_UTIS:
            with self.subTest(uti=uti):
                self.assertTrue(_is_sensitive(frozenset({uti, "public.utf8-plain-text"})))

    def test_sensitive_uti_negative(self) -> None:
        self.assertFalse(_is_sensitive(frozenset({"public.utf8-plain-text"})))
        self.assertFalse(_is_sensitive(frozenset()))

    def test_self_copy_marker_detected(self) -> None:
        self.assertTrue(_is_self_copy(frozenset({SELF_COPY_UTI, "public.utf8-plain-text"})))
        self.assertFalse(_is_self_copy(frozenset({"public.utf8-plain-text"})))

    def test_all_noise_when_only_known_noise(self) -> None:
        self.assertTrue(_is_all_noise(frozenset(NOISE_UTIS)))
        self.assertTrue(_is_all_noise(frozenset({"dyn.ah62d4rv4gk81g25xmqzwc8py"})))
        self.assertTrue(
            _is_all_noise(frozenset({
                "com.microsoft.ObjectLink",
                "com.microsoft.Link-Source",
                "dyn.foo",
            }))
        )

    def test_not_all_noise_when_real_type_present(self) -> None:
        self.assertFalse(
            _is_all_noise(frozenset({
                "public.utf8-plain-text",
                "com.apple.linkpresentation.metadata",
            }))
        )

    def test_pasteboard_types_handles_missing_method(self) -> None:
        class Broken:
            def types(self):
                raise RuntimeError("boom")

        self.assertEqual(_pasteboard_types(Broken()), frozenset())


class HandleChangeTests(unittest.TestCase):
    def _make_backend(self) -> MacOSClipboardBackend:
        backend = MacOSClipboardBackend()
        backend._callback = MagicMock()
        return backend

    def test_self_copy_short_circuits_callback(self) -> None:
        backend = self._make_backend()
        backend._suppress_signature = "stale-suppress"
        pb = FakePasteboard([SELF_COPY_UTI, "public.utf8-plain-text"])

        backend._handle_change(pb)

        backend._callback.assert_not_called()
        self.assertEqual(backend._suppress_signature, "")

    def test_sensitive_uti_short_circuits_callback(self) -> None:
        backend = self._make_backend()
        pb = FakePasteboard(["org.nspasteboard.ConcealedType", "public.utf8-plain-text"])

        backend._handle_change(pb)

        backend._callback.assert_not_called()

    def test_pure_noise_pasteboard_skips_read(self) -> None:
        backend = self._make_backend()
        pb = FakePasteboard(["com.apple.linkpresentation.metadata", "dyn.foo"])

        from app.services.clipboard.backends import macos_backend as mb

        with unittest.mock.patch.object(mb, "_read_pasteboard_draft") as read_mock:
            backend._handle_change(pb)
            read_mock.assert_not_called()

        backend._callback.assert_not_called()

    def test_real_text_passes_through(self) -> None:
        backend = self._make_backend()
        pb = FakePasteboard(["public.utf8-plain-text"])

        from app.services.clipboard.backends import macos_backend as mb

        with unittest.mock.patch.object(
            mb,
            "_read_pasteboard_draft",
            return_value=ClipboardItemDraft(item_type="text", content="hello", preview="hello"),
        ):
            backend._handle_change(pb)

        backend._callback.assert_called_once()
        draft = backend._callback.call_args.args[0]
        self.assertEqual(draft.item_type, "text")
        self.assertEqual(draft.content, "hello")


if __name__ == "__main__":
    unittest.main()
