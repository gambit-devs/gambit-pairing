"""Facts about the event itself: where it is held, who runs it, and when.

These describe the tournament rather than any one export, so they are stored
with the tournament and reused by every report that needs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class EventDetails:
    """City, federation, dates, arbiters and time control of an event.

    Every field is optional. An unset field is blank, or None for the dates.
    """

    city: str = ""
    federation: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    chief_arbiter: str = ""
    deputy_arbiter: str = ""
    time_control: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "federation": self.federation,
            "start_date": _iso(self.start_date),
            "end_date": _iso(self.end_date),
            "chief_arbiter": self.chief_arbiter,
            "deputy_arbiter": self.deputy_arbiter,
            "time_control": self.time_control,
        }

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> "EventDetails":
        """Read stored details; missing or unreadable values stay unset."""
        data = data or {}
        return cls(
            city=_text(data.get("city")),
            federation=_text(data.get("federation")).upper(),
            start_date=_parse_date(data.get("start_date")),
            end_date=_parse_date(data.get("end_date")),
            chief_arbiter=_text(data.get("chief_arbiter")),
            deputy_arbiter=_text(data.get("deputy_arbiter")),
            time_control=_text(data.get("time_control")),
        )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iso(value: Optional[date]) -> str:
    return value.isoformat() if value else ""


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or ""))
    except ValueError:
        return None
