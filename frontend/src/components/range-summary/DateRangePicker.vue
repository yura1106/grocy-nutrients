<template>
  <div
    class="inline-flex items-stretch rounded-lg border transition-colors"
    :class="hasRange
      ? 'bg-blue-50 border-blue-200'
      : 'bg-white border-gray-200 hover:bg-gray-50'"
  >
    <button
      ref="triggerRef"
      type="button"
      class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-l-lg"
      :class="[
        hasRange ? 'text-blue-700' : 'text-gray-700',
        !hasRange && 'rounded-r-lg',
      ]"
      :aria-label="hasRange ? `Період: ${label}. Натисніть, щоб змінити.` : 'Обрати період'"
      @click="openPicker"
    >
      <Calendar
        :size="13"
        :class="hasRange ? 'text-blue-500' : 'text-gray-400'"
      />
      <span class="max-w-[220px] truncate">{{ label }}</span>
      <ChevronDown
        v-if="!hasRange"
        :size="12"
        class="text-gray-400"
      />
    </button>
    <button
      v-if="hasRange"
      type="button"
      class="px-2 py-1.5 rounded-r-lg text-blue-400 hover:text-blue-700 transition-colors border-l border-blue-200"
      aria-label="Скинути період"
      @click="onClear"
    >
      <X :size="12" />
    </button>
    <input
      ref="inputRef"
      type="text"
      class="sr-only"
      aria-hidden="true"
      tabindex="-1"
      readonly
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Calendar, ChevronDown, X } from 'lucide-vue-next'
import flatpickr from 'flatpickr'
import { Ukrainian } from 'flatpickr/dist/l10n/uk'
import 'flatpickr/dist/flatpickr.min.css'
import type { Instance as FlatpickrInstance } from 'flatpickr/dist/types/instance'

const props = defineProps<{
  from: string
  to: string
  isDefault: boolean
}>()
const emit = defineEmits<{
  'update:range': [from: string, to: string]
  clear: []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
let fp: FlatpickrInstance | null = null

const hasRange = computed(() => !props.isDefault)

const MONTHS_SHORT = ['січ', 'лют', 'бер', 'кв', 'трав', 'черв', 'лип', 'серп', 'вер', 'жовт', 'лист', 'груд']

function formatDay(s: string, withYear: boolean): string {
  const [y, m, d] = s.split('-').map(Number)
  const month = MONTHS_SHORT[m - 1]
  return withYear ? `${d} ${month} ${y}` : `${d} ${month}`
}

const label = computed(() => {
  const fromYear = props.from.slice(0, 4)
  const toYear = props.to.slice(0, 4)
  const sameYear = fromYear === toYear
  return `${formatDay(props.from, !sameYear)} – ${formatDay(props.to, true)}`
})

function openPicker(): void {
  fp?.open()
}

function onClear(): void {
  emit('clear')
}

function formatIso(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

onMounted(() => {
  if (!inputRef.value) return
  fp = flatpickr(inputRef.value, {
    mode: 'range',
    dateFormat: 'Y-m-d',
    defaultDate: [props.from, props.to],
    locale: Ukrainian,
    positionElement: triggerRef.value ?? undefined,
    clickOpens: false,
    allowInput: false,
    onClose: (selectedDates) => {
      if (selectedDates.length === 2) {
        const [a, b] = selectedDates
        const fromIso = formatIso(a < b ? a : b)
        const toIso = formatIso(a < b ? b : a)
        emit('update:range', fromIso, toIso)
      }
    },
  })
})

watch(
  () => [props.from, props.to],
  ([f, t]) => {
    if (fp) fp.setDate([f, t], false)
  },
)

onBeforeUnmount(() => {
  fp?.destroy()
  fp = null
})
</script>
