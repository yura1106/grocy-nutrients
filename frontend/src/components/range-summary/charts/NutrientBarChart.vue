<template>
  <div class="w-full">
    <p class="text-xs text-gray-500 mb-3">
      Денний показник <span
        class="font-medium"
        :style="{ color: NUTRIENT_COLOR }"
      >
        {{ NUTRIENT_META[nutrientKey].label }}
      </span>
      vs середній ліміт ({{ avgLimit != null ? avgLimit.toFixed(NUTRIENT_META[nutrientKey].decimals) : '—' }}
      {{ NUTRIENT_META[nutrientKey].unit }}). Кольори барів — за статусом.
    </p>
    <div
      class="h-[280px] overflow-x-auto"
      role="img"
      :aria-label="ariaLabel"
    >
      <div
        :style="{
          height: '100%',
          minWidth: minChartWidth + 'px',
          width: '100%',
        }"
      >
        <Bar
          :data="chartData"
          :options="chartOptions"
        />
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-100">
      <StatBlock
        label="Min"
        :value="stats.min"
        :unit="NUTRIENT_META[nutrientKey].unit"
        :limit="avgLimit"
        :decimals="NUTRIENT_META[nutrientKey].decimals"
        :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter"
      />
      <StatBlock
        label="Max"
        :value="stats.max"
        :unit="NUTRIENT_META[nutrientKey].unit"
        :limit="avgLimit"
        :decimals="NUTRIENT_META[nutrientKey].decimals"
        :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter"
      />
      <StatBlock
        label="Avg"
        :value="stats.avg"
        :unit="NUTRIENT_META[nutrientKey].unit"
        :limit="avgLimit"
        :decimals="NUTRIENT_META[nutrientKey].decimals"
        :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter"
      />
      <StatBlock
        label="Limit"
        :value="avgLimit ?? 0"
        :unit="NUTRIENT_META[nutrientKey].unit"
        :limit="null"
        :decimals="NUTRIENT_META[nutrientKey].decimals"
        :less-is-better="false"
        :force-neutral="true"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import {
  type DailyStatsRow,
  type NutrientKey,
  NUTRIENT_META,
  NUTRIENT_COLORS,
  STATS_FIELD,
  NORM_FIELD,
  formatDayShortUk,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'
import { nutrientHex } from '@/composables/useNutrientColor'
import { ensureChartJsRegistered } from './chartSetup'
import StatBlock from './StatBlock.vue'

ensureChartJsRegistered()

const props = defineProps<{
  nutrientKey: NutrientKey
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const NUTRIENT_COLOR = computed(() => NUTRIENT_COLORS[props.nutrientKey])

const consumedDays = computed(() =>
  [...props.days].filter(d => d.products_count > 0).reverse(),
)

const values = computed(() =>
  consumedDays.value.map(d => d[STATS_FIELD[props.nutrientKey]] as number),
)

const avgLimit = computed(() => {
  let sum = 0
  let count = 0
  for (const d of consumedDays.value) {
    const norm = props.effectiveLimitsByDate.get(d.date)
    const v = norm?.[NORM_FIELD[props.nutrientKey]] ?? null
    if (v != null) {
      sum += v
      count += 1
    }
  }
  return count > 0 ? sum / count : null
})

const stats = computed(() => {
  const v = values.value
  if (v.length === 0) return { min: 0, max: 0, avg: 0 }
  const min = Math.min(...v)
  const max = Math.max(...v)
  const avg = v.reduce((a, b) => a + b, 0) / v.length
  return { min, max, avg }
})

const labels = computed(() => consumedDays.value.map(d => formatDayShortUk(d.date)))

const minChartWidth = computed(() => Math.max(consumedDays.value.length * 12, 200))

const ariaLabel = computed(() => {
  const meta = NUTRIENT_META[props.nutrientKey]
  return `Стовпчастий графік: ${meta.label} (${meta.unit}) за ${consumedDays.value.length} днів.`
})

const chartData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: NUTRIENT_META[props.nutrientKey].label,
      data: values.value,
      backgroundColor: consumedDays.value.map((d, i) => {
        const norm = props.effectiveLimitsByDate.get(d.date)
        const limit = norm?.[NORM_FIELD[props.nutrientKey]] ?? null
        if (limit == null) return '#6b7280'
        return nutrientHex(values.value[i], limit, NUTRIENT_META[props.nutrientKey].lessIsBetter)
      }),
      borderRadius: 4,
      maxBarThickness: 42,
    },
  ],
}))

const chartOptions = computed(() => {
  const meta = NUTRIENT_META[props.nutrientKey]
  const limit = avgLimit.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: TooltipItem<'bar'>) => {
            const v = ctx.parsed.y
            if (v == null) return [`Значення: —`]
            const pct = limit ? Math.round((v / limit) * 100) : null
            return [
              `Значення: ${v.toFixed(meta.decimals)} ${meta.unit}`,
              limit != null ? `% ліміту: ${pct}%` : '',
            ].filter(Boolean) as string[]
          },
        },
      },
      annotation: limit != null
        ? {
            annotations: {
              avgLimit: {
                type: 'line' as const,
                yMin: limit,
                yMax: limit,
                borderColor: '#6b7280',
                borderWidth: 2,
                borderDash: [5, 4],
                label: {
                  display: true,
                  content: `Ліміт: ${limit.toFixed(meta.decimals)} ${meta.unit}`,
                  position: 'end' as const,
                  backgroundColor: 'transparent',
                  color: '#6b7280',
                  font: { size: 10 },
                },
              },
            },
          }
        : { annotations: {} },
    },
    scales: {
      x: { grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
      y: { beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    },
  }
})
</script>
