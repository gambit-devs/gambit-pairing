# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Pairings printing functionality.

This module handles the printing of tournament round pairings in a clean,
professional, ink-friendly format.
"""

from typing import List, Optional, Tuple

from PyQt6.QtCore import QDateTime
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QWidget

from gambitpairing.utils.print import TournamentPrintUtils


class PairingsPrinter:
    """
    Handles printing of tournament pairings.

    This class generates HTML for professional pairing sheets and manages
    the print preview dialog.

    Parameters
    ----------
    parent : QWidget
        The parent widget for dialogs
    """

    def __init__(self, parent: QWidget):
        self.parent = parent

    def generate_pairings_html(
        self,
        tournament_name: str,
        round_title: str,
        pairings: List[Tuple[str, str]],
        bye_text: Optional[str] = None,
    ) -> str:
        """
        Generate HTML for pairings printout.

        Parameters
        ----------
        tournament_name : str
            Name of the tournament
        round_title : str
            The round title/label (e.g., "Round 1 of 5")
        pairings : list
            List of (white_name, black_name) tuples
        bye_text : str, optional
            Text to display for bye (e.g., "Bye: John Smith")

        Returns
        -------
        str
            Complete HTML document for printing
        """
        # Clean up title for printing
        round_title = TournamentPrintUtils.get_clean_print_title(round_title)

        # Build main title
        main_title = "Pairings"
        if tournament_name:
            main_title += f" - {tournament_name}"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #000; background: #fff; margin: 0; padding: 0; }}
                h2 {{ text-align: center; margin: 0 0 0.5em 0; font-size: 1.35em; font-weight: normal; letter-spacing: 0.03em; }}
                .subtitle {{ text-align: center; font-size: 1.05em; margin-bottom: 1.2em; }}
                table.pairings {{ border-collapse: collapse; width: 100%; margin: 0 auto 1.5em auto; }}
                table.pairings th, table.pairings td {{ border: 1px solid #222; padding: 6px 10px; text-align: left; font-size: 11pt; white-space: nowrap; }}
                table.pairings th {{ font-weight: bold; background: none; }}
                .bye-row td {{ font-style: italic; font-weight: bold; text-align: center; border-top: 2px solid #222; }}
                .footer {{ text-align: center; font-size: 9pt; margin-top: 2em; color: #888; letter-spacing: 0.04em; }}
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

        for i, (white_name, black_name) in enumerate(pairings, start=1):
            html += f"<tr><td>{i}</td><td>{white_name}</td><td>{black_name}</td></tr>"

        if bye_text and bye_text != "Bye: None":
            html += f'<tr class="bye-row"><td colspan="3">{bye_text}</td></tr>'

        html += f"""
            </table>
            <div class="footer">
                Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}
            </div>
        </body>
        </html>
        """

        return html

    def print_pairings(
        self,
        tournament_name: str,
        round_title: str,
        pairings: List[Tuple[str, str]],
        bye_text: Optional[str] = None,
    ):
        """
        Show print preview dialog for pairings.

        Parameters
        ----------
        tournament_name : str
            Name of the tournament
        round_title : str
            The round title/label
        pairings : list
            List of (white_name, black_name) tuples
        bye_text : str, optional
            Text to display for bye
        """
        if not pairings and not bye_text:
            return

        printer, preview = TournamentPrintUtils.create_print_preview_dialog(
            self.parent, "Print Preview - Pairings"
        )
        _ = printer  # printer is used by preview internally

        def render_preview(printer_obj):
            html = self.generate_pairings_html(
                tournament_name, round_title, pairings, bye_text
            )
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print(printer_obj)

        preview.paintRequested.connect(render_preview)
        preview.exec()

    def print_from_table(
        self, table_widget, tournament_name: str, round_title: str, bye_label
    ):
        """
        Print pairings from a QTableWidget.

        Extracts data from the table widget and bye label, then prints.

        Parameters
        ----------
        table_widget : QTableWidget
            The pairings table widget
        tournament_name : str
            Name of the tournament
        round_title : str
            The round title/label
        bye_label : QLabel
            The bye information label
        """
        if table_widget.rowCount() == 0:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self.parent, "Print Pairings", "No pairings to print."
            )
            return

        # Extract pairings from table
        # Table columns: 0=Board, 1=White, 2=Black, 3=Result
        pairings = []
        for row in range(table_widget.rowCount()):
            white_item = table_widget.item(row, 1)  # White is column 1
            black_item = table_widget.item(row, 2)  # Black is column 2
            white_name = white_item.text() if white_item else ""
            black_name = black_item.text() if black_item else ""
            pairings.append((white_name, black_name))

        # Get bye text
        bye_text = None
        if bye_label.isVisible() and bye_label.text():
            bye_text = bye_label.text()

        self.print_pairings(tournament_name, round_title, pairings, bye_text)
