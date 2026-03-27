"""Pure nutrient calculation functions — no DB dependencies."""

_DEFAULT_DEFICIT_PERCENT = 15.0


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
    Raises ValueError on unknown activity_level or goal.
    """
    if activity_level not in _PROTEIN_FACTORS:
        raise ValueError(
            f"Unknown activity_level {activity_level!r}. Valid values: {list(_PROTEIN_FACTORS)}"
        )
    if goal not in _GOAL_PROTEIN_MULTIPLIERS:
        raise ValueError(f"Unknown goal {goal!r}. Valid values: {list(_GOAL_PROTEIN_MULTIPLIERS)}")

    deficit = (
        calorie_deficit_percent
        if calorie_deficit_percent is not None
        else _DEFAULT_DEFICIT_PERCENT
    )

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
