import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.views.tournament.tournament_printing import (
    PairingsPrintRow,
    build_combined_tournament_print_html,
    build_page_separator,
    build_pairings_print_section,
    build_standings_print_section,
)
from gambitpairing.utils.print import TournamentPrintUtils


_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = app
    return _APP


def test_pairings_print_section_includes_rows_and_bye():
    html = build_pairings_print_section(
        "Club Championship",
        "Round 2 Pairings",
        [PairingsPrintRow(1, "Ada", "Bert")],
        "Cora receives 1.0 point",
    )

    assert "Pairings - Club Championship" in html
    assert "Round 2 Pairings" in html
    assert "<td>1</td><td>Ada</td><td>Bert</td>" in html
    assert "Cora receives 1.0 point" in html


def test_pairings_print_section_is_empty_without_rows():
    assert build_pairings_print_section("", "", [], "") == ""


def test_standings_print_section_uses_separator_and_round_context():
    html = build_standings_print_section(
        "Club Championship",
        3,
        "<table class=\"standings\"></table>",
        build_page_separator(separate_pages=True),
    )

    assert "page-break-before" in html
    assert "Standings - Club Championship" in html
    assert "After Round 3" in html
    assert "standings" in html


def test_standings_print_section_is_empty_without_standings_html():
    assert build_standings_print_section("Event", 1, "", "<hr>") == ""


def test_combined_tournament_print_html_wraps_sections_and_timestamp():
    html = build_combined_tournament_print_html(
        "<table class=\"pairings\"></table>",
        "<table class=\"standings\"></table>",
        "2026-06-29 21:30",
    )

    assert "<html>" in html
    assert "pairings" in html
    assert "standings" in html
    assert "Printed by Gambit Pairing" in html
    assert "2026-06-29 21:30" in html


def test_print_preview_toolbar_is_locked_in_place():
    _app()

    _printer, preview = TournamentPrintUtils.create_print_preview_dialog(
        None, "Print Preview - Test"
    )
    toolbar = preview.findChild(QtWidgets.QToolBar)

    assert toolbar is not None
    assert not toolbar.isMovable()
    assert not toolbar.isFloatable()
    assert toolbar.allowedAreas() == Qt.ToolBarArea.TopToolBarArea
    assert toolbar.contextMenuPolicy() == Qt.ContextMenuPolicy.NoContextMenu

    preview.close()
