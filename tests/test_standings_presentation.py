from gambitpairing.constants import TB_MEDIAN, TB_MOST_BLACKS, TB_SOLKOFF
from gambitpairing.gui.views.standings.standings_presentation import (
    build_export_rows,
    build_print_standings_html,
    build_standings_headers,
    build_standings_table_html,
    format_tiebreak_value,
    project_standings_rows,
    table_width_for_player_count,
)
from gambitpairing.models.player import Player


def _player(name: str, rating: int, score: float) -> Player:
    player = Player(name, rating)
    player.score = score
    player.tiebreakers = {TB_SOLKOFF: 3.456, TB_MEDIAN: 2.345, TB_MOST_BLACKS: 2}
    return player


def test_standings_headers_and_tiebreak_formatting():
    projection = build_standings_headers([TB_SOLKOFF, "custom"])

    assert projection.headers == ["Rank", "Player", "Score", "Solkoff", "CUSTOM"]
    assert projection.tooltips == [
        "Rank",
        "Player Name (Rating)",
        "Total Score",
        "Solkoff",
        "Tiebreak: custom",
    ]
    assert format_tiebreak_value(TB_SOLKOFF, 3.456) == "3.46"
    assert format_tiebreak_value(TB_MOST_BLACKS, 2.0) == "2"


def test_standings_rows_and_export_rows():
    rows = project_standings_rows(
        [_player("Ada", 1800, 2.5)], [TB_SOLKOFF, TB_MEDIAN, TB_MOST_BLACKS]
    )

    assert rows[0].cells == ["1", "Ada (1800)", "2.5", "3.46", "2.35", "2"]
    assert build_export_rows(rows) == [
        ["1", "Ada (1800)", "2.5", "3.46", "2.35", "2"]
    ]


def test_standings_html_builders_handle_empty_and_escaped_content():
    rows = project_standings_rows([_player("Ada <A>", 0, 1.0)], [TB_SOLKOFF])

    assert build_standings_table_html([], [TB_SOLKOFF]) == ""
    html = build_standings_table_html(rows, [TB_SOLKOFF])

    assert "Ada &lt;A&gt; (NR)" in html
    assert "TB1 = Solkoff" in html


def test_print_standings_html_includes_title_width_and_footer():
    rows = project_standings_rows([_player("Ada", 1800, 1.0)], [TB_SOLKOFF])

    assert table_width_for_player_count(8) == "70%"
    assert table_width_for_player_count(16) == "85%"
    assert table_width_for_player_count(17) == "95%"

    html = build_print_standings_html(
        tournament_name="City Open",
        round_subtitle="After Round 2",
        rows=rows,
        tiebreak_order=[TB_SOLKOFF],
        printed_at="2026-06-29 21:30",
    )

    assert "Standings - City Open" in html
    assert "After Round 2" in html
    assert "2026-06-29 21:30" in html
