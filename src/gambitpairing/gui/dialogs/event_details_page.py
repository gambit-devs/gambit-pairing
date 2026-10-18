"""Event details page, shared by the New Tournament and Tournament Settings dialogs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.tournament import EventDetails

# The date edits show "Not set" at this date, so an unset date stays unset.
NOT_SET_DATE = QtCore.QDate(1900, 1, 1)


class EventDetailsPage(QtWidgets.QWidget):
    """Edit where, when and by whom a tournament is run."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        event: Optional[EventDetails] = None,
    ) -> None:
        super().__init__(parent)
        load_ui_into(self, "event_details_page.ui")
        self.city_edit = required_child(self, QtWidgets.QLineEdit, "city_edit")
        self.federation_edit = required_child(
            self, QtWidgets.QLineEdit, "federation_edit"
        )
        self.start_date_edit = required_child(
            self, QtWidgets.QDateEdit, "start_date_edit"
        )
        self.end_date_edit = required_child(self, QtWidgets.QDateEdit, "end_date_edit")
        self.chief_arbiter_edit = required_child(
            self, QtWidgets.QLineEdit, "chief_arbiter_edit"
        )
        self.deputy_arbiter_edit = required_child(
            self, QtWidgets.QLineEdit, "deputy_arbiter_edit"
        )
        self.time_control_edit = required_child(
            self, QtWidgets.QLineEdit, "time_control_edit"
        )
        self.set_event(event or EventDetails())

    def set_event(self, event: EventDetails) -> None:
        self.city_edit.setText(event.city)
        self.federation_edit.setText(event.federation)
        self.start_date_edit.setDate(_to_qdate(event.start_date))
        self.end_date_edit.setDate(_to_qdate(event.end_date))
        self.chief_arbiter_edit.setText(event.chief_arbiter)
        self.deputy_arbiter_edit.setText(event.deputy_arbiter)
        self.time_control_edit.setText(event.time_control)

    def event_details(self) -> EventDetails:
        return EventDetails(
            city=self.city_edit.text().strip(),
            federation=self.federation_edit.text().strip().upper(),
            start_date=_to_date(self.start_date_edit.date()),
            end_date=_to_date(self.end_date_edit.date()),
            chief_arbiter=self.chief_arbiter_edit.text().strip(),
            deputy_arbiter=self.deputy_arbiter_edit.text().strip(),
            time_control=self.time_control_edit.text().strip(),
        )

    def validation_error(self) -> Optional[str]:
        """Return why the page cannot be saved yet, or None when it can."""
        start = self.start_date_edit.date()
        end = self.end_date_edit.date()
        if start != NOT_SET_DATE and end != NOT_SET_DATE and end < start:
            return "The end date is before the start date."
        return None


def _to_qdate(value: Optional[date]) -> QtCore.QDate:
    if value is None:
        return NOT_SET_DATE
    return QtCore.QDate(value.year, value.month, value.day)


def _to_date(value: QtCore.QDate) -> Optional[date]:
    if value == NOT_SET_DATE or not value.isValid():
        return None
    return date(value.year(), value.month(), value.day())
