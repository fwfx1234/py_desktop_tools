from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


PlatformName = Literal["windows", "macos", "unknown"]
DisplayId = str


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    name: PlatformName
    display_name: str
    version: str = ""
    is_packaged: bool = False


@dataclass(frozen=True, slots=True)
class PlatformResult:
    ok: bool
    message: str = ""
    code: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileDialogFilter:
    name: str
    patterns: list[str] = field(default_factory=list)

    def to_qt_filter(self) -> str:
        pattern_text = " ".join(self.patterns) if self.patterns else "*"
        return f"{self.name} ({pattern_text})"


@dataclass(frozen=True, slots=True)
class FileDialogOptions:
    title: str = ""
    directory: str = ""
    filters: list[FileDialogFilter] = field(default_factory=list)
    default_name: str = ""


@dataclass(frozen=True, slots=True)
class DisplayInfo:
    id: DisplayId
    name: str
    x: int
    y: int
    width: int
    height: int
    available_x: int
    available_y: int
    available_width: int
    available_height: int
    scale_factor: float = 1.0
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class CursorPosition:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class AppEntry:
    platform: PlatformName
    name: str
    launch_path: str
    bundle_id: str = ""
    icon_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self) -> dict:
        return {
            "platform": self.platform,
            "name": self.name,
            "launch_path": self.launch_path,
            "bundle_id": self.bundle_id,
            "icon_path": self.icon_path,
        }


@dataclass(frozen=True, slots=True)
class SystemCommand:
    id: str
    name: str
    description: str
    icon: str
    action: str
    keywords: list[str]

    def to_item_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "action": self.action,
            "keywords": self.keywords,
        }
