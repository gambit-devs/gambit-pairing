import os
import importlib
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from importlib_resources import as_file, files
from PyQt6 import QtWidgets

from gambitpairing.gui.dialogs.print_options_dialog import PrintOptionsDialog
from gambitpairing.gui.dialogs.update_dialog import UpdateDownloadDialog

_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def test_packaged_ui_files_are_parseable():
    ui_files = [
        resource
        for resource in files("gambitpairing.ui").iterdir()
        if resource.name.endswith(".ui")
    ]

    assert ui_files
    load_ui_type = cast(Any, importlib.import_module("PyQt6.uic")).loadUiType
    for resource in ui_files:
        with as_file(resource) as path:
            form_class, base_class = load_ui_type(str(path))
            assert form_class is not None, resource.name
            assert base_class is not None, resource.name


def test_designer_backed_dialogs_wire_expected_controls():
    _app()

    print_dialog = PrintOptionsDialog(
        has_pairings=True,
        has_standings=True,
        round_info="Round 2 pairings ready",
        default_pairings=True,
        default_standings=True,
    )
    assert print_dialog.round_info_label.text() == "Round 2 pairings ready"
    assert not print_dialog.chk_page_break.isHidden()
    assert print_dialog.btn_print.isEnabled()

    update_dialog = UpdateDownloadDialog()
    update_dialog.update_progress(45)
    update_dialog.update_status("Downloading...")

    assert update_dialog.progress_bar.value() == 45
    assert update_dialog.status_label.text() == "Downloading..."

    print_dialog.close()
    update_dialog.close()
