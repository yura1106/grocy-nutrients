"""Tests for the per-household Grocy mapping registry."""

import pytest

from app.core.grocy_mapping_keys import (
    KEY_ENV_FALLBACK,
    KEY_TYPES,
    KEY_VALIDATORS,
    GrocyMappingKey,
    MissingHouseholdSetting,
)


class TestGrocyMappingKey:
    def test_enum_values_are_stable(self):
        # Public contract: keys are persisted in DB rows + JSON, must not drift.
        assert GrocyMappingKey.GRAM_UNIT_ID.value == "gram_unit_id"
        assert GrocyMappingKey.ML_UNIT_ID.value == "ml_unit_id"
        assert GrocyMappingKey.PORTION_UNIT_ID.value == "portion_unit_id"

    def test_enum_member_count(self):
        assert len(list(GrocyMappingKey)) == 3

    def test_str_enum_str_equality(self):
        # StrEnum: member.value usage in checks like `data["code"] == key.value`.
        assert GrocyMappingKey.GRAM_UNIT_ID == "gram_unit_id"


class TestKeyTypesCoverage:
    def test_every_key_has_a_type(self):
        for key in GrocyMappingKey:
            assert key in KEY_TYPES, f"missing type for {key}"

    def test_all_types_are_int(self):
        for key in GrocyMappingKey:
            assert KEY_TYPES[key] is int


class TestKeyEnvFallbackCoverage:
    def test_every_key_has_env_fallback(self):
        for key in GrocyMappingKey:
            assert key in KEY_ENV_FALLBACK

    def test_env_fallback_names(self):
        assert KEY_ENV_FALLBACK[GrocyMappingKey.GRAM_UNIT_ID] == "GROCY_GRAM_UNIT_ID"
        assert KEY_ENV_FALLBACK[GrocyMappingKey.ML_UNIT_ID] == "GROCY_ML_UNIT_ID"
        assert KEY_ENV_FALLBACK[GrocyMappingKey.PORTION_UNIT_ID] == "GROCY_PORTION_UNIT_ID"


class TestKeyValidators:
    def test_every_key_has_validator(self):
        for key in GrocyMappingKey:
            assert key in KEY_VALIDATORS

    @pytest.mark.parametrize("key", list(GrocyMappingKey))
    def test_positive_int_string_is_valid(self, key):
        assert KEY_VALIDATORS[key]("1") is True
        assert KEY_VALIDATORS[key]("82") is True
        assert KEY_VALIDATORS[key]("99999") is True

    @pytest.mark.parametrize("key", list(GrocyMappingKey))
    def test_zero_is_invalid(self, key):
        assert KEY_VALIDATORS[key]("0") is False

    @pytest.mark.parametrize("key", list(GrocyMappingKey))
    def test_negative_is_invalid(self, key):
        assert KEY_VALIDATORS[key]("-1") is False

    @pytest.mark.parametrize("key", list(GrocyMappingKey))
    @pytest.mark.parametrize("bad", ["", "abc", "1.5", "1e2", " ", "1 2"])
    def test_non_int_strings_are_invalid(self, key, bad):
        assert KEY_VALIDATORS[key](bad) is False


class TestMissingHouseholdSetting:
    def test_carries_key_attribute(self):
        exc = MissingHouseholdSetting("gram_unit_id")
        assert exc.key == "gram_unit_id"

    def test_message_includes_key(self):
        exc = MissingHouseholdSetting("ml_unit_id")
        assert "ml_unit_id" in str(exc)

    def test_is_exception_subclass(self):
        exc = MissingHouseholdSetting("portion_unit_id")
        assert isinstance(exc, Exception)
