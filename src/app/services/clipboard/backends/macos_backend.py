from __future__ import annotations

from io import BytesIO
from pathlib import Path
from threading import Event, Thread

from app.services.clipboard.models import ClipboardItemDraft


_appkit = None
_foundation = None
_consts: dict[str, object] = {}


def _ensure_appkit():
    global _appkit, _foundation
    if _appkit is not None:
        return _appkit, _foundation
    try:
        import AppKit
        import Foundation
    except Exception as exc:
        raise RuntimeError("AppKit 不可用，macOS 剪切板能力不可用") from exc
    _appkit = AppKit
    _foundation = Foundation
    _consts["string"] = AppKit.NSPasteboardTypeString
    _consts["png"] = AppKit.NSPasteboardTypePNG
    _consts["tiff"] = AppKit.NSPasteboardTypeTIFF
    _consts["file_url"] = AppKit.NSPasteboardTypeFileURL
    _consts["url_only_key"] = AppKit.NSPasteboardURLReadingFileURLsOnlyKey
    return _appkit, _foundation


def _general_pasteboard():
    appkit, _ = _ensure_appkit()
    return appkit.NSPasteboard.generalPasteboard()


class MacOSClipboardBackend:
    def __init__(self, *, poll_interval: float = 0.5) -> None:
        self._poll_interval = max(0.05, float(poll_interval))
        self._callback = None
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._last_change_count = 0
        self._last_signature = ""
        self._suppress_signature = ""
        self._pasteboard = None

    def start(self, on_change) -> None:
        self._callback = on_change
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        try:
            self._pasteboard = _general_pasteboard()
            self._last_change_count = int(self._pasteboard.changeCount())
        except Exception:
            self._pasteboard = None
            self._last_change_count = 0
        self._thread = Thread(
            target=self._poll_loop,
            name="clipboard-macos-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._callback = None

    def read_current(self) -> ClipboardItemDraft | None:
        pb = self._pasteboard
        if pb is None:
            try:
                pb = _general_pasteboard()
            except RuntimeError:
                return None
        return _read_pasteboard_draft(pb)

    def read_text(self) -> str:
        draft = self.read_current()
        if draft is None or draft.item_type != "text":
            return ""
        return draft.content

    def write_text(self, text: str) -> None:
        _ensure_appkit()
        pb = self._pasteboard or _general_pasteboard()
        pb.clearContents()
        if not pb.setString_forType_(text or "", _consts["string"]):
            raise OSError("写入文本失败")
        self._suppress_signature = f"text:{text or ''}"
        self._last_signature = self._suppress_signature
        try:
            self._last_change_count = int(pb.changeCount())
        except Exception:
            pass

    def write_files(self, paths: list[str]) -> None:
        _, foundation = _ensure_appkit()
        clean_paths = [str(Path(path)) for path in paths if path]
        if not clean_paths:
            raise ValueError("文件列表为空")
        for path in clean_paths:
            if not Path(path).exists():
                raise FileNotFoundError(path)
        urls = [foundation.NSURL.fileURLWithPath_(p) for p in clean_paths]
        pb = self._pasteboard or _general_pasteboard()
        pb.clearContents()
        if not pb.writeObjects_(urls):
            raise OSError("写入文件失败")
        self._suppress_signature = "files:" + "|".join(clean_paths)
        self._last_signature = self._suppress_signature
        try:
            self._last_change_count = int(pb.changeCount())
        except Exception:
            pass

    def write_image(self, path: str | Path) -> None:
        appkit, _ = _ensure_appkit()
        image_path = Path(path)
        if not image_path.exists():
            raise FileNotFoundError(str(image_path))
        ns_image = appkit.NSImage.alloc().initWithContentsOfFile_(str(image_path))
        if ns_image is None:
            raise OSError("无法读取图片")
        tiff_data = ns_image.TIFFRepresentation()
        if tiff_data is None:
            raise OSError("无法编码图片")
        pb = self._pasteboard or _general_pasteboard()
        pb.clearContents()
        if not pb.setData_forType_(tiff_data, _consts["tiff"]):
            raise OSError("写入图片失败")
        png_bytes = _tiff_data_to_png_bytes(bytes(tiff_data))
        signature = f"image:{len(png_bytes)}:{hash(png_bytes)}"
        self._suppress_signature = signature
        self._last_signature = signature
        try:
            self._last_change_count = int(pb.changeCount())
        except Exception:
            pass

    def clear(self) -> None:
        pb = self._pasteboard
        if pb is None:
            try:
                pb = _general_pasteboard()
            except RuntimeError:
                return
        pb.clearContents()
        self._suppress_signature = ""
        self._last_signature = ""

    def _poll_loop(self) -> None:
        wait = self._stop_event.wait
        interval = self._poll_interval
        pb = self._pasteboard
        while not self._stop_event.is_set():
            try:
                change_count = int(pb.changeCount()) if pb is not None else 0
            except Exception:
                change_count = self._last_change_count
            if change_count and change_count != self._last_change_count:
                self._last_change_count = change_count
                self._handle_change(pb)
            wait(interval)

    def _handle_change(self, pasteboard) -> None:
        draft = _read_pasteboard_draft(pasteboard)
        signature = _draft_signature(draft)
        if draft is None or not signature or signature == self._last_signature:
            return
        if signature == self._suppress_signature:
            self._suppress_signature = ""
            self._last_signature = signature
            return
        self._last_signature = signature
        callback = self._callback
        if not callable(callback):
            return
        try:
            callback(draft)
        except Exception:
            pass


def _read_pasteboard_draft(pasteboard) -> ClipboardItemDraft | None:
    paths = _read_file_urls(pasteboard)
    if paths:
        names = [Path(path).name or path for path in paths]
        preview = ", ".join(names[:3])
        if len(names) > 3:
            preview += f" ... (+{len(names) - 3})"
        return ClipboardItemDraft(
            item_type="files",
            preview=preview,
            metadata={"count": len(paths), "paths": paths},
        )
    image_draft = _read_image_draft(pasteboard)
    if image_draft is not None:
        return image_draft
    text = _read_text(pasteboard)
    if text:
        return ClipboardItemDraft(
            item_type="text",
            content=text,
            preview=_compact_preview(text),
        )
    return None


def _read_file_urls(pasteboard) -> list[str]:
    try:
        _, foundation = _ensure_appkit()
    except RuntimeError:
        return []
    options = {_consts["url_only_key"]: True}
    urls = pasteboard.readObjectsForClasses_options_([foundation.NSURL], options) or []
    paths: list[str] = []
    for url in urls:
        path = url.path() if hasattr(url, "path") else None
        if path:
            paths.append(str(path))
    return paths


def _read_text(pasteboard) -> str:
    try:
        _ensure_appkit()
    except RuntimeError:
        return ""
    value = pasteboard.stringForType_(_consts["string"])
    if value is None:
        return ""
    return str(value)


def _read_image_draft(pasteboard) -> ClipboardItemDraft | None:
    try:
        _ensure_appkit()
    except RuntimeError:
        return None
    png_data = pasteboard.dataForType_(_consts["png"])
    tiff_data = None
    if png_data is None:
        tiff_data = pasteboard.dataForType_(_consts["tiff"])
    if png_data is None and tiff_data is None:
        return None
    png_bytes: bytes
    width = 0
    height = 0
    if png_data is not None:
        png_bytes = bytes(png_data)
        size = _png_dimensions(png_bytes)
        if size is not None:
            width, height = size
    else:
        converted = _tiff_to_png(bytes(tiff_data))
        if converted is None:
            return None
        png_bytes, width, height = converted
    preview = f"{width} x {height} PNG" if width and height else "图片"
    return ClipboardItemDraft(
        item_type="image",
        preview=preview,
        metadata={"width": width, "height": height},
        image_bytes=png_bytes,
    )


def _tiff_to_png(raw: bytes) -> tuple[bytes, int, int] | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(BytesIO(raw)) as image:
            normalized = image.convert("RGBA")
            width, height = normalized.size
            buffer = BytesIO()
            normalized.save(buffer, format="PNG")
            return buffer.getvalue(), int(width), int(height)
    except Exception:
        return None


def _tiff_data_to_png_bytes(raw: bytes) -> bytes:
    converted = _tiff_to_png(raw)
    if converted is None:
        return b""
    return converted[0]


def _png_dimensions(png_bytes: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(BytesIO(png_bytes)) as image:
            width, height = image.size
            return int(width), int(height)
    except Exception:
        return None


def _compact_preview(text: str, limit: int = 160) -> str:
    preview = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(preview) > limit:
        return preview[: limit - 3] + "..."
    return preview


def _draft_signature(draft: ClipboardItemDraft | None) -> str:
    if draft is None:
        return ""
    if draft.item_type == "files":
        paths = draft.metadata.get("paths", [])
        if isinstance(paths, list):
            return "files:" + "|".join(str(path) for path in paths)
    if draft.item_type == "image":
        return f"image:{len(draft.image_bytes or b'')}:{hash(draft.image_bytes or b'')}"
    return f"text:{draft.content}"
