<script setup lang="ts" generic="T extends object">
import { computed, ref } from 'vue'
import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue'

interface Props {
  modelValue: T | null
  options: T[]
  labelKey: keyof T
  trackBy: keyof T
  placeholder?: string
  disabled?: boolean
  filter?: (option: T, query: string) => boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Search...',
  disabled: false,
  filter: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: T | null]
  select: [value: T]
}>()

defineSlots<{
  option(props: { option: T; active: boolean; selected: boolean }): unknown
}>()

const query = ref('')

const filtered = computed(() => {
  if (query.value === '') return props.options
  const q = query.value.toLowerCase()
  if (props.filter) {
    return props.options.filter((o) => props.filter!(o, query.value))
  }
  return props.options.filter((o) =>
    String(o[props.labelKey]).toLowerCase().includes(q),
  )
})

const displayValue = (option: T | null) => {
  if (!option) return ''
  return String(option[props.labelKey])
}

const onChange = (value: T | null) => {
  emit('update:modelValue', value)
  if (value) emit('select', value)
}
</script>

<template>
  <Combobox
    :model-value="modelValue"
    :disabled="disabled"
    :by="trackBy as string"
    nullable
    @update:model-value="onChange"
  >
    <div class="relative">
      <div
        class="relative w-full cursor-default overflow-hidden rounded-md border border-gray-300 bg-white text-left shadow-xs focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500"
      >
        <ComboboxInput
          class="w-full border-none py-2 pl-3 pr-10 text-sm leading-5 text-gray-900 focus:outline-hidden disabled:opacity-50 disabled:cursor-not-allowed"
          :display-value="displayValue as (option: unknown) => string"
          :placeholder="placeholder"
          :disabled="disabled"
          @change="query = $event.target.value"
        />
        <ComboboxButton class="absolute inset-y-0 right-0 flex items-center pr-2">
          <svg
            class="h-5 w-5 text-gray-400"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fill-rule="evenodd"
              d="M10 3a.75.75 0 01.55.24l3.25 3.5a.75.75 0 11-1.1 1.02L10 4.852 7.3 7.76a.75.75 0 01-1.1-1.02l3.25-3.5A.75.75 0 0110 3zm-3.76 9.2a.75.75 0 011.06.04l2.7 2.908 2.7-2.908a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0l-3.25-3.5a.75.75 0 01.04-1.06z"
              clip-rule="evenodd"
            />
          </svg>
        </ComboboxButton>
      </div>

      <transition
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
        @after-leave="query = ''"
      >
        <ComboboxOptions
          class="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-sm shadow-lg ring-1 ring-black/5 focus:outline-hidden"
        >
          <div
            v-if="filtered.length === 0 && query !== ''"
            class="relative cursor-default select-none py-2 px-4 text-gray-500"
          >
            Nothing found.
          </div>

          <ComboboxOption
            v-for="option in filtered"
            :key="String(option[trackBy])"
            v-slot="{ active, selected }"
            :value="option"
            as="template"
          >
            <li
              class="relative cursor-default select-none py-2 px-4"
              :class="active ? 'bg-indigo-100 text-indigo-900' : 'text-gray-900'"
            >
              <slot
                name="option"
                :option="option"
                :active="active"
                :selected="selected"
              >
                <span
                  class="block truncate"
                  :class="selected ? 'font-semibold' : 'font-normal'"
                >
                  {{ option[labelKey] }}
                </span>
              </slot>
            </li>
          </ComboboxOption>
        </ComboboxOptions>
      </transition>
    </div>
  </Combobox>
</template>
