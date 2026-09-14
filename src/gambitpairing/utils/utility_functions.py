"""Utility function used in Gambit Pairing."""

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


from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QListWidget

from .identity import generate_id


# --- Utility Functions ---
def resize_list_to_show_all_items(list_widget: QListWidget) -> None:
    """Let Qt size a list to its contents while retaining native scrolling."""
    list_widget.setSizeAdjustPolicy(
        QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
    )
    list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    list_widget.updateGeometry()
