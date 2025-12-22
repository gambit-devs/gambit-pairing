from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import QDateTime
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog

from gambitpairing.constants import TIEBREAK_NAMES
from gambitpairing.utils.print import PrintOptionsDialog, TournamentPrintUtils


def print_pairings(self):
    """Print the current round's pairings table in a clean, ink-friendly, professional format."""
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

        # Determine table width based on number of pairings for better centering
        num_pairings = self.table_pairings.rowCount()
        if num_pairings <= 4:
            table_width = "60%"  # Small tournaments - more centered
        elif num_pairings <= 8:
            table_width = "75%"  # Medium tournaments
        else:
            table_width = "90%"  # Large tournaments - use more width

        # Collect bye information
        bye_players = []
        if (
            self.lbl_bye.isVisible()
            and self.lbl_bye.text()
            and self.lbl_bye.text() != "Bye: None"
        ):
            bye_text = self.lbl_bye.text()
            # Extract player names from "Bye: Player1, Player2" format
            if "Bye:" in bye_text:
                bye_part = bye_text.split("Bye:")[1].strip()
                if bye_part and bye_part != "None":
                    bye_players = [name.strip() for name in bye_part.split(",")]

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
                    width: {table_width};
                    margin: 0 auto 1.5em auto;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                table.pairings th, table.pairings td {{
                    border: 1px solid #222;
                    padding: 8px 12px;
                    text-align: left;
                    font-size: 11pt;
                    white-space: nowrap;
                }}
                table.pairings th {{
                    font-weight: bold;
                    background: #f8f8f8;
                    border-bottom: 2px solid #222;
                }}
                .board-number {{
                    text-align: center;
                    font-weight: bold;
                    width: 8%;
                }}
                .player-name {{
                    width: 46%;
                }}
                .bye-section {{
                    margin: 1.5em auto;
                    padding: 1em;
                    border: 2px solid #666;
                    border-radius: 5px;
                    background: #f9f9f9;
                    width: {table_width};
                    text-align: center;
                }}
                .bye-title {{
                    font-weight: bold;
                    font-size: 1.1em;
                    margin-bottom: 0.5em;
                    color: #444;
                }}
                .bye-player {{
                    font-style: italic;
                    font-size: 1.05em;
                    color: #222;
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
                    <th class="board-number">Board</th>
                    <th class="player-name">White</th>
                    <th class="player-name">Black</th>
                </tr>
        """
        for row in range(self.table_pairings.rowCount()):
            white_item = self.table_pairings.item(row, 0)
            black_item = self.table_pairings.item(row, 1)
            white = white_item.text() if white_item else ""
            black = black_item.text() if black_item else ""
            html += f"""
                <tr>
                    <td class="board-number">{row + 1}</td>
                    <td class="player-name">{white}</td>
                    <td class="player-name">{black}</td>
                </tr>
            """
        html += "</table>"

        # Add bye section if there are bye players
        if bye_players:
            html += '<div class="bye-section">'
            html += '<div class="bye-title">Bye Players</div>'
            html += '<div class="bye-player">' + ", ".join(bye_players) + "</div>"
            html += "</div>"

        html += f"""
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
    """Print the current standings table in a clean, ink-friendly, professional format with an enhanced legend."""
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

        # Determine table width based on number of players
        num_players = self.table_standings.rowCount()
        if num_players <= 8:
            table_width = "70%"  # Small tournaments - more centered
        elif num_players <= 16:
            table_width = "85%"  # Medium tournaments
        else:
            table_width = "95%"  # Large tournaments

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
                <h2>{main_title}</h2>
                <div class="subtitle">{subtitle}</div>
                <div class="legend">
                    <span class="legend-title">Tiebreaker Explanations</span>
                    <table class="legend-table">
            """
        for short, name in tb_legend:
            html += f"<tr><td>{short}:</td><td>{name}</td></tr>"
        html += """
                    </table>
                </div>
                <table class="standings">
                    <tr>
                        <th class="rank-column">#</th>
                        <th class="player-column">Player</th>
                        <th class="score-column">Score</th>
            """
        for short in tb_keys:
            html += f'<th class="tiebreak-column">{short}</th>'
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
