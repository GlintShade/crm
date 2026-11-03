<!--
  Edytor grafiku dostępności na karcie handlowca (b82, decyzja 2: malowanie na
  karcie). Kratki pełnych godzin osi (decyzja 8): przeciągnięcie od jasnej
  kratki zaciemnia, od ciemnej rozjaśnia. Szablony dla zaznaczonych dni.
  Zapis jako stały grafik (co tydzień) albo zmiana tylko na ten tydzień
  (decyzja 7) przez crm.api.kalendarz.ustaw_dostepnosc. Godziny poza osią
  (np. 0 do 8 przy "Cały dzień") są zachowane, choć nie widać ich kratek.
-->
<template>
  <div
    class="rounded-xl border-2 border-outline-blue-3 bg-surface-base p-3.5 text-xs"
    data-testid="kalendarz-edycja-grafiku"
  >
    <div class="flex items-center gap-2.5">
      <span
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
        :class="kolor.pelny"
      >
        {{ inicjaly(handlowiec.full_name) }}
      </span>
      <div class="min-w-0 flex-1">
        <div class="truncate text-sm font-semibold text-ink-gray-9">
          {{ handlowiec.full_name }}: {{ __('grafik dostępności') }}
        </div>
        <div class="truncate text-xs text-ink-gray-5">
          {{ etykietaTygodnia }}
        </div>
      </div>
    </div>

    <div
      class="mt-3 flex flex-wrap items-center gap-1.5 rounded-lg bg-surface-gray-2 p-2"
    >
      <span class="mr-1 text-ink-gray-5">{{
        wybrane.size
          ? __('Zaznaczone dni: {0}. Ustaw:', [wybrane.size])
          : __('Zaznacz dni po lewej albo przeciągnij po kratkach.')
      }}</span>
      <Button
        v-for="s in SZABLONY"
        :key="s.klucz"
        size="sm"
        variant="outline"
        :label="s.etykieta"
        :disabled="!wybrane.size"
        @click="ustawSzablon(s.klucz)"
      />
      <span class="flex-1"></span>
      <Button
        size="sm"
        variant="ghost"
        :label="__('Zaznacz pon do pt')"
        @click="wybrane = new Set([0, 1, 2, 3, 4])"
      />
      <Button
        size="sm"
        variant="ghost"
        :label="__('Odznacz')"
        @click="wybrane = new Set()"
      />
    </div>

    <div class="mt-2.5 flex items-end border-b border-outline-gray-2 pb-1.5">
      <div
        class="shrink-0 text-xs uppercase tracking-wide text-ink-gray-5"
        :style="{ width: KOLUMNA_DNI_PX + 'px' }"
      >
        {{ __('Dzień') }}
      </div>
      <div class="relative h-4 flex-1 sm:mr-24">
        <span
          v-for="g in etykietyGodzin"
          :key="g"
          class="absolute top-0 -translate-x-1/2 text-xs tabular-nums text-ink-gray-5"
          :style="{ left: pozycjaGodzinyPct(g, os.od, os.do) + '%' }"
        >
          {{ String(g).padStart(2, '0') }}
        </span>
      </div>
    </div>

    <div class="mt-2 flex select-none flex-col gap-1.5">
      <div
        v-for="(dzien, d) in dni"
        :key="dzien"
        class="flex h-[30px] items-center"
      >
        <div class="shrink-0" :style="{ width: KOLUMNA_DNI_PX + 'px' }">
          <button
            type="button"
            class="flex h-6 items-center gap-1 rounded-md border px-1.5 text-xs font-semibold"
            :class="
              wybrane.has(d)
                ? 'border-transparent bg-surface-gray-7 text-ink-white'
                : 'border-outline-gray-2 bg-surface-base text-ink-gray-8'
            "
            :data-dzien="dzien"
            @click="przelaczDzien(d)"
          >
            {{ skrotDnia(dzien) }}
            <span class="font-normal opacity-75">{{ numerDnia(dzien) }}</span>
          </button>
        </div>
        <div
          class="grid h-full flex-1 cursor-crosshair gap-0.5"
          :style="{
            gridTemplateColumns: `repeat(${os.do - os.od}, minmax(0, 1fr))`,
            touchAction: 'none',
          }"
        >
          <div
            v-for="h in godzinyOsiEdycji"
            :key="h"
            class="rounded"
            :class="
              godziny[d][h]
                ? [kolor.jasny, 'border', kolor.ramka]
                : 'kalendarz-niedostepny'
            "
            :data-d="d"
            :data-h="h"
            @pointerdown.prevent="zacznij($event, d, h)"
          ></div>
        </div>
        <div
          class="hidden w-24 shrink-0 pl-2 text-right tabular-nums text-ink-gray-6 sm:block"
        >
          {{ opisOkien(oknaZGodzin(godziny[d])) }}
          <span
            v-if="zmiany.includes(dzien)"
            class="ml-1 rounded bg-surface-amber-1 px-1 text-ink-amber-8"
            :title="__('W tym dniu obowiązuje zmiana tylko na ten tydzień')"
            >{{ __('zmiana') }}</span
          >
        </div>
      </div>
    </div>

    <div
      class="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-outline-gray-2 pt-2.5 text-ink-gray-6"
    >
      <span class="flex items-center gap-1.5">
        <span
          class="h-2.5 w-4 rounded-sm border"
          :class="[kolor.jasny, kolor.ramka]"
        ></span
        >{{ __('Dostępny') }}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="kalendarz-niedostepny h-2.5 w-4 rounded-sm"></span
        >{{ __('Niedostępny') }}
      </span>
      <span class="text-ink-gray-5">{{
        __(
          'Przeciągnij od jasnej kratki, żeby zaciemnić; od ciemnej, żeby rozjaśnić.',
        )
      }}</span>
    </div>

    <ErrorMessage v-if="blad" :message="blad" class="mt-2" />

    <div
      class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-outline-gray-2 pt-3 text-sm"
    >
      <span class="text-xs text-ink-gray-5">{{ __('Zapisz jako') }}</span>
      <label class="flex cursor-pointer items-center gap-1.5 text-ink-gray-8">
        <input v-model="zakres" type="radio" value="staly" />
        {{ __('stały grafik, co tydzień') }}
      </label>
      <label class="flex cursor-pointer items-center gap-1.5 text-ink-gray-8">
        <input v-model="zakres" type="radio" value="tydzien" />
        {{ __('zmiana tylko na ten tydzień ({0})', [etykietaTygodnia]) }}
      </label>
      <span class="flex-1"></span>
      <Button :label="__('Anuluj')" @click="$emit('anuluj')" />
      <Button
        variant="solid"
        :label="__('Zapisz grafik')"
        :loading="zapisuje"
        data-testid="kalendarz-zapisz-grafik"
        @click="zapisz"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Button, ErrorMessage, call, toast } from 'frappe-ui'
