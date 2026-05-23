from __future__ import annotations

import hashlib
import re
import tempfile
from datetime import datetime
from pathlib import Path


DEFAULT_AUTO_SAVE_DIR = Path.home() / "Downloads" / "PyDesktopTools" / "QR"


class QrService:
    def __init__(self, save_root: Path | None = None) -> None:
        self._history: list[dict] = []
        self._save_root = save_root or DEFAULT_AUTO_SAVE_DIR

    @property
    def save_root(self) -> Path:
        return self._save_root

    def preview(self, content: str) -> str:
        if not content.strip():
            return ""
        image = self._render(content)
        temp = Path(tempfile.gettempdir()) / "py_desktop_tools_qr_preview.png"
        image.save(temp)
        return temp.as_posix()

    def save(self, content: str) -> tuple[str, str]:
        if not content.strip():
            return "", "请输入要生成二维码的内容"
        try:
            self._save_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return "", f"无法创建输出目录: {exc}"
        image = self._render(content)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
        filename = f"qr_{ts}_{digest}.png"
        target = self._unique_path(self._save_root / filename)
        try:
            image.save(target)
        except Exception as exc:
            return "", f"保存失败: {exc}"
        self._push_history("保存", content, str(target))
        return target.as_posix(), ""

    def record_copy(self, content: str) -> None:
        if not content.strip():
            return
        self._push_history("复制", content, "")

    def scan(self, image_path: str) -> tuple[str, str]:
        try:
            import zxingcpp
            from PIL import Image
        except Exception:
            return "", "扫码依赖未安装，请安装 zxing-cpp 与 Pillow。"
        try:
            with Image.open(image_path) as img:
                results = zxingcpp.read_barcodes(img)
        except FileNotFoundError:
            return "", "无法读取图片"
        except Exception as exc:
            return "", f"无法读取图片: {exc}"
        if not results:
            return "", "未识别到二维码"
        data = results[0].text or ""
        if not data:
            return "", "二维码内容为空"
        self._push_history("扫描", data, image_path)
        return data, ""

    def get_history(self) -> list[dict]:
        return list(self._history)

    def clear_history(self) -> list[dict]:
        self._history = []
        return self._history

    def remove_history(self, item_id: str) -> list[dict]:
        self._history = [item for item in self._history if item.get("id") != item_id]
        return self._history

    def export(self, save_path: str | None = None) -> tuple[str, str]:
        if not self._history:
            return "", "暂无历史可导出"
        if save_path:
            target = Path(save_path)
        else:
            try:
                self._save_root.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                return "", f"无法创建输出目录: {exc}"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = self._save_root / f"qr_history_{ts}.txt"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            lines: list[str] = []
            for item in self._history:
                lines.append(f"[{item.get('type', '')}] {item.get('createdAt', '')}")
                lines.append(str(item.get("content", "")))
                if item.get("source"):
                    lines.append(f"来源: {item.get('source')}")
                lines.append("")
            target.write_text("\n".join(lines), encoding="utf-8")
        except Exception as exc:
            return "", f"导出失败: {exc}"
        return target.as_posix(), ""

    def _render(self, content: str):
        import qrcode
        qr = qrcode.QRCode(version=None, box_size=10, border=4)
        qr.add_data(content)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    def _push_history(self, record_type: str, content: str, source: str) -> None:
        record = {
            "id": hashlib.sha1(
                f"{record_type}|{datetime.now().isoformat()}|{content}".encode("utf-8")
            ).hexdigest()[:12],
            "type": record_type,
            "content": content,
            "source": source,
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._history = [record] + self._history[:200]

    @staticmethod
    def _unique_path(target: Path) -> Path:
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1


def normalize_local_path(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw
    if cleaned.startswith("file://"):
        cleaned = re.sub(r"^file:/+", "/", cleaned)
    return cleaned
