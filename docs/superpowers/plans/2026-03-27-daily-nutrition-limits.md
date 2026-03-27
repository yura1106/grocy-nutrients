# Daily Nutrition Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add per-day nutrient limit records derived from TDEE/body weight, with auto-calculation and fallback to static profile norms across all comparison pages.

**Architecture:** Backend-heavy calculation via a pure `nutrient_calculator.py` module; a new `daily_nutrition_limits` table stores per-day records; a new Pinia store + `useNorms` composable provides transparent fallback (daily limit → profile) across all existing pages.

**Tech Stack:** FastAPI + SQLModel + Alembic (backend); Vue 3 + Pinia + TypeScript (frontend); pytest / Vitest (tests); all commands run inside Docker via `make` targets.

---

## File Map

**Backend — new:**
- `backend/app/core/nutrient_calculator.py` — pure functions, no DB
- `backend/app/models/nutrition_limit.py` — `DailyNutritionLimit` SQLModel table
- `backend/app/schemas/nutrition_limit.py` — request/response schemas
- `backend/app/services/nutrition_limits.py` — CRUD + preview logic
- `backend/app/api/endpoints/nutrition_limits.py` — FastAPI router
- `backend/migrations/versions/022_add_daily_nutrition_limits_table.py`
- `backend/migrations/versions/023_add_calorie_deficit_percent_to_profiles.py`
- `backend/tests/core/test_nutrient_calculator.py`
- `backend/tests/api/test_nutrition_limits.py`

**Backend — modified:**
- `backend/app/models/user_health_profile.py` — add `calorie_deficit_percent`
- `backend/app/schemas/user.py` — add `calorie_deficit_percent` to `HealthParametersUpdate` / `HealthParametersRead`
- `backend/app/api/api.py` — register `nutrition_limits` router
- `backend/app/db/base.py` — import `DailyNutritionLimit`
- `backend/migrations/env.py` — import `DailyNutritionLimit` + `UserHealthProfile`

**Frontend — new:**
- `frontend/src/types/nutritionLimit.ts`
- `frontend/src/store/nutritionLimits.ts`
- `frontend/src/composables/useNorms.ts`
- `frontend/src/components/nutrition-limits/NewLimitForm.vue`
- `frontend/src/components/nutrition-limits/DailyLimitsTable.vue`
- `frontend/src/components/nutrition-limits/EditLimitModal.vue`
- `frontend/src/views/DailyNutritionLimitsView.vue`
- `frontend/src/tests/store/nutritionLimits.test.ts`
- `frontend/src/tests/composables/useNorms.test.ts`

**Frontend — modified:**
- `frontend/src/components/NutrientTotalsBar.vue` — remove `useHealthStore`, accept `norms` prop
- `frontend/src/components/DayDetailContent.vue` — use `useNorms(date)`, pass norms to bar
- `frontend/src/views/ConsumedProductsStatsView.vue` — use `useNorms()` for table row coloring
- `frontend/src/views/RecipeDetailView.vue` — use `useNorms()`, pass norms to bar
- `frontend/src/views/ProductDetailView.vue` — use `useNorms()`, pass norms to bar
- `frontend/src/views/ConsumeView.vue` — use `useNorms()`, pass norms to bar
- `frontend/src/App.vue` — parallel fetch of today's limit
- `frontend/src/router/index.ts` — add `/daily-nutrition-limits` route
- `frontend/src/components/profile/HealthParameters.vue` — add `calorie_deficit_percent` input

---

## Task 1: nutrient_calculator.py — pure calculation functions

**Files:**
- Create: `backend/app/core/nutrient_calculator.py`
- Test: `backend/tests/core/test_nutrient_calculator.py`

- [x] **Step 1: Write failing tests**

```python
# backend/tests/core/test_nutrient_calculator.py
import pytest
from app.core.nutrient_calculator import calculate_nutrients, NegativeCarbsError


class TestCalculateCalories:
    def test_maintain_goal_equals_tdee(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="moderately_active", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["calories"] == pytest.approx(2000.0)

    def test_lose_goal_applies_deficit(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="moderately_active", goal="lose",
            calorie_deficit_percent=15.0,
        )
        assert result["calories"] == pytest.approx(1700.0)

    def test_gain_goal_adds_surplus(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="moderately_active", goal="gain",
            calorie_deficit_percent=10.0,
        )
        assert result["calories"] == pytest.approx(2200.0)

    def test_none_deficit_defaults_to_15(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="sedentary", goal="lose",
            calorie_deficit_percent=None,
        )
        assert result["calories"] == pytest.approx(1700.0)


class TestCalculateProteins:
    def test_moderately_active_maintain(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=80.0,
            activity_level="moderately_active", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # 80 * 1.6 * 1.0 = 128
        assert result["proteins"] == pytest.approx(128.0)

    def test_sedentary_lose_applies_multiplier(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=80.0,
            activity_level="sedentary", goal="lose",
            calorie_deficit_percent=15.0,
        )
        # 80 * 0.9 * 1.15 = 82.8
        assert result["proteins"] == pytest.approx(82.8)

    def test_extra_active_gain(self):
        result = calculate_nutrients(
            calories_burned=3000.0, body_weight=90.0,
            activity_level="extra_active", goal="gain",
            calorie_deficit_percent=15.0,
        )
        # 90 * 2.2 * 1.10 = 217.8
        assert result["proteins"] == pytest.approx(217.8)


class TestCalculateFats:
    def test_fats_25pct_of_calories(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="sedentary", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 * 0.25) / 9 ≈ 55.56
        assert result["fats"] == pytest.approx(55.56, rel=1e-2)

    def test_sat_fat_10pct_of_calories(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="sedentary", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 * 0.10) / 9 ≈ 22.22
        assert result["fats_saturated"] == pytest.approx(22.22, rel=1e-2)


class TestCalculateSalt:
    def test_sedentary_salt(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="sedentary", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["salt"] == pytest.approx(5.0)

    def test_extra_active_salt(self):
        result = calculate_nutrients(
            calories_burned=3000.0, body_weight=75.0,
            activity_level="extra_active", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["salt"] == pytest.approx(7.0)


class TestCalculateFibers:
    def test_fibers_14g_per_1000kcal(self):
        result = calculate_nutrients(
            calories_burned=2000.0, body_weight=75.0,
            activity_level="sedentary", goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 / 1000) * 14 = 28
        assert result["fibers"] == pytest.approx(28.0)


class TestNegativeCarbs:
    def test_raises_on_negative_carbs(self):
        # Very high protein, very low calories → carbs go negative
        with pytest.raises(NegativeCarbsError):
            calculate_nutrients(
                calories_burned=800.0, body_weight=100.0,
                activity_level="extra_active", goal="lose",
                calorie_deficit_percent=15.0,
            )
```

- [x] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend pytest tests/core/test_nutrient_calculator.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.core.nutrient_calculator'`

- [x] **Step 3: Write implementation**

```python
# backend/app/core/nutrient_calculator.py
"""Pure nutrient calculation functions — no DB dependencies."""


class NegativeCarbsError(ValueError):
    """Raised when calculated carbohydrates would be negative."""


_PROTEIN_FACTORS: dict[str, float] = {
    "sedentary": 0.9,
    "lightly_active": 1.4,
    "moderately_active": 1.6,
    "very_active": 2.0,
    "extra_active": 2.2,
}

_GOAL_PROTEIN_MULTIPLIERS: dict[str, float] = {
    "maintain": 1.0,
    "lose": 1.15,
    "gain": 1.10,
}

_SALT_BY_ACTIVITY: dict[str, float] = {
    "sedentary": 5.0,
    "lightly_active": 5.0,
    "moderately_active": 5.5,
    "very_active": 6.0,
    "extra_active": 7.0,
}


def calculate_nutrients(
    *,
    calories_burned: float,
    body_weight: float,
    activity_level: str,
    goal: str,
    calorie_deficit_percent: float | None,
) -> dict[str, float]:
    """
    Calculate all 8 daily nutrient limits from inputs.

    Returns dict with keys: calories, proteins, fats, fats_saturated,
    carbohydrates, carbohydrates_of_sugars, salt, fibers.

    Raises NegativeCarbsError if carbohydrates would be negative.
    """
    deficit = calorie_deficit_percent if calorie_deficit_percent is not None else 15.0

    # 1. Calories
    if goal == "lose":
        calories = calories_burned * (1 - deficit / 100)
    elif goal == "gain":
        calories = calories_burned * (1 + deficit / 100)
    else:  # maintain
        calories = calories_burned

    # 2. Proteins
    protein_factor = _PROTEIN_FACTORS[activity_level]
    goal_mult = _GOAL_PROTEIN_MULTIPLIERS[goal]
    proteins = body_weight * protein_factor * goal_mult

    # 3. Fats (25% of calories)
    fats = (calories * 0.25) / 9

    # 4. Saturated fat (10% of calories)
    fats_saturated = (calories * 0.10) / 9

    # 5. Carbohydrates (remainder)
    carbohydrates = (calories - proteins * 4 - fats * 9) / 4
    if carbohydrates < 0:
        raise NegativeCarbsError(
            f"Calculated carbohydrates are negative ({carbohydrates:.1f} g). "
            "Reduce protein target or increase calories."
        )

    # 6. Sugars (10% of calories)
    carbohydrates_of_sugars = (calories * 0.10) / 4

    # 7. Salt (activity-based)
    salt = _SALT_BY_ACTIVITY[activity_level]

    # 8. Fibers (14g per 1000 kcal)
    fibers = (calories / 1000) * 14

    return {
        "calories": calories,
        "proteins": proteins,
        "fats": fats,
        "fats_saturated": fats_saturated,
        "carbohydrates": carbohydrates,
        "carbohydrates_of_sugars": carbohydrates_of_sugars,
        "salt": salt,
        "fibers": fibers,
    }
```

