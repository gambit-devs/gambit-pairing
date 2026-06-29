"""Presentation helpers for tournament print output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PairingsPrintRow:
    board: int
    white: str
    black: str


def build_page_separator(separate_pages: bool) -> str:
    if separate_pages:
        return '<div style="page-break-before: always;"></div>'
    return '<hr style="margin: 2em 0; border: none; border-top: 2px solid #222;">'


def build_pairings_print_section(
    tournament_name: str,
    round_title: str,
    rows: Sequence[PairingsPrintRow],
    bye_text: str,
) -> str:
    if not rows:
        return ""

    title_suffix = f" - {tournament_name}" if tournament_name else ""
    html = f"""
            <h2>Pairings{title_suffix}</h2>
            <div class="subtitle">{round_title}</div>
            <table class="pairings">
                <tr>
                    <th style="width:7%;">Bd</th>
                    <th style="width:46%;">White</th>
                    <th style="width:46%;">Black</th>
                </tr>
            """
    for row in rows:
        html += (
            f"<tr><td>{row.board}</td><td>{row.white}</td>"
            f"<td>{row.black}</td></tr>"
        )

    if bye_text:
        html += f'<tr class="bye-row"><td colspan="3">{bye_text}</td></tr>'

    html += "</table>"
    return html


def build_standings_print_section(
    tournament_name: str,
    current_round_index: int,
    standings_html: str,
    page_separator: str,
) -> str:
    if not standings_html:
        return ""

    title_suffix = f" - {tournament_name}" if tournament_name else ""
    return f"""
                {page_separator}
                <h2>Standings{title_suffix}</h2>
                <div class="subtitle">After Round {current_round_index}</div>
                {standings_html}
                """


def build_combined_tournament_print_html(
    pairings_html: str, standings_html: str, printed_at: str
) -> str:
    return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #000; background: #fff; margin: 0; padding: 20px; }}
                h2 {{ text-align: center; margin: 0 0 0.5em 0; font-size: 1.35em; font-weight: bold; letter-spacing: 0.03em; }}
                .subtitle {{ text-align: center; font-size: 1.05em; margin-bottom: 1.2em; color: #444; }}
                table.pairings, table.standings {{ border-collapse: collapse; width: 100%; margin: 0 auto 1.5em auto; }}
                table.pairings th, table.pairings td,
                table.standings th, table.standings td {{ border: 1px solid #222; padding: 6px 10px; text-align: center; font-size: 11pt; }}
                table.pairings th, table.standings th {{ font-weight: bold; background: #f0f0f0; }}
                table.pairings td:nth-child(2), table.pairings td:nth-child(3) {{ text-align: left; }}
                table.standings td:nth-child(2) {{ text-align: left; }}
                .bye-row td {{ font-style: italic; font-weight: bold; text-align: center; border-top: 2px solid #222; }}
                .legend {{ margin-top: 1em; font-size: 10pt; color: #444; }}
                .footer {{ text-align: center; font-size: 9pt; margin-top: 2em; color: #888; }}
            </style>
        </head>
        <body>
            {pairings_html}
            {standings_html}
            <div class="footer">
                Printed by Gambit Pairing &mdash; {printed_at}
            </div>
        </body>
        </html>
        """
