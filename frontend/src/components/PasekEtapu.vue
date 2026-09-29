<!--
  Segmentowy pasek postepu procesu pod odznaka statusu, na liscie szans
  (kolumna "Etap procesu", wariant B listy Umowy, b65). Czysto
  prezentacyjny: nie pobiera niczego sam, dostaje gotowe liczby (etap,
  etapow) i motyw koloru (ten sam Badge theme co odznaka statusu) od
  rodzica (DealsListView.vue), ktory liczy je z crm.api.pipeline.
  volteo_pipeline_grupy i store'u statusow (patrz utils/pasekEtapu.js).

  Bez tekstu "N z M" w tresci - tylko atrybut title (natywny tooltip
  przegladarki po najechaniu, nie tekst renderowany w komorce).

  Klasy koloru musza byc literalnymi stringami (Tailwind JIT nie generuje
  dynamicznych nazw klas ze zmiennej), wiec kolor wypelnionych segmentow
  zyje w mapie MOTYW_KLASY, oparte na tokenach surface-* (nie na surowej
  palecie). Segmenty CP (etapow > 8) sa wezsze, zeby 12 zmiescilo sie w tej
  samej szerokosci kolumny co 5-krokowy proces OZE.
-->
<template>
  <div
    v-if="etapow > 0"
    class="flex items-center gap-0.5"
    :title="`${etapEfektywny} z ${etapow}`"
  >
    <div
      v-for="n in etapow"
      :key="n"
      class="h-1.5 rounded-full"
      :class="[segmentWidthClass, n <= etapEfektywny ? filledClass : 'bg-surface-gray-3']"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  etap: { type: Number, default: 0 },
  etapow: { type: Number, default: 0 },
  theme: { type: String, default: 'gray' },
})

const MOTYW_KLASY = {
  gray: 'bg-surface-gray-6',
  blue: 'bg-surface-blue-6',
  green: 'bg-surface-green-6',
  amber: 'bg-surface-amber-6',
  red: 'bg-surface-red-6',
  violet: 'bg-surface-violet-6',
}

const filledClass = computed(() => MOTYW_KLASY[props.theme] || MOTYW_KLASY.gray)

// Zabezpieczenie przed etap > etapow / etap < 0 (dane z wywolujacego nie sa
// tu osobno walidowane) - pasek nigdy nie ma wiecej wypelnionych segmentow
// niz ich jest, ani ujemnie wypelnionych.
const etapEfektywny = computed(() => Math.min(Math.max(props.etap, 0), props.etapow))

// CP ma 12 krokow - wezsze segmenty, zeby zmiescily sie w tej samej
// szerokosci kolumny co 5-krokowy proces OZE.
const segmentWidthClass = computed(() => (props.etapow > 8 ? 'w-1.5' : 'w-3'))
</script>
