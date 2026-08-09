"""Test-visible inventory for the MVC/UI refactor boundary."""

from __future__ import annotations

UI_REFACTOR_BOUNDARY_RULES: tuple[str, ...] = (
    "Static layout belongs in Designer .ui files.",
    "Behavior, signal wiring, and runtime state belong in Python.",
    "Styling belongs in QSS resources.",
    "Models hold data only.",
    "Representation and persistence own serialization and save/load.",
    "Qt-free domain logic must not live in GUI modules.",
    "GUI dependencies must not leak into domain modules.",
)

DESIGNER_BACKED_UI_FILES: tuple[str, ...] = (
    "about_dialog.ui",
    "crosstable_view.ui",
    "history_view.ui",
    "main_window.ui",
    "manual_pairing_dialog.ui",
    "new_tournament_dialog.ui",
    "pairings_table.ui",
    "pairing_info_dialog.ui",
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
    "unsaved_changes_dialog.ui",
)

REMAINING_PYTHON_BUILT_LAYOUTS: tuple[str, ...] = ()

DYNAMIC_WIDGET_EXCEPTIONS: tuple[str, ...] = (
    "DroppableByeListWidget",
    "DroppableTableWidget",
    "DragListWidget",
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
    "player_import_workflow",
    "manual_pairing_state",
    "manual_pairing_io",
    "manual_pairing_controller",
    "tournament_view_workflow",
    "tournament_printing",
)

PAIRING_ENGINE_GUARDED_FILES: tuple[str, ...] = (
    "src/gambitpairing/controllers/pairing/dutch_swiss.py",
    "src/gambitpairing/controllers/pairing/round_robin.py",
)
