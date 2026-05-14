from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class AppViewModel(QObject):
    """Global application state exposed to QML (theme, settings, etc.)."""

    themeChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._theme = "light"

    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        return self._theme

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value == self._theme:
            return
        self._theme = value
        self.themeChanged.emit()
