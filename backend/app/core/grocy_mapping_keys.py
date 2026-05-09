from collections.abc import Callable
from enum import StrEnum


class GrocyMappingKey(StrEnum):
    GRAM_UNIT_ID = "gram_unit_id"
    ML_UNIT_ID = "ml_unit_id"
    PORTION_UNIT_ID = "portion_unit_id"


KEY_TYPES: dict[GrocyMappingKey, type] = {
    GrocyMappingKey.GRAM_UNIT_ID: int,
    GrocyMappingKey.ML_UNIT_ID: int,
    GrocyMappingKey.PORTION_UNIT_ID: int,
}

KEY_ENV_FALLBACK: dict[GrocyMappingKey, str] = {
    GrocyMappingKey.GRAM_UNIT_ID: "GROCY_GRAM_UNIT_ID",
    GrocyMappingKey.ML_UNIT_ID: "GROCY_ML_UNIT_ID",
    GrocyMappingKey.PORTION_UNIT_ID: "GROCY_PORTION_UNIT_ID",
}


def _is_positive_int_str(value: str) -> bool:
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


KEY_VALIDATORS: dict[GrocyMappingKey, Callable[[str], bool]] = {
    GrocyMappingKey.GRAM_UNIT_ID: _is_positive_int_str,
    GrocyMappingKey.ML_UNIT_ID: _is_positive_int_str,
    GrocyMappingKey.PORTION_UNIT_ID: _is_positive_int_str,
}


class MissingHouseholdSetting(Exception):
    """Raised when a required per-household Grocy mapping value is NULL or absent."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Missing household setting: {key}")
