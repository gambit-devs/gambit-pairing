"""Test-visible inventory for the MVC/UI refactor boundary."""

from __future__ import annotations

DESIGNER_BACKED_UI_FILES: tuple[str, ...] = (
    "about_dialog.ui",
    "crosstable_view.ui",
    "history_view.ui",
    "main_window.ui",
    "manual_pairing_dialog.ui",
    "new_tournament_dialog.ui",
    "pairings_table.ui",
    "player_management_dialog.ui",
    "player_placeholder.ui",
    "players_view.ui",
    "pre_tournament_start.ui",
    "print_options_dialog.ui",
    "result_selector.ui",
    "round_controls.ui",
    "round_progress_indicator.ui",
    "standings_view.ui",
    "tab_header.ui",
    "tournament_placeholder.ui",
    "tournament_settings_dialog.ui",
    "tournament_view.ui",
    "update_download_dialog.ui",
    "update_prompt_dialog.ui",
)

REMAINING_PYTHON_BUILT_LAYOUTS: tuple[str, ...] = (
    "GambitPairingMainWindow toolbar tournament-info widget",
    "ManualPairingDialog dynamic dock, toolbar, bye list, and pairings panel",
    "PlayerManagementDialog tab interiors for details/import/tournament players",
    "Notification popup body",
)

DYNAMIC_WIDGET_EXCEPTIONS: tuple[str, ...] = (
    "DroppableByeListWidget",
    "DroppableTableWidget",
    "DragListWidget",
    "DragTableWidget",
    "NumericTableWidgetItem",
)

EXTRACTED_WORKFLOW_HELPERS: tuple[str, ...] = (
    "main_window_state",
    "main_window_file_flow",
    "main_window_save_flow",
    "main_window_tournament_flow",
    "update_workflow",
    "players_view_workflow",
    "standings_presentation",
    "player_management_data",
    "manual_pairing_state",
    "manual_pairing_io",
    "tournament_view_workflow",
    "tournament_printing",
)

PAIRING_ENGINE_GUARDED_FILES: tuple[str, ...] = (
    "src/gambitpairing/controllers/pairing/dutch_swiss.py",
    "src/gambitpairing/controllers/pairing/round_robin.py",
)
