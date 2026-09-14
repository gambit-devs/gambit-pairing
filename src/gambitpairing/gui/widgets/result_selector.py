"""Compact result cell used by the Rounds workspace.

The original widget exposed three permanent buttons.  That API is retained
for older callers, while the compact variant used by the Rounds tab presents
one spreadsheet-like cell that opens a small result menu.
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from gambitpairing.constants import (
    RESULT_BLACK_FORFEIT_WIN,
    RESULT_BLACK_WIN,
    RESULT_DOUBLE_FORFEIT,
    RESULT_DRAW,
    RESULT_WHITE_FORFEIT_WIN,
    RESULT_WHITE_WIN,
)
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class ResultSelector(QtWidgets.QWidget):
    """A result cell with normal and exceptional result choices.

    ``compact=True`` is the Rounds-tab presentation.  The legacy button
    attributes remain available in both modes so existing integrations and
    tests can continue to use ``setResult``/``selectedResult``.
    """

    result_changed = QtCore.pyqtSignal(str, str)
    activated = QtCore.pyqtSignal()
    key_pressed = QtCore.pyqtSignal(int, str, int)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        load_ui_into(self, "result_selector.ui")

        self.compact = compact
        self._current_result = ""

        self.btn_white_win = required_child(
            self, QtWidgets.QPushButton, "btn_white_win"
        )
        self.btn_draw = required_child(self, QtWidgets.QPushButton, "btn_draw")
        self.btn_black_win = required_child(
            self, QtWidgets.QPushButton, "btn_black_win"
        )

        self.btn_white_win.setText("1-0")
        self.btn_white_win.setToolTip("White wins")

        self.btn_draw.setText("½-½")
        self.btn_draw.setToolTip("Draw")

        self.btn_black_win.setText("0-1")
        self.btn_black_win.setToolTip("Black wins")

        self._button_results = {
            self.btn_white_win: RESULT_WHITE_WIN,
            self.btn_draw: RESULT_DRAW,
            self.btn_black_win: RESULT_BLACK_WIN,
        }

        for button in (self.btn_white_win, self.btn_draw, self.btn_black_win):
            button.setCheckable(True)

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)
        for button in (
            self.btn_white_win,
            self.btn_draw,
            self.btn_black_win,
        ):
            self.button_group.addButton(button)
        self.button_group.buttonClicked.connect(self._on_legacy_button_clicked)

        self.menu_button = QtWidgets.QToolButton()
        self.menu_button.setObjectName("result_menu_button")
        self.menu_button.setToolTip("Choose result (1, D, or 0)")
        self.menu_button.setAccessibleName("Result")
        self.menu_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.menu_button.setAutoRaise(True)
        self.menu_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.menu_button.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.menu_button.pressed.connect(self.activated.emit)

        self.result_menu = QtWidgets.QMenu(self)
        self.result_menu.addAction("1-0", lambda: self.setResult(RESULT_WHITE_WIN))
        self.result_menu.addAction("½-½", lambda: self.setResult(RESULT_DRAW))
        self.result_menu.addAction("0-1", lambda: self.setResult(RESULT_BLACK_WIN))
        self.result_menu.addSeparator()
        self.forfeit_menu = self.result_menu.addMenu("Other...")
        self.forfeit_menu.addAction(
            "White wins by forfeit",
            lambda: self.setResult(RESULT_WHITE_FORFEIT_WIN),
        )
        self.forfeit_menu.addAction(
            "Black wins by forfeit",
            lambda: self.setResult(RESULT_BLACK_FORFEIT_WIN),
        )
        self.forfeit_menu.addAction(
            "Double forfeit",
            lambda: self.setResult(RESULT_DOUBLE_FORFEIT),
        )
        self.menu_button.setMenu(self.result_menu)

        layout = self.layout()
        if layout is not None:
            if compact:
                for button in (
                    self.btn_white_win,
                    self.btn_draw,
                    self.btn_black_win,
                ):
                    button.hide()
                layout.addWidget(self.menu_button)
            else:
                self.menu_button.setText("More")
                layout.addWidget(self.menu_button)

        if compact:
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._refresh_display()

    def selectedResult(self) -> str:
        """Return the result constant or an empty string for a blank cell."""
        if self._current_result:
            return self._current_result
        checked_button = self.button_group.checkedButton()
        return (
            self._button_results.get(checked_button, "")
            if isinstance(checked_button, QtWidgets.QPushButton)
            else ""
        )

    def displayText(self) -> str:
        """Return the short value shown in the compact result cell."""
        return self.formatResult(self.selectedResult()) or "—"

    @staticmethod
    def formatResult(result: str) -> str:
        """Format an internal result constant for the operator-facing UI."""
        return "½-½" if result == RESULT_DRAW else result

    def _on_legacy_button_clicked(self, button: QtWidgets.QAbstractButton) -> None:
        result = (
            self._button_results.get(button, "")
            if isinstance(button, QtWidgets.QPushButton)
            else ""
        )
        if result:
            self._set_result(result, emit=True)

    def _set_result(self, result_constant: str, emit: bool) -> None:
        previous = self.selectedResult()
        valid_results = {
            "",
            RESULT_WHITE_WIN,
            RESULT_DRAW,
            RESULT_BLACK_WIN,
            RESULT_WHITE_FORFEIT_WIN,
            RESULT_BLACK_FORFEIT_WIN,
            RESULT_DOUBLE_FORFEIT,
        }
        result = result_constant if result_constant in valid_results else ""

        self._current_result = ""
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.button_group.setExclusive(False)
            checked_button.setChecked(False)
            self.button_group.setExclusive(True)

        if result in {RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN}:
            for button, button_result in self._button_results.items():
                if button_result == result:
                    button.setChecked(True)
                    break
        elif result in {
            RESULT_WHITE_FORFEIT_WIN,
            RESULT_BLACK_FORFEIT_WIN,
            RESULT_DOUBLE_FORFEIT,
        }:
            self._current_result = result

        self._refresh_display()
        if emit and previous != result:
            self.result_changed.emit(result, previous)

    def setResult(self, result_constant: str, emit: bool = True) -> None:
        """Set the selected result, preserving the legacy public API."""
        self._set_result(result_constant, emit=emit)

    def clearResult(self, emit: bool = True) -> None:
        """Clear the cell back to a blank result."""
        self._set_result("", emit=emit)

    def setEditable(self, editable: bool) -> None:
        """Enable or disable mouse and menu entry for this result cell."""
        self.setEnabled(editable)
        self.menu_button.setEnabled(editable)
        for button in self.button_group.buttons():
            button.setEnabled(editable)

    def _refresh_display(self) -> None:
        if not self.compact:
            return
        result = self.selectedResult()
        self.menu_button.setText(self.displayText())
        self.menu_button.setToolTip(
            f"{result or 'Blank'} result — click for options; 1, D, 0 to enter"
        )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.compact and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.activated.emit()
            self.menu_button.showMenu()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Forward keyboard input to the containing pairing table."""
        if self.compact:
            self.key_pressed.emit(event.key(), event.text(), event.modifiers().value)
            event.accept()
            return
        super().keyPressEvent(event)
