<template>
  <div class="flex flex-col items-center gap-0.5 bg-gray-50 rounded-lg px-3 py-2">
    <span class="text-[10px] text-gray-400 uppercase tracking-wide">{{ label }}</span>
    <span
      class="text-sm font-semibold"
      :class="textClass"
    >
      {{ value.toFixed(decimals) }}
      <span class="text-xs text-gray-400 ml-0.5">{{ unit }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { nutrientColor } from '@/composables/useNutrientColor'

const props = withDefaults(
  defineProps<{
    label: string
    value: number
    unit: string
    limit: number | null
    decimals: number
    lessIsBetter: boolean
    forceNeutral?: boolean
  }>(),
  { forceNeutral: false },
)

const textClass = computed(() => {
  if (props.forceNeutral || props.limit == null) return 'text-gray-700'
  return nutrientColor(props.value, props.limit, props.lessIsBetter).textClass || 'text-gray-700'
})
</script>
