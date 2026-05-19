"""Parse nutrient values embedded in meal plan note text.

Format example: "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
"""

import contextlib

NOTE_NUTRIENT_MAP: dict[str, str] = {
    "Калорій": "calories",
    "Білків": "proteins",
    "Вуглеводів": "carbohydrates",
    "Жирів": "fats",
    "Жирів нас.": "fats_saturated",
    "Вуглеводів цукрів": "carbohydrates_of_sugars",
    "Солі": "salt",
    "Клітковини": "fibers",
}


def parse_note_nutrients(note: str) -> dict[str, float]:
    """Parse nutrient values from a meal plan note string.

    Returns only the keys actually found in the note. Unknown keys, malformed
    values, and notes without the format produce an empty dict — non-matching
    notes are not an error.
    """
    result: dict[str, float] = {}
    if not note:
        return result
    for part in note.split("/"):
        kv = part.split(":")
        if len(kv) == 2:
            key = NOTE_NUTRIENT_MAP.get(kv[0].strip())
            if key:
                with contextlib.suppress(ValueError):
                    result[key] = float(kv[1].strip())
    return result
