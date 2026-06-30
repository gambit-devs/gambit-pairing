from pathlib import Path

from importlib_resources import files

from gambitpairing.gui.architecture_inventory import (
    DESIGNER_BACKED_UI_FILES,
    DYNAMIC_WIDGET_EXCEPTIONS,
    EXTRACTED_WORKFLOW_HELPERS,
    PAIRING_ENGINE_GUARDED_FILES,
    REMAINING_PYTHON_BUILT_LAYOUTS,
)
from gambitpairing.gui.notification import Notification as CanonicalNotification
from gambitpairing.gui.widgets.notification import Notification as WidgetNotification


def test_architecture_inventory_matches_packaged_ui_files():
    packaged_ui_files = {
        resource.name
        for resource in files("gambitpairing.ui").iterdir()
        if resource.name.endswith(".ui")
    }

    assert set(DESIGNER_BACKED_UI_FILES) == packaged_ui_files


def test_architecture_inventory_tracks_remaining_layout_and_workflow_boundaries():
    assert any(
        "ManualPairingDialog dynamic dock" in item
        for item in REMAINING_PYTHON_BUILT_LAYOUTS
    )
    assert any(
        "PlayerManagementDialog tab interiors" in item
        for item in REMAINING_PYTHON_BUILT_LAYOUTS
    )
    assert "Notification popup body" in REMAINING_PYTHON_BUILT_LAYOUTS
    assert "DroppableTableWidget" in DYNAMIC_WIDGET_EXCEPTIONS
    assert "main_window_file_flow" in EXTRACTED_WORKFLOW_HELPERS
    assert "main_window_save_flow" in EXTRACTED_WORKFLOW_HELPERS
    assert "main_window_tournament_flow" in EXTRACTED_WORKFLOW_HELPERS
    assert "players_view_workflow" in EXTRACTED_WORKFLOW_HELPERS
    assert "standings_presentation" in EXTRACTED_WORKFLOW_HELPERS
    assert "player_management_data" in EXTRACTED_WORKFLOW_HELPERS
    assert "manual_pairing_state" in EXTRACTED_WORKFLOW_HELPERS
    assert "manual_pairing_io" in EXTRACTED_WORKFLOW_HELPERS
    assert "tournament_view_workflow" in EXTRACTED_WORKFLOW_HELPERS
    assert "tournament_printing" in EXTRACTED_WORKFLOW_HELPERS


def test_pairing_engine_guarded_files_exist():
    for guarded_file in PAIRING_ENGINE_GUARDED_FILES:
        assert Path(guarded_file).exists()


def test_legacy_widget_notification_import_uses_canonical_implementation():
    assert WidgetNotification is CanonicalNotification