import {
  OS_DO,
  OS_OD,
  SZABLONY_GRAFIKU,
  etykietaZakresu,
  godzinyEtykiet,
  godzinyZOkien,
  inicjaly,
  kolorHandlowca,
  numerDnia,
  oknaDnia,
  oknaZGodzin,
  opisOkien,
  pozycjaGodzinyPct,
  skrotDnia,
} from '@/utils/kalendarz'

const KOLUMNA_DNI_PX = 58
const SZABLONY = [
  { klucz: 'caly', etykieta: __('Cały dzień') },
  { klucz: 'rano', etykieta: __('Rano 8-14') },
  { klucz: 'popoludnie', etykieta: __('Popołudnie 14-22') },
  { klucz: 'wolne', etykieta: __('Wolne') },
]

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  // 7 dat tygodnia (pon..niedz).
  dni: { type: Array, required: true },
  dostepnosc: { type: Object, default: null },
  // Daty tego tygodnia, w których obowiązuje zmiana zamiast stałego grafiku.
  zmiany: { type: Array, default: () => [] },
})

const emit = defineEmits(['anuluj', 'zapisano'])

// Kratki pełnych godzin na domyślnej osi kalendarza (8 do 22).
const os = { od: OS_OD, do: OS_DO }
const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const etykietaTygodnia = computed(() =>
  etykietaZakresu(props.dni[0], props.dni[props.dni.length - 1]),
)
const etykietyGodzin = godzinyEtykiet(os.od, os.do, 1)
const godzinyOsiEdycji = Array.from(
  { length: os.do - os.od },
  (_, i) => os.od + i,
)

const godziny = ref(
  props.dni.map((dzien) => godzinyZOkien(oknaDnia(props.dostepnosc, dzien))),
)
const wybrane = ref(new Set())
const zakres = ref(props.zmiany.length ? 'tydzien' : 'staly')
const zapisuje = ref(false)
const blad = ref('')

function przelaczDzien(d) {
  const nowe = new Set(wybrane.value)
  if (nowe.has(d)) nowe.delete(d)
  else nowe.add(d)
  wybrane.value = nowe
}

function ustawSzablon(klucz) {
  for (const d of wybrane.value)
    godziny.value[d] = godzinyZOkien(SZABLONY_GRAFIKU[klucz])
}

// Malowanie przeciąganiem: wartość ustala pierwsza kratka.
let malowanie = null

function ustaw(d, h) {
  if (godziny.value[d][h] === malowanie) return
  godziny.value[d][h] = malowanie
}

function zacznij(event, d, h) {
  malowanie = !godziny.value[d][h]
  ustaw(d, h)
}

function ruch(event) {
  if (malowanie === null) return
  const el = document.elementFromPoint(event.clientX, event.clientY)
  if (!el || el.dataset?.h === undefined || el.dataset?.d === undefined) return
  ustaw(Number(el.dataset.d), Number(el.dataset.h))
}

function koniec() {
  malowanie = null
}

onMounted(() => {
  window.addEventListener('pointermove', ruch)
  window.addEventListener('pointerup', koniec)
  window.addEventListener('pointercancel', koniec)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', ruch)
  window.removeEventListener('pointerup', koniec)
  window.removeEventListener('pointercancel', koniec)
})

async function zapisz() {
  blad.value = ''
  zapisuje.value = true
  try {
    await call('crm.api.kalendarz.ustaw_dostepnosc', {
      handlowiec: props.handlowiec.user,
      dni: godziny.value.map(oknaZGodzin),
      zakres: zakres.value,
      tydzien_od: props.dni[0],
    })
    toast.success(__('Zapisano grafik: {0}', [props.handlowiec.full_name]))
    emit('zapisano')
  } catch (e) {
    blad.value =
      e?.messages?.[0] || e?.message || __('Nie udało się zapisać grafiku.')
  } finally {
    zapisuje.value = false
  }
}
</script>
