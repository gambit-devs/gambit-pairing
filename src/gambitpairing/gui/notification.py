"""Handle Notification widget functionality."""

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
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from gambitpairing.widgets.notification import Notification


def show_notification(
    parent: QWidget, message: str, duration: int = 3000, notification_type: str = "info"
) -> Notification:
    """Create and return a Notification inside `parent`.

    The parent will get a `_notification_stack` list and a `_reposition_notifications`
    callable which keeps notifications stacked and inside the parent's bounds.
    """
    if not hasattr(parent, "_notification_stack"):
        parent._notification_stack = []

    if not hasattr(parent, "_notification_event_filter"):
        parent._notification_event_filter = NotificationEventFilter(parent)
        parent.installEventFilter(parent._notification_event_filter)

    parent._reposition_notifications = _reposition_notifications

    notification = Notification(parent, message, duration, notification_type)
    parent._notification_stack.append(notification)

    # Reposition stack immediately
    try:
        parent._reposition_notifications()
    except Exception:
        pass

    notification.destroyed.connect(_cleanup)

    return notification


def _reposition_notifications(note_stack):
    y_offset = _MARGIN
    p_w = parent.width()
    p_h = parent.height()

    for notif in list(note_stack):
        if notif is None:
            continue

        # Ensure width fits
        if notif.width() > p_w - (_MARGIN * 2):
            notif.setFixedWidth(max(_MIN_WIDTH, p_w - (_MARGIN * 2)))
            notif.adjustSize()

        target_x = max(_MARGIN, p_w - notif.width() - _MARGIN)
        target_y = y_offset
        start_x = p_w + _MARGIN

        notif.update_position(
            QtCore.QPoint(start_x, target_y), QtCore.QPoint(target_x, target_y)
        )
        notif.move(notif.pos().x(), target_y)
        notif.raise_()

        y_offset += notif.height() + _SPACING

        # If overflow vertically, clamp to bottom area
        if target_y + notif.height() > p_h - _MARGIN:
            new_y = max(_MARGIN, p_h - notif.height() - _MARGIN)
            notif.move(notif.pos().x(), new_y)


def _cleanup_notifications(parent: QWidget):
    if notification in parent._notification_stack:
        parent._notification_stack.remove(notification)
        parent._reposition_notifications()
