<!--
  Karta handlowca (kalendarz spotkań, ops#318, układ E): nagłówek z awatarem,
  wiersze dni z poziomą osią godzin i paskami spotkań. Czysta prezentacja:
  pozycje i daty liczy utils/kalendarz.js, dane i zapis żyją w Kalendarz.vue.
  Prop `duzy` = ta sama karta na całą szerokość, większa czcionka.
-->
<template>
  <div
    class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-base"
    :class="duzy ? 'text-sm' : 'text-xs'"
  >
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
        <div class="text-ink-gray-5">{{ etykietaZakresu }}</div>
      </div>
      <span
        class="shrink-0 rounded-full px-2 py-0.5 font-medium"
        :class="[kolor.jasny, kolor.tekst]"
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

    <div
      class="flex items-stretch border-b border-outline-gray-1 bg-surface-gray-1"
    >
      <div class="shrink-0" :class="duzy ? 'w-24' : 'w-16'"></div>
      <div class="relative h-6 flex-1">
        <span
          v-for="g in godziny.slice(0, -1)"
          :key="g"
          class="absolute top-1 -translate-x-0 pl-1 text-ink-gray-5"
          :style="{ left: pozycjaGodziny(g) }"
        >
          {{ String(g).padStart(2, '0') }}
        </span>
      </div>
    </div>

    <div>
      <div
        v-for="dzien in dni"
        :key="dzien"
        class="flex items-stretch border-b border-outline-gray-1 last:border-b-0"
        :class="[
          czyWeekend(dzien) ? 'bg-surface-gray-1' : '',
          czyDzis(dzien, teraz) ? 'bg-surface-blue-1' : '',
        ]"
      >
        <div
          class="flex shrink-0 items-center px-2"
          :class="[
            duzy ? 'w-24' : 'w-16',
            czyDzis(dzien, teraz)
              ? 'font-semibold text-ink-blue-8'
              : czyWeekend(dzien)
                ? 'text-ink-gray-4'
                : 'text-ink-gray-7',
          ]"
        >
          {{ etykietaDniaKrotka(dzien) }}
        </div>
        <div
          class="relative flex-1 cursor-pointer"
          :class="duzy ? 'h-12' : 'h-9'"
          :data-dzien="dzien"
          @click="klikPuste($event, dzien)"
        >
          <span
            v-for="g in godziny"
            :key="g"
            class="pointer-events-none absolute bottom-0 top-0 border-l border-outline-gray-1"
            :style="{ left: pozycjaGodziny(g) }"
          ></span>
          <button
            v-for="s in poDniach[dzien] || []"
            :key="s.name"
            type="button"
            class="absolute bottom-1 top-1 overflow-hidden rounded px-1.5 text-left font-medium leading-tight text-white"
            :class="[
              kolor.pelny,
              czyUmowiony(s.status) ? '' : 'opacity-[0.65]',
            ]"
            :style="stylPaska(s)"
            :title="opisSpotkania(s)"
            :data-lead="s.name"
            @click.stop="$emit('otworz', s.name)"
          >
            <span class="block truncate">{{ s.lead_name }}</span>
          </button>
          <span
            v-if="znacznikTeraz(dzien) !== null"
            class="pointer-events-none absolute bottom-0 top-0 w-px bg-surface-red-4"
            :style="{ left: znacznikTeraz(dzien) + '%' }"
          ></span>
        </div>
      </div>
    </div>

    <div
      class="flex items-center gap-4 border-t border-outline-gray-2 px-3 py-2 text-ink-gray-5"
    >
      <span class="flex items-center gap-1.5"
        ><span class="h-2.5 w-2.5 rounded-sm" :class="kolor.pelny"></span
        >{{ __('Umówiony') }}</span
      >
      <span class="flex items-center gap-1.5"
        ><span
          class="h-2.5 w-2.5 rounded-sm opacity-[0.65]"
          :class="kolor.pelny"
        ></span
        >{{ __('Do potwierdzenia') }}</span
      >
      <span class="flex items-center gap-1.5"
        ><span class="h-3 w-px bg-surface-red-4"></span>{{ __('Teraz') }}</span
      >
      <span class="ml-auto"
        >{{ String(os.od).padStart(2, '0') }}:00 {{ __('do') }}
        {{ String(os.do).padStart(2, '0') }}:00</span
      >
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import {
  czyDzis,
  czyUmowiony,
  czyWeekend,
  etykietaDniaKrotka,
  etykietaUmowionych,
  etykietaZakresu as zbudujEtykieteZakresu,
  godzinaZKlikniecia,
  godzinyOsi,
  inicjaly,
  kolorHandlowca,
  liczbaUmowionych,
  opisSpotkania,
  osGodzin,
  pogrupujPoDniach,
  pozycjaPaska,
  pozycjaTeraz,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  spotkania: { type: Array, default: () => [] },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
  duzy: { type: Boolean, default: false },
})

const emit = defineEmits(['otworz', 'nowe', 'przesun'])

const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const os = computed(() => osGodzin(props.spotkania))
const godziny = computed(() => godzinyOsi(os.value.od, os.value.do))
const poDniach = computed(() => pogrupujPoDniach(props.spotkania))
const umowione = computed(() => liczbaUmowionych(props.spotkania))
const etykietaZakresu = computed(() =>
  props.dni.length
    ? zbudujEtykieteZakresu(props.dni[0], props.dni[props.dni.length - 1])
    : '',
)

function pozycjaGodziny(g) {
  return ((g - os.value.od) / (os.value.do - os.value.od)) * 100 + '%'
}

function stylPaska(s) {
  const p = pozycjaPaska(s.termin, os.value.od, os.value.do)
  return { left: p.leftPct + '%', width: p.widthPct + '%' }
}

function znacznikTeraz(dzien) {
  if (!czyDzis(dzien, props.teraz)) return null
  return pozycjaTeraz(props.teraz, os.value.od, os.value.do)
}

function klikPuste(event, dzien) {
  const cel = event.currentTarget
  const prostokat = cel.getBoundingClientRect()
  if (!prostokat.width) return
  const xPct = ((event.clientX - prostokat.left) / prostokat.width) * 100
  emit('nowe', {
    data: dzien,
    godzina: godzinaZKlikniecia(xPct, os.value.od, os.value.do),
    handlowiec: props.handlowiec.user,
  })
}
</script>
