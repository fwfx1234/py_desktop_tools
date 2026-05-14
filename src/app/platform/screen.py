from __future__ import annotations

from PySide6.QtGui import QCursor, QGuiApplication, QScreen

from .models import CursorPosition, DisplayInfo


class QtScreenApi:
    def primary_display(self) -> DisplayInfo | None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return _to_display_info(screen, is_primary=True)

    def all_displays(self) -> list[DisplayInfo]:
        primary = QGuiApplication.primaryScreen()
        displays: list[DisplayInfo] = []
        for screen in QGuiApplication.screens():
            displays.append(_to_display_info(screen, is_primary=screen is primary))
        return displays

    def cursor_position(self) -> CursorPosition:
        pos = QCursor.pos()
        return CursorPosition(x=pos.x(), y=pos.y())

    def display_at_cursor(self) -> DisplayInfo | None:
        pos = QCursor.pos()
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        primary = QGuiApplication.primaryScreen()
        return _to_display_info(screen, is_primary=screen is primary)


def _to_display_info(screen: QScreen, *, is_primary: bool) -> DisplayInfo:
    geometry = screen.geometry()
    available = screen.availableGeometry()
    return DisplayInfo(
        id=f"{screen.name()}:{geometry.x()}:{geometry.y()}:{geometry.width()}:{geometry.height()}",
        name=screen.name(),
        x=geometry.x(),
        y=geometry.y(),
        width=geometry.width(),
        height=geometry.height(),
        available_x=available.x(),
        available_y=available.y(),
        available_width=available.width(),
        available_height=available.height(),
        scale_factor=float(screen.devicePixelRatio()),
        is_primary=is_primary,
    )