- [x] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest tests/core/test_nutrient_calculator.py -v
```
Expected: all PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/core/nutrient_calculator.py backend/tests/core/test_nutrient_calculator.py
git commit -m "feat: add nutrient calculator pure functions with tests"
```

---

## Task 2: Alembic migrations

**Files:**
- Create: `backend/migrations/versions/022_add_daily_nutrition_limits_table.py`
- Create: `backend/migrations/versions/023_add_calorie_deficit_percent_to_profiles.py`

- [x] **Step 1: Write migration 022**

```python
# backend/migrations/versions/022_add_daily_nutrition_limits_table.py
"""add daily_nutrition_limits table

Revision ID: 022
Revises: 021
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_nutrition_limits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("calories_burned", sa.Float(), nullable=True),
        sa.Column("body_weight", sa.Float(), nullable=True),
        sa.Column("activity_level", sa.String(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("proteins", sa.Float(), nullable=True),
        sa.Column("carbohydrates", sa.Float(), nullable=True),
        sa.Column("carbohydrates_of_sugars", sa.Float(), nullable=True),
        sa.Column("fats", sa.Float(), nullable=True),
        sa.Column("fats_saturated", sa.Float(), nullable=True),
        sa.Column("salt", sa.Float(), nullable=True),
        sa.Column("fibers", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_nutrition_limits_user_date"),
    )


def downgrade() -> None:
    op.drop_table("daily_nutrition_limits")
```

- [x] **Step 2: Write migration 023**

```python
# backend/migrations/versions/023_add_calorie_deficit_percent_to_profiles.py
"""add calorie_deficit_percent to user_health_profiles

Revision ID: 023
Revises: 022
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_health_profiles",
        sa.Column("calorie_deficit_percent", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_health_profiles", "calorie_deficit_percent")
```

- [x] **Step 3: Apply migrations**

```bash
make migrate
```
Expected: `Running upgrade 021 -> 022 ... done` then `Running upgrade 022 -> 023 ... done`

- [x] **Step 4: Commit**

```bash
git add backend/migrations/versions/022_add_daily_nutrition_limits_table.py \
        backend/migrations/versions/023_add_calorie_deficit_percent_to_profiles.py
git commit -m "feat: add migrations for daily_nutrition_limits table and calorie_deficit_percent"
```

---

## Task 3: DailyNutritionLimit model + calorie_deficit_percent on UserHealthProfile

**Files:**
- Create: `backend/app/models/nutrition_limit.py`
- Modify: `backend/app/models/user_health_profile.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/migrations/env.py`

- [x] **Step 1: Create model**

```python
# backend/app/models/nutrition_limit.py
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class DailyNutritionLimit(SQLModel, table=True):
    __tablename__ = "daily_nutrition_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_nutrition_limits_user_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    date: date_type = Field(nullable=False, sa_type=Date())  # type: ignore[call-overload]
    calories_burned: float | None = Field(default=None, nullable=True)
    body_weight: float | None = Field(default=None, nullable=True)
    activity_level: str | None = Field(default=None, nullable=True)
    calories: float | None = Field(default=None, nullable=True)
    proteins: float | None = Field(default=None, nullable=True)
    carbohydrates: float | None = Field(default=None, nullable=True)
    carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    fats: float | None = Field(default=None, nullable=True)
    fats_saturated: float | None = Field(default=None, nullable=True)
    salt: float | None = Field(default=None, nullable=True)
    fibers: float | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
```

- [x] **Step 2: Add calorie_deficit_percent to UserHealthProfile**

In `backend/app/models/user_health_profile.py`, add one field after `daily_fibers`:

```python
    calorie_deficit_percent: float | None = Field(default=None, nullable=True)
```

The file becomes:
```python
from datetime import datetime

from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class UserHealthProfile(SQLModel, table=True):
    __tablename__ = "user_health_profiles"

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", unique=True, nullable=False, index=True)

    # Body measurements
    height: float | None = Field(default=None, nullable=True)
    weight: float | None = Field(default=None, nullable=True)
    activity_level: str | None = Field(default=None, nullable=True)
    goal: str | None = Field(default=None, nullable=True)

    # Daily nutrient limits
    daily_calories: float | None = Field(default=None, nullable=True)
    daily_proteins: float | None = Field(default=None, nullable=True)
    daily_fats: float | None = Field(default=None, nullable=True)
    daily_fats_saturated: float | None = Field(default=None, nullable=True)
    daily_carbohydrates: float | None = Field(default=None, nullable=True)
    daily_carbohydrates_of_sugars: float | None = Field(default=None, nullable=True)
    daily_salt: float | None = Field(default=None, nullable=True)
    daily_fibers: float | None = Field(default=None, nullable=True)
    calorie_deficit_percent: float | None = Field(default=None, nullable=True)

    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
```

- [x] **Step 3: Register model in db/base.py**

Add import at the end of the imports block:
```python
from app.models.nutrition_limit import DailyNutritionLimit  # noqa
```

The file becomes:
```python
from app.db.base_class import Base  # noqa
from app.db.session import SessionLocal

from app.models.user import User  # noqa
from app.models.daily_nutrition import DailyNutrition  # noqa
from app.models.household import Household, HouseholdUser, Role  # noqa
from app.models.recipe import Recipe, RecipeData  # noqa
from app.models.user_health_profile import UserHealthProfile  # noqa
from app.models.nutrition_limit import DailyNutritionLimit  # noqa


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [x] **Step 4: Add imports to migrations/env.py**

Add two imports after existing model imports:
```python
from app.models.user_health_profile import UserHealthProfile  # noqa
from app.models.nutrition_limit import DailyNutritionLimit  # noqa
```

- [x] **Step 5: Commit**

```bash
git add backend/app/models/nutrition_limit.py \
        backend/app/models/user_health_profile.py \
        backend/app/db/base.py \
        backend/migrations/env.py
git commit -m "feat: add DailyNutritionLimit model and calorie_deficit_percent field"
```

---

## Task 4: Schemas for nutrition limits and updated user schemas

**Files:**
- Create: `backend/app/schemas/nutrition_limit.py`
- Modify: `backend/app/schemas/user.py`

- [x] **Step 1: Create schemas**

```python
# backend/app/schemas/nutrition_limit.py
from datetime import date as date_type

from pydantic import BaseModel, Field


class NutrientLimitsPreviewRequest(BaseModel):
    calories_burned: float = Field(gt=0)
    body_weight: float = Field(gt=0, le=500)
    activity_level: str


class NutrientLimitsPreview(BaseModel):
    calories: float
    proteins: float
    carbohydrates: float
    carbohydrates_of_sugars: float
    fats: float
    fats_saturated: float
    salt: float
    fibers: float


class NutritionLimitCreate(BaseModel):
    date: date_type
    calories_burned: float | None = None
    body_weight: float | None = None
    activity_level: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class NutritionLimitUpdate(BaseModel):
    calories_burned: float | None = None
    body_weight: float | None = None
    activity_level: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None


