<template>
  <div v-if="widoczne" class="flex items-center gap-2" data-testid="pigulka-kategorii">
    <div class="hidden h-5 w-px shrink-0 bg-outline-gray-2 sm:block" />
    <div class="inline-flex items-center rounded border border-outline-gray-2 overflow-hidden shrink-0">
      <button
        v-for="(k, index) in KATEGORIE"
        :key="k"
        type="button"
        class="flex h-7 items-center gap-1.5 whitespace-nowrap px-1.5 text-base transition-colors sm:px-2"
        :class="[
          aktywna.includes(k)
            ? 'bg-surface-gray-4 text-ink-gray-9'
            : 'text-ink-gray-6 hover:bg-surface-gray-2',
          index > 0 && 'border-l border-outline-gray-2',
        ]"
        :aria-pressed="aktywna.includes(k)"
        :data-testid="`pigulka-${slugKategorii(k)}`"
        @click="aktywna = przelacz(aktywna, k)"
      >
        <span
          class="inline-block h-2.5 w-2.5 shrink-0 rounded-full border"
          :style="{
            backgroundColor: kolorKategorii(k).wypelnienie,
            borderColor: kolorKategorii(k).obwodka,
          }"
        />
        <span>{{ k }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useKategoriaFiltr } from '@/composables/useKategoriaFiltr'
import {
  KATEGORIE,
  kolorKategorii,
  przelacz,
  slugKategorii,
} from '@/utils/kategorieHandlowcow'

const { aktywna, widoczne } = useKategoriaFiltr()
</script>
