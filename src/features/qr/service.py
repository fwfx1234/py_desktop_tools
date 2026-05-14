from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import qrcode

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None


class QrService:
    def __init__(self) -> None:
        self._history: list[dict] = []

    def generate(self, content: str) -> str:
        if not content.strip():
            return ""
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        temp = Path(tempfile.gettempdir()) / "py_desktop_tools_qr.png"
        img.save(temp)
        self._history = [self._make_record("生成", content)] + self._history[:200]
        return temp.as_posix()

    def scan(self, image_path: str) -> tuple[str, str]:
        if cv2 is None:
            return "", "未安装 OpenCV，无法扫码。请安装 opencv-python。"
        img = cv2.imread(image_path)
        if img is None:
            return "", "无法读取图片"
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if not data:
            return "", "未识别到二维码"
        self._history = [self._make_record("扫描", data)] + self._history[:200]
        return data, ""

    def get_history(self) -> list[dict]:
        return self._history

    def clear_history(self) -> list[dict]:
        self._history = []
        return self._history

    @staticmethod
    def _make_record(record_type: str, content: str) -> dict:
        return {
            "type": record_type,
            "content": content,
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
