<!-- Mały przełącznik segmentowy (kalendarz, ops#318): opcje [{ value, label }]. -->
<template>
  <div class="flex rounded border border-outline-gray-2 p-0.5 text-sm">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      class="rounded px-3 py-0.5"
      :class="
        modelValue === o.value
          ? 'bg-surface-gray-3 text-ink-gray-9'
          : 'text-ink-gray-6 hover:bg-surface-gray-2'
      "
      :data-wartosc="o.value"
      @click="$emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, required: true },
})
defineEmits(['update:modelValue'])
</script>
