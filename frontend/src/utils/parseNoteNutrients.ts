/**
 * Parse nutrient values embedded in meal plan note text.
 *
 * Format example: "Калорій:500/Білків:30/Вуглеводів:60/Жирів:15"
 *
 * Mirrors `app/core/note_nutrients.py` on the backend — keep both in sync
 * when the Ukrainian key mapping changes. Output keys use the same names
 * as `MealPlanDailyTotals` totals (kcal/protein/carbs/sugars/fat/satFat/fibers).
 * `salt` is dropped because daily totals do not track it.
 */

export interface ParsedNoteNutrients {
  kcal?: number
  protein?: number
  carbs?: number
  sugars?: number
  fat?: number
  satFat?: number
  fibers?: number
}

const NOTE_NUTRIENT_MAP: Record<string, keyof ParsedNoteNutrients | 'salt'> = {
  'Калорій': 'kcal',
  'Білків': 'protein',
  'Вуглеводів': 'carbs',
  'Жирів': 'fat',
  'Жирів нас.': 'satFat',
  'Вуглеводів цукрів': 'sugars',
  'Солі': 'salt',
  'Клітковини': 'fibers',
}

export function parseNoteNutrients(note: string | null | undefined): ParsedNoteNutrients {
  const result: ParsedNoteNutrients = {}
  if (!note) return result
  for (const part of note.split('/')) {
    const idx = part.indexOf(':')
    if (idx < 0) continue
    const rawKey = part.slice(0, idx).trim()
    const rawValue = part.slice(idx + 1).trim()
    const target = NOTE_NUTRIENT_MAP[rawKey]
    if (!target || target === 'salt') continue
    const num = Number(rawValue)
    if (Number.isFinite(num)) {
      result[target] = num
    }
  }
  return result
}
