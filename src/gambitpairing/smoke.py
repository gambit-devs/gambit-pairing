"""Small installed/frozen artifact check; no external services required."""

from pathlib import Path
import tempfile

from gambitpairing.controllers.tournament.session import TournamentSession
from gambitpairing.models.player import Player
from gambitpairing.representation import (
    load_tournament_document,
    save_tournament_document,
)


def check_tournament_round_trip():
    session = TournamentSession(
        "Smoke",
        [Player("Ada", 1800), Player("Ben", 1700)],
        1,
        use_experimental_dutch=True,
    )
    session.create_pairings(1)
    assert session.record_results(
        0, [(w, b, 1.0) for w, b in session.rounds[0].pairings]
    )
    with tempfile.TemporaryDirectory(prefix="gambit-smoke-") as directory:
        path = Path(directory) / "tournament.json"
        save_tournament_document(path, session)
        restored, _ = load_tournament_document(path)
        assert restored.get_completed_rounds() == 1
        assert sum(player.score for player in restored.players.values()) == 1.0
