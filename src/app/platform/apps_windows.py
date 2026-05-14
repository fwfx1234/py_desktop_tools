from __future__ import annotations

import ctypes
import hashlib
import os
import struct
from ctypes import wintypes
from pathlib import Path

from .models import AppEntry

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32


class WindowsAppIndexer:
    def scan_apps(self, icon_dir: Path | None = None) -> list[AppEntry]:
        if icon_dir is not None:
            icon_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        userprofile = os.environ.get("USERPROFILE", "")

        for base in [appdata, programdata]:
            if base:
                candidate = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                if candidate.is_dir():
                    paths.append(candidate)

        if userprofile:
            desktop = Path(userprofile) / "Desktop"
            if desktop.is_dir():
                paths.append(desktop)
            public_desktop = Path(programdata) / "Microsoft" / "Windows" / "Desktop"
            if public_desktop.is_dir():
                paths.append(public_desktop)

        seen_paths: set[str] = set()
        seen_names: set[str] = set()
        apps: list[AppEntry] = []
        for base in paths:
            for shortcut in base.rglob("*.lnk"):
                launch_path = str(shortcut)
                if launch_path in seen_paths:
                    continue
                name = shortcut.stem
                name_lower = name.lower()
                if "uninstall" in name_lower or "卸载" in name:
                    continue
                if name_lower in seen_names:
                    continue
                seen_paths.add(launch_path)
                seen_names.add(name_lower)
                icon_path = ""
                if icon_dir is not None:
                    icon_key = hashlib.md5(launch_path.encode()).hexdigest()[:12]
                    icon_path = _extract_icon(launch_path, icon_dir / f"{icon_key}.png")
                apps.append(
                    AppEntry(
                        platform="windows",
                        name=name,
                        launch_path=launch_path,
                        icon_path=icon_path,
                    )
                )
        return apps


def _extract_icon(lnk_path: str, out_path: Path) -> str:
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path)

    hicon = 0
    try:
        target = _resolve_lnk_target(lnk_path)
        if target and os.path.isfile(target):
            hicon = _extract_exe_icon(target)
        if not hicon:
            hicon = _sh_get_file_icon(lnk_path)
        if hicon:
            _hicon_to_png(hicon, str(out_path))
            user32.DestroyIcon(hicon)
            if out_path.exists() and out_path.stat().st_size > 0:
                return str(out_path)
    except Exception:
        if hicon:
            user32.DestroyIcon(hicon)
    return ""


def _sh_get_file_icon(path: str) -> int:
    shgfi_icon = 0x100
    shgfi_large_icon = 0x0

    class SHFILEINFOW(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HANDLE),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", ctypes.c_wchar * 260),
            ("szTypeName", ctypes.c_wchar * 80),
        ]

    info = SHFILEINFOW()
    result = shell32.SHGetFileInfoW(
        path,
        0,
        ctypes.byref(info),
        ctypes.sizeof(info),
        shgfi_icon | shgfi_large_icon,
    )
    return info.hIcon if result else 0


def _extract_exe_icon(exe_path: str) -> int:
    hicon = ctypes.c_void_p()
    result = shell32.ExtractIconExW(exe_path, 0, ctypes.byref(hicon), None, 1)
    return hicon.value if result > 0 and hicon.value else 0


def _resolve_lnk_target(lnk_path: str) -> str | None:
    try:
        with open(lnk_path, "rb") as file_obj:
            data = file_obj.read()

        if len(data) < 76 or data[:4] != b"L\x00\x00\x00":
            return None

        flags = struct.unpack_from("<I", data, 20)[0]
        if not (flags & 0x02):
            return None

        pos = 76
        if flags & 0x01:
            idl_size = struct.unpack_from("<H", data, pos)[0]
            pos += 2 + idl_size

        link_info_size = struct.unpack_from("<I", data, pos)[0]
        if link_info_size < 16:
            return None
        local_base_offset = struct.unpack_from("<I", data, pos + 16)[0]
        if local_base_offset <= 0 or local_base_offset >= link_info_size:
            return None

        path_pos = pos + local_base_offset
        end = data.find(b"\x00", path_pos)
        if end < 0:
            return None
        raw_path = data[path_pos:end]
        if len(raw_path) >= 2 and raw_path[1] == 0:
            target = raw_path.decode("utf-16-le")
        else:
            target = raw_path.decode("ascii", errors="ignore")
        return target if target and os.path.isfile(target) else None
    except Exception:
        return None


def _hicon_to_png(hicon: int, output_path: str) -> None:
    try:
        from PIL import Image

        size = 32
        hdc = user32.GetDC(0)

        def draw_on_background(rgb_bg: int) -> bytes:
            hdc_mem = gdi32.CreateCompatibleDC(hdc)
            hbm = gdi32.CreateCompatibleBitmap(hdc, size, size)
            old_bm = gdi32.SelectObject(hdc_mem, hbm)

            brush = gdi32.CreateSolidBrush(rgb_bg)
            rect = struct.pack("iiii", 0, 0, size, size)
            user32.FillRect(hdc_mem, rect, brush)
            gdi32.DeleteObject(brush)

            user32.DrawIconEx(hdc_mem, 0, 0, hicon, size, size, 0, 0, 0x0003)

            buffer = ctypes.create_string_buffer(size * size * 4)
            bmi = struct.pack("IiiHHIIiiII", 40, size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
            gdi32.GetDIBits(hdc_mem, hbm, 0, size, buffer, bmi, 0)

            gdi32.SelectObject(hdc_mem, old_bm)
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            return buffer.raw

        black_raw = draw_on_background(0x00000000)
        white_raw = draw_on_background(0x00FFFFFF)

        result = bytearray(size * size * 4)
        for index in range(0, len(result), 4):
            rb, gb, bb = black_raw[index], black_raw[index + 1], black_raw[index + 2]
            rw, gw, bw = white_raw[index], white_raw[index + 1], white_raw[index + 2]
            diff = max(abs(rw - rb), abs(gw - gb), abs(bw - bb))
            alpha = max(0, min(255, 255 - diff))
            result[index] = rb
            result[index + 1] = gb
            result[index + 2] = bb
            result[index + 3] = alpha

        image = Image.frombuffer("RGBA", (size, size), bytes(result), "raw", "BGRA", 0, 1)
        image.save(output_path, "PNG")
        user32.ReleaseDC(0, hdc)
    except Exception:
        pass
