from __future__ import annotations

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication


class AppViewModel(QObject):
    """Global application state exposed to QML (theme, settings, etc.)."""

    themeChanged = Signal()
    themeModeChanged = Signal()
    platformChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._theme_mode = "light"
        self._resolved_theme = "light"
        self._platform_name = "unknown"
        self._platform_display_name = "Unknown"

        style_hints = QGuiApplication.styleHints()
        if style_hints is not None:
            try:
                style_hints.colorSchemeChanged.connect(self._on_system_color_scheme_changed)
            except (AttributeError, TypeError):
                pass

    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        return self._resolved_theme

    @Property(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @Property(str, notify=platformChanged)
    def platformName(self) -> str:
        return self._platform_name

    @Property(str, notify=platformChanged)
    def platformDisplayName(self) -> str:
        return self._platform_display_name

    @Property(bool, notify=platformChanged)
    def isMacos(self) -> bool:
        return self._platform_name == "macos"

    @Property(bool, notify=platformChanged)
    def isWindows(self) -> bool:
        return self._platform_name == "windows"

    @Slot(str)
    def setTheme(self, value: str) -> None:
        normalized = value if value in ("light", "dark", "auto") else "light"
        mode_changed = normalized != self._theme_mode
        self._theme_mode = normalized
        if mode_changed:
            self.themeModeChanged.emit()
        self._apply_resolved_theme()

    @Slot(str, str)
    def setPlatform(self, name: str, display_name: str) -> None:
        next_name = name or "unknown"
        next_display_name = display_name or next_name
        if next_name == self._platform_name and next_display_name == self._platform_display_name:
            return
        self._platform_name = next_name
        self._platform_display_name = next_display_name
        self.platformChanged.emit()

    def _apply_resolved_theme(self) -> None:
        if self._theme_mode == "auto":
            resolved = self._detect_system_theme()
        else:
            resolved = self._theme_mode
        if resolved == self._resolved_theme:
            return
        self._resolved_theme = resolved
        self.themeChanged.emit()

    def _detect_system_theme(self) -> str:
        style_hints = QGuiApplication.styleHints()
        if style_hints is None:
            return "light"
        try:
            return "dark" if style_hints.colorScheme() == Qt.ColorScheme.Dark else "light"
        except (AttributeError, TypeError):
            return "light"

    def _on_system_color_scheme_changed(self, _scheme) -> None:
        if self._theme_mode == "auto":
            self._apply_resolved_theme()
