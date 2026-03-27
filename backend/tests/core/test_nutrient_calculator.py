import pytest

from app.core.nutrient_calculator import NegativeCarbsError, calculate_nutrients


class TestCalculateCalories:
    def test_maintain_goal_equals_tdee(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="moderately_active",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["calories"] == pytest.approx(2000.0)

    def test_lose_goal_applies_deficit(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="moderately_active",
            goal="lose",
            calorie_deficit_percent=15.0,
        )
        assert result["calories"] == pytest.approx(1700.0)

    def test_gain_goal_adds_surplus(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="moderately_active",
            goal="gain",
            calorie_deficit_percent=10.0,
        )
        assert result["calories"] == pytest.approx(2200.0)

    def test_none_deficit_defaults_to_15(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="lose",
            calorie_deficit_percent=None,
        )
        assert result["calories"] == pytest.approx(1700.0)


class TestCalculateProteins:
    def test_moderately_active_maintain(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=80.0,
            activity_level="moderately_active",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # 80 * 1.6 * 1.0 = 128
        assert result["proteins"] == pytest.approx(128.0)

    def test_sedentary_lose_applies_multiplier(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=80.0,
            activity_level="sedentary",
            goal="lose",
            calorie_deficit_percent=15.0,
        )
        # 80 * 0.9 * 1.15 = 82.8
        assert result["proteins"] == pytest.approx(82.8)

    def test_extra_active_gain(self):
        result = calculate_nutrients(
            calories_burned=3000.0,
            body_weight=90.0,
            activity_level="extra_active",
            goal="gain",
            calorie_deficit_percent=15.0,
        )
        # 90 * 2.2 * 1.10 = 217.8
        assert result["proteins"] == pytest.approx(217.8)


class TestCalculateFats:
    def test_fats_25pct_of_calories(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 * 0.25) / 9 ≈ 55.56
        assert result["fats"] == pytest.approx(55.56, rel=1e-2)

    def test_sat_fat_10pct_of_calories(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 * 0.10) / 9 ≈ 22.22
        assert result["fats_saturated"] == pytest.approx(22.22, rel=1e-2)


class TestCalculateSalt:
    def test_sedentary_salt(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["salt"] == pytest.approx(5.0)

    def test_extra_active_salt(self):
        result = calculate_nutrients(
            calories_burned=3000.0,
            body_weight=75.0,
            activity_level="extra_active",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["salt"] == pytest.approx(7.0)


class TestCalculateFibers:
    def test_fibers_14g_per_1000kcal(self):
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        # (2000 / 1000) * 14 = 28
        assert result["fibers"] == pytest.approx(28.0)


class TestCalculateCarbohydrates:
    def test_carbs_remainder_formula(self):
        # calories=2000, proteins=75*0.9*1.0=67.5, fats=(2000*0.25)/9≈55.56
        # carbs = (2000 - 67.5*4 - 55.56*9) / 4 = (2000 - 270 - 500) / 4 = 307.5
        result = calculate_nutrients(
            calories_burned=2000.0,
            body_weight=75.0,
            activity_level="sedentary",
            goal="maintain",
            calorie_deficit_percent=15.0,
        )
        assert result["carbohydrates"] == pytest.approx(307.5, rel=1e-2)


class TestNegativeCarbs:
    def test_raises_on_negative_carbs(self):
        # Very high protein, very low calories → carbs go negative
        with pytest.raises(NegativeCarbsError):
            calculate_nutrients(
                calories_burned=800.0,
                body_weight=100.0,
                activity_level="extra_active",
                goal="lose",
                calorie_deficit_percent=15.0,
            )


class TestInvalidInputs:
    def test_raises_on_unknown_activity_level(self):
        with pytest.raises(ValueError, match="activity_level"):
            calculate_nutrients(
                calories_burned=2000.0,
                body_weight=75.0,
                activity_level="active",
                goal="maintain",
                calorie_deficit_percent=15.0,
            )

    def test_raises_on_unknown_goal(self):
        with pytest.raises(ValueError, match="goal"):
            calculate_nutrients(
                calories_burned=2000.0,
                body_weight=75.0,
                activity_level="sedentary",
                goal="bulk",
                calorie_deficit_percent=15.0,
            )
