"""Compatibility import for the API player-import workflow."""

from .player_import_workflow import PlayerImportWorkflow

ImportPlayer = PlayerImportWorkflow

__all__ = ["ImportPlayer", "PlayerImportWorkflow"]