class NutritionLimitRead(BaseModel):
    id: int
    date: date_type
    calories_burned: float | None
    body_weight: float | None
    activity_level: str | None
    calories: float | None
    proteins: float | None
    carbohydrates: float | None
    carbohydrates_of_sugars: float | None
    fats: float | None
    fats_saturated: float | None
    salt: float | None
    fibers: float | None

    model_config = {"from_attributes": True}


class NutritionLimitListResponse(BaseModel):
    items: list[NutritionLimitRead]
    total: int
```

- [x] **Step 2: Add calorie_deficit_percent to user schemas**

In `backend/app/schemas/user.py`, add `calorie_deficit_percent` to both `HealthParametersUpdate` and `HealthParametersRead`:

In `HealthParametersUpdate` add after `daily_fibers`:
```python
    calorie_deficit_percent: float | None = Field(default=None, ge=0, le=50)
```

In `HealthParametersRead` add after `daily_fibers`:
```python
    calorie_deficit_percent: float | None = None
```

- [x] **Step 3: Commit**

```bash
git add backend/app/schemas/nutrition_limit.py backend/app/schemas/user.py
git commit -m "feat: add nutrition limit schemas and calorie_deficit_percent to user schemas"
```

---

## Task 5: Nutrition limits service

**Files:**
- Create: `backend/app/services/nutrition_limits.py`

- [x] **Step 1: Write service**

```python
# backend/app/services/nutrition_limits.py
from datetime import date as date_type

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.nutrient_calculator import NegativeCarbsError, calculate_nutrients
from app.models.nutrition_limit import DailyNutritionLimit
from app.models.user import User
from app.models.user_health_profile import UserHealthProfile
from app.schemas.nutrition_limit import (
    NutrientLimitsPreview,
    NutrientLimitsPreviewRequest,
    NutritionLimitCreate,
    NutritionLimitListResponse,
    NutritionLimitRead,
    NutritionLimitUpdate,
)


def preview_limits(
    db: Session,
    user: User,
    request: NutrientLimitsPreviewRequest,
) -> NutrientLimitsPreview:
    """Calculate nutrient limits without saving. Reads goal + deficit from user profile."""
    profile = db.exec(
        select(UserHealthProfile).where(UserHealthProfile.user_id == user.id)
    ).first()
    goal = (profile.goal if profile else None) or "maintain"
    calorie_deficit_percent = (
        profile.calorie_deficit_percent if profile else None
    )
    try:
        nutrients = calculate_nutrients(
            calories_burned=request.calories_burned,
            body_weight=request.body_weight,
            activity_level=request.activity_level,
            goal=goal,
            calorie_deficit_percent=calorie_deficit_percent,
        )
    except NegativeCarbsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return NutrientLimitsPreview(**nutrients)


def get_today_limit(
    db: Session, user: User, today: date_type
) -> DailyNutritionLimit | None:
    return db.exec(
        select(DailyNutritionLimit).where(
            DailyNutritionLimit.user_id == user.id,
            DailyNutritionLimit.date == today,
        )
    ).first()


