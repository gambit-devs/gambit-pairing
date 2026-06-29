import os
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from gambitpairing.gui.mainwindow import GambitPairingMainWindow
from gambitpairing.gui.views.players.players_view import PlayersView
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import Tournament

_APP: QtWidgets.QApplication | None = None


class _Parent(QtWidgets.QWidget):
    def prompt_new_tournament(self) -> None:
        pass

    def load_tournament(self) -> None:
        pass


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def test_players_view_shows_player_actions_after_empty_tournament_created():
    _app()
    parent = _Parent()
    view = PlayersView(parent)

    view.set_tournament(Tournament("City Open", [], 5))

    assert view.tournament_placeholder.isHidden()
    assert not view.players_placeholder.isHidden()
    assert view.table_players.isHidden()
    assert view.player_group.isHidden()

    view.close()
    parent.close()


def test_players_view_shows_table_after_players_are_added():
    _app()
    parent = _Parent()
    view = PlayersView(parent)
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)

    view.set_tournament(tournament)

    assert view.tournament_placeholder.isHidden()
    assert view.players_placeholder.isHidden()
    assert not view.player_group.isHidden()
    assert not view.table_players.isHidden()
    assert view.table_players.rowCount() == 1

    view.close()
    parent.close()


def test_main_window_propagates_new_tournament_to_players_view():
    _app()
    window = GambitPairingMainWindow()

    window.tournament = Tournament("City Open", [], 5)
    window._set_tournament_on_tabs()

    assert window.stacked_widget.currentWidget() is window.tabs
    assert window.players_tab.tournament is window.tournament
    assert window.players_tab.tournament_placeholder.isHidden()
    assert not window.players_tab.players_placeholder.isHidden()

    window.close()
