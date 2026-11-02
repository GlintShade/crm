<!--
  Siatka tygodnia (kalendarz spotkań, ops#318): kolumny dni, wiersze godzin,
  bloki spotkań z godziną, nazwiskiem i miastem. Dla jednego handlowca.
  Czysta prezentacja, pozycje liczy utils/kalendarz.js.
-->
<template>
  <div
    class="overflow-x-auto rounded-lg border border-outline-gray-2 bg-surface-base"
  >
    <div class="min-w-[640px]">
      <div class="flex border-b border-outline-gray-2 bg-surface-gray-1">
        <div class="w-14 shrink-0"></div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="flex-1 border-l border-outline-gray-1 px-2 py-2 text-center text-sm"
          :class="
            czyDzis(dzien, teraz)
              ? 'bg-surface-blue-1 font-semibold text-ink-blue-8'
              : 'text-ink-gray-7'
          "
        >
          {{ etykietaDniaZMiesiacem(dzien) }}
        </div>
      </div>
      <div class="flex">
        <div
          class="relative w-14 shrink-0"
          :style="{ height: wysokosc + 'px' }"
        >
          <span
            v-for="g in godziny.slice(0, -1)"
            :key="g"
            class="absolute right-2 -translate-y-1/2 text-xs text-ink-gray-5"
            :style="{ top: (g - os.od) * PX_NA_GODZINE + 'px' }"
          >
            {{ String(g).padStart(2, '0') }}:00
          </span>
        </div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="relative flex-1 cursor-pointer border-l border-outline-gray-1"
          :class="[
            czyWeekend(dzien) ? 'bg-surface-gray-1' : '',
            czyDzis(dzien, teraz) ? 'bg-surface-blue-1' : '',
          ]"
          :style="{ height: wysokosc + 'px' }"
          :data-dzien="dzien"
          @click="klikPuste($event, dzien)"
        >
          <span
            v-for="g in godziny"
            :key="g"
            class="pointer-events-none absolute left-0 right-0 border-t border-outline-gray-1"
            :style="{ top: (g - os.od) * PX_NA_GODZINE + 'px' }"
          ></span>
          <button
            v-for="s in poDniach[dzien] || []"
            :key="s.name"
            type="button"
            class="absolute left-1 right-1 overflow-hidden rounded px-1.5 py-1 text-left text-xs leading-tight text-white"
            :class="[
              kolor.pelny,
              czyUmowiony(s.status) ? '' : 'opacity-[0.65]',
            ]"
            :style="stylBloku(s)"
            :title="opisSpotkania(s)"
            :data-lead="s.name"
            @click.stop="$emit('otworz', s.name)"
          >
            <span class="block font-semibold"
              >{{ godzinaTekst(s.termin) }} {{ s.lead_name }}</span
            >
            <span v-if="s.miasto" class="block truncate">{{ s.miasto }}</span>
          </button>
          <span
            v-if="znacznikTeraz(dzien) !== null"
            class="pointer-events-none absolute left-0 right-0 h-px bg-surface-red-4"
            :style="{ top: znacznikTeraz(dzien) + 'px' }"
          ></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  PX_NA_GODZINE,
  czyDzis,
  czyUmowiony,
  czyWeekend,
  etykietaDniaZMiesiacem,
  godzinaTekst,
  godzinaZKliknieciaPion,
  godzinyOsi,
  kolorHandlowca,
  opisSpotkania,
  osGodzin,
  pogrupujPoDniach,
  pozycjaBlokuPion,
  pozycjaTeraz,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  spotkania: { type: Array, default: () => [] },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
})

const emit = defineEmits(['otworz', 'nowe'])

const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const os = computed(() => osGodzin(props.spotkania))
const godziny = computed(() => godzinyOsi(os.value.od, os.value.do))
const wysokosc = computed(() => (os.value.do - os.value.od) * PX_NA_GODZINE)
const poDniach = computed(() => pogrupujPoDniach(props.spotkania))

function stylBloku(s) {
  const p = pozycjaBlokuPion(s.termin, os.value.od)
  return { top: p.topPx + 'px', height: p.heightPx - 2 + 'px' }
}

function znacznikTeraz(dzien) {
  if (!czyDzis(dzien, props.teraz)) return null
  const pct = pozycjaTeraz(props.teraz, os.value.od, os.value.do)
  if (pct === null) return null
  return (pct / 100) * (os.value.do - os.value.od) * PX_NA_GODZINE
}

function klikPuste(event, dzien) {
  const prostokat = event.currentTarget.getBoundingClientRect()
  emit('nowe', {
    data: dzien,
    godzina: godzinaZKliknieciaPion(
      event.clientY - prostokat.top,
      os.value.od,
      os.value.do,
    ),
    handlowiec: props.handlowiec.user,
  })
}
</script>
