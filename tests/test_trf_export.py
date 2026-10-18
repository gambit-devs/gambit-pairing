from datetime import date
from pathlib import Path
import subprocess

import pytest

from gambitpairing.compatibility.bbp import parse_bbp_pairing_output
from gambitpairing.constants import OUTCOME_DOUBLE_FORFEIT, OUTCOME_FORFEIT_WIN
from gambitpairing.controllers.pairing.bbp_dutch import BBPPairingEngine
from gambitpairing.controllers.tournament.persistence import (
    TournamentPersistenceService,
)
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player
from gambitpairing.models.player.fide_player import FidePlayer
from gambitpairing.models.tournament import RoundData
from gambitpairing.representation import build_trf_document

BBP_ONLY_PREFIXES = ("XXC", "XXR", "240", "BBW", "BBD", "BBL", "BBZ", "BBF", "BBU")
FIXTURE = (
    Path(__file__).parents[1]
    / "test_data"
    / "tournaments"
    / "test_32_player_tournament.json"
)
BBP_EXECUTABLE = BBPPairingEngine.resolve_executable()


def _numbered(players):
    for number, player in enumerate(players, start=1):
        player.pairing_number = number
    return players


def _tournament(players, rounds=3):
    return Tournament("City Open", _numbered(players), rounds)


def _play(tournament, pairings, results, bye=None, scheduled=None, bye_type="full"):
    round_number = len(tournament.rounds) + 1
    tournament.rounds.append(
        RoundData(
            round_number=round_number,
            pairings=[(white.id, black.id) for white, black in pairings],
            bye_player_id=bye.id if bye else None,
            bye_type=bye_type,
            scheduled_byes={
                kind: [player.id for player in players]
                for kind, players in (scheduled or {}).items()
            },
        )
    )
    assert tournament.record_results(round_number - 1, results)


def _player_lines(document):
    return [line for line in document.splitlines() if line.startswith("001")]


def _eleven_player_event():
    players = [Player(f"Player {index:02d}", 2100 - 10 * index) for index in range(11)]
    tournament = _tournament(players)
    p = players
    _play(
        tournament,
        [(p[0], p[1]), (p[2], p[3]), (p[4], p[5]), (p[6], p[7])],
        [
            (p[0].id, p[1].id, 1.0),
            (p[2].id, p[3].id, 0.5),
            (p[4].id, p[5].id, 1.0, OUTCOME_FORFEIT_WIN),
            (p[6].id, p[7].id, 0.0, OUTCOME_DOUBLE_FORFEIT),
        ],
        bye=p[8],
        scheduled={"half_point": [p[9]], "zero_point": [p[10]]},
    )
    tournament.set_player_active(p[10].id, False)
    _play(
        tournament,
        [(p[0], p[2]), (p[3], p[1]), (p[4], p[6]), (p[5], p[7]), (p[8], p[9])],
        [
            (p[0].id, p[2].id, 0.0),
            (p[3].id, p[1].id, 0.0),
            (p[4].id, p[6].id, 0.0, OUTCOME_FORFEIT_WIN),
            (p[5].id, p[7].id, 1.0),
            (p[8].id, p[9].id, 0.5),
        ],
    )
    return tournament, players


def test_trf_header_has_name_counts_type_and_blank_unstored_fields():
    tournament, _players = _eleven_player_event()

    lines = build_trf_document(tournament).splitlines()

    assert lines[:13] == [
        "012 City Open",
        "022",
        "032",
        "042",
        "052",
        "062 11",
        "072 11",
        "082",
        "092 Individual: Swiss-System (Dutch)",
        "102",
        "112",
        "122",
        "132",
    ]


def test_trf_player_record_uses_fixed_trf16_columns():
    player = FidePlayer(
        "Polgar, Judit",
        rating=2735,
        gender="F",
        date_of_birth=date(1976, 7, 23),
        federation="HUN",
        fide_id=700070,
        fide_title="GM",
    )
    opponent = Player("Opponent", 1800)
    tournament = _tournament([player, opponent], rounds=1)
    _play(tournament, [(player, opponent)], [(player.id, opponent.id, 1.0)])

    line = _player_lines(build_trf_document(tournament))[0]

    assert line == (
        "001    1 w GM Polgar, Judit                     2735 HUN      700070 "
        "1976/07/23  1.0    1     2 w 1"
    )
    assert line[4:8] == "   1"
    assert line[9] == "w"
    assert line[10:13] == " GM"
    assert line[14:47].rstrip() == "Polgar, Judit"
    assert line[48:52] == "2735"
    assert line[53:56] == "HUN"
    assert line[57:68] == "     700070"
    assert line[69:79] == "1976/07/23"
    assert line[80:84] == " 1.0"
    assert line[85:89] == "   1"
    assert line[89:99] == "     2 w 1"


def test_trf_unrated_player_without_optional_fields_leaves_columns_blank():
    player = Player("Newcomer", 0)
    tournament = _tournament([player], rounds=1)

    line = _player_lines(build_trf_document(tournament))[0]

    assert line == "001    1" + " " * 6 + "Newcomer".ljust(33) + " " * 33 + " 0.0    1"


