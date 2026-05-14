from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from .models import FileDialogOptions


class QtDialogApi:
    def open_file(self, options: FileDialogOptions | None = None) -> Path | None:
        opts = options or FileDialogOptions()
        path, _ = QFileDialog.getOpenFileName(
            None,
            opts.title,
            opts.directory,
            _qt_filters(opts),
        )
        return Path(path) if path else None

    def open_files(self, options: FileDialogOptions | None = None) -> list[Path]:
        opts = options or FileDialogOptions()
        paths, _ = QFileDialog.getOpenFileNames(
            None,
            opts.title,
            opts.directory,
            _qt_filters(opts),
        )
        return [Path(path) for path in paths if path]

    def open_directory(self, options: FileDialogOptions | None = None) -> Path | None:
        opts = options or FileDialogOptions()
        path = QFileDialog.getExistingDirectory(
            None,
            opts.title,
            opts.directory,
        )
        return Path(path) if path else None

    def save_file(self, options: FileDialogOptions | None = None) -> Path | None:
        opts = options or FileDialogOptions()
        start_path = str(Path(opts.directory) / opts.default_name) if opts.default_name else opts.directory
        path, _ = QFileDialog.getSaveFileName(
            None,
            opts.title,
            start_path,
            _qt_filters(opts),
        )
        return Path(path) if path else None


def _qt_filters(options: FileDialogOptions) -> str:
    if not options.filters:
        return ""
    return ";;".join(item.to_qt_filter() for item in options.filters)
