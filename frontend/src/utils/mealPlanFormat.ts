/** Format a Date as YYYY-MM-DD in the local timezone.
 *
 * `Date#toISOString().slice(0, 10)` slices the UTC representation, which is
 * one day off for users east-or-west of UTC near midnight. User-facing dates
 * (meal plan day, daily nutrition, consumption history) are local concepts —
 * always use this helper, never `toISOString`.
 */
export function formatLocalDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Parse a YYYY-MM-DD string as a local-midnight Date.
 *
 * `new Date('YYYY-MM-DD')` parses as UTC midnight, which is the previous local
 * day for west-of-UTC users. This helper preserves the calendar date the user
 * meant.
 */
export function parseLocalDate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Today's date in the user's local timezone, as YYYY-MM-DD. */
export function todayLocal(): string {
  return formatLocalDate(new Date())
}

/** ISO week start (Monday) for a YYYY-MM-DD date. */
export function startOfWeek(s: string): string {
  const d = parseLocalDate(s)
  const dow = d.getDay() // 0=Sun..6=Sat
  const diff = (dow + 6) % 7
  d.setDate(d.getDate() - diff)
  return formatLocalDate(d)
}

export function addDays(s: string, n: number): string {
  const d = parseLocalDate(s)
  d.setDate(d.getDate() + n)
  return formatLocalDate(d)
}

/** 3 decimals, trailing zeros stripped: 22 -> "22", 0.06700 -> "0.067". */
export function formatAmount(v: string | number | null | undefined): string {
  if (v == null) return ''
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return String(v)
  return Number(n.toFixed(3)).toString()
}
