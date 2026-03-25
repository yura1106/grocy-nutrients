/**
 * Shared nutrient color logic based on daily norm percentage.
 *
 * "More is better" (calories, protein, carbs, fats, fiber):
 *   >105% → red, 95–105% → green, 80–95% → amber, <80% → blue
 *
 * "Less is better" (sugar, saturated fat, salt):
 *   >105% → red, 95–105% → amber, <95% → no color
 */

export interface NutrientColorResult {
  /** Tailwind text class for table cells / labels */
  textClass: string
  /** Hex color for SVG strokes (gauges) */
  hex: string
}

const RED: NutrientColorResult = { textClass: 'text-red-600 font-semibold', hex: '#ef4444' }
const GREEN: NutrientColorResult = { textClass: 'text-green-600 font-semibold', hex: '#22c55e' }
const AMBER: NutrientColorResult = { textClass: 'text-amber-600', hex: '#f59e0b' }
const BLUE: NutrientColorResult = { textClass: 'text-blue-500', hex: '#3b82f6' }
const NEUTRAL: NutrientColorResult = { textClass: '', hex: '#22c55e' }

export function nutrientColor(
  value: number,
  norm: number | null | undefined,
  lessIsBetter = false,
): NutrientColorResult {
  if (!norm) return NEUTRAL
  const pct = value / norm
  if (pct > 1.05) return RED
  if (lessIsBetter) {
    if (pct >= 0.95) return AMBER
    return NEUTRAL
  }
  if (pct >= 0.95) return GREEN
  if (pct >= 0.8) return AMBER
  return BLUE
}

/** Convenience: return only the Tailwind text class (for table cells). */
export function nutrientTextClass(
  value: number,
  norm: number | null | undefined,
  lessIsBetter = false,
): string {
  return nutrientColor(value, norm, lessIsBetter).textClass
}

/** Convenience: return only the hex color (for SVG gauges). */
export function nutrientHex(
  value: number,
  norm: number | null | undefined,
  lessIsBetter = false,
): string {
  return nutrientColor(value, norm, lessIsBetter).hex
}
