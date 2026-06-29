"""CFC player placeholder model.

The CFC integration is not wired into the tournament workflow yet. This module
keeps a small importable data shape instead of the stale ORM sketch that was
previously here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CfcPlayerRecord:
    """Basic Canadian Chess Federation player metadata."""

    cfc_id: Optional[int] = None
    fide_id: Optional[int] = None
    name_first: Optional[str] = None
    name_last: Optional[str] = None
    addr_city: Optional[str] = None
    addr_province: Optional[str] = None
    regular_rating: Optional[int] = None
    quick_rating: Optional[int] = None

    @property
    def display_name(self) -> str:
        return " ".join(part for part in [self.name_first, self.name_last] if part)
