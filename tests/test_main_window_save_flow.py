from gambitpairing.gui.main_window_save_flow import (
    build_unsaved_changes_prompt,
    should_continue_after_save_prompt,
    should_prompt_for_unsaved_changes,
)


def test_unsaved_changes_prompt_text_matches_existing_ui_contract():
    prompt = build_unsaved_changes_prompt()

    assert prompt.title == "Unsaved Changes"
    assert prompt.message == "You have unsaved changes. Do you want to save them?"
    assert prompt.save_label == "Save"
    assert prompt.discard_label == "Close without Saving"
    assert prompt.cancel_label == "Cancel"


def test_unsaved_changes_prompt_only_needed_for_dirty_state():
    assert should_prompt_for_unsaved_changes(is_dirty=True)
    assert not should_prompt_for_unsaved_changes(is_dirty=False)


def test_save_prompt_continuation_decisions_preserve_main_window_behavior():
    assert should_continue_after_save_prompt("save", save_succeeded=True)
    assert not should_continue_after_save_prompt("save", save_succeeded=False)
    assert should_continue_after_save_prompt("discard", save_succeeded=False)
    assert not should_continue_after_save_prompt("cancel", save_succeeded=True)
