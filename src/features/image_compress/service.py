from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from PIL import Image


class ImageCompressService:
    def compress_images(self, file_urls, quality: int, mode: str) -> str:
        total_original = 0
        total_compressed = 0
        count = 0
        output_dir = Path(tempfile.gettempdir()) / "py_desktop_tools_images"
        output_dir.mkdir(parents=True, exist_ok=True)
        for raw in file_urls:
            path = str(raw).replace("file:///", "")
            if not path:
                continue
            src = Path(path)
            if not src.exists():
                continue
            count += 1
            total_original += src.stat().st_size
            with Image.open(src) as img:
                # 使用唯一文件名避免同文件名冲突
                suffix = ".jpg" if mode != "visual" else src.suffix.lower()
                temp = output_dir / f"compressed_{src.stem}_{uuid4().hex[:6]}{suffix}"
                ext = src.suffix.lower()
                if mode == "visual":
                    if ext in (".png", ".gif", ".bmp"):
                        q = img.quantize(colors=256)
                        q.save(temp, format="PNG", optimize=True)
                    elif ext == ".webp":
                        img.save(temp, format="WEBP", quality=90)
                    else:
                        img.save(temp, format="JPEG", quality=90)
                else:
                    if ext in (".jpg", ".jpeg"):
                        img.save(temp, format="JPEG", quality=quality)
                    elif ext == ".png":
                        level = int((1 - quality / 100) * 9)
                        img.save(temp, format="PNG", compress_level=level)
                    elif ext == ".webp":
                        img.save(temp, format="WEBP", quality=quality)
                    else:
                        img.save(temp, format="JPEG", quality=quality)
                total_compressed += temp.stat().st_size
        ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
        return (
            f"共 {count} 个文件\n"
            f"输出目录: {output_dir}\n"
            f"总大小 {total_original/1024:.1f} KB -> {total_compressed/1024:.1f} KB\n"
            f"压缩率 {ratio:.1f}%"
        )
