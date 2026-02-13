from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon


class TabHeader(QtWidgets.QWidget):
    """
    A universal header widget for all tabs.
    Displays a title, an optional icon, and a container for action buttons.
    """

    def __init__(self, title: str, icon_name: str = None, parent=None):
        super().__init__(parent)
        self.setProperty("class", "TabHeader")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(12)

        # Top row: Icon, Title, Spacer, Actions
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(12)

        # Icon (optional)
        if icon_name:
            self.icon_label = QtWidgets.QLabel()
            set_svg_icon(self.icon_label, icon_name, "#2d5a27", 24)
            top_row.addWidget(self.icon_label)

        # Title
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setProperty("class", "TabTitle")
        font = self.title_label.font()
        font.setPointSize(20)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #2d5a27; padding-top: 4px;")
        top_row.addWidget(self.title_label)

        top_row.addStretch()

        # Action buttons container
        self.actions_layout = QtWidgets.QHBoxLayout()
        self.actions_layout.setSpacing(8)
        top_row.addLayout(self.actions_layout)

        layout.addLayout(top_row)

        # Separator line
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #e0e0e0; margin-top: 4px;")
        layout.addWidget(line)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def add_action_button(
        self, icon_name: str, tooltip: str, callback
    ) -> QtWidgets.QPushButton:
        """Adds an action button to the header."""
        btn = QtWidgets.QPushButton()
        icon = get_colored_icon(icon_name, "#2d5a27", 24)
        btn.setIcon(icon)
        btn.setProperty("class", "IconButton")
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Basic styling for icon button if class not defined
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #e0e4ea;
            }
            QPushButton:pressed {
                background-color: #d0d4da;
            }
        """)

        self.actions_layout.addWidget(btn)
        return btn
