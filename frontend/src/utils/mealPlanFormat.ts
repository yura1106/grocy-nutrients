/** ISO week start (Monday) for a YYYY-MM-DD date. */
export function startOfWeek(s: string): string {
  const d = new Date(s)
  const dow = d.getDay() // 0=Sun..6=Sat
  const diff = (dow + 6) % 7
  d.setDate(d.getDate() - diff)
  return d.toISOString().slice(0, 10)
}

export function addDays(s: string, n: number): string {
  const d = new Date(s)
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

/** 3 decimals, trailing zeros stripped: 22 -> "22", 0.06700 -> "0.067". */
export function formatAmount(v: string | number | null | undefined): string {
  if (v == null) return ''
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return String(v)
  return Number(n.toFixed(3)).toString()
}
