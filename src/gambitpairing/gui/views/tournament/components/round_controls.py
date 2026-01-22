from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from gambitpairing.gui.gui_utils import get_colored_icon
from gambitpairing.resources.resource_utils import get_resource_path


class RoundControlsWidget(QtWidgets.QWidget):
    """
    Widget containing the primary tournament controls (Start, Next Round, Record, Undo).
    """

    start_requested = pyqtSignal()
    prepare_requested = pyqtSignal()
    record_requested = pyqtSignal()
    undo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "ActionFooter")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Left side: Secondary actions
        left_actions = QtWidgets.QHBoxLayout()
        left_actions.setSpacing(8)

        # Undo button
        self.btn_undo = QtWidgets.QPushButton("Undo")
        self.btn_undo.setIcon(get_colored_icon("undo.svg", "#2d5a27", 16))
        self.btn_undo.setToolTip("Undo the last recorded round results")
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        left_actions.addWidget(self.btn_undo)

        layout.addLayout(left_actions)
        layout.addStretch()

        # Right side: Primary action
        self.btn_primary_action = QtWidgets.QPushButton("Start Tournament")
        self.btn_primary_action.setIconSize(QtCore.QSize(16, 16))
        self.btn_primary_action.setToolTip(
            "Start the tournament and generate first round pairings"
        )
        self.btn_primary_action.clicked.connect(self._on_primary_action_clicked)
        layout.addWidget(self.btn_primary_action)

        # Internal state to track what the primary button should do
        self._primary_action_state = "start"  # start, prepare, record

    def update_state(self, state: str):
        """
        Update the state of the controls based on tournament phase.

        Args:
            state: One of 'start', 'prepare', 'record', 'finished'
        """
        self._primary_action_state = state

        if state == "start":
            self.btn_primary_action.setText("Start Tournament")
            play_icon_path = get_resource_path("play.svg", subpackage="icons")
            self.btn_primary_action.setIcon(QtGui.QIcon(str(play_icon_path)))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip(
                "Start the tournament and generate first round pairings"
            )
        elif state == "prepare":
            self.btn_primary_action.setText("Prepare Next Round")
            refresh_icon_path = get_resource_path("refresh.svg", subpackage="icons")
            self.btn_primary_action.setIcon(QtGui.QIcon(str(refresh_icon_path)))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Generate pairings for the next round")
        elif state == "record":
            self.btn_primary_action.setText("Record Results")
            self.btn_primary_action.setIcon(
                get_colored_icon("checkmark-white.svg", "black", 16)
            )
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Save results and advance to next round")
        elif state == "finished":
            self.btn_primary_action.setText("Tournament Finished")
            self.btn_primary_action.setIcon(QtGui.QIcon())  # No icon for finished
            self.btn_primary_action.setEnabled(False)
            self.btn_primary_action.setToolTip("All rounds completed")

    def set_undo_enabled(self, enabled: bool):
        self.btn_undo.setEnabled(enabled)

    def _on_primary_action_clicked(self):
        if self._primary_action_state == "start":
            self.start_requested.emit()
        elif self._primary_action_state == "prepare":
            self.prepare_requested.emit()
        elif self._primary_action_state == "record":
            self.record_requested.emit()
