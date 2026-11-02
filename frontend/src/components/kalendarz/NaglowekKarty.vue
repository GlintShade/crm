<!--
  Nagłówek karty handlowca (kalendarz, ops#318): awatar 40 px z inicjałami w
  kolorze handlowca, nazwisko, zakres dat, obramowany chip liczby spotkań i
  strzałki tygodnia w jednym pojemniku. Wspólny dla KartaHandlowca (poziomo)
  i KalendarzPionowy (z propem `naglowek`).
-->
<template>
  <div class="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 sm:flex-nowrap">
    <span
      class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
      :class="kolor.pelny"
    >
      {{ inicjaly(handlowiec.full_name) }}
    </span>
    <div class="min-w-0 flex-1">
      <div class="truncate text-sm font-semibold text-ink-gray-9">
        {{ handlowiec.full_name }}
      </div>
      <div class="truncate text-xs text-ink-gray-5">{{ etykietaZakresu }}</div>
    </div>
    <span
      class="order-last shrink-0 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium sm:order-none"
      :class="
        chip.wolny
          ? 'border-outline-gray-2 bg-surface-gray-2 text-ink-gray-6'
          : 'border-outline-green-2 bg-surface-green-1 text-ink-green-8'
      "
      data-testid="kalendarz-chip"
    >
      {{ chip.tekst }}
    </span>
    <div class="flex shrink-0 items-center rounded-lg bg-surface-gray-2 p-0.5">
      <button
        type="button"
        class="rounded-md p-1 text-ink-gray-7 hover:bg-surface-gray-3"
        :title="__('Poprzedni')"
        @click="$emit('przesun', -1)"
      >
        <FeatherIcon name="chevron-left" class="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        class="rounded-md p-1 text-ink-gray-7 hover:bg-surface-gray-3"
        :title="__('Następny')"
        @click="$emit('przesun', 1)"
      >
        <FeatherIcon name="chevron-right" class="h-3.5 w-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui'
import { inicjaly } from '@/utils/kalendarz'

defineProps({
  handlowiec: { type: Object, required: true },
  kolor: { type: Object, required: true },
  etykietaZakresu: { type: String, default: '' },
  chip: { type: Object, required: true },
})

defineEmits(['przesun'])
</script>
