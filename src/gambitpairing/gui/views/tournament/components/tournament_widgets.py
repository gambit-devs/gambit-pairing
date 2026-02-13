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
Reusable UI widgets for the Tournament tab.

This module contains custom Qt widgets used in the tournament management interface:
- CheckableButton: A toggle button with a visual checkmark indicator
- ResultSelector: A widget for selecting game results (1-0, ½-½, 0-1) with forfeit options
- RoundProgressIndicator: Visual indicator showing tournament progress
"""

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import (
    RESULT_BLACK_FORFEIT_WIN,
    RESULT_BLACK_WIN,
    RESULT_DOUBLE_FORFEIT,
    RESULT_DRAW,
    RESULT_WHITE_FORFEIT_WIN,
    RESULT_WHITE_WIN,
)
from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon

if TYPE_CHECKING:
    from gambitpairing.gui.views.tournament.tournament_state import TournamentPhase


class RoundProgressIndicator(QtWidgets.QWidget):
    """
    A visual progress indicator showing the current round and tournament status.

    Displays round progress as a series of circles/dots:
    - Completed rounds are filled
    - Current round is highlighted
    - Future rounds are outlined

    Also shows a text summary of tournament progress.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "RoundProgressIndicator")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        # Progress dots container
        self.dots_container = QtWidgets.QWidget()
        self.dots_layout = QtWidgets.QHBoxLayout(self.dots_container)
        self.dots_layout.setContentsMargins(0, 0, 0, 0)
        self.dots_layout.setSpacing(8)
        layout.addWidget(self.dots_container)

        layout.addStretch()

        # Progress text label
        self.progress_label = QtWidgets.QLabel("")
        self.progress_label.setProperty("class", "ProgressLabel")
        layout.addWidget(self.progress_label)

        self._dots = []
        self._current_round = 0
        self._total_rounds = 0

    def update_progress(
        self, current_round: int, total_rounds: int, phase: "TournamentPhase"
    ):
        """
        Update the progress indicator.

        Parameters
        ----------
        current_round : int
            The current round number (1-indexed)
        total_rounds : int
            Total number of rounds in the tournament
        phase : TournamentPhase
            Current phase of the tournament
        """
        from gambitpairing.gui.views.tournament.tournament_state import TournamentPhase

        self._current_round = current_round
        self._total_rounds = total_rounds

        # Clear existing dots
        for dot in self._dots:
            dot.deleteLater()
        self._dots.clear()

        # Don't show dots if not started or too many rounds
        if total_rounds <= 0:
            self.progress_label.setText("Tournament not configured")
            return

        # Create dots (limit to 12 visible dots for very long tournaments)
        visible_rounds = min(total_rounds, 12)

        for i in range(visible_rounds):
            round_num = i + 1
            dot = QtWidgets.QLabel()
            dot.setFixedSize(16, 16)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if round_num < current_round:
                # Completed round
                dot.setProperty("state", "completed")
                set_svg_icon(dot, "checkmark-white.svg", "black", 12)
            elif round_num == current_round:
                # Current round
                if phase == TournamentPhase.AWAITING_RESULTS:
                    dot.setProperty("state", "active")
                elif phase == TournamentPhase.FINISHED:
                    dot.setProperty("state", "completed")
                    set_svg_icon(dot, "checkmark-white.svg", "black", 12)
                else:
                    dot.setProperty("state", "current")
                dot.setText(str(round_num)) if not dot.pixmap() else None
            else:
                # Future round
                dot.setProperty("state", "pending")
                dot.setText(str(round_num))

            self.dots_layout.addWidget(dot)
            self._dots.append(dot)

        # If there are more rounds than visible, add ellipsis
        if total_rounds > visible_rounds:
            ellipsis = QtWidgets.QLabel("...")
            ellipsis.setProperty("class", "ProgressEllipsis")
            self.dots_layout.addWidget(ellipsis)
            self._dots.append(ellipsis)

        # Update progress text
        if phase == TournamentPhase.FINISHED:
            self.progress_label.setText(f"Tournament Complete ({total_rounds} rounds)")
        elif phase == TournamentPhase.NOT_STARTED:
            self.progress_label.setText(f"{total_rounds} rounds planned")
        else:
            self.progress_label.setText(f"Round {current_round} of {total_rounds}")

        # Force style refresh on dots
        for dot in self._dots:
            dot.style().unpolish(dot)
            dot.style().polish(dot)


