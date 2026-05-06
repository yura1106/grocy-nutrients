<template>
  <div class="flex flex-col gap-1.5 p-3 bg-gray-50 rounded-lg border border-gray-100">
    <header class="flex items-center justify-between">
      <span class="text-xs text-gray-500 uppercase tracking-wide">{{ label }}</span>
      <component
        :is="trendIcon"
        :size="13"
        :class="trendClass"
      />
    </header>

    <div class="flex items-baseline gap-1">
      <span :class="['text-base font-semibold', textClass || 'text-gray-900']">
        {{ avg.toFixed(decimals) }}
      </span>
      <span class="text-xs text-gray-400">
        / {{ limit != null ? limit.toFixed(decimals) : '—' }} {{ unit }}
      </span>
    </div>

    <div
      v-if="limit != null"
      class="relative h-1.5 bg-gray-200 rounded-full"
    >
      <div
        class="h-full rounded-full transition-all"
        :class="barColorClass"
        :style="{ width: barWidth + '%' }"
      ></div>
      <div
        class="absolute top-1/2 -translate-y-1/2 w-0.5 h-3 bg-gray-500 rounded-full opacity-60"
        style="left: 50%"
      ></div>
    </div>

    <footer class="flex items-center justify-between">
      <span class="text-[10px] text-gray-400">
        {{ showCoverageHint ? `Ліміт: ${limitCoverageDays} з ${includedDayCount} днів` : 'Факт / Ліміт' }}
      </span>
      <span :class="['text-[11px] font-semibold', textClass || 'text-gray-400']">
        {{ limit != null ? `${pct}%` : '—' }}
      </span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Minus, TrendingDown, TrendingUp } from 'lucide-vue-next'
import { nutrientColor, type NutrientSeverity } from '../composables/useNutrientColor'

const props = withDefaults(
  defineProps<{
    label: string
    unit: string
    avg: number
    limit: number | null
    lessIsBetter?: boolean
    decimals?: number
    limitCoverageDays?: number
    includedDayCount?: number
  }>(),
  {
    lessIsBetter: false,
    decimals: 1,
    limitCoverageDays: undefined,
    includedDayCount: undefined,
  },
)

const showCoverageHint = computed(() => {
  const m = props.limitCoverageDays
  const n = props.includedDayCount
  return m != null && n != null && m > 0 && m < n
})

const colorResult = computed(() => nutrientColor(props.avg, props.limit, props.lessIsBetter))

const textClass = computed(() => colorResult.value.textClass)

const BAR_BG: Record<NutrientSeverity, string> = {
  red: 'bg-red-500',
  amber: 'bg-amber-500',
  green: 'bg-emerald-500',
  blue: 'bg-blue-400',
  neutral: 'bg-gray-300',
}

const barColorClass = computed(() => BAR_BG[colorResult.value.severity])

const pct = computed(() => {
  if (!props.limit) return 0
  return Math.round((props.avg / props.limit) * 100)
})

const barWidth = computed(() => {
  if (!props.limit) return 0
  return Math.min((props.avg / (props.limit * 2)) * 100, 100)
})

const trendIcon = computed(() => {
  if (props.limit == null) return Minus
  const dev = pct.value - 100
  if (dev > 5) return TrendingUp
  if (dev < -5) return TrendingDown
  return Minus
})

const trendClass = computed(() => {
  if (props.limit == null) return 'text-gray-300'
  const dev = pct.value - 100
  if (dev > 5) return 'text-red-500'
  if (dev < -5) return 'text-blue-400'
  return 'text-emerald-500'
})
</script>