def test_trf_round_records_map_every_recorded_outcome():
    tournament, players = _eleven_player_event()

    records = {
        line[4:8].strip(): (line[89:99], line[99:109])
        for line in _player_lines(build_trf_document(tournament))
    }

    assert records == {
        "1": ("     2 w 1", "     3 w 0"),  # win, loss
        "2": ("     1 b 0", "     4 b 1"),  # loss, win
        "3": ("     4 w =", "     1 b 1"),  # draw, win
        "4": ("     3 b =", "     2 w 0"),
        "5": ("     6 w +", "     7 w -"),  # forfeit win, forfeit loss
        "6": ("     5 b -", "     8 w 1"),
        "7": ("     8 w -", "     5 b +"),  # double forfeit
        "8": ("     7 b -", "     6 b 0"),
        "9": ("  0000 - U", "    10 w ="),  # pairing-allocated bye
        "10": ("  0000 - H", "     9 b ="),  # requested half-point bye
        "11": ("  0000 - Z", "          "),  # zero-point bye, then withdrawn
    }


def test_trf_scores_and_ranks_come_from_app_standings():
    tournament, players = _eleven_player_event()
    standings = {player.id: player for player in tournament.get_standings()}

    lines = _player_lines(build_trf_document(tournament))

    for player, line in zip(players, lines):
        assert line[80:84] == f"{player.score:>4.1f}"
        expected_rank = (
            str(standings[player.id].standing_rank) if player.id in standings else ""
        )
        assert line[85:89] == f"{expected_rank:>4}"
    assert lines[10][85:89] == "    "  # withdrawn players have no standings rank


def test_trf_reduced_pairing_allocated_bye_is_written_by_score():
    players = [Player("Ada", 1500), Player("Bert", 1400), Player("Cora", 1300)]
    tournament = _tournament(players, rounds=1)
    _play(
        tournament,
        [(players[0], players[1])],
        [(players[0].id, players[1].id, 1.0)],
        bye=players[2],
        bye_type="half",
    )

    line = _player_lines(build_trf_document(tournament))[2]

    assert line[80:84] == " 0.5"
    assert line[89:99] == "  0000 - H"


def test_trf_document_omits_unfinished_rounds_and_bbp_extensions():
    tournament, players = _eleven_player_event()
    tournament.rounds.append(
        RoundData(round_number=3, pairings=[(players[0].id, players[1].id)])
    )

    document = build_trf_document(tournament)

    assert "\\n" not in document
    assert document.endswith("\n")
    assert all(len(line) == 109 for line in _player_lines(document))
    assert not [
        line for line in document.splitlines() if line.startswith(BBP_ONLY_PREFIXES)
    ]


def test_trf_start_numbers_follow_pairing_numbers_then_rating():
    players = [Player("Low", 1200), Player("High", 2000), Player("Seeded", 1000)]
    players[2].pairing_number = 1
    tournament = Tournament("City Open", players, 1)

    lines = _player_lines(build_trf_document(tournament))

    assert [line[4:8] for line in lines] == ["   1", "   2", "   3"]
    assert [line[14:47].rstrip() for line in lines] == ["Seeded", "High", "Low"]
    assert all(player.pairing_number is None for player in players[:2])


def _run_bbp(trf_path):
    return subprocess.run(
        [BBP_EXECUTABLE, "--dutch", str(trf_path), "-p"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _result(index, white, black, round_index):
    if round_index == 0 and index == 0:
        return (white.id, black.id, 0.0, OUTCOME_DOUBLE_FORFEIT)
    if index % 7 == 3:
        return (white.id, black.id, 1.0, OUTCOME_FORFEIT_WIN)
    return (white.id, black.id, (1.0, 0.5, 0.0)[(index + round_index) % 3])


def _tournament_after(rounds_played):
    tournament = TournamentPersistenceService().load(FIXTURE).tournament
    # The legacy fixture selects the native engine; the app's default is BBP.
    tournament.use_experimental_dutch = False
    # An odd field puts pairing-allocated byes into the exported history.
    tournament.remove_player(next(iter(tournament.players)))
    for round_index in range(rounds_played):
        pairings, _bye = tournament.create_pairings(round_index + 1)
        assert tournament.rounds[round_index].pairing_engine == "BBP Dutch"
        results = [
            _result(index, white, black, round_index)
            for index, (white, black) in enumerate(pairings)
        ]
        assert tournament.record_results(round_index, results)
    return tournament


@pytest.mark.skipif(BBP_EXECUTABLE is None, reason="BBP engine is not staged")
def test_exported_trf_pairs_next_round_like_the_app(tmp_path):
    tournament = _tournament_after(rounds_played=3)
    numbers = sorted(player.pairing_number for player in tournament.players.values())
    assert numbers == list(range(1, len(tournament.players) + 1))

    # TRF-16 has no total-rounds record; BBP needs one to pair a next round.
    trf_path = tmp_path / "export.trf"
    trf_path.write_text(
        build_trf_document(tournament) + f"XXR {tournament.num_rounds}\n",
        encoding="utf-8",
    )
    completed = _run_bbp(trf_path)
    assert completed.returncode == 0, completed.stderr
    bbp_pairings, bbp_bye = parse_bbp_pairing_output(
        completed.stdout, tournament.players.values()
    )

    app_pairings, app_bye = tournament.create_pairings(4)

    assert {(white.id, black.id) for white, black in bbp_pairings} == {
        (white.id, black.id) for white, black in app_pairings
    }
    assert bbp_bye is not None and app_bye is not None
    assert bbp_bye.id == app_bye.id


@pytest.mark.skipif(BBP_EXECUTABLE is None, reason="BBP engine is not staged")
def test_bbp_reader_accepts_every_exported_outcome(tmp_path):
    tournament, _players = _eleven_player_event()
    trf_path = tmp_path / "outcomes.trf"
    trf_path.write_text(build_trf_document(tournament) + "XXR 3\n", encoding="utf-8")

    completed = _run_bbp(trf_path)

    # BBP also rejects files whose scores disagree with the round records.
    assert completed.returncode == 0, completed.stderr
