"""Schema validation for `type="note"` meal plan lines.

Notes require a non-empty `note` body and must not carry product/recipe fields;
correspondingly, product/recipe lines must not carry a note.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.meal_plan import MealPlanLineCreate, MealPlanLineEdit

DAY = date(2026, 5, 20)


def test_note_create_requires_non_empty_note():
    with pytest.raises(ValidationError, match="non-empty note"):
        MealPlanLineCreate(type="note", day=DAY, section_id=2, note="")


def test_note_create_requires_non_whitespace_note():
    with pytest.raises(ValidationError, match="non-empty note"):
        MealPlanLineCreate(type="note", day=DAY, section_id=2, note="   ")


def test_note_create_accepts_valid_body():
    line = MealPlanLineCreate(type="note", day=DAY, section_id=2, note="lunch out")
    assert line.type == "note"
    assert line.note == "lunch out"


def test_note_create_rejects_product_fields():
    with pytest.raises(ValidationError, match="must not include product/recipe"):
        MealPlanLineCreate(
            type="note",
            day=DAY,
            section_id=2,
            note="x",
            product_grocy_id=1,
            product_amount=Decimal("1"),
            product_amount_stock=Decimal("1"),
            product_qu_id=1,
        )


def test_note_create_rejects_recipe_fields():
    with pytest.raises(ValidationError, match="must not include product/recipe"):
        MealPlanLineCreate(
            type="note",
            day=DAY,
            section_id=2,
            note="x",
            recipe_grocy_id=5,
            recipe_servings=Decimal("1"),
        )


def test_product_create_rejects_note():
    with pytest.raises(ValidationError, match="must not include note"):
        MealPlanLineCreate(
            type="product",
            day=DAY,
            section_id=2,
            product_grocy_id=1,
            product_amount=Decimal("1"),
            product_amount_stock=Decimal("1"),
            product_qu_id=1,
            note="anything",
        )


def test_recipe_create_rejects_note():
    with pytest.raises(ValidationError, match="must not include note"):
        MealPlanLineCreate(
            type="recipe",
            day=DAY,
            section_id=2,
            recipe_grocy_id=5,
            recipe_servings=Decimal("1"),
            note="anything",
        )


def test_edit_allows_note_only():
    edit = MealPlanLineEdit(note="new body")
    assert edit.note == "new body"


def test_edit_rejects_empty_note():
    with pytest.raises(ValidationError, match="non-empty"):
        MealPlanLineEdit(note="   ")
