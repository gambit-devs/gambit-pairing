import os
import importlib
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from importlib_resources import as_file, files
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER
from gambitpairing.constants import RESULT_BLACK_WIN, RESULT_DRAW, RESULT_WHITE_WIN
from gambitpairing.gui.dialogs.about_dialog import AboutDialog
from gambitpairing.gui.dialogs.new_tournament_dialog import NewTournamentDialog
from gambitpairing.gui.dialogs.print_options_dialog import PrintOptionsDialog
from gambitpairing.gui.dialogs.tournament_settings_dialoug import SettingsDialog
from gambitpairing.gui.dialogs.update_dialog import UpdateDownloadDialog
from gambitpairing.gui.dialogs.update_prompt_dialog import UpdatePromptDialog
from gambitpairing.gui.widgets.header import TabHeader
from gambitpairing.gui.widgets.pairings_table import PairingsTable
from gambitpairing.gui.widgets.player_placeholder import PlayerPlaceholder
from gambitpairing.gui.widgets.pre_tournament_start import PreTournamentStart
from gambitpairing.gui.widgets.result_selector import ResultSelector
from gambitpairing.gui.widgets.round_progress_indicator import RoundProgressIndicator
from gambitpairing.gui.widgets.round_controls import RoundControlsWidget
from gambitpairing.gui.widgets.tournament_placeholder import TournamentPlaceholder
from gambitpairing.models import Player
from gambitpairing.models.enums import TournamentPhase

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


def test_designer_backed_placeholder_widgets_preserve_api_and_signals():
    _app()

    player_placeholder = PlayerPlaceholder()
    player_signals = {"import": 0, "add": 0}
    player_placeholder.import_players_requested.connect(
        lambda: player_signals.__setitem__("import", player_signals["import"] + 1)
    )
    player_placeholder.add_player_requested.connect(
        lambda: player_signals.__setitem__("add", player_signals["add"] + 1)
    )

    assert player_placeholder.title_label.text() == "No Players Added"
    assert (
        player_placeholder.desc_label.text()
        == "Add players to your tournament to get started."
    )
    assert player_placeholder.import_btn.text() == "Import Players"
    assert player_placeholder.add_btn.text() == "Add Player"

    player_placeholder.import_btn.click()
    player_placeholder.add_btn.click()
    assert player_signals == {"import": 1, "add": 1}

    default_tournament_placeholder = TournamentPlaceholder()
    assert (
        default_tournament_placeholder.desc_label.text()
        == "Create a tournament to begin managing your chess competition."
    )

    tournament_placeholder = TournamentPlaceholder(tab_name="Standings")
    tournament_signals = {"create": 0, "import": 0}
    tournament_placeholder.create_tournament_requested.connect(
        lambda: tournament_signals.__setitem__(
            "create", tournament_signals["create"] + 1
        )
    )
    tournament_placeholder.import_tournament_requested.connect(
        lambda: tournament_signals.__setitem__(
            "import", tournament_signals["import"] + 1
        )
    )

    assert tournament_placeholder.title_label.text() == "No Tournament Loaded"
    assert (
        tournament_placeholder.desc_label.text()
        == "The Standings tab will be available once you create a tournament."
    )
    assert tournament_placeholder.create_btn.text() == "Create Tournament"
    assert tournament_placeholder.import_btn.text() == "Import Tournament"

    tournament_placeholder.create_btn.click()
    tournament_placeholder.import_btn.click()
    assert tournament_signals == {"create": 1, "import": 1}

    player_placeholder.close()
    default_tournament_placeholder.close()
    tournament_placeholder.close()


def test_designer_backed_tab_header_preserves_actions_and_title_api():
    _app()

    header = TabHeader("Players")
    calls = {"refresh": 0}
    button = header.add_action_button(
        "refresh.svg",
        "Refresh",
        lambda: calls.__setitem__("refresh", calls["refresh"] + 1),
    )

    assert header.title_label.text() == "Players"
    assert header.icon_label.isHidden()
    assert button.toolTip() == "Refresh"

    button.click()
    assert calls == {"refresh": 1}

    header.set_title("Updated")
    assert header.title_label.text() == "Updated"

    icon_header = TabHeader("Rounds", "play.svg")
    assert not icon_header.icon_label.isHidden()

    header.close()
    icon_header.close()


