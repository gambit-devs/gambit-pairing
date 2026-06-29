"""Runtime helpers for loading Qt Designer ``.ui`` files."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from PyQt6 import uic
from importlib_resources import as_file, files


UI_PACKAGE = "gambitpairing.ui"


@contextmanager
def ui_file_path(ui_name: str) -> Iterator[Path]:
    """Yield a filesystem path for a packaged Designer file."""
    resource = files(UI_PACKAGE).joinpath(ui_name)
    with as_file(resource) as path:
        yield Path(path)


def load_ui_into(widget: object, ui_name: str) -> object:
    """Load a packaged Designer file into an existing widget instance."""
    with ui_file_path(ui_name) as path:
        return uic.loadUi(str(path), widget)
