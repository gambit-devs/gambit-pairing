from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import QDateTime
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog

from gambitpairing.constants import TIEBREAK_NAMES
from gambitpairing.utils.print import PrintOptionsDialog, TournamentPrintUtils


def print_pairings(self):
    """Print the current round's pairings table in a clean, ink-friendly, professional format (no input widgets)."""
    if self.table_pairings.rowCount() == 0:
        QtWidgets.QMessageBox.information(
            self, "Print Pairings", "No pairings to print."
        )
        return

    # Always include tournament name
    tournament_name = ""
    if hasattr(self, "tournament") and self.tournament and self.tournament.name:
        tournament_name = self.tournament.name
    printer, preview = TournamentPrintUtils.create_print_preview_dialog(
        self, "Print Preview - Pairings"
    )
    include_tournament_name = True

    def render_preview(printer_obj):
        doc = QtGui.QTextDocument()
        # Use unified utility for clean round title
        round_title = ""
        if hasattr(self, "lbl_round_title") and hasattr(self.lbl_round_title, "text"):
            round_title = TournamentPrintUtils.get_clean_print_title(
                self.lbl_round_title.text()
            )
        elif hasattr(self, "round_group") and hasattr(self.round_group, "title"):
            round_title = TournamentPrintUtils.get_clean_print_title(
                self.round_group.title()
            )

        # Build title with optional tournament name
        main_title = "Pairings"
        if include_tournament_name and tournament_name:
            main_title += f" - {tournament_name}"

        html = f"""
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
                table.pairings {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 0 auto 1.5em auto;
                }}
                table.pairings th, table.pairings td {{
                    border: 1px solid #222;
                    padding: 6px 10px;
                    text-align: left;
                    font-size: 11pt;
                    white-space: nowrap;
                }}
                table.pairings th {{
                    font-weight: bold;
                    background: none;
                }}
                .bye-row td {{
                    font-style: italic;
                    font-weight: bold;
                    text-align: center;
                    border-top: 2px solid #222;
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
            <h2>{main_title}</h2>
            <div class="subtitle">{round_title}</div>
            <table class="pairings">
                <tr>
                    <th style="width:7%;">Bd</th>
                    <th style="width:46%;">White</th>
                    <th style="width:46%;">Black</th>
                </tr>
        """
        for row in range(self.table_pairings.rowCount()):
            white_item = self.table_pairings.item(row, 0)
            black_item = self.table_pairings.item(row, 1)
            white = white_item.text() if white_item else ""
            black = black_item.text() if black_item else ""
            html += f"""
                <tr>
                    <td style="text-align:center;">{row + 1}</td>
                    <td>{white}</td>
                    <td>{black}</td>
                </tr>
            """
        if (
            self.lbl_bye.isVisible()
            and self.lbl_bye.text()
            and self.lbl_bye.text() != "Bye: None"
        ):
            html += f"""
            <tr class="bye-row">
                <td colspan="3">{self.lbl_bye.text()}</td>
            </tr>
            """
        html += f"""
            </table>
            <div class="footer">
                Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")}
            </div>
        </body>
        </html>
        """
        doc.setHtml(html)
        doc.print(printer_obj)

    preview.paintRequested.connect(render_preview)
    preview.exec()


def print_standings(self):
    """Print the current standings table in a clean, ink-friendly, professional format with a polished legend."""
    if self.table_standings.rowCount() == 0:
        QtWidgets.QMessageBox.information(
            self, "Print Standings", "No standings to print."
        )
        return

    # Always include tournament name
    tournament_name = ""
    if hasattr(self, "tournament") and self.tournament and self.tournament.name:
        tournament_name = self.tournament.name
    printer, preview = TournamentPrintUtils.create_print_preview_dialog(
        self, "Print Preview - Standings"
    )
    include_tournament_name = True

    def render_preview(printer_obj):
        doc = QtGui.QTextDocument()
        # Use unified utility for round information
        subtitle = ""
        if hasattr(self, "lbl_round_title") and hasattr(self.lbl_round_title, "text"):
            subtitle = self.lbl_round_title.text()
        elif hasattr(self, "round_group") and hasattr(self.round_group, "title"):
            subtitle = self.round_group.title()

        # Build title with optional tournament name
        main_title = "Standings"
        if include_tournament_name and tournament_name:
            main_title += f" - {tournament_name}"
        tb_keys = []
        tb_legend = []
        for i, tb_key in enumerate(self.tournament.tiebreak_order):
            short = f"TB{i+1}"
            tb_keys.append(short)
            tb_legend.append((short, TIEBREAK_NAMES.get(tb_key, tb_key.title())))
        html = f"""
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
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                    }}
                    table.standings th, table.standings td {{
                        border: 1px solid #222;
                        padding: 6px 10px;
                        text-align: center;
                        font-size: 11pt;
                        white-space: nowrap;
                    }}
                    table.standings th {{
                        font-weight: bold;
                        background: none;
                    }}
                    .legend {{
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                        font-size: 10.5pt;
                        color: #222;
                        border: 1px solid #bbb;
                        background: none;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    .legend-title {{
                        font-weight: bold;
                        font-size: 11pt;
                        margin-bottom: 0.3em;
                        display: block;
                        letter-spacing: 0.02em;
                    }}
                    .legend-table {{
                        border-collapse: collapse;
                        margin-top: 0.2em;
                    }}
                    .legend-table td {{
                        border: none;
                        padding: 2px 10px 2px 0;
                        font-size: 10pt;
                        vertical-align: top;
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
                <h2>{main_title}</h2>
                <div class="subtitle">{subtitle}</div>
                <div class="legend">
                    <span class="legend-title">Tiebreaker Legend</span>
                    <table class="legend-table">
            """
        for short, name in tb_legend:
            html += f"<tr><td><b>{short}</b></td><td>{name}</td></tr>"
        html += """
                    </table>
                </div>
                <table class="standings">
                    <tr>
                        <th style="width:6%;">#</th>
                        <th style="width:32%;">Player</th>
                        <th style="width:10%;">Score</th>
            """
        for short in tb_keys:
            html += f'<th style="width:7%;">{short}</th>'
        html += "</tr>"
        # --- Table Rows ---
        for row in range(self.table_standings.rowCount()):
            html += "<tr>"
            for col in range(self.table_standings.columnCount()):
                item = self.table_standings.item(row, col)
                cell = item.text() if item else ""
                # Rank and Score columns bold
                if col == 0 or col == 2:
                    html += f'<td style="font-weight:bold;">{cell}</td>'
                else:
                    html += f"<td>{cell}</td>"
            html += "</tr>"
        html += f"""
                </table>
                <div class="footer">
                    Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")}
                </div>
            </body>
            </html>
            """
        doc.setHtml(html)
        doc.print(printer_obj)

    preview.paintRequested.connect(render_preview)
    preview.exec()
