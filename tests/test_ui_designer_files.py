import os
import importlib
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from importlib_resources import as_file, files
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER
from gambitpairing.gui.dialogs.about_dialog import AboutDialog
from gambitpairing.gui.dialogs.new_tournament_dialog import NewTournamentDialog
from gambitpairing.gui.dialogs.print_options_dialog import PrintOptionsDialog
from gambitpairing.gui.dialogs.tournament_settings_dialoug import SettingsDialog
from gambitpairing.gui.dialogs.update_dialog import UpdateDownloadDialog
from gambitpairing.gui.dialogs.update_prompt_dialog import UpdatePromptDialog

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

    settings_dialog = SettingsDialog(5, ["solkoff", "median"])
    settings_dialog.configure_round_count_controls("round_robin", False)
    assert settings_dialog.spin_num_rounds.isHidden()
    assert settings_dialog.rounds_label.isHidden()

    settings_dialog.configure_round_count_controls("dutch_swiss", True)
    assert not settings_dialog.spin_num_rounds.isHidden()
    assert not settings_dialog.spin_num_rounds.isEnabled()

    update_prompt = UpdatePromptDialog("2.0.0", "1.0.0", "## Changes")
    assert "Gambit Pairing" in update_prompt.title_label.text()
    assert "2.0.0" in update_prompt.version_info_label.text()

    new_tournament = NewTournamentDialog()
    assert new_tournament.get_data() == (
        "My Swiss Tournament",
        5,
        list(DEFAULT_TIEBREAK_SORT_ORDER),
        "dutch_swiss",
    )

    new_tournament.tiebreak_list.setCurrentRow(1)
    moved_item = new_tournament.tiebreak_list.item(1)
    assert moved_item is not None
    moved_tiebreak = moved_item.data(Qt.ItemDataRole.UserRole)
    new_tournament.move_tiebreak_up()
    new_tournament.update_order_from_list()
    assert new_tournament.current_tiebreak_order[0] == moved_tiebreak

    new_tournament.pairing_combo.setCurrentIndex(
        new_tournament.pairing_combo.findData("round_robin")
    )
    new_tournament.set_player_count(8)
    assert new_tournament.rounds_spin.value() == 7
    assert new_tournament.rounds_spin.isHidden()
    assert new_tournament.rounds_label.isHidden()

    about_dialog = AboutDialog()
    assert about_dialog.windowTitle() == "About Gambit Pairing"
    assert about_dialog.tab_widget.count() == 2
    assert about_dialog.app_name_label.text() == "Gambit Pairing"
    assert "Gambit Pairing" in about_dialog.version_label.text()
    assert about_dialog.support_label.openExternalLinks()
    assert "GNU General Public License" in about_dialog.license_text.toPlainText()
    assert about_dialog.close_button.text() == "Close"

    print_dialog.close()
    update_dialog.close()
    settings_dialog.close()
    update_prompt.close()
    new_tournament.close()
    about_dialog.close()
