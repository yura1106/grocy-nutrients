import { computed, onMounted, type ComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/
/** Backend `/api/consumption/stats` rejects ranges wider than this. Realistic
 *  usage is 60–90 days; the bound just prevents accidental URL tampering. */
export const MAX_RANGE_DAYS = 365

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function isValidIsoDate(s: unknown): s is string {
  if (typeof s !== 'string' || !ISO_DATE_RE.test(s)) return false
  const d = new Date(s + 'T00:00:00')
  if (Number.isNaN(d.getTime())) return false
  // Reject rolled-over dates like 2026-04-31 (silently becomes 2026-05-01).
  return isoDate(d) === s
}

function daysBetweenInclusive(fromIso: string, toIso: string): number {
  const f = new Date(fromIso + 'T00:00:00').getTime()
  const t = new Date(toIso + 'T00:00:00').getTime()
  return Math.round((t - f) / 86_400_000) + 1
}

function defaultRange(): { from: string; to: string } {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const from = new Date(today)
  from.setDate(from.getDate() - 6)
  return { from: isoDate(from), to: isoDate(today) }
}

export interface UseDateRangeQueryReturn {
  from: ComputedRef<string>
  to: ComputedRef<string>
  isDefault: ComputedRef<boolean>
  setRange: (from: string, to: string) => void
  clearRange: () => void
}

export function useDateRangeQuery(): UseDateRangeQueryReturn {
  const route = useRoute()
  const router = useRouter()

  const parsed = computed(() => {
    const qFrom = route.query.from
    const qTo = route.query.to
    const validFrom = isValidIsoDate(qFrom) ? qFrom : null
    const validTo = isValidIsoDate(qTo) ? qTo : null
    if (
      validFrom &&
      validTo &&
      validFrom <= validTo &&
      daysBetweenInclusive(validFrom, validTo) <= MAX_RANGE_DAYS
    ) {
      return { from: validFrom, to: validTo, isDefault: false }
    }
    const def = defaultRange()
    return { from: def.from, to: def.to, isDefault: true }
  })

  const from = computed(() => parsed.value.from)
  const to = computed(() => parsed.value.to)
  const isDefault = computed(() => parsed.value.isDefault)

  function setRange(newFrom: string, newTo: string): void {
    if (!isValidIsoDate(newFrom) || !isValidIsoDate(newTo)) return
    if (newFrom > newTo) return
    if (daysBetweenInclusive(newFrom, newTo) > MAX_RANGE_DAYS) return
    router.replace({ query: { ...route.query, from: newFrom, to: newTo } })
  }

  function clearRange(): void {
    const next = { ...route.query }
    delete next.from
    delete next.to
    router.replace({ query: next })
  }

  // Writeback: if the URL has invalid from/to params but we fell back to the
  // default range, scrub them so the user's bookmark/share isn't broken. Only
  // touches the URL when there's something to remove (avoids spurious history
  // entries when the URL is already clean).
  onMounted(() => {
    if (isDefault.value && (route.query.from != null || route.query.to != null)) {
      const next = { ...route.query }
      delete next.from
      delete next.to
      router.replace({ query: next })
    }
  })

  return { from, to, isDefault, setRange, clearRange }
}
