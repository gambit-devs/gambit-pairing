from gambitpairing.gui.views.players.players_view_workflow import (
    build_duplicate_player_prompt,
    build_export_success_status,
    build_export_unavailable_prompt,
    build_import_empty_prompt,
    build_import_success_history,
    build_import_success_notification,
    build_player_tooltip,
    build_remove_player_prompt,
    project_player_table_row,
)
from gambitpairing.models.player import FidePlayer, Player


def test_player_table_projection_for_active_and_inactive_players():
    player = Player("Ada", 1800, gender="Female", federation="CAN")
    projection = project_player_table_row(player)

    assert projection.name == "Ada"
    assert projection.rating == "1800"
    assert projection.age == ""
    assert projection.status == "Active"
    assert not projection.inactive
    assert "Federation: CAN" in projection.tooltip

    player.is_active = False
    assert project_player_table_row(player).status == "Inactive"
    assert project_player_table_row(player).inactive


def test_player_tooltip_includes_fide_fields_when_available():
    player = FidePlayer(
        "Titled Player",
        fide_id=1234,
        fide_title="FM",
        fide_standard=2100,
        fide_rapid=2050,
        fide_blitz=2000,
    )

    tooltip = build_player_tooltip(player)

    assert "FIDE ID: 1234" in tooltip
    assert "Title: FM" in tooltip
    assert "Std: 2100" in tooltip
    assert "Rapid: 2050" in tooltip
    assert "Blitz: 2000" in tooltip


def test_player_workflow_prompt_and_status_text_helpers():
    assert build_remove_player_prompt("Ada").message == (
        "Remove player 'Ada' permanently?"
    )
    assert build_duplicate_player_prompt("Ada").message == (
        "Player 'Ada' already exists."
    )
    assert build_import_success_history(3, "C:/tmp/players.csv") == (
        "Imported 3 players from C:/tmp/players.csv."
    )
    assert build_import_success_notification(3, "C:/tmp/players.csv") == (
        "Imported 3 players from players.csv"
    )
    assert build_import_empty_prompt().title == "Import Notice"
    assert build_export_unavailable_prompt().message == (
        "No players available to export."
    )
    assert build_export_success_status("out.csv") == "Players exported to out.csv"
