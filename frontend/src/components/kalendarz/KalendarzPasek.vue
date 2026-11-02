<!--
  Pasek nawigacji kalendarza (ops#318): strzałki poprzedni/następny, "Dziś",
  etykieta zakresu, przełącznik Tydzień / Dzień i "Nowe spotkanie". Jeden
  komponent w czterech ułożeniach (prop `czesc`): "lewa" i "prawa" do
  LayoutHeader strony /kalendarz, "calosc" jako własny pasek widoku w Leadach,
  "mobilna" (etykieta i przełącznik widoku) pod nagłówkiem na wąskim ekranie.
  Czysta prezentacja: stan trzyma KalendarzWidok.
-->
<template>
  <div
    v-if="czesc === 'mobilna'"
    class="flex items-center justify-between gap-2"
  >
    <span class="text-sm text-ink-gray-7">{{ etykieta }}</span>
    <PrzelacznikSegmentowy
      :model-value="widok"
      :options="OPCJE_WIDOKU"
      @update:model-value="(v) => $emit('update:widok', v)"
    />
  </div>
  <div
    v-else
    class="flex flex-wrap items-center gap-2"
    :class="czesc === 'calosc' ? 'justify-between' : ''"
  >
    <div v-if="czesc !== 'prawa'" class="flex items-center gap-2">
      <slot name="tytul" />
      <div class="flex items-center">
        <Button
          variant="ghost"
          :tooltip="__('Poprzedni')"
          @click="$emit('przesun', -1)"
        >
          <template #icon
            ><FeatherIcon name="chevron-left" class="h-4 w-4"
          /></template>
        </Button>
        <Button variant="ghost" :label="__('Dziś')" @click="$emit('dzis')" />
        <Button
          variant="ghost"
          :tooltip="__('Następny')"
          @click="$emit('przesun', 1)"
        >
          <template #icon
            ><FeatherIcon name="chevron-right" class="h-4 w-4"
          /></template>
        </Button>
      </div>
      <span
        class="text-sm text-ink-gray-7"
        :class="czesc === 'lewa' ? 'hidden sm:inline' : ''"
        data-testid="kalendarz-etykieta"
        >{{ etykieta }}</span
      >
    </div>
    <div v-if="czesc !== 'lewa'" class="flex items-center gap-2">
      <PrzelacznikSegmentowy
        :model-value="widok"
        :options="OPCJE_WIDOKU"
        :class="czesc === 'prawa' ? 'hidden sm:flex' : ''"
        @update:model-value="(v) => $emit('update:widok', v)"
      />
      <Button
        variant="solid"
        :title="__('Nowe spotkanie')"
        @click="$emit('nowe')"
      >
        <template #prefix><FeatherIcon name="plus" class="h-4 w-4" /></template>
        <span class="hidden sm:inline">{{ __('Nowe spotkanie') }}</span>
      </Button>
    </div>
  </div>
</template>

<script setup>
import { Button, FeatherIcon } from 'frappe-ui'
import PrzelacznikSegmentowy from '@/components/kalendarz/PrzelacznikSegmentowy.vue'

defineProps({
  czesc: {
    type: String,
    default: 'calosc',
    validator: (v) => ['lewa', 'prawa', 'calosc', 'mobilna'].includes(v),
  },
  etykieta: { type: String, default: '' },
  widok: { type: String, default: 'tydzien' },
})

defineEmits(['przesun', 'dzis', 'nowe', 'update:widok'])

const OPCJE_WIDOKU = [
  { value: 'tydzien', label: __('Tydzień') },
  { value: 'dzien', label: __('Dzień') },
]
</script>
