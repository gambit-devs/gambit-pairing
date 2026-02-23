"""keep notifications positioned correctly when the parent is resized or moved."""

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

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets


class NotificationEventFilter(QtCore.QObject):
    """Filter events to keep notifications positioned correctly when the parent is resized or moved."""

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent

    def eventFilter(self, obj, event):
        et = event.type()
        # Use Resize, Move and Show events to recompute positions
        if et in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Move,
            QtCore.QEvent.Type.Show,
        ):
            if hasattr(self._parent, "_reposition_notifications"):
                try:
                    self._parent._reposition_notifications()
                except Exception:
                    pass
        return False
