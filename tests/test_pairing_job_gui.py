import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtCore, QtWidgets

from gambitpairing.controllers.tournament.session import TournamentSession
from gambitpairing.gui.pairing_job import generate_with_progress
from gambitpairing.models.player import Player


def test_pairing_process_keeps_qt_event_loop_responsive():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    parent = QtWidgets.QWidget()
    tournament = TournamentSession(
        "Process",
        [Player(str(i), 1800) for i in range(8)],
        3,
        use_experimental_dutch=True,
    )
    ticks = []
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(5)
    try:
        result = generate_with_progress(parent, tournament.to_dict(), 0)
        assert not result.get("error"), result
        assert len(result["document"]["rounds"]) == 1
        assert ticks
        assert tournament.rounds == []
    finally:
        timer.stop()
        parent.close()


def test_cancel_pairing_process_leaves_tournament_unchanged():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    parent = QtWidgets.QWidget()
    tournament = TournamentSession(
        "Cancel",
        [Player(str(i), 1800) for i in range(8)],
        3,
        use_experimental_dutch=True,
    )
    expected = tournament.to_dict()

    def cancel():
        for widget in app.topLevelWidgets():
            if isinstance(widget, QtWidgets.QProgressDialog):
                widget.reject()

    QtCore.QTimer.singleShot(0, cancel)
    result = generate_with_progress(parent, expected, 0)
    assert result.get("cancelled")
    assert tournament.to_dict() == expected
    parent.close()
