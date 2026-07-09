from gambitpairing.gui.main_window_file_flow import (
    build_load_error_prompt,
    build_load_success_history,
    build_load_success_status,
    build_overwrite_confirmation_prompt,
    build_save_error_prompt,
    build_save_history,
    build_save_status,
    should_request_save_path,
)


def test_save_path_and_overwrite_decisions_preserve_existing_text():
    assert should_request_save_path(None, save_as=False)
    assert should_request_save_path("event.json", save_as=True)
    assert not should_request_save_path("event.json", save_as=False)

    prompt = build_overwrite_confirmation_prompt()
    assert prompt.title == "will overwrite tournament"
    assert prompt.message == "Is that what you want?"


def test_save_and_load_messages_preserve_existing_text():
    assert build_save_status("C:/tmp/event.json") == (
        "Tournament saved to C:/tmp/event.json"
    )
    assert build_save_history("C:/tmp/event.json") == (
        "Tournament saved as: event.json"
    )
    assert build_load_success_history("C:/tmp/event.json") == (
        "--- Tournament loaded from event.json ---"
    )
    assert build_load_success_status("City Open") == "Loaded tournament: City Open"


def test_error_messages_preserve_existing_text():
    error = ValueError("bad json")

    assert build_save_error_prompt(error).message == (
        "Could not save tournament:\nbad json"
    )
    assert build_load_error_prompt(error).message == (
        "Could not load tournament file:\nbad json"
    )
