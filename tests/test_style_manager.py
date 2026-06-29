from gambitpairing.resources.style_manager import get_stylesheet, list_themes


def test_stylesheet_loads_partials_in_order_and_substitutes_tokens():
    stylesheet = get_stylesheet("light")

    assert "01 — FOCUS RESET" in stylesheet
    assert "14 — PRINT PREVIEW" in stylesheet
    assert stylesheet.index("01 — FOCUS RESET") < stylesheet.index(
        "14 — PRINT PREVIEW"
    )
    assert "{{" not in stylesheet
    assert "}}" not in stylesheet


def test_style_manager_lists_known_themes():
    assert list_themes() == ["dark", "light"]
