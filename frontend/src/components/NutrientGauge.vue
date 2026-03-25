<template>
  <div class="flex flex-col items-center">
    <svg
      :width="size"
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
    >
      <!-- Background circle -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="bgColor"
        :stroke-width="strokeWidth"
      />
      <!-- Progress arc -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="progressColor"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        :transform="`rotate(-90 ${center} ${center})`"
      />
      <!-- Percentage text -->
      <text
        :x="center"
        :y="center"
        text-anchor="middle"
        dominant-baseline="central"
        :font-size="fontSize"
        font-weight="600"
        :fill="progressColor"
      >
        {{ displayPercent }}
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { nutrientHex } from '../composables/useNutrientColor'

const props = withDefaults(defineProps<{
  value: number
  max: number | null
  size?: number
  strokeWidth?: number
  lessIsBetter?: boolean
}>(), {
  size: 40,
  strokeWidth: 3.5,
  lessIsBetter: false,
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const percent = computed(() => {
  if (!props.max || props.max <= 0) return 0
  return (props.value / props.max) * 100
})

const clampedPercent = computed(() => Math.min(percent.value, 100))

const dashOffset = computed(() => {
  return circumference.value * (1 - clampedPercent.value / 100)
})

const bgColor = '#e5e7eb'

const progressColor = computed(() =>
  nutrientHex(props.value, props.max, props.lessIsBetter),
)

const fontSize = computed(() => Math.round(props.size * 0.26))

const displayPercent = computed(() => {
  const p = Math.round(percent.value)
  return p > 999 ? '999' : `${p}%`
})
</script>
