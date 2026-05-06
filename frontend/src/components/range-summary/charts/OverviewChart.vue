<template>
  <div class="w-full">
    <p class="text-xs text-gray-500 mb-3">
      Усі нутрієнти як <span class="font-medium text-gray-700">% ефективного ліміту</span>. Лінія 100% — норма.
    </p>
    <div
      class="h-[320px]"
      role="img"
      :aria-label="ariaLabel"
    >
      <Line
        :data="chartData"
        :options="chartOptions"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import {
  type DailyStatsRow,
  NUTRIENT_KEYS,
  NUTRIENT_META,
  NUTRIENT_COLORS,
  STATS_FIELD,
  NORM_FIELD,
  formatDayShortUk,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'
import { ensureChartJsRegistered } from './chartSetup'

ensureChartJsRegistered()

const props = defineProps<{
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const consumedDays = computed(() =>
  [...props.days].filter(d => d.products_count > 0).reverse(),
)

const labels = computed(() => consumedDays.value.map(d => formatDayShortUk(d.date)))

const ariaLabel = computed(
  () => `Лінійний графік: % ефективного ліміту для 8 нутрієнтів за ${consumedDays.value.length} днів.`,
)

const chartData = computed(() => {
  const datasets = NUTRIENT_KEYS.map((key) => {
    const color = NUTRIENT_COLORS[key]
    const data = consumedDays.value.map((d) => {
      const norm = props.effectiveLimitsByDate.get(d.date)
      const limit = norm?.[NORM_FIELD[key]] ?? null
      const value = d[STATS_FIELD[key]] as number
      if (limit == null || limit === 0) return null
      return Math.round((value / limit) * 100)
    })
    return {
      label: NUTRIENT_META[key].label,
      data,
      borderColor: color,
      backgroundColor: color,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
      spanGaps: false,
    }
  })

  return { labels: labels.value, datasets }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { font: { size: 11 }, color: '#6b7280', boxWidth: 12 },
    },
    tooltip: {
      callbacks: {
        label: (ctx: TooltipItem<'line'>) => {
          if (ctx.parsed.y == null) return `${ctx.dataset.label}: —`
          return `${ctx.dataset.label}: ${ctx.parsed.y}%`
        },
      },
    },
    annotation: {
      annotations: {
        target: {
          type: 'line' as const,
          yMin: 100,
          yMax: 100,
          borderColor: '#9ca3af',
          borderWidth: 1.5,
          borderDash: [5, 4],
          label: {
            display: true,
            content: '100%',
            position: 'end' as const,
            backgroundColor: 'transparent',
            color: '#6b7280',
            font: { size: 10 },
          },
        },
      },
    },
  },
  scales: {
    x: { grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    y: {
      beginAtZero: true,
      grid: { color: '#f0f0f0' },
      ticks: { color: '#9ca3af', font: { size: 11 }, callback: (v: number | string) => `${v}%` },
    },
  },
}))
</script>
