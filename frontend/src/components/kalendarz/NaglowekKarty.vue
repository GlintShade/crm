<!--
  Nagłówek karty handlowca (kalendarz, ops#318): awatar z inicjałami w kolorze
  handlowca, nazwisko, zakres dat, chip "N umówionych" i strzałki tygodnia.
  Wspólny dla KartaHandlowca (poziomo) i KalendarzPionowy (kompakt w tablicy).
-->
<template>
  <div
    class="flex items-center gap-3 border-b border-outline-gray-2 px-3 py-2.5"
  >
    <span
      class="flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      :class="[kolor.pelny, duzy ? 'h-10 w-10 text-sm' : 'h-8 w-8 text-xs']"
    >
      {{ inicjaly(handlowiec.full_name) }}
    </span>
    <div class="min-w-0 flex-1">
      <div
        class="truncate font-semibold text-ink-gray-9"
        :class="duzy ? 'text-base' : 'text-sm'"
      >
        {{ handlowiec.full_name }}
      </div>
      <div class="text-xs text-ink-gray-5" :class="duzy ? 'sm:text-sm' : ''">
        {{ etykietaZakresu }}
      </div>
    </div>
    <span
      class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
      :class="[kolor.jasny, kolor.tekst, duzy ? 'sm:text-sm' : '']"
    >
      {{ etykietaUmowionych(umowione) }}
    </span>
    <div class="flex shrink-0 items-center">
      <button
        type="button"
        class="rounded p-1 text-ink-gray-6 hover:bg-surface-gray-2"
        :title="__('Poprzedni')"
        @click="$emit('przesun', -1)"
      >
        <FeatherIcon name="chevron-left" class="h-4 w-4" />
      </button>
      <button
        type="button"
        class="rounded p-1 text-ink-gray-6 hover:bg-surface-gray-2"
        :title="__('Następny')"
        @click="$emit('przesun', 1)"
      >
        <FeatherIcon name="chevron-right" class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui'
import { etykietaUmowionych, inicjaly } from '@/utils/kalendarz'

defineProps({
  handlowiec: { type: Object, required: true },
  kolor: { type: Object, required: true },
  etykietaZakresu: { type: String, default: '' },
  umowione: { type: Number, default: 0 },
  duzy: { type: Boolean, default: false },
})

defineEmits(['przesun'])
</script>