def test_designer_backed_round_controls_preserve_state_api_and_signals():
    _app()

    controls = RoundControlsWidget()
    signals = {"start": 0, "prepare": 0, "record": 0, "undo": 0}
    controls.start_requested.connect(
        lambda: signals.__setitem__("start", signals["start"] + 1)
    )
    controls.prepare_requested.connect(
        lambda: signals.__setitem__("prepare", signals["prepare"] + 1)
    )
    controls.record_requested.connect(
        lambda: signals.__setitem__("record", signals["record"] + 1)
    )
    controls.undo_requested.connect(
        lambda: signals.__setitem__("undo", signals["undo"] + 1)
    )

    controls.update_state("start")
    assert controls.btn_primary_action.text() == "Start Tournament"
    controls.btn_primary_action.click()

    controls.update_state("prepare")
    assert controls.btn_primary_action.text() == "Prepare Next Round"
    controls.btn_primary_action.click()

    controls.update_state("record")
    assert controls.btn_primary_action.text() == "Record Results"
    controls.btn_primary_action.click()

    controls.set_undo_enabled(False)
    assert not controls.btn_undo.isEnabled()
    controls.set_undo_enabled(True)
    controls.set_undo_visible(False)
    assert controls.btn_undo.isHidden()
    controls.set_undo_visible(True)
    controls.btn_undo.click()

    controls.update_state("finished")
    assert controls.btn_primary_action.text() == "Tournament Finished"
    assert not controls.btn_primary_action.isEnabled()
    assert signals == {"start": 1, "prepare": 1, "record": 1, "undo": 1}

    controls.close()


def test_designer_backed_pre_tournament_start_preserves_signal_and_runtime_text():
    _app()

    widget = PreTournamentStart()
    signals = {"start": 0}
    widget.start_requested.connect(
        lambda: signals.__setitem__("start", signals["start"] + 1)
    )

    assert widget.title_label.text() == "Ready to Start"
    assert "generate the first round pairings" in widget.desc_label.text()
    assert widget.btn_start.text() == "Start Tournament"

    widget.btn_start.click()
    assert signals == {"start": 1}

    widget.close()


def test_designer_backed_result_selector_preserves_selection_api():
    _app()

    selector = ResultSelector()

    assert selector.selectedResult() == ""
    assert selector.btn_white_win.text() == "1-0"
    assert selector.btn_draw.text() == "½-½"
    assert selector.btn_black_win.text() == "0-1"

    selector.setResult(RESULT_WHITE_WIN)
    assert selector.selectedResult() == RESULT_WHITE_WIN

    selector.setResult(RESULT_DRAW)
    assert selector.selectedResult() == RESULT_DRAW

    selector.btn_black_win.click()
    assert selector.selectedResult() == RESULT_BLACK_WIN

    selector.setResult("unknown")
    assert selector.selectedResult() == ""

    selector.close()


def test_designer_backed_pairings_table_preserves_public_api_and_results():
    _app()

    white = Player("Ada", rating=2100)
    black = Player("Bert", rating=2000)
    bye_player = Player("Cora", rating=1900)
    table = PairingsTable()

    table.display_pairings([(white, black)], [bye_player], current_round_index=0)

    assert table.rowCount() == 1
    board_item = table.item(0, 0)
    white_item = table.item(0, 1)
    black_item = table.item(0, 2)
    assert board_item is not None
    assert white_item is not None
    assert black_item is not None
    assert board_item.text() == "1"
    assert white_item.text() == "Ada (2100)"
    assert black_item.text() == "Bert (2000)"
    model = table.table.model()
    assert model is not None
    cell_center = table.table.visualRect(model.index(0, 0)).center()
    assert table.itemAt(cell_center) is not None
    assert table.viewport() is table.table.viewport()
    assert not table.bye_container.isHidden()
    assert "Cora" in table.lbl_bye.text()

    result_selector = table.cellWidget(0, 3)
    assert isinstance(result_selector, ResultSelector)
    assert table.get_results() == ([], False)

    result_selector.setResult(RESULT_WHITE_WIN)
    assert table.get_results() == ([(white.id, black.id, 1.0)], True)

    table.reset_display()
    assert table.rowCount() == 0
    assert table.bye_container.isHidden()

    table.close()


def test_designer_backed_round_progress_indicator_keeps_dynamic_dots():
    _app()

    indicator = RoundProgressIndicator()
    indicator.update_progress(2, 4, TournamentPhase.AWAITING_RESULTS)

    assert indicator.progress_label.text() == "Round 2 of 4"
    assert len(indicator._dots) == 4
    assert indicator._dots[0].property("state") == "completed"
    assert indicator._dots[1].property("state") == "active"
    assert indicator._dots[2].property("state") == "pending"

    indicator.update_progress(4, 4, TournamentPhase.FINISHED)
    assert indicator.progress_label.text() == "Tournament Complete (4 rounds)"

    indicator.close()
