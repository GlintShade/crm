<!--
  Prosty wielokrotny wybor z checkboxami (ops#283): przycisk z podsumowaniem,
  panel z lista opcji. Opcje: [{ value, label }]. v-model to tablica value.
-->
<template>
  <div ref="korzen" class="relative">
    <label v-if="label" class="mb-1 block text-xs text-ink-gray-5">{{ label }}</label>
    <button
      type="button"
      class="flex h-7 w-full min-w-36 items-center justify-between gap-2 rounded border border-outline-gray-2 bg-surface-base px-2 text-sm text-ink-gray-8 hover:bg-surface-gray-1"
      @click="otwarte = !otwarte"
    >
      <span class="truncate">{{ podsumowanie }}</span>
      <FeatherIcon name="chevron-down" class="h-3.5 w-3.5 shrink-0 text-ink-gray-5" />
    </button>
    <div
      v-if="otwarte"
      class="absolute left-0 top-full z-20 mt-1 min-w-full rounded-lg border border-outline-gray-2 bg-surface-base p-1 shadow-xl"
    >
      <label
        v-for="opcja in options"
        :key="opcja.value"
        class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2"
      >
        <input
          type="checkbox"
          class="rounded border-outline-gray-3"
          :checked="modelValue.includes(opcja.value)"
          @change="przelacz(opcja.value)"
        />
        <span class="whitespace-nowrap">{{ opcja.label }}</span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { FeatherIcon } from 'frappe-ui'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, required: true },
  label: { type: String, default: '' },
  pusty: { type: String, default: 'Wszystkie' },
})
const emit = defineEmits(['update:modelValue'])

const otwarte = ref(false)
const korzen = ref(null)
onClickOutside(korzen, () => (otwarte.value = false))

const podsumowanie = computed(() => {
  const wybrane = props.options.filter((o) => props.modelValue.includes(o.value))
  if (!wybrane.length) return props.pusty
  if (wybrane.length <= 2) return wybrane.map((o) => o.label).join(', ')
  return `${wybrane.length} wybrane`
})

function przelacz(value) {
  const biezace = props.modelValue
  const nowe = biezace.includes(value) ? biezace.filter((v) => v !== value) : [...biezace, value]
  emit('update:modelValue', nowe)
}
</script>
