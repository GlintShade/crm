<!--
  Siatka tygodnia (kalendarz spotkań, ops#318): kolumny dni, wiersze godzin,
  bloki spotkań z godziną i nazwiskiem. Dla jednego handlowca.
  Prop `kompakt` = mniejsza skala godziny i czcionki (karta w tablicy), `naglowek`
  = dokłada nagłówek karty (NaglowekKarty) jak w KartaHandlowca.
  Czysta prezentacja, pozycje liczy utils/kalendarz.js.
-->
<template>
  <div
    class="rounded-lg border border-outline-gray-2 bg-surface-base"
    :class="kompakt ? 'overflow-hidden' : 'overflow-x-auto'"
  >
    <NaglowekKarty
      v-if="naglowek"
      :handlowiec="handlowiec"
      :kolor="kolor"
      :etykieta-zakresu="etykietaZakresu"
      :umowione="umowione"
      @przesun="(k) => $emit('przesun', k)"
    />
    <div :class="kompakt ? '' : 'min-w-[640px]'">
      <div class="flex border-b border-outline-gray-2 bg-surface-gray-1">
        <div class="shrink-0" :class="kompakt ? 'w-9' : 'w-14'"></div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="min-w-0 flex-1 truncate border-l border-outline-gray-1 text-center"
          :class="[
            kompakt ? 'px-0.5 py-1 text-xs' : 'px-2 py-2 text-sm',
            czyDzis(dzien, teraz)
              ? 'bg-surface-blue-1 font-semibold text-ink-blue-8'
              : 'text-ink-gray-7',
          ]"
        >
          {{
            kompakt ? etykietaDniaKrotka(dzien) : etykietaDniaZMiesiacem(dzien)
          }}
        </div>
      </div>
      <div class="flex">
        <div
          class="relative shrink-0"
          :class="kompakt ? 'w-9' : 'w-14'"
          :style="{ height: wysokosc + 'px' }"
        >
          <span
            v-for="g in godziny.slice(0, -1)"
            :key="g"
            class="absolute right-1 -translate-y-1/2 text-xs text-ink-gray-5"
            :style="{ top: (g - os.od) * pxNaH + 'px' }"
          >
            {{ String(g).padStart(2, '0') }}{{ kompakt ? '' : ':00' }}
          </span>
        </div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="relative min-w-0 flex-1 cursor-pointer border-l border-outline-gray-1"
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
            :style="{ top: (g - os.od) * pxNaH + 'px' }"
          ></span>
          <button
            v-for="s in poDniach[dzien] || []"
            :key="s.name"
            type="button"
            class="absolute overflow-hidden rounded text-left text-xs leading-tight text-white"
            :class="[
              kompakt
                ? 'left-0.5 right-0.5 px-1 py-0.5'
                : 'left-1 right-1 px-1.5 py-1',
              kolor.pelny,
              czyUmowiony(s.status) ? '' : 'opacity-[0.65]',
            ]"
            :style="stylBloku(s)"
            :title="opisSpotkania(s)"
            :data-lead="s.name"
            @click.stop="$emit('otworz', s.name)"
          >
            <template v-if="kompakt">
              <span class="block truncate font-semibold">{{
                godzinaTekst(s.termin)
              }}</span>
              <span class="block truncate">{{ s.lead_name }}</span>
            </template>
            <template v-else>
              <span class="block font-semibold"
                >{{ godzinaTekst(s.termin) }} {{ s.lead_name }}</span
              >
              <span v-if="s.miasto" class="block truncate">{{ s.miasto }}</span>
            </template>
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
import NaglowekKarty from '@/components/kalendarz/NaglowekKarty.vue'
import {
  czyDzis,
  czyUmowiony,
  czyWeekend,
  etykietaDniaKrotka,
  etykietaDniaZMiesiacem,
  etykietaZakresu as zbudujEtykieteZakresu,
  godzinaTekst,
  godzinaZKliknieciaPion,
  godzinyOsi,
  kolorHandlowca,
  liczbaUmowionych,
  opisSpotkania,
  osGodzin,
  pogrupujPoDniach,
  pozycjaBlokuPion,
  pozycjaTeraz,
  skalaPionowa,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  spotkania: { type: Array, default: () => [] },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
  kompakt: { type: Boolean, default: false },
  naglowek: { type: Boolean, default: false },
})

const emit = defineEmits(['otworz', 'nowe', 'przesun'])

const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const os = computed(() => osGodzin(props.spotkania))
const godziny = computed(() => godzinyOsi(os.value.od, os.value.do))
const pxNaH = computed(() => skalaPionowa(props.kompakt))
const wysokosc = computed(() => (os.value.do - os.value.od) * pxNaH.value)
const poDniach = computed(() => pogrupujPoDniach(props.spotkania))
const umowione = computed(() => liczbaUmowionych(props.spotkania))
const etykietaZakresu = computed(() =>
  props.dni.length
    ? zbudujEtykieteZakresu(props.dni[0], props.dni[props.dni.length - 1])
    : '',
)

function stylBloku(s) {
  const p = pozycjaBlokuPion(s.termin, os.value.od, pxNaH.value)
  return { top: p.topPx + 'px', height: p.heightPx - 2 + 'px' }
}

function znacznikTeraz(dzien) {
  if (!czyDzis(dzien, props.teraz)) return null
  const pct = pozycjaTeraz(props.teraz, os.value.od, os.value.do)
  if (pct === null) return null
  return (pct / 100) * (os.value.do - os.value.od) * pxNaH.value
}

function klikPuste(event, dzien) {
  const prostokat = event.currentTarget.getBoundingClientRect()
  emit('nowe', {
    data: dzien,
    godzina: godzinaZKliknieciaPion(
      event.clientY - prostokat.top,
      os.value.od,
      os.value.do,
      pxNaH.value,
    ),
    handlowiec: props.handlowiec.user,
  })
}
</script>
