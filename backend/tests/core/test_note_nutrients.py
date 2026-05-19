"""Tests for `parse_note_nutrients` — extracting Ukrainian-keyed nutrient
values from meal plan note text.
"""

from app.core.note_nutrients import parse_note_nutrients


def test_full_format_parses_all_known_keys():
    note = "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
    assert parse_note_nutrients(note) == {
        "calories": 500.0,
        "proteins": 30.0,
        "carbohydrates": 60.0,
        "fats": 15.0,
    }


def test_extended_format_with_saturated_and_sugars():
    note = (
        "Калорій:750/Білків:40/Вуглеводів:50/Вуглеводів цукрів:5/"
        "Жирів:35/Жирів нас.:8/Клітковини:7/Солі:1.2"
    )
    parsed = parse_note_nutrients(note)
    assert parsed == {
        "calories": 750.0,
        "proteins": 40.0,
        "carbohydrates": 50.0,
        "carbohydrates_of_sugars": 5.0,
        "fats": 35.0,
        "fats_saturated": 8.0,
        "fibers": 7.0,
        "salt": 1.2,
    }


def test_plain_note_returns_empty():
    assert parse_note_nutrients("просто текст") == {}


def test_empty_string_returns_empty():
    assert parse_note_nutrients("") == {}


def test_handles_whitespace_in_keys_and_values():
    note = " Калорій : 200 / Білків : 10 "
    assert parse_note_nutrients(note) == {"calories": 200.0, "proteins": 10.0}


def test_partial_match_keeps_known_keys():
    note = "Калорій:300/невідоме:1/Жирів:5"
    assert parse_note_nutrients(note) == {"calories": 300.0, "fats": 5.0}


def test_malformed_value_is_skipped():
    note = "Калорій:abc/Білків:20"
    assert parse_note_nutrients(note) == {"proteins": 20.0}


def test_unknown_keys_dropped_silently():
    assert parse_note_nutrients("Cal:100") == {}


def test_float_values_parsed():
    note = "Калорій:250.5/Білків:12.75"
    assert parse_note_nutrients(note) == {"calories": 250.5, "proteins": 12.75}
