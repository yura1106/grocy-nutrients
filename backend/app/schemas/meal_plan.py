"""
Schemas for meal plan endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MealPlanLineType = Literal["product", "recipe", "note"]
MealPlanLineStatus = Literal["pending", "syncing", "synced", "failed"]


class MealPlanLineCreate(BaseModel):
    """One line to be added to the meal plan."""

    type: MealPlanLineType
    day: date
    section_id: int

    product_grocy_id: int | None = None
    product_amount: Decimal | None = None
    product_amount_stock: Decimal | None = None
    product_qu_id: int | None = None

    recipe_grocy_id: int | None = None
    recipe_servings: Decimal | None = None

    note: str | None = None

    @model_validator(mode="after")
    def _validate_typed_fields(self) -> "MealPlanLineCreate":
        if self.type == "product":
            if (
                self.product_grocy_id is None
                or self.product_amount is None
                or self.product_amount_stock is None
                or self.product_qu_id is None
            ):
                raise ValueError(
                    "product lines require product_grocy_id, product_amount, "
                    "product_amount_stock and product_qu_id"
                )
            if self.product_amount <= 0:
                raise ValueError("product_amount must be > 0")
            if self.product_amount_stock <= 0:
                raise ValueError("product_amount_stock must be > 0")
            if self.recipe_grocy_id is not None or self.recipe_servings is not None:
                raise ValueError("product lines must not include recipe_grocy_id/recipe_servings")
            if self.note is not None:
                raise ValueError("product lines must not include note")
        elif self.type == "recipe":
            if self.recipe_grocy_id is None or self.recipe_servings is None:
                raise ValueError("recipe lines require recipe_grocy_id and recipe_servings")
            if self.recipe_servings <= 0:
                raise ValueError("recipe_servings must be > 0")
            if (
                self.product_grocy_id is not None
                or self.product_amount is not None
                or self.product_amount_stock is not None
                or self.product_qu_id is not None
            ):
                raise ValueError(
                    "recipe lines must not include product_grocy_id/product_amount/"
                    "product_amount_stock/product_qu_id"
                )
            if self.note is not None:
                raise ValueError("recipe lines must not include note")
        else:  # note
            if self.note is None or not self.note.strip():
                raise ValueError("note lines require a non-empty note")
            if (
                self.product_grocy_id is not None
                or self.product_amount is not None
                or self.product_amount_stock is not None
                or self.product_qu_id is not None
                or self.recipe_grocy_id is not None
                or self.recipe_servings is not None
            ):
                raise ValueError("note lines must not include product/recipe fields")
        return self


class MealPlanLineEdit(BaseModel):
    """Patch body for editing a synced meal plan row.

    Type-vs-field cross-validation lives in the service layer because the
    schema doesn't know `row.type`. Schema only enforces value-level rules
    (positivity, non-empty note).
    """

    product_amount: Decimal | None = None
    product_amount_stock: Decimal | None = None
    recipe_servings: Decimal | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _validate_positive(self) -> "MealPlanLineEdit":
        if self.product_amount is not None and self.product_amount <= 0:
            raise ValueError("product_amount must be > 0")
        if self.product_amount_stock is not None and self.product_amount_stock <= 0:
            raise ValueError("product_amount_stock must be > 0")
        if self.recipe_servings is not None and self.recipe_servings <= 0:
            raise ValueError("recipe_servings must be > 0")
        if self.note is not None and not self.note.strip():
            raise ValueError("note must be non-empty")
        return self


class MealPlanLineRead(BaseModel):
    id: int
    household_id: int
    user_id: int | None = None

    grocy_meal_plan_id: int | None = None
    grocy_shadow_recipe_id: int | None = None

    type: MealPlanLineType
    day: date
    section_id: int

    product_grocy_id: int | None = None
    product_amount: Decimal | None = None
    product_amount_stock: Decimal | None = None
    product_qu_id: int | None = None
    product_qu_name: str | None = None

    recipe_grocy_id: int | None = None
    recipe_servings: Decimal | None = None

    note: str | None = None

    # Enriched at response time from local products/recipes tables.
    # None when the referenced row is unknown locally even after a best-effort
    # lazy sync from Grocy — the view shows "Product #ID" as a fallback.
    product_name: str | None = None
    recipe_name: str | None = None

    # Local DB primary key for the linked product/recipe — needed for the
    # frontend to route to /products/{id} and /recipes/{id} (the *_grocy_id
    # fields above carry the Grocy ID).
    product_local_id: int | None = None
    recipe_local_id: int | None = None

    status: MealPlanLineStatus
    error_message: str | None = None
    retry_count: int = 0

    done: bool = False
    done_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MealPlanBatchCreateRequest(BaseModel):
    """Body of POST /api/meal-plan/lines."""

    lines: list[MealPlanLineCreate] = Field(min_length=1)


class MealPlanBatchCreateResponse(BaseModel):
    task_id: str
    line_ids: list[int]


class MealPlanJobStatusResponse(BaseModel):
    """Polling response for the batch job."""

    task_id: str
    state: str  # PENDING | PROGRESS | SUCCESS | FAILURE | NONE
    current: int = 0
    total: int = 0
    errors: list[str] = []
    summary: dict | None = None
    error: str | None = None


class MealPlanSection(BaseModel):
    section_id: int
    name: str
    sort_number: int | None = None


class MealPlanSectionsResponse(BaseModel):
    sections: list[MealPlanSection]


class MealPlanUnit(BaseModel):
    qu_id: int
    name: str
    name_plural: str | None = None
    is_stock_default: bool = False
    factor_to_stock: float


class MealPlanUnitsResponse(BaseModel):
    units: list[MealPlanUnit]
    # Grams (or ml, for ml-stocked products) per 1 stock unit.
    # For products stocked in g or ml this is 1.0; for products stocked in pieces,
    # packages, etc., this is the conversion factor to real weight/volume.
    # None means no conversion is known and per-gram math is not possible.
    stock_to_grams_ml: float | None = None


class MealPlanRetryResponse(BaseModel):
    line: MealPlanLineRead


class MealPlanDoneToggleRequest(BaseModel):
    done: bool


class MealPlanMissingItem(BaseModel):
    type: str
    grocy_id: int
    name: str


class MealPlanDailyTotals(BaseModel):
    kcal: float
    protein: float
    carbs: float
    sugars: float
    fat: float
    sat_fat: float
    salt: float
    fibers: float
    missing_items: list[MealPlanMissingItem]


class MealPlanPullDayRequest(BaseModel):
    day: date


class MealPlanPullDayResponse(BaseModel):
    pulled: int = 0
    pulled_already_done: int = 0
    skipped_already_local: int = 0
    skipped_other_owner: int = 0
    skipped_notes: int = 0
    userfield_write_failures: int = 0
    lines: list[MealPlanLineRead] = []
