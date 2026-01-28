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

# Layout/animation constants
_MARGIN = 20
_SPACING = 10
_MAX_WIDTH_DEFAULT = 420
_MIN_WIDTH = 120
_SLIDE_DURATION = 420
_PROGRESS_HEIGHT = 4


class NotificationEventFilter(QtCore.QObject):
    """Event filter installed on the parent widget to keep notifications positioned
    correctly when the parent is resized or moved.
    """

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


class Notification(QWidget):
    """A polished notification widget that is a child of the provided parent.

    Features:
    - Slides in/out inside the parent's bounds
    - Hover to pause the timeout progress
    - Click to dismiss immediately
    - Stacks neatly with other notifications
    """

    def __init__(
        self,
        parent: QWidget,
        message: str,
        duration: int = 3000,
        notification_type: str = "info",
    ):
        super().__init__(parent)
        self.parent = parent
        self.duration = max(300, duration)
        self.notification_type = notification_type

        # Sizing
        parent_width = parent.width() if parent is not None else _MAX_WIDTH_DEFAULT
        max_width = max(200, min(_MAX_WIDTH_DEFAULT, parent_width - (_MARGIN * 2)))
        self.setFixedWidth(max_width)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(8)

        # Message
        self.message_label = QLabel(message, self)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(_PROGRESS_HEIGHT)

        layout.addWidget(self.message_label)
        layout.addWidget(self.progress_bar)

        # Finalize size
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

        # Visuals: translucent background and opacity effect for fade
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Internal state
        self._bg_color = QtGui.QColor("#1f2937")
        self._paused = False
        self._closing = False

        # Style and store color
        self._apply_styling()

        # Default positions will be updated by the caller
        start_y = _MARGIN
        start_x = parent_width + _MARGIN
        self.start_pos = QtCore.QPoint(start_x, start_y)
        end_x = max(_MARGIN, parent_width - self.width() - _MARGIN)
        self.end_pos = QtCore.QPoint(end_x, start_y)

        # Make sure the widget is shown as a child and on top of siblings
        self.move(self.start_pos)
        self.show()
        self.raise_()

        # Animations
        self._create_animations()
        self._start_slide_in()

    def _create_animations(self):
        # Position animation
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(_SLIDE_DURATION)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Progress animation
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_anim.setDuration(self.duration)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(100)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.Linear)

        # Fade animation
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(360)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InQuart)

        # Hook up transitions
        self.slide_anim.finished.connect(self._start_progress)
        self.progress_anim.finished.connect(self._start_slide_out)

    def update_position(self, start_pos: QtCore.QPoint, end_pos: QtCore.QPoint):
        """Called by the parent stack manager to set new start/end positions.

        Positions are clamped so the notification always stays inside the parent.
        """
        if self.parent is not None:
            parent_w = self.parent.width()
            # Clamp width to available space
            if self.width() > parent_w - (_MARGIN * 2):
                self.setFixedWidth(max(_MIN_WIDTH, parent_w - (_MARGIN * 2)))
                self.adjustSize()

            end_x = max(_MARGIN, min(end_pos.x(), parent_w - self.width() - _MARGIN))
            start_x = parent_w + _MARGIN
            end_pos = QtCore.QPoint(end_x, end_pos.y())
            start_pos = QtCore.QPoint(start_x, start_pos.y())

        self.start_pos = start_pos
        self.end_pos = end_pos
        self.move(start_pos)

    def _apply_styling(self):
        """Style content colours and fonts and set background color used in paintEvent."""
        nt = self.notification_type
        if nt == "success":
            bg = "#2d5a27"
            text = "#ffffff"
            prog = "#6e8b5b"
        elif nt == "error":
            bg = "#dc2626"
            text = "#ffffff"
            prog = "#f87171"
        elif nt == "warning":
            bg = "#f59e0b"
            text = "#111111"
            prog = "#fbbf24"
        else:
            bg = "#1f2937"
            text = "#ffffff"
            prog = "#6b7280"

        self._bg_color = QtGui.QColor(bg)

        self.message_label.setStyleSheet(
            f"""
            QLabel {{
                color: {text};
                font-size: 11pt;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """
        )

        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: rgba(255,255,255,0.08);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {prog};
                border-radius: 2px;
            }}
        """
        )

    def _start_slide_in(self):
        self.slide_anim.stop()
        self.slide_anim.setStartValue(self.start_pos)
        self.slide_anim.setEndValue(self.end_pos)
        self.slide_anim.start()

    def _start_progress(self):
        # Only start the progress if not paused or closing
        if self._closing:
            return
        try:
            self.progress_anim.start()
        except Exception:
            pass

    def _start_slide_out(self):
        # Prevent double-closing
        if self._closing:
            return
        self._closing = True

        # Stop progress if running
        try:
            if self.progress_anim.state() == QtCore.QAbstractAnimation.State.Running:
                self.progress_anim.stop()
        except Exception:
            pass

        parent_w = (
            self.parent.width()
            if self.parent is not None
            else self.pos().x() + self.width()
        )
        slide_out_pos = QtCore.QPoint(parent_w + _MARGIN, self.pos().y())

        self.slide_out_anim = QPropertyAnimation(self, b"pos")
        self.slide_out_anim.setDuration(360)
        self.slide_out_anim.setStartValue(self.pos())
        self.slide_out_anim.setEndValue(slide_out_pos)
        self.slide_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade at the same time
        self.fade_anim.start()

        def _cleanup():
            try:
                self.deleteLater()
            except Exception:
                pass

        self.slide_out_anim.finished.connect(_cleanup)
        self.slide_out_anim.start()

    def dismiss(self):
        """Public method to dismiss the notification early."""
        self._start_slide_out()

    # Interactivity: pause on hover, click to dismiss
    def enterEvent(self, event: QtCore.QEvent):
        if not self._closing:
            try:
                if (
                    self.progress_anim.state()
                    == QtCore.QAbstractAnimation.State.Running
                ):
                    self.progress_anim.pause()
                    self._paused = True
            except Exception:
                pass
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent):
        if self._paused and not self._closing:
            try:
                self.progress_anim.resume()
                self._paused = False
            except Exception:
                pass
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        # Click anywhere to dismiss immediately
        self.dismiss()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Soft shadow (drawn as a translucent rounded rect behind the widget)
        shadow_color = QtGui.QColor(0, 0, 0, 48)
        shadow_rect = self.rect().adjusted(4, 6, -4, -4)
        painter.setBrush(shadow_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        path_shadow = QPainterPath()
        path_shadow.addRoundedRect(QtCore.QRectF(shadow_rect), 12, 12)
        painter.drawPath(path_shadow)

        # Main rounded background
        path = QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), 12, 12)

        painter.setBrush(self._bg_color)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 18), 1))
        painter.drawPath(path)

        super().paintEvent(event)


def show_notification(
    parent: QWidget, message: str, duration: int = 3000, notification_type: str = "info"
) -> Notification:
    """Create and show a ModernNotification inside `parent` and return it.

    The parent will get a `_notification_stack` list and a `_reposition_notifications`
    callable which keeps notifications stacked and inside the parent's bounds.
    """
    if not hasattr(parent, "_notification_stack"):
        parent._notification_stack = []

    if not hasattr(parent, "_notification_event_filter"):
        parent._notification_event_filter = NotificationEventFilter(parent)
        parent.installEventFilter(parent._notification_event_filter)

    def _reposition_notifications():
        y_offset = _MARGIN
        p_w = parent.width()
        p_h = parent.height()

        for notif in list(parent._notification_stack):
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

    parent._reposition_notifications = _reposition_notifications

    notification = Notification(parent, message, duration, notification_type)
    parent._notification_stack.append(notification)

    # Reposition stack immediately
    try:
        parent._reposition_notifications()
    except Exception:
        pass

    def _cleanup():
        if notification in parent._notification_stack:
            parent._notification_stack.remove(notification)
            try:
                parent._reposition_notifications()
            except Exception:
                pass

    notification.destroyed.connect(_cleanup)

    return notification


# Legacy function kept for backward compatibility
def show_legacy_notification(parent, message: str, duration: int = 1500):
    notif = QtWidgets.QLabel(message, parent)
    notif.setStyleSheet(
        """
        QLabel {
            background: rgba(30,30,30,220);
            color: white;
            border-radius: 10px;
            padding: 12px 32px;
            font-size: 13pt;
            font-weight: 700;
            min-width: 200px;
            qproperty-alignment: AlignCenter;
            border: 1px solid rgba(0,0,0,0.18);
        }
    """
    )
    notif.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
    notif.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
    notif.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    notif.adjustSize()
    geo = parent.geometry()
    notif_geo = notif.frameGeometry()
    x = (geo.width() - notif_geo.width()) // 2
    y = geo.height() - notif_geo.height() - 48
    notif.move(x, y)
    notif.setWindowOpacity(0.0)
    notif.show()
    notif.raise_()
    anim_in = QtCore.QPropertyAnimation(notif, b"windowOpacity", parent)
    anim_in.setDuration(250)
    anim_in.setStartValue(0.0)
    anim_in.setEndValue(1.0)

    def start_fade_out():
        anim_out = QtCore.QPropertyAnimation(notif, b"windowOpacity", parent)
        anim_out.setDuration(600)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.finished.connect(notif.close)
        anim_out.start()

    anim_in.finished.connect(lambda: QtCore.QTimer.singleShot(duration, start_fade_out))
    anim_in.start()
