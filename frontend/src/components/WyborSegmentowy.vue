<!--
  Kontrolka segmentowa (radiogroup): jeden pasek z kilkoma przyciskami,
  zaznaczony segment wypełniony. Używana w kalkulatorze OZE zamiast osobnych
  kafelków i natywnych selectów Nie/Tak.
-->
<template>
  <div
    role="radiogroup"
    class="inline-flex max-w-full flex-wrap gap-0.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-0.5"
  >
    <button
      v-for="o in normalized" :key="o.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === o.value"
      :disabled="disabled || o.disabled"
      :title="o.title || undefined"
      :data-testid="testidPrefix ? testidPrefix + o.value : undefined"
      class="rounded-md px-3 py-1 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
      :class="modelValue === o.value
        ? 'bg-surface-gray-10 font-medium text-ink-base'
        : 'text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8'"
      @click="select(o.value)"
    ><span v-if="o.swatch" class="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" :style="o.swatch"></span>{{ o.label }}<span v-if="o.hint" class="ml-1 opacity-70">{{ o.hint }}</span></button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  options: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  testidPrefix: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const normalized = computed(() =>
  props.options.map((o) => (typeof o === 'object' && o !== null ? o : { value: o, label: String(o) })),
)

function select(value) {
  if (props.disabled || value === props.modelValue) return
  emit('update:modelValue', value)
}
</script>
