from gambitpairing.gui.dialogs.player_management_data import (
    PlayerFormFields,
    build_player_data_from_fields,
    gender_code_from_display,
    gender_display_from_code,
    has_fide_fields,
    optional_int_from_text,
    project_tournament_player_row,
    search_result_count_text,
)
from gambitpairing.models.player import Player


def test_player_form_fields_map_to_manual_player_data():
    fields = PlayerFormFields(
        name=" Ada ",
        rating=1800,
        gender_text="Female",
        date_of_birth="2000-01-02",
        phone=" 555 ",
        email=" ada@example.com ",
        club=" Club ",
        federation=" CAN ",
    )

    assert build_player_data_from_fields(fields, include_fide_fields=False) == {
        "name": "Ada",
        "rating": 1800,
        "gender": "F",
        "date_of_birth": "2000-01-02",
        "phone": "555",
        "email": "ada@example.com",
        "club": "Club",
        "federation": "CAN",
    }


def test_player_form_fields_map_to_fide_player_data():
    fields = PlayerFormFields(
        name="Ada",
        rating=1800,
        gender_text="Male",
        date_of_birth="",
        phone="",
        email="",
        club="",
        federation="CAN",
        fide_id="123",
        fide_title=" FM ",
        fide_standard="2000",
        fide_rapid="",
        fide_blitz="1900",
    )

    assert has_fide_fields(fields)
    data = build_player_data_from_fields(
        fields, include_fide_fields=True, selected_birth_year=1990
    )

    assert data["gender"] == "M"
    assert data["fide_id"] == 123
    assert data["fide_title"] == "FM"
    assert data["fide_standard"] == 2000
    assert data["fide_rapid"] is None
    assert data["fide_blitz"] == 1900
    assert data["birth_year"] == 1990


def test_tournament_player_row_projection_and_small_helpers():
    player = Player("Ada", 1800, gender="F")
    row = project_tournament_player_row(player)

    assert row.player_id == player.id
    assert row.name == "Ada"
    assert row.rating == "1800"
    assert row.gender == "Female"
    assert gender_code_from_display("Male") == "M"
    assert gender_display_from_code("M") == "Male"
    assert optional_int_from_text("123") == 123
    assert optional_int_from_text("abc") is None
    assert search_result_count_text(1).startswith("Found 1 player.")
    assert search_result_count_text(2).startswith("Found 2 players.")
