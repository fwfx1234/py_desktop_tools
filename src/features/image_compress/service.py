from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from PIL import Image


TEMP_OUTPUT_DIR = Path(tempfile.gettempdir()) / "py_desktop_tools_image_compress"


@dataclass(slots=True)
class CompressionEntry:
    id: str
    source: str
    file_name: str
    output: str = ""
    original_bytes: int = 0
    compressed_bytes: int = 0
    saved_ratio: float = 0.0
    state: str = "pending"  # pending | success | failed
    error: str = ""
    from_clipboard: bool = False

    @property
    def success(self) -> bool:
        return self.state == "success"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "fileName": self.file_name,
            "output": self.output,
            "originalBytes": self.original_bytes,
            "compressedBytes": self.compressed_bytes,
            "savedRatio": round(self.saved_ratio, 2),
            "state": self.state,
            "success": self.success,
            "error": self.error,
            "fromClipboard": self.from_clipboard,
        }


class ImageCompressService:
    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or TEMP_OUTPUT_DIR
        self._entries: dict[str, CompressionEntry] = {}
        self._order: list[str] = []
        self._pending_sources: dict[str, str] = {}
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def entries(self) -> list[CompressionEntry]:
        return [self._entries[eid] for eid in self._order if eid in self._entries]

    def get(self, entry_id: str) -> CompressionEntry | None:
        return self._entries.get(entry_id)

    def pending(self) -> list[CompressionEntry]:
        return [entry for entry in self.entries() if entry.state == "pending"]

    def pending_ids(self) -> list[str]:
        return [entry.id for entry in self.pending()]

    def clear(self) -> None:
        for entry in list(self._entries.values()):
            if entry.output:
                self._safe_unlink(Path(entry.output))
        self._entries.clear()
        self._order.clear()

    def remove(self, entry_id: str) -> None:
        entry = self._entries.pop(entry_id, None)
        if entry_id in self._order:
            self._order.remove(entry_id)
        if entry and entry.output:
            self._safe_unlink(Path(entry.output))

    def add_pending(self, file_urls, *, from_clipboard: bool) -> list[CompressionEntry]:
        added: list[CompressionEntry] = []
        for raw in file_urls or []:
            cleaned = _normalize_path(str(raw))
            if not cleaned:
                continue
            src = Path(cleaned)
            entry = CompressionEntry(
                id=uuid4().hex,
                source="" if from_clipboard else cleaned,
                file_name="(剪贴板)" if from_clipboard else (src.name or cleaned),
                from_clipboard=from_clipboard,
                state="pending",
            )
            try:
                if src.exists():
                    entry.original_bytes = src.stat().st_size
                else:
                    entry.state = "failed"
                    entry.error = "文件不存在"
            except OSError as exc:
                entry.state = "failed"
                entry.error = f"读取失败: {exc}"
            # store both compressed source and live source for actual compress later
            entry_metadata_source = cleaned
            self._entries[entry.id] = entry
            self._pending_sources[entry.id] = entry_metadata_source
            self._order.append(entry.id)
            added.append(entry)
        return added

    def compress_pending(self, quality: int, mode: str) -> list[CompressionEntry]:
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            for entry in self.pending():
                entry.state = "failed"
                entry.error = f"无法创建输出目录: {exc}"
            return [self._entries[eid] for eid in self._order]

        for entry in self.pending():
            raw_source = self._pending_sources.get(entry.id) or entry.source
            self._compress_into(entry, raw_source, quality, mode)
        return [self._entries[eid] for eid in self._order]

    def retry(self, entry_id: str, quality: int, mode: str) -> CompressionEntry | None:
        entry = self._entries.get(entry_id)
        if entry is None:
            return None
        if entry.output:
            self._safe_unlink(Path(entry.output))
            entry.output = ""
        entry.state = "pending"
        entry.error = ""
        entry.compressed_bytes = 0
        entry.saved_ratio = 0.0
        raw_source = self._pending_sources.get(entry.id) or entry.source
        self._compress_into(entry, raw_source, quality, mode)
        return entry

    def compress(
        self,
        file_urls,
        quality: int,
        mode: str,
        *,
        from_clipboard: bool = False,
    ) -> list[CompressionEntry]:
        added = self.add_pending(file_urls, from_clipboard=from_clipboard)
        # Compress only the newly added ones, not previously pending entries.
        for entry in added:
            if entry.state != "pending":
                continue
            raw_source = self._pending_sources.get(entry.id) or entry.source
            self._compress_into(entry, raw_source, quality, mode)
        return added

    def save_as(self, entry_id: str, target_path: str) -> tuple[bool, str]:
        entry = self._entries.get(entry_id)
        if entry is None or entry.state != "success" or not entry.output:
            return False, "无可保存内容"
        target = Path(_normalize_path(target_path))
        if not target.suffix:
            target = target.with_suffix(Path(entry.output).suffix)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry.output, target)
        except Exception as exc:
            return False, f"保存失败: {exc}"
        return True, str(target)

    def overwrite_original(self, entry_id: str) -> tuple[bool, str]:
        entry = self._entries.get(entry_id)
        if entry is None or entry.state != "success" or not entry.output:
            return False, "无可保存内容"
        if entry.from_clipboard or not entry.source:
            return False, "剪贴板图片没有源文件，无法覆盖"
        source = Path(entry.source)
        if not source.exists():
            return False, "源文件不存在"
        try:
            shutil.copyfile(entry.output, source)
        except Exception as exc:
            return False, f"写回失败: {exc}"
        try:
            entry.original_bytes = source.stat().st_size
            entry.saved_ratio = 0.0
            entry.compressed_bytes = entry.original_bytes
        except OSError:
            pass
        return True, str(source)

    def _compress_into(self, entry: CompressionEntry, raw_source: str, quality: int, mode: str) -> None:
        src_path = Path(raw_source) if raw_source else None
        if src_path is None or not src_path.exists():
            entry.state = "failed"
            entry.error = "文件不存在"
            return
        if entry.original_bytes <= 0:
            try:
                entry.original_bytes = src_path.stat().st_size
            except OSError as exc:
                entry.state = "failed"
                entry.error = f"读取失败: {exc}"
                return
        try:
            ext = src_path.suffix.lower()
            output_suffix = ".jpg" if mode != "visual" and ext not in {".png", ".webp"} else (ext or ".jpg")
            target = self._output_dir / f"{src_path.stem or 'clip'}_{entry.id[:6]}{output_suffix}"
            with Image.open(src_path) as img:
                if mode == "visual":
                    self._save_visual(img, target, ext)
                else:
                    self._save_normal(img, target, ext, quality)
            entry.output = str(target)
            entry.compressed_bytes = target.stat().st_size
            entry.state = "success"
            entry.error = ""
            if entry.original_bytes > 0:
                entry.saved_ratio = (1 - entry.compressed_bytes / entry.original_bytes) * 100
        except Exception as exc:
            entry.state = "failed"
            entry.error = f"压缩失败: {exc}"

    @staticmethod
    def _save_visual(img: Image.Image, target: Path, ext: str) -> None:
        if ext in (".png", ".gif", ".bmp"):
            quantized = img.quantize(colors=256)
            quantized.save(target, format="PNG", optimize=True)
        elif ext == ".webp":
            img.save(target, format="WEBP", quality=90)
        else:
            img.save(target, format="JPEG", quality=90)

    @staticmethod
    def _save_normal(img: Image.Image, target: Path, ext: str, quality: int) -> None:
        if ext in (".jpg", ".jpeg"):
            img.save(target, format="JPEG", quality=quality)
        elif ext == ".png":
            level = int((1 - quality / 100) * 9)
            img.save(target, format="PNG", compress_level=level)
        elif ext == ".webp":
            img.save(target, format="WEBP", quality=quality)
        else:
            img.save(target, format="JPEG", quality=quality)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def _normalize_path(value: str) -> str:
    path_text = value.strip().strip("\"'")
    if path_text.startswith("file://"):
        from urllib.parse import unquote, urlparse

        parsed = urlparse(path_text)
        path_text = unquote(parsed.path)
        if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
    return path_text
