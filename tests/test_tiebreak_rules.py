from gambitpairing import constants as c
from gambitpairing.models.player import Player
from gambitpairing.models.enums import Colour
from gambitpairing.controllers.tournament.tiebreak_calculator import TiebreakCalculator
from gambitpairing.controllers.tournament.standings import rank_players


def test_bye_only_record_has_wins_and_fide_capped_dummy():
    p = Player("Bye", 1500)
    p.add_round_result(None, 1, None, c.OUTCOME_BYE)
    TiebreakCalculator().calculate_all_tiebreaks({p.id: p})
    assert p.tiebreakers[c.TB_WINS] == 1
    assert p.tiebreakers[c.TB_PROGRESSIVE] == 1
    assert p.tiebreakers[c.TB_CUMULATIVE] == 0
    assert p.tiebreakers[c.TB_BUCHHOLZ] == 0.5
    assert p.tiebreakers[c.TB_BUCHHOLZ_CUT_1] == 0


def test_nine_round_modified_median_cuts_two():
    p = Player("Plus", 1500)
    p.score = 9
    calc = TiebreakCalculator()
    assert calc._calculate_median(p, list(range(1, 10))) == 42
    p.score = 4.5
    assert calc._calculate_median(p, list(range(1, 10))) == 25
    p.score = 4
    assert calc._calculate_median(p, list(range(1, 10))) == 28


def test_opposition_cumulative_and_withdrawal_adjustments():
    p, q, r = [Player(name, 1500) for name in "PQR"]
    p.add_round_result(q, 1, Colour.WHITE)
    q.add_round_result(p, 0, Colour.BLACK)
    p.add_round_result(r, 0.5, Colour.BLACK)
    q.add_round_result(None, 0.5, None, c.OUTCOME_BYE)
    r.add_round_result(None, 1, None, c.OUTCOME_BYE)
    r.add_round_result(p, 0.5, Colour.WHITE)
    calc = TiebreakCalculator()
    calc.calculate_all_tiebreaks({x.id: x for x in (p, q, r)})
    assert p.tiebreakers[c.TB_CUMULATIVE_OPP] == 1.5
    assert p.tiebreakers[c.TB_SOLKOFF] == 1.5
    assert p.tiebreakers[c.TB_BUCHHOLZ] == 2


def test_forfeit_has_no_played_black_or_rating_contribution():
    p, q = Player("P", 1800), Player("Q", 2000)
    p.add_round_result(q, 1, Colour.BLACK, c.OUTCOME_FORFEIT_WIN)
    q.add_round_result(p, 0, Colour.WHITE, c.OUTCOME_FORFEIT_LOSS)
    TiebreakCalculator().calculate_all_tiebreaks({p.id: p, q.id: q})
    assert p.tiebreakers[c.TB_BLACK_GAMES] == 0
    assert p.tiebreakers[c.TB_GAMES_WON] == 0
    assert p.tiebreakers[c.TB_ARO] == 0
    assert p.tiebreakers[c.TB_BUCHHOLZ] == 0


def test_shared_places_and_derived_ranks_not_saved():
    players = [
        Player(name, rating) for name, rating in [("A", 1800), ("B", 1600), ("C", 1700)]
    ]
    players[0].score = players[1].score = 1
    ranked = rank_players({p.id: p for p in players}, [])
    assert [p.standing_rank for p in ranked] == [1, 1, 3]
    assert all("standing_rank" not in p.to_dict() for p in ranked)


def test_direct_encounter_reapplies_to_subgroup():
    a, b, d, e = [Player(name, 1500) for name in "ABDE"]
    b.rating = 2000  # Display-order fallback would incorrectly put B first.
    for white, black, score in [
        (a, b, 1),
        (d, e, 0.5),
        (a, d, 0),
        (b, e, 1),
        (a, e, 1),
        (b, d, 1),
    ]:
        white.add_round_result(black, score, Colour.WHITE)
        black.add_round_result(white, 1 - score, Colour.BLACK)
    for p in (a, b, d, e):
        p.score = 2
    assert rank_players({p.id: p for p in (a, b, d, e)}, [c.TB_DIRECT_ENCOUNTER]) == [
        a,
        b,
        d,
        e,
    ]


def test_partial_direct_encounter_can_determine_unique_leader():
    a, b, d = [Player(name, 1500) for name in "ABD"]
    for opponent in (b, d):
        a.add_round_result(opponent, 1, Colour.WHITE)
        opponent.add_round_result(a, 0, Colour.BLACK)
    for p in (a, b, d):
        p.score = 2
    ranked = rank_players({p.id: p for p in (a, b, d)}, [c.TB_DIRECT_ENCOUNTER])
    assert ranked[0] is a
    assert [p.standing_rank for p in ranked] == [1, 2, 2]


def test_round_robin_forfeit_uses_actual_opponent_for_sb():
    p, q, r = [Player(name, 1500) for name in "PQR"]
    p.add_round_result(q, 1, Colour.BLACK, c.OUTCOME_FORFEIT_WIN)
    q.add_round_result(p, 0, Colour.WHITE, c.OUTCOME_FORFEIT_LOSS)
    q.add_round_result(r, 1, Colour.WHITE)
    r.add_round_result(q, 0, Colour.BLACK)
    TiebreakCalculator(pairing_system="round_robin").calculate_all_tiebreaks(
        {x.id: x for x in (p, q, r)}
    )
    assert p.tiebreakers[c.TB_SONNENBORN_BERGER] == 1
    assert p.tiebreakers[c.TB_GAMES_WON] == 1
    assert p.tiebreakers[c.TB_ARO] == 0


def test_vur_is_cut_before_lower_played_contribution():
    p, q, r = [Player(name, 1500) for name in "PQR"]
    p.add_round_result(None, 0.5, None, c.OUTCOME_BYE)
    p.add_round_result(q, 1, Colour.WHITE)
    p.add_round_result(r, 0.5, Colour.BLACK)
    for opponent, scores in ((q, [0, 0, 1]), (r, [0.5, 1, 0.5])):
        opponent.results = scores
        opponent.opponent_ids = [p.id] * 3
        opponent.outcome_types = ["normal"] * 3
        opponent.score = sum(scores)
    TiebreakCalculator().calculate_all_tiebreaks({x.id: x for x in (p, q, r)})
    assert p.tiebreakers[c.TB_BUCHHOLZ] == 4.5
    assert p.tiebreakers[c.TB_BUCHHOLZ_CUT_1] == 3


def test_scheduled_byes_survive_record_save_load_and_undo():
    from gambitpairing.controllers.tournament.session import TournamentSession
    from gambitpairing.models.tournament import RoundData
    from gambitpairing.representation import tournament_from_dict

    players = [Player(name, 1500) for name in "ABCD"]
    a, b, d, e = players
    session = TournamentSession("Byes", players, 2, pairing_system="manual")
    session.rounds = [
        RoundData(
            1,
            [(a.id, b.id)],
            scheduled_byes={"half_point": [d.id], "zero_point": [e.id]},
        )
    ]
    assert session.record_results(0, [(a.id, b.id, 1)])
    session.compute_tiebreakers()
    restored = tournament_from_dict(session.to_dict())
    restored.compute_tiebreakers()
    assert {key: p.tiebreakers for key, p in session.players.items()} == {
        key: p.tiebreakers for key, p in restored.players.items()
    }
    assert restored.players[d.id].score == 0.5
    assert restored.result_recorder.undo_round_results(
        restored.rounds[0], restored.players
    )
    assert all(p.score == 0 and p.results == [] for p in restored.players.values())
