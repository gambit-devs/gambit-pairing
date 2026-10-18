"""Add players found by search to a tournament, several at a time.

The search results are the standardized dictionaries that
``MergedSearchRow.player_data`` returns. This module turns them into players,
skips anyone the tournament already has, and reports what happened. It has no
Qt code, so the Add Player window and the Players view share one rule set.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from gambitpairing.exceptions import InvalidPlayerDataException
from gambitpairing.models.player import Player, create_player_from_dict

NAME_TAKEN = "name already in the tournament"
FIDE_ID_TAKEN = "FIDE ID already in the tournament"
CFC_ID_TAKEN = "CFC ID already in the tournament"


@dataclass(frozen=True)
class RegistrationResult:
    """The players added, and the rows skipped with the reason for each."""

    added: tuple[Player, ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()

    def describe(self) -> str:
        """Return a one-line summary for the status bar and the dialog."""
        text = f"Added {len(self.added)} player{_plural(len(self.added))}"
        if self.skipped:
            text += (
                f"; skipped {len(self.skipped)} already in the tournament or invalid"
            )
        return text + "."


def _plural(count: int) -> str:
    return "" if count == 1 else "s"


def _as_int(value: Any) -> Optional[int]:
    """Return ``value`` as an int, or None when it is blank, zero or not a number."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value or None
    text = str(value).strip()
    if not text.isdigit():
        return None
    return int(text) or None


def registration_data(search: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a search result into the dictionary the player factory accepts.

    Blank contact fields are left empty, as the Add Player form leaves them
    when a search result fills it. Dates become ISO strings, as the form's
    date field produces.
    """
    birth = search.get("date_of_birth")
    data: dict[str, Any] = {
        "name": str(search.get("name") or "").strip(),
        "rating": _as_int(search.get("rating")) or 0,
        "gender": search.get("gender") or None,
        "date_of_birth": (
            birth.isoformat() if isinstance(birth, date) else (birth or "")
        ),
        "federation": str(search.get("federation") or "").strip(),
        "phone": "",
        "email": "",
        "club": "",
    }
    for key in ("fide_id", "fide_standard", "fide_rapid", "fide_blitz", "cfc_id"):
        number = _as_int(search.get(key))
        if number:
            data[key] = number
    title = str(search.get("fide_title") or "").strip()
    if title:
        data["fide_title"] = title
    return data


def registered_reason(
    players: Iterable[Any], search: Mapping[str, Any]
) -> Optional[str]:
    """Return why the search result is already in ``players``, or None if it is new."""
    name = str(search.get("name") or "").strip()
    fide_id = _as_int(search.get("fide_id"))
    cfc_id = _as_int(search.get("cfc_id"))
    for player in players:
        if name and player.name == name:
            return NAME_TAKEN
        if fide_id and _as_int(getattr(player, "fide_id", None)) == fide_id:
            return FIDE_ID_TAKEN
        if cfc_id and _as_int(getattr(player, "cfc_id", None)) == cfc_id:
            return CFC_ID_TAKEN
    return None


def add_registrations(
    tournament: Any, search_results: Sequence[Mapping[str, Any]]
) -> RegistrationResult:
    """Add each new search result to ``tournament`` and skip the rest.

    A result is skipped when its name, FIDE ID or CFC ID is already in the
    tournament, including by an earlier row of the same batch. Invalid rows
    are skipped with the reason from the player factory.
    """
    added: list[Player] = []
    skipped: list[tuple[str, str]] = []
    for search in search_results:
        data = registration_data(search)
        name = data["name"] or "(no name)"
        if not data["name"]:
            skipped.append((name, "no name"))
            continue
        existing = [*tournament.players.values(), *added]
        reason = registered_reason(existing, data)
        if reason:
            skipped.append((name, reason))
            continue
        try:
            player = create_player_from_dict(data)
        except InvalidPlayerDataException as error:
            skipped.append((name, str(error)))
            continue
        tournament.add_player(player)
        added.append(player)
    return RegistrationResult(tuple(added), tuple(skipped))