class CheckableButton(QtWidgets.QPushButton):
    """
    A toggle button that displays a checkmark when checked.

    Used for result selection buttons in the tournament pairings table.
    The checkmark is drawn in the top-right corner when the button is checked.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        # Icon color chosen dynamically in paintEvent so it contrasts with the selected background
        self.setProperty("class", "ResultSelectorButton")

    def paintEvent(self, a0):
        """Custom paint event to draw checkmark on checked buttons."""
        super().paintEvent(a0)
        if self.isChecked():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            rect = self.rect()
            # Move checkmark further left for White win and Draw to avoid clipping
            if self.text() in ["1-0", "½-½"]:
                offset = 20
            else:
                offset = 18
            checkmark_rect = QtCore.QRect(rect.right() - offset, rect.top() + 2, 12, 12)

            # Choose a checkmark color that contrasts with the selected button background:
            # - For white-result buttons, use chess green so it remains visible on a light background.
            # - For other buttons, use white to stand out on darker backgrounds.
            result_type = self.property("result_type")
            if result_type == "white":
                icon_color = "#2d5a27"
                fallback_qcolor = QtGui.QColor("#2d5a27")
            else:
                icon_color = "white"
                fallback_qcolor = QtGui.QColor("white")

            icon = get_colored_icon("checkmark-white.svg", icon_color, 12)
            if not icon.isNull():
                icon.paint(painter, checkmark_rect)
            else:
                # Fallback: draw a simple tick with contrasting color
                painter.setPen(QtGui.QPen(fallback_qcolor, 2))
                font = QtGui.QFont(painter.font())
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(checkmark_rect, Qt.AlignmentFlag.AlignCenter, "✓")


class ResultSelector(QtWidgets.QWidget):
    """
    A widget for selecting chess game results with a cleaner UX.

    Normal mode displays:
    - White wins (1-0)
    - Draw (½-½)
    - Black wins (0-1)
    - Menu button (⋮) for forfeit options

    When a forfeit is selected, the widget switches to display mode showing
    the selected forfeit outcome with an option to change it.

    The selected result can be retrieved via selectedResult() and
    programmatically set via setResult().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "ResultSelector")

        # Main layout
        self.main_layout = QtWidgets.QStackedLayout(self)
        self.main_layout.setContentsMargins(2, 2, 8, 16)

        # Enforce minimum size
        self.setMinimumWidth(180)
        self.setMinimumHeight(40)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed
        )

        # Create two widgets: selector mode and display mode
        self._create_selector_widget()
        self._create_display_widget()

        # Track current selection
        self._current_result = ""

        # Start in selector mode
        self.main_layout.setCurrentWidget(self.selector_widget)

    def _create_selector_widget(self):
        """Create the selector widget with 3 main buttons + menu."""
        self.selector_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.selector_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Create main result buttons with color-coded styling
        self.btn_white_win = CheckableButton("1-0")
        self.btn_white_win.setProperty("result_const", RESULT_WHITE_WIN)
        self.btn_white_win.setProperty("result_type", "white")
        self.btn_white_win.setToolTip("White wins")

        self.btn_draw = CheckableButton("½-½")
        self.btn_draw.setProperty("result_const", RESULT_DRAW)
        self.btn_draw.setProperty("result_type", "draw")
        self.btn_draw.setToolTip("Draw")

        self.btn_black_win = CheckableButton("0-1")
        self.btn_black_win.setProperty("result_const", RESULT_BLACK_WIN)
        self.btn_black_win.setProperty("result_type", "black")
        self.btn_black_win.setToolTip("Black wins")

        # Add buttons to layout and button group
        for btn in [self.btn_white_win, self.btn_draw, self.btn_black_win]:
            self.button_group.addButton(btn)
            layout.addWidget(btn)

        # Create menu button for forfeit options - styled like copy buttons
        self.menu_button = QtWidgets.QPushButton()
        self.menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.menu_button.setFlat(True)
        self.menu_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.menu_button.setFixedSize(32, 32)
        self.menu_button.setToolTip("More options (forfeits)")
        self.menu_button.setProperty("class", "OptionsButton")

        # Use three-dot (ellipsis) icon
        icon = get_colored_icon("ellipsis-vertical.svg", "#555", 16)
        if icon and not icon.isNull():
            self.menu_button.setIcon(icon)
            self.menu_button.setIconSize(QtCore.QSize(16, 16))
        else:
            # Fallback to text if icon not found
            self.menu_button.setText("⋮")

        self.menu_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                color: #555;
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover {
                background: #e0e4ea;
                color: #222;
            }
            QPushButton:pressed {
                background: #d0d4da;
            }
            QPushButton::menu-indicator {
                width: 0;
                height: 0;
            }
        """)

        # Create menu for forfeit options
        self.forfeit_menu = QtWidgets.QMenu(self)
        self.forfeit_menu.addAction(
            "White wins by forfeit (FF W)",
            lambda: self._select_forfeit(RESULT_WHITE_FORFEIT_WIN),
        )
        self.forfeit_menu.addAction(
            "Black wins by forfeit (FF B)",
            lambda: self._select_forfeit(RESULT_BLACK_FORFEIT_WIN),
        )
        self.forfeit_menu.addAction(
            "Double forfeit (FF X)", lambda: self._select_forfeit(RESULT_DOUBLE_FORFEIT)
        )

        self.menu_button.setMenu(self.forfeit_menu)
        layout.addWidget(self.menu_button)

        self.main_layout.addWidget(self.selector_widget)

    def _create_display_widget(self):
        """Create the display widget for showing selected forfeit."""
        self.display_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.display_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label to show the selected forfeit
        self.display_label = QtWidgets.QLabel()
        self.display_label.setProperty("class", "ForfeitDisplay")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.display_label.font()
        font.setBold(True)
        self.display_label.setFont(font)
        layout.addWidget(self.display_label, 1)

        # Button to change selection - styled like copy buttons
        self.change_button = QtWidgets.QPushButton()
        self.change_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.change_button.setFlat(True)
        self.change_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.change_button.setFixedSize(28, 28)
        self.change_button.setToolTip("Change result")
        self.change_button.setProperty("class", "ChangeButton")

        # Use edit icon
        icon = get_colored_icon("edit.svg", "#555", 14)
        if icon and not icon.isNull():
            self.change_button.setIcon(icon)
            self.change_button.setIconSize(QtCore.QSize(14, 14))
        else:
            # Fallback to text if icon not found
            self.change_button.setText("✎")

        self.change_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                color: #555;
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover {
                background: #e0e4ea;
                color: #222;
            }
            QPushButton:pressed {
                background: #d0d4da;
            }
        """)
        self.change_button.clicked.connect(self._return_to_selector)
        layout.addWidget(self.change_button)

        self.main_layout.addWidget(self.display_widget)

    def _select_forfeit(self, result_const: str):
        """Handle forfeit selection from menu."""
        self._current_result = result_const

        # Update display label
        display_text = {
            RESULT_WHITE_FORFEIT_WIN: "1-0 (Forfeit)",
            RESULT_BLACK_FORFEIT_WIN: "0-1 (Forfeit)",
            RESULT_DOUBLE_FORFEIT: "0-0 (Double Forfeit)",
        }.get(result_const, result_const)

        self.display_label.setText(display_text)

        # Switch to display mode
        self.main_layout.setCurrentWidget(self.display_widget)

    def _return_to_selector(self):
        """Return to selector mode."""
        # Clear any button selections
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.button_group.setExclusive(False)
            checked_button.setChecked(False)
            self.button_group.setExclusive(True)

        # Clear current result if it's a forfeit
        if self._current_result in [
            RESULT_WHITE_FORFEIT_WIN,
            RESULT_BLACK_FORFEIT_WIN,
            RESULT_DOUBLE_FORFEIT,
        ]:
            self._current_result = ""

        # Switch back to selector mode
        self.main_layout.setCurrentWidget(self.selector_widget)

    def selectedResult(self) -> str:
        """
        Get the currently selected result.

        Returns
        -------
        str
            The result constant (RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN,
            RESULT_WHITE_FORFEIT_WIN, RESULT_BLACK_FORFEIT_WIN, or RESULT_DOUBLE_FORFEIT),
            or empty string if no result is selected.
        """
        # Check if a forfeit is selected
        if self._current_result:
            return self._current_result

        # Otherwise check the button group
        checked_button = self.button_group.checkedButton()
        return checked_button.property("result_const") if checked_button else ""

    def setResult(self, result_constant: str):
        """
        Programmatically set the selected result.

        Parameters
        ----------
        result_constant : str
            One of RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN,
            RESULT_WHITE_FORFEIT_WIN, RESULT_BLACK_FORFEIT_WIN, or RESULT_DOUBLE_FORFEIT.
            If the value doesn't match, the selection is cleared.
        """
        # Check if it's a forfeit result
        if result_constant in [
            RESULT_WHITE_FORFEIT_WIN,
            RESULT_BLACK_FORFEIT_WIN,
            RESULT_DOUBLE_FORFEIT,
        ]:
            self._select_forfeit(result_constant)
            return

        # Check if it's a normal result
        for button in self.button_group.buttons():
            if button.property("result_const") == result_constant:
                button.setChecked(True)
                self._current_result = ""
                self.main_layout.setCurrentWidget(self.selector_widget)
                return

        # No match, clear selection
        self._current_result = ""
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.button_group.setExclusive(False)
            checked_button.setChecked(False)
            self.button_group.setExclusive(True)
        self.main_layout.setCurrentWidget(self.selector_widget)
