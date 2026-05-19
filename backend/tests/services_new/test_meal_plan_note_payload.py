"""Payload shape for `type="note"` rows when POSTing/PUTing to Grocy.

Grocy expects `{day, type=note, section_id, note}` — no product/recipe fields.
The edit-variant substitutes the new `note` text without touching anything
else.
"""

from datetime import date

from app.models.meal_plan import MealPlan
from app.services.meal_plan import (
    build_grocy_payload,
    build_grocy_payload_for_edit,
)

DAY = date(2026, 5, 20)


def _note_row(note: str = "buy bread", *, grocy_id: int | None = None) -> MealPlan:
    return MealPlan(
        household_id=1,
        user_id=1,
        type="note",
        day=DAY,
        section_id=3,
        note=note,
        status="pending",
        grocy_meal_plan_id=grocy_id,
    )


def test_build_payload_for_note_has_note_field():
    row = _note_row("lunch out")
    payload = build_grocy_payload(row)

    assert payload == {
        "day": "2026-05-20",
        "type": "note",
        "section_id": 3,
        "note": "lunch out",
    }


def test_build_payload_for_note_handles_none_as_empty():
    row = _note_row()
    row.note = None
    payload = build_grocy_payload(row)
    assert payload["note"] == ""


def test_edit_payload_substitutes_note():
    row = _note_row("old text", grocy_id=999)
    payload = build_grocy_payload_for_edit(
        row, product_amount_stock=None, recipe_servings=None, note="new text"
    )

    assert payload == {
        "day": "2026-05-20",
        "type": "note",
        "section_id": 3,
        "note": "new text",
    }


def test_edit_payload_falls_back_to_existing_note_when_no_override():
    row = _note_row("keep me", grocy_id=999)
    payload = build_grocy_payload_for_edit(
        row, product_amount_stock=None, recipe_servings=None, note=None
    )

    assert payload["note"] == "keep me"
