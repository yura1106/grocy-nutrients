<template>
  <div class="w-full">
    <p class="text-xs text-gray-500 mb-3">
      <span
        class="font-medium"
        :style="{ color: HARMFUL_COLOR }"
      >Цукри в норму</span>
      +
      <span
        class="font-medium"
        :style="{ color: FRESH_COLOR }"
      >свіжі (не враховуються)</span>
      по днях. Пунктир — середній ліміт цукрів
      ({{ avgLimit != null ? avgLimit.toFixed(1) : '—' }} г).
    </p>
    <div
      class="h-[280px] overflow-x-auto"
      role="img"
      :aria-label="ariaLabel"
    >
      <div
        :style="{ height: '100%', minWidth: minChartWidth + 'px', width: '100%' }"
      >
        <Bar
          :data="chartData"
          :options="chartOptions"
        />
      </div>
    </div>
    <div class="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-gray-100">
      <StatBlock
        label="Цукри в норму (avg)"
        :value="avgHarmful"
        unit="г"
        :limit="avgLimit"
        :decimals="1"
        :less-is-better="true"
      />
      <StatBlock
        label="Свіжі (avg)"
        :value="avgFresh"
        unit="г"
        :limit="null"
        :decimals="1"
        :less-is-better="false"
        :force-neutral="true"
      />
      <StatBlock
        label="Ліміт"
        :value="avgLimit ?? 0"
        unit="г"
        :limit="null"
        :decimals="1"
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
  NUTRIENT_COLORS,
  formatDayShortUk,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'
import { buildSugarsStackedView } from '@/composables/useSugarsStacked'
import { ensureChartJsRegistered } from './chartSetup'
import StatBlock from './StatBlock.vue'

ensureChartJsRegistered()

const props = defineProps<{
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const HARMFUL_COLOR = NUTRIENT_COLORS.carbohydrates_of_sugars
const FRESH_COLOR = '#22c55e'

const view = computed(() => buildSugarsStackedView(props.days, props.effectiveLimitsByDate))

const consumedDays = computed(() => view.value.days)
const harmful = computed(() => view.value.harmful)
const fresh = computed(() => view.value.fresh)
const avgLimit = computed(() => view.value.avgLimit)
const avgHarmful = computed(() => view.value.avgHarmful)
const avgFresh = computed(() => view.value.avgFresh)

const labels = computed(() => consumedDays.value.map(d => formatDayShortUk(d.date)))
const minChartWidth = computed(() => Math.max(consumedDays.value.length * 14, 200))

const ariaLabel = computed(
  () => `Складений графік цукрів: в норму та свіжі за ${consumedDays.value.length} днів.`,
)

const chartData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: 'Цукри в норму',
      data: harmful.value,
      backgroundColor: HARMFUL_COLOR,
      stack: 'sugars',
      borderRadius: 2,
      maxBarThickness: 42,
    },
    {
      label: 'Свіжі (не враховуються)',
      data: fresh.value,
      backgroundColor: FRESH_COLOR,
      stack: 'sugars',
      borderRadius: 2,
      maxBarThickness: 42,
    },
  ],
}))

const chartOptions = computed(() => {
  const limit = avgLimit.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom' as const,
        labels: { boxWidth: 10, font: { size: 11 }, color: '#6b7280' },
      },
      tooltip: {
        callbacks: {
          label: (ctx: TooltipItem<'bar'>) =>
            `${ctx.dataset.label}: ${(ctx.parsed.y ?? 0).toFixed(1)} г`,
        },
      },
      annotation: limit != null
        ? {
            annotations: {
              sugarLimit: {
                type: 'line' as const,
                yMin: limit,
                yMax: limit,
                borderColor: '#6b7280',
                borderWidth: 2,
                borderDash: [5, 4],
                label: {
                  display: true,
                  content: `Ліміт: ${limit.toFixed(1)} г`,
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
      x: {
        stacked: true,
        grid: { color: '#f0f0f0' },
        ticks: { color: '#9ca3af', font: { size: 11 } },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        grid: { color: '#f0f0f0' },
        ticks: { color: '#9ca3af', font: { size: 11 } },
      },
    },
  }
})
</script>
