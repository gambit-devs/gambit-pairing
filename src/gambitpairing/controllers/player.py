"""Backend helpers for importing and exporting tournament players."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import List, Tuple

from gambitpairing.models.player import Player, create_player


def import_players_from_csv(
    file_path: str | Path,
    existing_players: Iterable[Player] = (),
) -> Tuple[int, List[Player]]:
    """Read players from a CSV file without touching GUI state."""
    if not file_path:
        return 0, []

    existing_names = {player.name for player in existing_players}
    imported_players: List[Player] = []

    with Path(file_path).open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            name = (row.get("Name") or row.get("name") or "").strip()
            if not name or name in existing_names:
                continue

            rating_text = (row.get("Rating") or row.get("rating") or "").strip()
            rating = int(rating_text) if rating_text.isdigit() else None

            player = create_player(
                name=name,
                rating=rating,
                gender=row.get("Gender") or row.get("gender"),
                date_of_birth=row.get("Date of Birth")
                or row.get("date_of_birth")
                or row.get("dob"),
                phone=row.get("Phone") or row.get("phone"),
                email=row.get("Email") or row.get("email"),
                club=row.get("Club") or row.get("club"),
                federation=row.get("Federation") or row.get("federation"),
            )
            imported_players.append(player)
            existing_names.add(name)

    return len(imported_players), imported_players


def export_players_to_csv(
    players: Iterable[Player] | Mapping[str, Player],
    file_path: str | Path,
) -> None:
    """Write players to a CSV file without depending on Qt widgets."""
    if isinstance(players, Mapping):
        player_iterable = players.values()
    else:
        player_iterable = players

    sorted_players = sorted(player_iterable, key=lambda player: player.name)
    if not file_path:
        raise RuntimeError("export_players_to_csv(...) needs a file path.")

    with Path(file_path).open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "Name",
                "Rating",
                "Gender",
                "Date of Birth",
                "Phone",
                "Email",
                "Club",
                "Federation",
                "Active",
                "ID",
            ]
        )
        for player in sorted_players:
            writer.writerow(
                [
                    player.name,
                    player.rating if player.rating is not None else "",
                    player.gender or "",
                    player.dob or "",
                    player.phone or "",
                    player.email or "",
                    player.club or "",
                    player.federation or "",
                    "Yes" if player.is_active else "No",
                    player.id,
                ]
            )
