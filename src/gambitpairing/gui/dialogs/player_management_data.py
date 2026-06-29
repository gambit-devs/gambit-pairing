"""Pure data helpers for PlayerManagementDialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gambitpairing.models.player import Player


@dataclass(frozen=True)
class PlayerFormFields:
    name: str
    rating: int
    gender_text: str
    date_of_birth: str
    phone: str
    email: str
    club: str
    federation: str
    fide_id: str = ""
    fide_title: str = ""
    fide_standard: str = ""
    fide_rapid: str = ""
    fide_blitz: str = ""


@dataclass(frozen=True)
class TournamentPlayerRow:
    player_id: str
    name: str
    rating: str
    age: str
    gender: str


def gender_code_from_display(gender_text: str) -> str | None:
    if gender_text == "Male":
        return "M"
    if gender_text == "Female":
        return "F"
    return None


def gender_display_from_code(gender: str | None) -> str:
    if gender == "M":
        return "Male"
    if gender == "F":
        return "Female"
    return ""


def optional_int_from_text(text: str) -> int | None:
    stripped = text.strip()
    return int(stripped) if stripped.isdigit() else None


def has_fide_fields(fields: PlayerFormFields) -> bool:
    return any(
        [
            fields.fide_id,
            fields.fide_title,
            fields.fide_standard,
            fields.fide_rapid,
            fields.fide_blitz,
        ]
    )


def build_player_data_from_fields(
    fields: PlayerFormFields,
    include_fide_fields: bool,
    selected_birth_year: Any = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": fields.name.strip(),
        "rating": fields.rating,
        "gender": gender_code_from_display(fields.gender_text),
        "date_of_birth": fields.date_of_birth,
        "phone": fields.phone.strip(),
        "email": fields.email.strip(),
        "club": fields.club.strip(),
        "federation": fields.federation.strip(),
    }
    if include_fide_fields:
        data.update(
            {
                "fide_id": optional_int_from_text(fields.fide_id),
                "fide_title": fields.fide_title.strip() or None,
                "fide_standard": optional_int_from_text(fields.fide_standard),
                "fide_rapid": optional_int_from_text(fields.fide_rapid),
                "fide_blitz": optional_int_from_text(fields.fide_blitz),
            }
        )
        if selected_birth_year is not None:
            data["birth_year"] = selected_birth_year
    return data


def project_tournament_player_row(player: Player) -> TournamentPlayerRow:
    age = player.age
    return TournamentPlayerRow(
        player_id=player.id,
        name=player.name,
        rating=str(player.rating),
        age=str(age) if age is not None else "",
        gender=gender_display_from_code(player.gender),
    )


def search_result_count_text(count: int) -> str:
    if count == 1:
        return (
            "Found 1 player. Double-click or select and click "
            "'Import Selected Player' to use."
        )
    return (
        f"Found {count} players. Double-click or select and click "
        "'Import Selected Player' to use."
    )
