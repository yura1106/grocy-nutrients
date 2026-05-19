"""Reconcile matching for `type="note"` rows.

Notes lack a Grocy product/recipe id, so the tuple identity collapses to
(day, section_id, type, note_text). Duplicates with identical text resolve in
Grocy-id (FIFO) order, mirroring how product/recipe duplicates do.
"""

from datetime import date

from app.models.meal_plan import MealPlan
from app.services.meal_plan import assign_grocy_ids_in_order

DAY = date(2026, 5, 20)


def _note_row(note: str) -> MealPlan:
    return MealPlan(
        household_id=1,
        user_id=1,
        type="note",
        day=DAY,
        section_id=2,
        note=note,
        status="pending",
    )


def _grocy_note(*, id_: int, note: str, ts: str = "2026-05-20 12:00:00") -> dict:
    return {
        "id": id_,
        "day": DAY.isoformat(),
        "section_id": 2,
        "type": "note",
        "note": note,
        "row_created_timestamp": ts,
    }


def test_note_matches_grocy_row_by_text():
    row = _note_row("buy bread")
    candidate = _grocy_note(id_=7777, note="buy bread")

    matched, unmatched = assign_grocy_ids_in_order([row], [candidate])

    assert unmatched == []
    assert matched == [row]
    assert row.grocy_meal_plan_id == 7777
    assert row.status == "synced"


def test_duplicate_notes_assigned_in_grocy_id_order():
    row_a = _note_row("snack")
    row_b = _note_row("snack")
    candidates = [
        _grocy_note(id_=200, note="snack", ts="2026-05-20 13:00:00"),
        _grocy_note(id_=100, note="snack", ts="2026-05-20 12:00:00"),
    ]

    _matched, unmatched = assign_grocy_ids_in_order([row_a, row_b], candidates)

    assert unmatched == []
    # Sorted by Grocy id ascending → earliest Grocy id pops first.
    assert row_a.grocy_meal_plan_id == 100
    assert row_b.grocy_meal_plan_id == 200


def test_note_does_not_match_product_with_same_section_day():
    row = _note_row("oats")
    product_candidate = {
        "id": 50,
        "day": DAY.isoformat(),
        "section_id": 2,
        "type": "product",
        "product_id": 7,
        "product_amount": "1",
    }

    matched, unmatched = assign_grocy_ids_in_order([row], [product_candidate])

    assert matched == []
    assert unmatched == [row]


def test_note_text_must_match_exactly():
    row = _note_row("eat fruit")
    candidate = _grocy_note(id_=11, note="eat vegetables")

    matched, unmatched = assign_grocy_ids_in_order([row], [candidate])

    assert matched == []
    assert unmatched == [row]


def test_note_text_is_trimmed_for_matching():
    """Local row stores trimmed text; Grocy may echo back with stray whitespace
    or vice-versa. Both sides trim before tuple-building."""
    row = _note_row("water")
    candidate = _grocy_note(id_=22, note="  water  ")

    _matched, unmatched = assign_grocy_ids_in_order([row], [candidate])

    assert unmatched == []
    assert row.grocy_meal_plan_id == 22
