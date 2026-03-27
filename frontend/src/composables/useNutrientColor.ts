/**
 * Shared nutrient color logic based on daily norm percentage.
 *
 * "More is better" (calories, protein, carbs, fats, fiber):
 *   >105% → red, 95–105% → green, 80–95% → amber, <80% → blue
 *
 * "Less is better" (sugar, saturated fat, salt):
 *   >105% → red, 95–105% → amber, <95% → no color
 */

export type NutrientSeverity = 'red' | 'amber' | 'blue' | 'green' | 'neutral'

export interface NutrientColorResult {
  severity: NutrientSeverity
  /** Tailwind text class for table cells / labels */
  textClass: string
  /** Hex color for SVG strokes (gauges) */
  hex: string
}

const RED: NutrientColorResult = { severity: 'red', textClass: 'text-red-600 font-semibold', hex: '#ef4444' }
const GREEN: NutrientColorResult = { severity: 'green', textClass: 'text-green-600 font-semibold', hex: '#22c55e' }
const AMBER: NutrientColorResult = { severity: 'amber', textClass: 'text-amber-600', hex: '#f59e0b' }
const BLUE: NutrientColorResult = { severity: 'blue', textClass: 'text-blue-500', hex: '#3b82f6' }
const NEUTRAL: NutrientColorResult = { severity: 'neutral', textClass: '', hex: '#22c55e' }

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

/**
 * Color for a single product's share of the daily norm.
 * Answers: "does this one product eat up too much of the daily budget?"
 *
 * ≥20% → RED, ≥12% → AMBER, ≥5% → BLUE, <5% → no color
 */
export function productNutrientColor(
  value: number,
  norm: number | null | undefined,
): NutrientColorResult {
  if (!norm || value <= 0) return NEUTRAL
  const share = value / norm
  if (share >= 0.20) return RED
  if (share >= 0.12) return AMBER
  if (share >= 0.05) return BLUE
  return NEUTRAL
}

export function productNutrientTextClass(
  value: number,
  norm: number | null | undefined,
): string {
  return productNutrientColor(value, norm).textClass
}
