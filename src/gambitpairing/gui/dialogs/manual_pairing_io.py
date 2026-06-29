"""Pure import/export helpers for ManualPairingDialog."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def build_pairings_export_data(
    round_number: int,
    pairings: Sequence[tuple[Any | None, Any | None]],
    bye_players: Sequence[Any],
) -> dict[str, Any]:
    return {
        "round_number": round_number,
        "pairings": [
            {
                "white": {"id": white.id, "name": white.name} if white else None,
                "black": {"id": black.id, "name": black.name} if black else None,
            }
            for white, black in pairings
        ],
        "bye_players": [
            {"id": player.id, "name": player.name} for player in bye_players
        ],
    }


def parse_pairings_import_data(
    import_data: Mapping[str, Any], player_lookup: Mapping[str, Any]
) -> tuple[list[tuple[Any | None, Any | None]], list[Any]]:
    if not isinstance(import_data, dict) or "pairings" not in import_data:
        raise ValueError("Invalid pairings file format")

    imported_pairings: list[tuple[Any | None, Any | None]] = []
    for pairing_data in import_data["pairings"]:
        white_data = pairing_data.get("white")
        black_data = pairing_data.get("black")
        white = player_lookup.get(white_data["id"]) if white_data else None
        black = player_lookup.get(black_data["id"]) if black_data else None
        imported_pairings.append((white, black))

    imported_byes: list[Any] = []
    if "bye_players" in import_data:
        for bye_data in import_data["bye_players"]:
            bye_player = player_lookup.get(bye_data["id"])
            if bye_player:
                imported_byes.append(bye_player)
    elif "bye_player" in import_data and import_data["bye_player"]:
        bye_data = import_data["bye_player"]
        bye_player = player_lookup.get(bye_data["id"])
        if bye_player:
            imported_byes.append(bye_player)

    return imported_pairings, imported_byes
