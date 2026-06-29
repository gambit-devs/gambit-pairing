"""Runtime helpers for loading Qt Designer ``.ui`` files."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TypeVar

from PyQt6 import QtCore, uic
from importlib_resources import as_file, files


UI_PACKAGE = "gambitpairing.ui"
T = TypeVar("T", bound=QtCore.QObject)


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


def required_child(parent: QtCore.QObject, child_type: type[T], name: str) -> T:
    """Return a named Designer child or fail with a useful wiring error."""
    child = parent.findChild(child_type, name)
    if child is None:
        raise RuntimeError(
            f"Designer UI is missing required {child_type.__name__!s}: {name}"
        )
    return child