def get_limit_list(
    db: Session, user: User, skip: int, limit: int
) -> NutritionLimitListResponse:
    total = db.exec(
        select(func.count()).where(DailyNutritionLimit.user_id == user.id)
    ).one()
    items = db.exec(
        select(DailyNutritionLimit)
        .where(DailyNutritionLimit.user_id == user.id)
        .order_by(DailyNutritionLimit.date.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return NutritionLimitListResponse(
        items=[NutritionLimitRead.model_validate(r) for r in items],
        total=total,
    )


def create_limit(
    db: Session, user: User, data: NutritionLimitCreate
) -> DailyNutritionLimit:
    record = DailyNutritionLimit(user_id=user.id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_limit(
    db: Session, user: User, record_id: int, data: NutritionLimitUpdate
) -> DailyNutritionLimit:
    record = db.get(DailyNutritionLimit, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_limit(db: Session, user: User, record_id: int) -> None:
    record = db.get(DailyNutritionLimit, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(record)
    db.commit()
```

- [x] **Step 2: Commit**

```bash
git add backend/app/services/nutrition_limits.py
git commit -m "feat: add nutrition limits service"
```

---

## Task 6: Nutrition limits API endpoints + register router

**Files:**
- Create: `backend/app/api/endpoints/nutrition_limits.py`
- Modify: `backend/app/api/api.py`

- [x] **Step 1: Create endpoint file**

```python
# backend/app/api/endpoints/nutrition_limits.py
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.nutrition_limit import (
    NutrientLimitsPreview,
    NutrientLimitsPreviewRequest,
    NutritionLimitCreate,
    NutritionLimitListResponse,
    NutritionLimitRead,
    NutritionLimitUpdate,
)
from app.services import nutrition_limits as svc

router = APIRouter()


@router.post("/preview", response_model=NutrientLimitsPreview)
def preview_limits(
    request: NutrientLimitsPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.preview_limits(db, current_user, request)


@router.get("", response_model=NutritionLimitListResponse)
def list_limits(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.get_limit_list(db, current_user, skip, limit)


@router.get("/today", response_model=NutritionLimitRead | None)
def get_today(
    today: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.get_today_limit(db, current_user, today)


@router.post("", response_model=NutritionLimitRead, status_code=status.HTTP_201_CREATED)
def create_limit(
    data: NutritionLimitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.create_limit(db, current_user, data)


@router.put("/{record_id}", response_model=NutritionLimitRead)
def update_limit(
    record_id: int,
    data: NutritionLimitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return svc.update_limit(db, current_user, record_id, data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_limit(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    svc.delete_limit(db, current_user, record_id)
```

- [x] **Step 2: Register router in api.py**

```python
# backend/app/api/api.py
from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    consumption,
    daily_nutrition,
    households,
    nutrition_limits,
    products,
    recipes,
    sync,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(consumption.router, prefix="/consumption", tags=["consumption"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(
    daily_nutrition.router, prefix="/daily-nutrition", tags=["daily-nutrition"]
)
api_router.include_router(households.router, prefix="/households", tags=["households"])
api_router.include_router(
    nutrition_limits.router, prefix="/nutrition-limits", tags=["nutrition-limits"]
)
```

- [x] **Step 3: Commit**

```bash
git add backend/app/api/endpoints/nutrition_limits.py backend/app/api/api.py
git commit -m "feat: add nutrition limits API endpoints"
```

---

## Task 7: Backend API tests for nutrition limits

**Files:**
- Create: `backend/tests/api/test_nutrition_limits.py`

- [x] **Step 1: Write tests**

```python
# backend/tests/api/test_nutrition_limits.py
"""Integration tests for /api/nutrition-limits endpoints."""
from datetime import UTC, date, datetime

import pytest
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models.nutrition_limit import DailyNutritionLimit
from app.models.user import User
from app.models.user_health_profile import UserHealthProfile


def make_limit(db: Session, user_id: int, d: date, **kwargs) -> DailyNutritionLimit:
    record = DailyNutritionLimit(
        user_id=user_id,
        date=d,
        calories=2000.0,
        proteins=150.0,
        carbohydrates=200.0,
        carbohydrates_of_sugars=50.0,
        fats=67.0,
        fats_saturated=22.0,
        salt=5.0,
        fibers=28.0,
        **kwargs,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@pytest.mark.integration
class TestPreviewLimits:
    def test_returns_preview_for_maintain_goal(self, client, db, test_user):
        profile = UserHealthProfile(
            user_id=test_user.id, goal="maintain", calorie_deficit_percent=15.0
        )
        db.add(profile)
        db.commit()

        response = client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["calories"] == pytest.approx(2000.0)
        assert "proteins" in data
        assert "carbohydrates" in data

    def test_defaults_to_maintain_when_no_profile(self, client):
        response = client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 200
        assert response.json()["calories"] == pytest.approx(2000.0)

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/nutrition-limits/preview",
            json={"calories_burned": 2000.0, "body_weight": 75.0, "activity_level": "sedentary"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestCreateLimit:
    def test_creates_record_with_user_id_from_token(self, client, test_user):
        payload = {
            "date": "2026-03-27",
            "calories_burned": 2500.0,
            "body_weight": 80.0,
            "activity_level": "moderately_active",
            "calories": 2125.0,
            "proteins": 148.0,
            "carbohydrates": 250.0,
            "carbohydrates_of_sugars": 53.0,
            "fats": 59.0,
            "fats_saturated": 23.6,
            "salt": 5.5,
            "fibers": 29.75,
        }
        response = client.post("/api/nutrition-limits", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["date"] == "2026-03-27"
        assert data["calories"] == pytest.approx(2125.0)
        assert "id" in data

    def test_unauthenticated_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.post(
            "/api/nutrition-limits",
            json={"date": "2026-03-27", "calories": 2000.0},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestGetTodayLimit:
    def test_returns_null_when_no_record(self, client):
        response = client.get("/api/nutrition-limits/today", params={"today": "2026-03-27"})
        assert response.status_code == 200
        assert response.json() is None

    def test_returns_todays_record(self, client, db, test_user):
        make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.get("/api/nutrition-limits/today", params={"today": "2026-03-27"})
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-03-27"
        assert data["calories"] == pytest.approx(2000.0)


@pytest.mark.integration
class TestUpdateLimit:
    def test_updates_fields(self, client, db, test_user):
        record = make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.put(
            f"/api/nutrition-limits/{record.id}",
            json={"calories": 1800.0},
        )
        assert response.status_code == 200
        assert response.json()["calories"] == pytest.approx(1800.0)

    def test_returns_403_for_another_users_record(self, client, db):
        other = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("Pass1234!"),
            created_at=datetime.now(UTC),
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        record = make_limit(db, other.id, date(2026, 3, 27))
        response = client.put(f"/api/nutrition-limits/{record.id}", json={"calories": 999.0})
        assert response.status_code == 403


@pytest.mark.integration
class TestDeleteLimit:
    def test_returns_204_on_success(self, client, db, test_user):
        record = make_limit(db, test_user.id, date(2026, 3, 27))
        response = client.delete(f"/api/nutrition-limits/{record.id}")
        assert response.status_code == 204

    def test_returns_403_for_another_users_record(self, client, db):
        other = User(
            email="other2@example.com",
            username="otheruser2",
            hashed_password=get_password_hash("Pass1234!"),
            created_at=datetime.now(UTC),
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        record = make_limit(db, other.id, date(2026, 3, 20))
        response = client.delete(f"/api/nutrition-limits/{record.id}")
        assert response.status_code == 403
```

- [x] **Step 2: Run tests**

```bash
docker compose exec backend pytest tests/api/test_nutrition_limits.py -v
```
Expected: all PASS

- [x] **Step 3: Run full backend suite to confirm nothing broken**

```bash
docker compose exec backend pytest -v
```
Expected: all PASS

- [x] **Step 4: Commit**

```bash
git add backend/tests/api/test_nutrition_limits.py
git commit -m "test: add nutrition limits API integration tests"
```

---

## Task 8: Frontend types and Pinia store

**Files:**
- Create: `frontend/src/types/nutritionLimit.ts`
- Create: `frontend/src/store/nutritionLimits.ts`

- [x] **Step 1: Write types**

```typescript
// frontend/src/types/nutritionLimit.ts
export interface NutritionLimit {
  id: number
  date: string
  calories_burned: number | null
  body_weight: number | null
  activity_level: string | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

export interface NutrientLimitsPreview {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  salt: number
  fibers: number
}

export interface NutritionLimitCreate {
  date: string
  calories_burned?: number | null
  body_weight?: number | null
  activity_level?: string | null
  calories?: number | null
  proteins?: number | null
  carbohydrates?: number | null
  carbohydrates_of_sugars?: number | null
  fats?: number | null
  fats_saturated?: number | null
  salt?: number | null
  fibers?: number | null
}

export interface NutritionLimitUpdate {
  calories_burned?: number | null
  body_weight?: number | null
  activity_level?: string | null
  calories?: number | null
  proteins?: number | null
  carbohydrates?: number | null
  carbohydrates_of_sugars?: number | null
  fats?: number | null
  fats_saturated?: number | null
  salt?: number | null
  fibers?: number | null
}

export interface PreviewRequest {
  calories_burned: number
  body_weight: number
  activity_level: string
}
```

- [x] **Step 2: Write Pinia store**

```typescript
// frontend/src/store/nutritionLimits.ts
import { defineStore } from 'pinia'
import axios from 'axios'
import type {
  NutritionLimit,
  NutrientLimitsPreview,
  NutritionLimitCreate,
  NutritionLimitUpdate,
  PreviewRequest,
} from '../types/nutritionLimit'
import { parseApiError } from '../utils/parseApiError'

interface NutritionLimitsState {
  todayLimit: NutritionLimit | null
  preview: NutrientLimitsPreview | null
  list: NutritionLimit[]
  total: number
  loading: boolean
  previewLoading: boolean
  error: string
}

export const useNutritionLimitsStore = defineStore('nutritionLimits', {
  state: (): NutritionLimitsState => ({
    todayLimit: null,
    preview: null,
    list: [],
    total: 0,
    loading: false,
    previewLoading: false,
    error: '',
  }),

  getters: {
    getLimitByDate: (state) => (dateStr: string): NutritionLimit | undefined =>
      state.list.find((l) => l.date === dateStr),
  },

  actions: {
    async fetchTodayLimit(today?: string) {
      this.loading = true
      this.error = ''
      try {
        const params = today ? { today } : {}
        const { data } = await axios.get('/api/nutrition-limits/today', { params })
        this.todayLimit = data
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to load today\'s limit')
      } finally {
        this.loading = false
      }
    },

    async fetchList(skip = 0, limit = 20) {
      this.loading = true
      this.error = ''
      try {
        const { data } = await axios.get('/api/nutrition-limits', { params: { skip, limit } })
        this.list = data.items
        this.total = data.total
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to load limits list')
      } finally {
        this.loading = false
      }
    },

    async previewLimits(params: PreviewRequest) {
      this.previewLoading = true
      this.error = ''
      try {
        const { data } = await axios.post('/api/nutrition-limits/preview', params)
        this.preview = data
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Preview failed')
      } finally {
        this.previewLoading = false
      }
    },

    async createLimit(data: NutritionLimitCreate) {
      this.loading = true
      this.error = ''
      try {
        const { data: created } = await axios.post('/api/nutrition-limits', data)
        this.list.unshift(created)
        this.total += 1
        this.preview = null
        return created as NutritionLimit
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to create limit')
        throw err
      } finally {
        this.loading = false
      }
    },

    async updateLimit(id: number, data: NutritionLimitUpdate) {
      this.loading = true
      this.error = ''
      try {
        const { data: updated } = await axios.put(`/api/nutrition-limits/${id}`, data)
        const idx = this.list.findIndex((l) => l.id === id)
        if (idx !== -1) this.list[idx] = updated
        if (this.todayLimit?.id === id) this.todayLimit = updated
        return updated as NutritionLimit
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to update limit')
        throw err
      } finally {
        this.loading = false
      }
    },

    async deleteLimit(id: number) {
      this.loading = true
      this.error = ''
      try {
        await axios.delete(`/api/nutrition-limits/${id}`)
        this.list = this.list.filter((l) => l.id !== id)
        this.total -= 1
        if (this.todayLimit?.id === id) this.todayLimit = null
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to delete limit')
        throw err
      } finally {
        this.loading = false
      }
    },
  },
})
```

- [x] **Step 3: Commit**

```bash
git add frontend/src/types/nutritionLimit.ts frontend/src/store/nutritionLimits.ts
git commit -m "feat: add NutritionLimit types and Pinia store"
```

---

## Task 9: useNorms composable

**Files:**
- Create: `frontend/src/composables/useNorms.ts`

- [x] **Step 1: Write composable**

```typescript
// frontend/src/composables/useNorms.ts
import { computed, unref } from 'vue'
import type { MaybeRef } from 'vue'
import { useNutritionLimitsStore } from '../store/nutritionLimits'
import { useHealthStore } from '../store/health'

export interface NormValues {
  daily_calories: number | null
  daily_proteins: number | null
  daily_fats: number | null
  daily_fats_saturated: number | null
  daily_carbohydrates: number | null
  daily_carbohydrates_of_sugars: number | null
  daily_salt: number | null
  daily_fibers: number | null
}

export function useNorms(date?: MaybeRef<string | null>) {
  const limitsStore = useNutritionLimitsStore()
  const healthStore = useHealthStore()

  const norms = computed((): NormValues | null => {
    const d = date !== undefined ? unref(date) : null
    const limit = d ? limitsStore.getLimitByDate(d) : limitsStore.todayLimit

    if (limit) {
      return {
        daily_calories: limit.calories,
        daily_proteins: limit.proteins,
        daily_fats: limit.fats,
        daily_fats_saturated: limit.fats_saturated,
        daily_carbohydrates: limit.carbohydrates,
        daily_carbohydrates_of_sugars: limit.carbohydrates_of_sugars,
        daily_salt: limit.salt,
        daily_fibers: limit.fibers,
      }
    }

    const p = healthStore.params
    if (p) {
      return {
        daily_calories: p.daily_calories,
        daily_proteins: p.daily_proteins,
        daily_fats: p.daily_fats,
        daily_fats_saturated: p.daily_fats_saturated,
        daily_carbohydrates: p.daily_carbohydrates,
        daily_carbohydrates_of_sugars: p.daily_carbohydrates_of_sugars,
        daily_salt: p.daily_salt,
        daily_fibers: p.daily_fibers,
      }
    }

    return null
  })

  return { norms }
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/composables/useNorms.ts
git commit -m "feat: add useNorms composable for daily limit / profile fallback"
```

---

## Task 10: Update NutrientTotalsBar to accept norms prop

**Files:**
- Modify: `frontend/src/components/NutrientTotalsBar.vue`

The `<script setup>` section currently imports `useHealthStore` and computes `norms` internally. Replace with a required `norms` prop.

- [x] **Step 1: Update script section**

Replace the entire `<script setup>` block with:

```typescript
<script setup lang="ts">
import { computed } from 'vue'
import type { NormValues } from '../composables/useNorms'
import { nutrientTextClass } from '../composables/useNutrientColor'
import NutrientGauge from './NutrientGauge.vue'

export interface NutrientTotals {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  fibers: number
  salt: number
  cost?: number | null
}

const props = withDefaults(defineProps<{
  totals: NutrientTotals
  norms: NormValues | null
  layout?: 'vertical' | 'horizontal'
}>(), {
  norms: null,
  layout: 'vertical',
})

const isHorizontal = computed(() => props.layout === 'horizontal')

const cellClass = computed(() =>
  isHorizontal.value
    ? 'flex flex-row items-center justify-center gap-2'
    : 'flex flex-col items-center',
)

const sizes = computed(() =>
  isHorizontal.value
    ? {
        primary: { gauge: 56, stroke: 5, text: 'text-2xl', label: 'text-xs text-gray-500' },
        secondary: { gauge: 44, stroke: 4, text: 'text-lg', label: 'text-xs text-gray-400' },
      }
    : {
        primary: { gauge: 48, stroke: 4, text: 'text-xl', label: 'text-sm text-gray-500' },
        secondary: { gauge: 36, stroke: 3, text: 'text-base', label: 'text-xs text-gray-400' },
      },
)

const norms = computed(() => props.norms)

const fmt = (val: number): string => val.toFixed(1)
</script>
```

The template stays exactly the same (it already references `norms.daily_*` — this alias computed keeps it working).

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/NutrientTotalsBar.vue
git commit -m "refactor: NutrientTotalsBar accepts norms prop instead of reading healthStore directly"
```

---

## Task 11: Update all NutrientTotalsBar call sites

**Files:**
- Modify: `frontend/src/components/DayDetailContent.vue`
- Modify: `frontend/src/views/RecipeDetailView.vue`
- Modify: `frontend/src/views/ProductDetailView.vue`
- Modify: `frontend/src/views/ConsumeView.vue`

### DayDetailContent.vue

- [x] **Step 1: Update DayDetailContent**

In the `<script setup>` section, add imports and `useNorms` call:

```typescript
// Add import at top of script section:
import { computed } from 'vue'
import type { ConsumedDayDetail } from '../types/consumed'
import NutrientTotalsBar from './NutrientTotalsBar.vue'
import { useNorms } from '../composables/useNorms'

const props = defineProps<{ detail: ConsumedDayDetail }>()

const { norms } = useNorms(computed(() => props.detail.date))

const nutrientTotals = computed(() => ({
  calories: props.detail.total_calories,
  proteins: props.detail.total_proteins,
  carbohydrates: props.detail.total_carbohydrates,
  carbohydrates_of_sugars: props.detail.total_carbohydrates_of_sugars,
  fats: props.detail.total_fats,
  fats_saturated: props.detail.total_fats_saturated,
  fibers: props.detail.total_fibers,
  salt: props.detail.total_salt,
  cost: props.detail.total_cost,
}))

const fmt = (val: number): string => val.toFixed(1)

const fmtQty = (qty: number): string => {
  if (qty >= 1000) return `${(qty / 1000).toFixed(2)} kg`
  return `${qty.toFixed(1)} g`
}
```

In the template, update the bar to pass norms:
```html
<NutrientTotalsBar :totals="nutrientTotals" :norms="norms" />
```

### RecipeDetailView.vue

- [x] **Step 2: Update RecipeDetailView**

In the `<script setup>` section:
- Remove `import { useHealthStore } from '@/store/health'` and `const healthStore = useHealthStore()` and `if (!healthStore.params) healthStore.fetchHealthParams()`
- Add `import { useNorms } from '@/composables/useNorms'` and `const { norms } = useNorms()`

Update the `NutrientTotalsBar` tag:
```html
<NutrientTotalsBar
  v-if="expandedNutrients"
  layout="horizontal"
  :totals="expandedNutrients"
  :norms="norms"
/>
```

### ProductDetailView.vue

- [x] **Step 3: Update ProductDetailView**

Same pattern:
- Remove `useHealthStore` import, const, and eager-fetch line
- Add `import { useNorms } from '@/composables/useNorms'` and `const { norms } = useNorms()`

Update `NutrientTotalsBar`:
```html
<NutrientTotalsBar
  v-if="expandedNutrients"
  :totals="expandedNutrients"
  :norms="norms"
/>
```

### ConsumeView.vue

- [x] **Step 4: Update ConsumeView**

Same pattern:
- Remove `useHealthStore` import, const, and eager-fetch line
- Add `import { useNorms } from '@/composables/useNorms'` and `const { norms } = useNorms()`

Update `NutrientTotalsBar`:
```html
<NutrientTotalsBar
  v-if="dryRunTotals"
  :totals="dryRunTotals"
  layout="horizontal"
  :norms="norms"
/>
```

- [x] **Step 5: Commit**

```bash
git add frontend/src/components/DayDetailContent.vue \
        frontend/src/views/RecipeDetailView.vue \
        frontend/src/views/ProductDetailView.vue \
        frontend/src/views/ConsumeView.vue
git commit -m "refactor: pass norms prop to NutrientTotalsBar in all call sites"
```

---

## Task 12: Update ConsumedProductsStatsView to use useNorms()

**Files:**
- Modify: `frontend/src/views/ConsumedProductsStatsView.vue`

- [x] **Step 1: Update script section**

Replace the health store usage in the script block:

Remove:
```typescript
import { useHealthStore } from '@/store/health'
const healthStore = useHealthStore()
if (!healthStore.params) healthStore.fetchHealthParams()
```

Add:
```typescript
import { useNorms } from '@/composables/useNorms'
const { norms } = useNorms()
```

- [x] **Step 2: Update table row coloring in template**

Replace all occurrences of `healthStore.params?.daily_calories` → `norms?.daily_calories`, etc.:

```html
<!-- Before (example): -->
:class="nutrientTextClass(day.total_calories, healthStore.params?.daily_calories) || ..."
<!-- After: -->
:class="nutrientTextClass(day.total_calories, norms?.daily_calories) || ..."
```

Apply the same substitution for all 5 nutrient columns:
- `healthStore.params?.daily_calories` → `norms?.daily_calories`
- `healthStore.params?.daily_carbohydrates` → `norms?.daily_carbohydrates`
- `healthStore.params?.daily_proteins` → `norms?.daily_proteins`
- `healthStore.params?.daily_fats` → `norms?.daily_fats`
- `healthStore.params?.daily_fibers` → `norms?.daily_fibers`

Note: `DayDetailContent` (detail panel) already handles per-date norms via its own `useNorms(date)` call (updated in Task 11).

- [x] **Step 3: Commit**

```bash
git add frontend/src/views/ConsumedProductsStatsView.vue
git commit -m "refactor: use useNorms() in ConsumedProductsStatsView for table coloring"
```

---

## Task 13: App.vue — parallel fetch of today's limit

**Files:**
- Modify: `frontend/src/App.vue`

- [x] **Step 1: Update the watch block in App.vue**

In `<script setup>`, add import for the nutritionLimits store, and update the `watch` to also fetch today's limit when user becomes authenticated:

```typescript
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './store/auth'
import { useHouseholdStore } from './store/household'
import { useNutritionLimitsStore } from './store/nutritionLimits'

const router = useRouter()
const authStore = useAuthStore()
const householdStore = useHouseholdStore()
const limitsStore = useNutritionLimitsStore()
const mobileOpen = ref(false)

watch(
  () => authStore.user,
  (user, oldUser) => {
    if (user) {
      householdStore.fetchHouseholds()
      limitsStore.fetchTodayLimit()
    } else if (oldUser) {
      householdStore.clear()
      limitsStore.$reset()
    }
  },
  { immediate: true }
)
```

Also add `/daily-nutrition-limits` to the nav items:
```typescript
const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/consumed-stats', label: 'Nutrient Stats' },
  { to: '/daily-nutrition-limits', label: 'Daily Limits' },
  { to: '/recipes', label: 'Recipes' },
  { to: '/products', label: 'Products' },
  { to: '/consumption-history', label: 'Consumption Log' },
  { to: '/history-import', label: 'History' },
  { to: '/profile', label: 'Profile' },
]

const logout = async () => {
  await authStore.logout()
  householdStore.clear()
  limitsStore.$reset()
  router.push('/login')
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: fetch today's nutrition limit on login and add nav item"
```

---

## Task 14: Add calorie_deficit_percent field to HealthParameters.vue

**Files:**
- Modify: `frontend/src/components/profile/HealthParameters.vue`

- [x] **Step 1: Add to types/health.ts**

In `frontend/src/types/health.ts`, add `calorie_deficit_percent` to the `HealthParameters` interface:
```typescript
export interface HealthParameters {
  // ... existing fields ...
  calorie_deficit_percent: number | null
}
```

- [x] **Step 2: Add to form state in HealthParameters.vue**

In the `form` reactive object, add:
```typescript
calorie_deficit_percent: null as number | null,
```

In `populateForm()`, add:
```typescript
form.calorie_deficit_percent = p.calorie_deficit_percent ?? null
```

- [x] **Step 3: Add input field to the template**

After the `Goal` multiselect and before BMI display, add a new grid item in the body measurements section:

```html
<div>
  <label
    for="calorie_deficit_percent"
    class="block text-sm font-medium text-gray-700"
  >% Deficit / Surplus from TDEE</label>
  <div class="mt-1">
    <input
      id="calorie_deficit_percent"
      v-model.number="form.calorie_deficit_percent"
      type="number"
      min="0"
      max="50"
      step="1"
      placeholder="15"
      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
    />
  </div>
  <p class="mt-1 text-xs text-gray-400">Used for auto-calculating daily limits. Default: 15%.</p>
</div>
```

- [x] **Step 4: Commit**

```bash
git add frontend/src/types/health.ts frontend/src/components/profile/HealthParameters.vue
git commit -m "feat: add calorie_deficit_percent field to health parameters form"
```

---

## Task 15: Daily Nutrition Limits page — view and components

**Files:**
- Create: `frontend/src/views/DailyNutritionLimitsView.vue`
- Create: `frontend/src/components/nutrition-limits/NewLimitForm.vue`
- Create: `frontend/src/components/nutrition-limits/DailyLimitsTable.vue`
- Create: `frontend/src/components/nutrition-limits/EditLimitModal.vue`

- [x] **Step 1: Create NewLimitForm.vue**

```vue
<!-- frontend/src/components/nutrition-limits/NewLimitForm.vue -->
<template>
  <div class="bg-white shadow sm:rounded-lg p-6">
    <h3 class="text-lg font-medium text-gray-900 mb-4">Set Today's Limits</h3>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-4">
      <div>
        <label class="block text-sm font-medium text-gray-700">Calories Burned (kcal)</label>
        <input
          v-model.number="form.calories_burned"
          type="number"
          min="500"
          max="10000"
          step="1"
          placeholder="2000"
          class="mt-1 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Body Weight (kg)</label>
        <input
          v-model.number="form.body_weight"
          type="number"
          min="20"
          max="500"
          step="0.1"
          placeholder="75"
          class="mt-1 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Activity Level</label>
        <select
          v-model="form.activity_level"
          class="mt-1 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">— select —</option>
          <option value="sedentary">Sedentary</option>
          <option value="lightly_active">Lightly Active</option>
          <option value="moderately_active">Moderately Active</option>
          <option value="very_active">Very Active</option>
          <option value="extra_active">Extra Active</option>
        </select>
      </div>
    </div>

    <div class="flex gap-3 mb-4">
      <button
        @click="generate"
        :disabled="!canGenerate || store.previewLoading"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
      >
        {{ store.previewLoading ? 'Calculating...' : 'Generate' }}
      </button>
      <button
        @click="fillFromProfile"
        :disabled="!healthStore.params"
        class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        Fill from Profile
      </button>
    </div>

    <!-- Preview -->
    <div v-if="nutrients" class="mb-4 bg-indigo-50 rounded-lg p-4">
      <div class="grid grid-cols-4 gap-2 text-sm">
        <div v-for="field in previewFields" :key="field.key" class="text-center">
          <div class="font-semibold text-indigo-800">{{ fmt(nutrients[field.key]) }}</div>
          <div class="text-xs text-gray-500">{{ field.label }}</div>
        </div>
      </div>
    </div>

    <div v-if="store.error" class="text-red-500 text-sm mb-4">{{ store.error }}</div>

    <button
      v-if="nutrients"
      @click="save"
      :disabled="store.loading"
      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
    >
      {{ store.loading ? 'Saving...' : 'Save for Today' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import { useHealthStore } from '../../store/health'
import type { NutrientLimitsPreview } from '../../types/nutritionLimit'

const store = useNutritionLimitsStore()
const healthStore = useHealthStore()

const today = new Date().toISOString().slice(0, 10)

const form = reactive({
  calories_burned: null as number | null,
  body_weight: null as number | null,
  activity_level: '' as string,
})

const canGenerate = computed(() =>
  form.calories_burned !== null && form.body_weight !== null && form.activity_level !== '',
)

const nutrients = computed((): NutrientLimitsPreview | null => store.preview)

const previewFields: { key: keyof NutrientLimitsPreview; label: string }[] = [
  { key: 'calories', label: 'kcal' },
  { key: 'proteins', label: 'protein' },
  { key: 'carbohydrates', label: 'carbs' },
  { key: 'fats', label: 'fats' },
  { key: 'fibers', label: 'fiber' },
  { key: 'salt', label: 'salt' },
  { key: 'fats_saturated', label: 'sat.fat' },
  { key: 'carbohydrates_of_sugars', label: 'sugars' },
]

const fmt = (val: number) => val.toFixed(1)

async function generate() {
  if (!canGenerate.value) return
  await store.previewLimits({
    calories_burned: form.calories_burned!,
    body_weight: form.body_weight!,
    activity_level: form.activity_level,
  })
}

function fillFromProfile() {
  const p = healthStore.params
  if (!p) return
  store.preview = {
    calories: p.daily_calories ?? 0,
    proteins: p.daily_proteins ?? 0,
    carbohydrates: p.daily_carbohydrates ?? 0,
    carbohydrates_of_sugars: p.daily_carbohydrates_of_sugars ?? 0,
    fats: p.daily_fats ?? 0,
    fats_saturated: p.daily_fats_saturated ?? 0,
    salt: p.daily_salt ?? 0,
    fibers: p.daily_fibers ?? 0,
  }
}

const emit = defineEmits<{ created: [] }>()

async function save() {
  if (!nutrients.value) return
  await store.createLimit({
    date: today,
    ...nutrients.value,
  })
  form.calories_burned = null
  form.body_weight = null
  form.activity_level = ''
  emit('created')
}
</script>
```

- [x] **Step 2: Create DailyLimitsTable.vue**

```vue
<!-- frontend/src/components/nutrition-limits/DailyLimitsTable.vue -->
<template>
  <div class="bg-white shadow sm:rounded-lg overflow-hidden">
    <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
      <h3 class="text-lg font-medium text-gray-900">Saved Daily Limits</h3>
      <p class="text-sm text-gray-500">Total: {{ store.total }}</p>
    </div>

    <div v-if="store.loading" class="text-center py-8 text-sm text-gray-500">Loading...</div>
    <div v-else-if="store.list.length === 0" class="text-center py-8 text-sm text-gray-400">
      No records yet.
    </div>
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Weight</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Activity</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Kcal</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Prot</th>
            <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Carbs</th>
            <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fats</th>
            <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fiber</th>
            <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Salt</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="item in store.list"
            :key="item.id"
            class="cursor-pointer hover:bg-indigo-50 transition-colors"
            @click="emit('edit', item)"
          >
            <td class="px-4 py-3 font-medium text-gray-900">{{ item.date }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ item.body_weight ?? '—' }}</td>
            <td class="px-4 py-3 text-right text-gray-500 text-xs">{{ item.activity_level ?? '—' }}</td>
            <td class="px-4 py-3 text-right font-semibold text-indigo-700">{{ fmt(item.calories) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.proteins) }}</td>
            <td class="hidden sm:table-cell px-4 py-3 text-right text-gray-700">{{ fmt(item.carbohydrates) }}</td>
            <td class="hidden sm:table-cell px-4 py-3 text-right text-gray-700">{{ fmt(item.fats) }}</td>
            <td class="hidden sm:table-cell px-4 py-3 text-right text-gray-700">{{ fmt(item.fibers) }}</td>
            <td class="hidden sm:table-cell px-4 py-3 text-right text-gray-700">{{ fmt(item.salt) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PaginationBar
      v-if="store.total > pageSize"
      :total="store.total"
      :skip="skip"
      :limit="pageSize"
      @update:skip="onSkipChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import type { NutritionLimit } from '../../types/nutritionLimit'
import PaginationBar from '../PaginationBar.vue'

const store = useNutritionLimitsStore()
const pageSize = 20
const skip = ref(0)

const emit = defineEmits<{ edit: [item: NutritionLimit] }>()

const fmt = (val: number | null) => (val !== null ? val.toFixed(1) : '—')

async function onSkipChange(newSkip: number) {
  skip.value = newSkip
  await store.fetchList(newSkip, pageSize)
}

onMounted(() => store.fetchList(0, pageSize))
</script>
```

- [x] **Step 3: Create EditLimitModal.vue**

```vue
<!-- frontend/src/components/nutrition-limits/EditLimitModal.vue -->
<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    @click.self="emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-medium text-gray-900">Edit Limit — {{ item.date }}</h3>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">✕</button>
      </div>

      <div class="grid grid-cols-2 gap-4 mb-4">
        <div v-for="field in editFields" :key="field.key">
          <label class="block text-xs font-medium text-gray-700 mb-1">{{ field.label }}</label>
          <input
            v-model.number="form[field.key]"
            type="number"
            :step="field.step"
            class="block w-full shadow-sm sm:text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      <div v-if="store.error" class="text-red-500 text-sm mb-3">{{ store.error }}</div>

      <div class="flex justify-between gap-3">
        <button
          @click="del"
          :disabled="store.loading"
          class="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
        <div class="flex gap-3">
          <button
            @click="emit('close')"
            class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="save"
            :disabled="store.loading"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ store.loading ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import type { NutritionLimit } from '../../types/nutritionLimit'

const props = defineProps<{ item: NutritionLimit }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useNutritionLimitsStore()

type EditKey = 'calories_burned' | 'body_weight' | 'calories' | 'proteins' |
               'carbohydrates' | 'carbohydrates_of_sugars' | 'fats' | 'fats_saturated' |
               'salt' | 'fibers'

const editFields: { key: EditKey; label: string; step: number }[] = [
  { key: 'calories_burned', label: 'Calories Burned', step: 1 },
  { key: 'body_weight', label: 'Body Weight (kg)', step: 0.1 },
  { key: 'calories', label: 'Kcal Limit', step: 1 },
  { key: 'proteins', label: 'Proteins (g)', step: 1 },
  { key: 'carbohydrates', label: 'Carbs (g)', step: 1 },
  { key: 'carbohydrates_of_sugars', label: 'Sugars (g)', step: 1 },
  { key: 'fats', label: 'Fats (g)', step: 1 },
  { key: 'fats_saturated', label: 'Sat. Fats (g)', step: 1 },
  { key: 'salt', label: 'Salt (g)', step: 0.1 },
  { key: 'fibers', label: 'Fiber (g)', step: 1 },
]

const form = reactive<Record<EditKey, number | null>>({
  calories_burned: props.item.calories_burned,
  body_weight: props.item.body_weight,
  calories: props.item.calories,
  proteins: props.item.proteins,
  carbohydrates: props.item.carbohydrates,
  carbohydrates_of_sugars: props.item.carbohydrates_of_sugars,
  fats: props.item.fats,
  fats_saturated: props.item.fats_saturated,
  salt: props.item.salt,
  fibers: props.item.fibers,
})

async function save() {
  await store.updateLimit(props.item.id, { ...form })
  emit('saved')
  emit('close')
}

async function del() {
  await store.deleteLimit(props.item.id)
  emit('saved')
  emit('close')
}
</script>
```

- [x] **Step 4: Create DailyNutritionLimitsView.vue**

```vue
<!-- frontend/src/views/DailyNutritionLimitsView.vue -->
<template>
  <div class="bg-gray-100 min-h-screen">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Daily Nutrition Limits</h1>
          <p class="mt-2 text-sm text-gray-600">Set per-day nutrient targets based on TDEE and body weight</p>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8 mt-6 space-y-6 px-4">
          <NewLimitForm @created="onCreated" />
          <DailyLimitsTable ref="tableRef" @edit="openEdit" />
        </div>
      </main>
    </div>

    <EditLimitModal
      v-if="editing"
      :item="editing"
      @close="editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import NewLimitForm from '../components/nutrition-limits/NewLimitForm.vue'
import DailyLimitsTable from '../components/nutrition-limits/DailyLimitsTable.vue'
import EditLimitModal from '../components/nutrition-limits/EditLimitModal.vue'
import type { NutritionLimit } from '../types/nutritionLimit'
import { useNutritionLimitsStore } from '../store/nutritionLimits'

const store = useNutritionLimitsStore()
const editing = ref<NutritionLimit | null>(null)

function openEdit(item: NutritionLimit) {
  editing.value = item
}

function onCreated() {
  // Refresh today's limit in store
  store.fetchTodayLimit()
}

function onSaved() {
  store.fetchTodayLimit()
}
</script>
```

- [x] **Step 5: Commit**

```bash
git add frontend/src/components/nutrition-limits/ \
        frontend/src/views/DailyNutritionLimitsView.vue
git commit -m "feat: add DailyNutritionLimitsView and nutrition-limits components"
```

---

## Task 16: Router — add daily-nutrition-limits route

**Files:**
- Modify: `frontend/src/router/index.ts`

- [x] **Step 1: Update router**

Add import and route entry:

```typescript
import DailyNutritionLimitsView from '../views/DailyNutritionLimitsView.vue'
```

Add to routes array (after `consumed-stats`):
```typescript
{
  path: '/daily-nutrition-limits',
  name: 'daily-nutrition-limits',
  component: DailyNutritionLimitsView,
  meta: { requiresAuth: true }
},
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: add /daily-nutrition-limits route"
```

---

## Task 17: Frontend store tests

**Files:**
- Create: `frontend/src/tests/store/nutritionLimits.test.ts`

- [x] **Step 1: Write tests**

```typescript
// frontend/src/tests/store/nutritionLimits.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNutritionLimitsStore } from '@/store/nutritionLimits'
import axios from 'axios'

vi.mock('axios', () => {
  const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} as Record<string, string> } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios, true)

const makeLimit = (id = 1, dateStr = '2026-03-27') => ({
  id,
  date: dateStr,
  calories_burned: 2500,
  body_weight: 80,
  activity_level: 'moderately_active',
  calories: 2125,
  proteins: 148,
  carbohydrates: 250,
  carbohydrates_of_sugars: 53,
  fats: 59,
  fats_saturated: 23,
  salt: 5.5,
  fibers: 29,
})

describe('NutritionLimits Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('fetchTodayLimit', () => {
    it('sets todayLimit on success', async () => {
      const limit = makeLimit()
      mockedAxios.get.mockResolvedValueOnce({ data: limit })
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.todayLimit).toEqual(limit)
    })

    it('sets todayLimit to null when API returns null', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: null })
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.todayLimit).toBeNull()
    })

    it('sets error on failure', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'))
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.error).not.toBe('')
    })
  })

  describe('previewLimits', () => {
    it('stores preview result', async () => {
      const preview = {
        calories: 2000, proteins: 150, carbohydrates: 200,
        carbohydrates_of_sugars: 50, fats: 56, fats_saturated: 22,
        salt: 5, fibers: 28,
      }
      mockedAxios.post.mockResolvedValueOnce({ data: preview })
      const store = useNutritionLimitsStore()
      await store.previewLimits({ calories_burned: 2000, body_weight: 75, activity_level: 'sedentary' })
      expect(store.preview).toEqual(preview)
    })

    it('does not add preview to list', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: { calories: 2000 } })
      const store = useNutritionLimitsStore()
      await store.previewLimits({ calories_burned: 2000, body_weight: 75, activity_level: 'sedentary' })
      expect(store.list).toHaveLength(0)
    })
  })

  describe('createLimit', () => {
    it('prepends created record to list', async () => {
      const created = makeLimit(42)
      mockedAxios.post.mockResolvedValueOnce({ data: created })
      const store = useNutritionLimitsStore()
      await store.createLimit({ date: '2026-03-27' })
      expect(store.list[0]).toEqual(created)
      expect(store.total).toBe(1)
    })

    it('clears preview after create', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: makeLimit() })
      const store = useNutritionLimitsStore()
      store.preview = { calories: 2000, proteins: 150, carbohydrates: 200,
        carbohydrates_of_sugars: 50, fats: 56, fats_saturated: 22, salt: 5, fibers: 28 }
      await store.createLimit({ date: '2026-03-27' })
      expect(store.preview).toBeNull()
    })
  })

  describe('getLimitByDate getter', () => {
    it('returns matching limit by date', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: { items: [makeLimit(1, '2026-03-27'), makeLimit(2, '2026-03-26')], total: 2 },
      })
      const store = useNutritionLimitsStore()
      await store.fetchList()
      expect(store.getLimitByDate('2026-03-27')?.id).toBe(1)
      expect(store.getLimitByDate('2026-03-26')?.id).toBe(2)
    })

    it('returns undefined for unknown date', () => {
      const store = useNutritionLimitsStore()
      expect(store.getLimitByDate('2099-01-01')).toBeUndefined()
    })
  })
})
```

- [x] **Step 2: Run tests**

```bash
docker compose exec frontend npm run test -- --reporter=verbose src/tests/store/nutritionLimits.test.ts
```
Expected: all PASS

- [x] **Step 3: Commit**

```bash
git add frontend/src/tests/store/nutritionLimits.test.ts
git commit -m "test: add NutritionLimits store unit tests"
```

---

## Task 18: Frontend useNorms composable tests

**Files:**
- Create: `frontend/src/tests/composables/useNorms.test.ts`

- [x] **Step 1: Write tests**

```typescript
// frontend/src/tests/composables/useNorms.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ref } from 'vue'
import { useNorms } from '@/composables/useNorms'
import { useNutritionLimitsStore } from '@/store/nutritionLimits'
import { useHealthStore } from '@/store/health'

// useNorms only reads from stores — no axios needed
vi.mock('axios', () => ({
  default: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

const makeLimit = (overrides = {}) => ({
  id: 1,
  date: '2026-03-27',
  calories_burned: null,
  body_weight: null,
  activity_level: null,
  calories: 2000,
  proteins: 150,
  carbohydrates: 200,
  carbohydrates_of_sugars: 50,
  fats: 56,
  fats_saturated: 22,
  salt: 5,
  fibers: 28,
  ...overrides,
})

const makeHealthParams = (overrides = {}) => ({
  gender: null,
  date_of_birth: null,
  height: null,
  weight: null,
  activity_level: null,
  goal: null,
  calorie_deficit_percent: null,
  daily_calories: 1800,
  daily_proteins: 120,
  daily_fats: 50,
  daily_fats_saturated: 18,
  daily_carbohydrates: 220,
  daily_carbohydrates_of_sugars: 45,
  daily_salt: 5,
  daily_fibers: 25,
  ...overrides,
})

describe('useNorms', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('no date arg — uses todayLimit', () => {
    it('returns todayLimit mapped to daily_* shape when todayLimit is set', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.todayLimit = makeLimit()
      const { norms } = useNorms()
      expect(norms.value?.daily_calories).toBe(2000)
      expect(norms.value?.daily_proteins).toBe(150)
    })

    it('falls back to healthStore.params when todayLimit is null', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.todayLimit = null
      const healthStore = useHealthStore()
      healthStore.params = makeHealthParams()
      const { norms } = useNorms()
      expect(norms.value?.daily_calories).toBe(1800)
      expect(norms.value?.daily_proteins).toBe(120)
    })

    it('returns null when both stores are empty', () => {
      const { norms } = useNorms()
      expect(norms.value).toBeNull()
    })
  })

  describe('with date arg — uses getLimitByDate', () => {
    it('returns limit for provided date', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = [makeLimit({ date: '2026-03-20', calories: 1900, proteins: 140 })]
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1900)
      expect(norms.value?.daily_proteins).toBe(140)
    })

    it('falls back to healthStore.params when no record for that date', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = []
      const healthStore = useHealthStore()
      healthStore.params = makeHealthParams()
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1800)
    })

    it('is reactive — updates when date ref changes', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = [
        makeLimit({ date: '2026-03-20', calories: 1900 }),
        makeLimit({ id: 2, date: '2026-03-21', calories: 2100 }),
      ]
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1900)
      date.value = '2026-03-21'
      expect(norms.value?.daily_calories).toBe(2100)
    })
  })
})
```

- [x] **Step 2: Run tests**

```bash
docker compose exec frontend npm run test -- --reporter=verbose src/tests/composables/useNorms.test.ts
```
Expected: all PASS

- [x] **Step 3: Run full frontend test suite**

```bash
docker compose exec frontend npm run test
```
Expected: all PASS

- [x] **Step 4: Commit**

```bash
git add frontend/src/tests/composables/useNorms.test.ts
git commit -m "test: add useNorms composable tests"
```

---

## Task 19: Frontend lint + type-check

- [x] **Step 1: Type-check**

```bash
docker compose exec frontend npm run type-check
```
Expected: 0 errors

- [x] **Step 2: Lint**

```bash
docker compose exec frontend npm run lint
```
Expected: 0 errors

- [x] **Step 3: Fix any type errors**

Common issues and fixes:
- `NormValues | null` prop default: ensure `withDefaults` has `norms: null` (already in Task 10)
- `$reset()` on Pinia store: add `$reset` call or use `store.todayLimit = null; store.preview = null; store.list = []; store.total = 0` if `$reset` is unavailable (setup stores don't have it, options stores do — our store uses options API so `$reset` is available)

- [x] **Step 4: Build check**

```bash
docker compose exec frontend npm run build
```
Expected: build succeeds

- [x] **Step 5: Commit any lint fixes**

```bash
git add -p
git commit -m "fix: lint and type errors from daily nutrition limits feature"
```

---

## Task 20: Full CI run

- [x] **Step 1: Run full CI**

```bash
make ci
```
Expected: all checks PASS (`=== All CI checks passed ===`)

- [x] **Step 2: If any check fails, fix it**

- Backend ruff/mypy errors: run `make lint-fix-python`, then inspect remaining mypy errors
- Frontend type errors: fix the specific file indicated
- Test failures: read the failure traceback, fix the specific assertion

---

## Self-Review

**1. Spec coverage check:**

| Spec requirement | Plan task |
|---|---|
| New `daily_nutrition_limits` table | Tasks 2, 3 |
| `calorie_deficit_percent` on user_health_profiles | Tasks 2, 3, 4, 6, 14 |
| `nutrient_calculator.py` pure functions | Task 1 |
| `POST /nutrition-limits/preview` | Task 6 |
| `GET /nutrition-limits`, `GET /today`, `POST`, `PUT`, `DELETE` | Task 6 |
| Backend tests (calculator + API) | Tasks 1, 7 |
| `NutritionLimit` TS types + Pinia store | Task 8 |
| `useNorms` composable | Task 9 |
| `NutrientTotalsBar` remove healthStore dep | Task 10 |
| Update DayDetailContent, RecipeDetailView, ProductDetailView, ConsumeView | Task 11 |
| Update ConsumedProductsStatsView | Task 12 |
| App.vue parallel fetch | Task 13 |
| HealthParameters.vue calorie_deficit_percent field | Task 14 |
| DailyNutritionLimitsView + components | Tasks 15, 16 |
| Frontend store + composable tests | Tasks 17, 18 |
| "Fill from Profile" shortcut | Task 15 (NewLimitForm.vue `fillFromProfile`) |
| `getLimitByDate` getter | Task 8 (store) |

**2. Placeholder scan:** None found — all steps contain complete code.

**3. Type consistency check:**
- `NutritionLimit.calories` (bare name in store/types) → normalized to `NormValues.daily_calories` in `useNorms` ✓
- `NutrientTotalsBar` props: `norms: NormValues | null` — template uses `norms.daily_calories` ✓
- `store.preview = null` in `createLimit` action ✓
- `store.preview` direct assignment in `fillFromProfile` — Pinia `state` is reactive, direct assignment works for options store ✓
