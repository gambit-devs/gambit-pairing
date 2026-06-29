from gambitpairing.gui.main_window_tournament_flow import (
    build_new_tournament_history,
    build_new_tournament_notification,
    project_new_tournament_data,
)


def test_new_tournament_projection_and_messages_preserve_existing_text():
    projection = project_new_tournament_data(
        ("City Open", 5, ("solkoff", "median"), "dutch_swiss")
    )

    assert projection.name == "City Open"
    assert projection.num_rounds == 5
    assert projection.tiebreak_order == ["solkoff", "median"]
    assert projection.pairing_system == "dutch_swiss"
    assert build_new_tournament_history(projection) == (
        "--- New Tournament 'City Open' Created "
        "(Rounds: 5, Pairing: dutch_swiss) ---"
    )
    assert build_new_tournament_notification(projection) == (
        "New tournament 'City Open' created."
    )
