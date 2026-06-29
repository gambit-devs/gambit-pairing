"""Pure presentation helpers for the standings view."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Iterable, Sequence

from gambitpairing.constants import (
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_MEDIAN,
    TB_MOST_BLACKS,
    TB_SOLKOFF,
    TB_SONNENBORN_BERGER,
    TIEBREAK_NAMES,
)


TIEBREAK_FORMATS: dict[str, str] = {
    TB_MEDIAN: ".2f",
    TB_SOLKOFF: ".2f",
    TB_CUMULATIVE: ".1f",
    TB_CUMULATIVE_OPP: ".1f",
    TB_SONNENBORN_BERGER: ".2f",
    TB_MOST_BLACKS: ".0f",
}


@dataclass(frozen=True)
class StandingsHeaderProjection:
    headers: list[str]
    tooltips: list[str]


@dataclass(frozen=True)
class StandingsRowProjection:
    rank: str
    player: str
    score: str
    tiebreaks: list[str]

    @property
    def cells(self) -> list[str]:
        return [self.rank, self.player, self.score, *self.tiebreaks]


def build_standings_headers(
    tiebreak_order: Sequence[str],
) -> StandingsHeaderProjection:
    return StandingsHeaderProjection(
        headers=[
            "Rank",
            "Player",
            "Score",
            *[TIEBREAK_NAMES.get(key, key.upper()) for key in tiebreak_order],
        ],
        tooltips=[
            "Rank",
            "Player Name (Rating)",
            "Total Score",
            *[
                TIEBREAK_NAMES.get(key, f"Tiebreak: {key}")
                for key in tiebreak_order
            ],
        ],
    )


def format_tiebreak_value(tb_key: str, value: float) -> str:
    format_spec = TIEBREAK_FORMATS.get(tb_key, ".2f")
    return f"{value:{format_spec}}"


def project_standings_rows(
    standings: Iterable[Any], tiebreak_order: Sequence[str]
) -> list[StandingsRowProjection]:
    rows: list[StandingsRowProjection] = []
    for rank, player in enumerate(standings):
        rows.append(
            StandingsRowProjection(
                rank=str(rank + 1),
                player=f"{player.name} ({player.rating or 'NR'})",
                score=f"{player.score:.1f}",
                tiebreaks=[
                    format_tiebreak_value(
                        tb_key, player.tiebreakers.get(tb_key, 0.0)
                    )
                    for tb_key in tiebreak_order
                ],
            )
        )
    return rows


def build_export_rows(
    rows: Sequence[StandingsRowProjection],
) -> list[list[str]]:
    return [row.cells for row in rows]


def build_tiebreak_legend_items(
    tiebreak_order: Sequence[str],
) -> list[tuple[str, str]]:
    return [
        (f"TB{i + 1}", TIEBREAK_NAMES.get(tb_key, tb_key.title()))
        for i, tb_key in enumerate(tiebreak_order)
    ]


def table_width_for_player_count(player_count: int) -> str:
    if player_count <= 8:
        return "70%"
    if player_count <= 16:
        return "85%"
    return "95%"


def build_standings_table_html(
    rows: Sequence[StandingsRowProjection],
    tiebreak_order: Sequence[str],
    include_legend: bool = True,
) -> str:
    if not rows:
        return ""

    html = """
        <table class="standings">
            <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>Score</th>
        """
    for short, _ in build_tiebreak_legend_items(tiebreak_order):
        html += f"<th>{short}</th>"

    html += "</tr>"
    for row in rows:
        html += "<tr>"
        for value in row.cells:
            html += f"<td>{escape(value)}</td>"
        html += "</tr>"
    html += "</table>"

    if include_legend and tiebreak_order:
        legend = ", ".join(
            f"{short} = {escape(name)}"
            for short, name in build_tiebreak_legend_items(tiebreak_order)
        )
        html += f'<div class="legend"><strong>Tiebreakers:</strong> {legend}</div>'

    return html


def build_print_standings_html(
    tournament_name: str,
    round_subtitle: str,
    rows: Sequence[StandingsRowProjection],
    tiebreak_order: Sequence[str],
    printed_at: str,
    include_tournament_name: bool = True,
) -> str:
    main_title = "Standings"
    if include_tournament_name and tournament_name:
        main_title += f" - {tournament_name}"

    table_width = table_width_for_player_count(len(rows))
    tb_legend = build_tiebreak_legend_items(tiebreak_order)
    tb_headers = "".join(
        f'<th class="tiebreak-column">{short}</th>' for short, _ in tb_legend
    )
    legend_rows = "".join(
        f"<tr><td>{short}:</td><td>{escape(name)}</td></tr>"
        for short, name in tb_legend
    )

    table_rows = ""
    for row in rows:
        table_rows += "<tr>"
        for col, cell in enumerate(row.cells):
            escaped_cell = escape(cell)
            if col == 0 or col == 2:
                table_rows += f'<td style="font-weight:bold;">{escaped_cell}</td>'
            else:
                table_rows += f"<td>{escaped_cell}</td>"
        table_rows += "</tr>"

    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #000;
                background: #fff;
                margin: 0;
                padding: 0;
            }}
            h2 {{
                text-align: center;
                margin: 0 0 0.5em 0;
                font-size: 1.35em;
                font-weight: normal;
                letter-spacing: 0.03em;
            }}
            .subtitle {{
                text-align: center;
                font-size: 1.05em;
                margin-bottom: 1.2em;
            }}
            table.standings {{
                border-collapse: collapse;
                width: {table_width};
                margin: 0 auto 1.5em auto;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            table.standings th, table.standings td {{
                border: 1px solid #222;
                padding: 8px 10px;
                text-align: center;
                font-size: 11pt;
                white-space: nowrap;
            }}
            table.standings th {{
                font-weight: bold;
                background: #f8f8f8;
                border-bottom: 2px solid #222;
            }}
            .rank-column {{
                width: 8%;
                font-weight: bold;
            }}
            .player-column {{
                width: 35%;
                text-align: left;
            }}
            .score-column {{
                width: 12%;
                font-weight: bold;
            }}
            .tiebreak-column {{
                width: 7%;
            }}
            .legend {{
                width: {table_width};
                margin: 0 auto 1.5em auto;
                font-size: 10.5pt;
                color: #222;
                border: 2px solid #666;
                border-radius: 5px;
                background: #f9f9f9;
                padding: 12px 15px;
                text-align: left;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .legend-title {{
                font-weight: bold;
                font-size: 1.1em;
                margin-bottom: 0.8em;
                display: block;
                letter-spacing: 0.02em;
                color: #333;
                border-bottom: 1px solid #ccc;
                padding-bottom: 0.3em;
            }}
            .legend-table {{
                border-collapse: collapse;
                margin-top: 0.2em;
                width: 100%;
            }}
            .legend-table td {{
                border: none;
                padding: 3px 12px 3px 0;
                font-size: 10.5pt;
                vertical-align: top;
            }}
            .legend-table td:first-child {{
                font-weight: bold;
                color: #444;
                width: 15%;
            }}
            .legend-table td:last-child {{
                color: #555;
            }}
            .footer {{
                text-align: center;
                font-size: 9pt;
                margin-top: 2em;
                color: #888;
                letter-spacing: 0.04em;
            }}
        </style>
    </head>
    <body>
        <h2>{escape(main_title)}</h2>
        <div class="subtitle">{escape(round_subtitle)}</div>
        <div class="legend">
            <span class="legend-title">Tiebreaker Explanations</span>
            <table class="legend-table">
                {legend_rows}
            </table>
        </div>
        <table class="standings">
            <tr>
                <th class="rank-column">#</th>
                <th class="player-column">Player</th>
                <th class="score-column">Score</th>
                {tb_headers}
            </tr>
            {table_rows}
        </table>
        <div class="footer">
            Printed by Gambit Pairing &mdash; {escape(printed_at)}
        </div>
    </body>
    </html>
    """
