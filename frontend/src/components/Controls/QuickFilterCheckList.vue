<template>
  <Popover placement="bottom-start" @close="wyslijTeraz">
    <template #target="{ togglePopover }">
      <button
        type="button"
        class="relative flex h-7 w-full items-center justify-between gap-1 rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1 text-base transition-colors hover:border-outline-elevation-2 hover:bg-surface-gray-3"
        @click="togglePopover()"
      >
        <span
          class="truncate"
          :class="wybrane.length ? 'text-ink-gray-7' : 'text-ink-gray-4'"
        >
          {{ etykieta }}
        </span>
        <span class="flex shrink-0 items-center gap-1">
          <FeatherIcon
            v-if="wybrane.length"
            name="x"
            class="h-3.5 w-3.5 text-ink-gray-5 hover:text-ink-gray-8"
            @click.stop="wyczysc()"
          />
          <FeatherIcon
            name="chevron-down"
            class="h-4 w-4 text-ink-gray-5"
          />
        </span>
      </button>
    </template>
    <template #body="{ close }">
      <div
        class="my-1 w-60 rounded-lg bg-surface-elevation-2 p-1 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        <div v-if="jestLink" class="p-1">
          <FormControl
            type="text"
            :placeholder="__('Search')"
            :modelValue="zapytanie"
            @input="(e) => naZmianeZapytania(e.target.value)"
          />
        </div>
        <div class="max-h-60 overflow-y-auto">
          <div
            v-for="opcja in widoczneOpcje"
            :key="opcja.value"
            class="rounded px-2 py-1 hover:bg-surface-gray-2"
          >
            <Checkbox
              :modelValue="jestZaznaczona(opcja.value)"
              :label="opcja.label"
              @update:modelValue="(zaznaczona) => przelacz(opcja.value, zaznaczona)"
            />
          </div>
          <div
            v-if="jestLink && zasob.loading"
            class="flex justify-center p-2"
          >
            <LoadingIndicator class="h-4 w-4" />
          </div>
          <div
            v-else-if="!widoczneOpcje.length"
            class="px-2 py-1.5 text-sm text-ink-gray-4"
          >
            {{ __('No results') }}
          </div>
        </div>
        <div class="mt-1 border-t pt-1">
          <Button
            variant="ghost"
            class="w-full justify-center"
            :label="__('Clear')"
            @click="wyczyscIZamknij(close)"
          />
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
// Chip szybkiego filtra dla pól Select i Link (poza User i datami, patrz
// czyWielokrotnyWybor w filtrWielokrotny.js) z wielokrotnym wyborem przez
// checkboxy (issue #127, decyzja właściciela 2026-09-10). Celowo NIE
// frappe-ui MultiSelect: właściciel chciał listę, która zostaje otwarta po
// każdym kliknięciu opcji, z filtrem stosowanym natychmiast po każdym
// przełączeniu: to własny, prosty i przewidywalny Popover + lista
// checkboxów zamiast polegania na wewnętrznej logice zamykania comboboksa
// wielokrotnego wyboru w frappe-ui (patrz JSDoc w LinkMultiSelect.vue: ten
// komponent to jego odpowiednik dla rozwijanego Filter.vue, tam zamykanie
// po wyborze nie przeszkadza, bo to inny wzorzec UI: pole z "chipami"
// wartości w środku, nie zwarty przycisk na pasku szybkich filtrów).
//
// Dwa tryby, zależnie od fieldtype:
//   Select: opcje statyczne z `options` (kształt {label, value}, tak jak
//            zwraca crm.api.doc.get_quick_filters; placeholder pustej
//            wartości '' pomijany, bo w liście checkboxów jest bez sensu,
//            czyszczenie idzie przez "x" na chipie albo "Wyczyść" na dole).
//   Link: opcje z frappe.desk.search.search_link (ten sam wzorzec co
//            LinkMultiSelect.vue: debounce zapytania, scalanie wyników z
//            aktualnie zaznaczonymi wartościami przez scalOpcjeZZaznaczonymi,
//            żeby zaznaczenie zostało widoczne nawet gdy kolejne zapytanie
//            zawęzi wyniki i akurat pominie już wybraną wartość). Ten
//            komponent nigdy nie dostaje doctype='User', patrz wyłączenie
//            w czyWielokrotnyWybor i jego JSDoc.
import {
  Button,
  Checkbox,
  FeatherIcon,
  FormControl,
  LoadingIndicator,
  Popover,
  createResource,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { scalOpcjeZZaznaczonymi } from '@/utils/filtrWielokrotny'
import {
  etykietaChipaFiltraSzybkiego,
  ustawWartoscWielokrotna,
} from '@/utils/filtrSzybki'

const props = defineProps({
  label: { type: String, required: true },
  fieldtype: { type: String, required: true },
  // Select: tablica {label, value}. Link: nazwa doctype'u do przeszukania.
  options: { type: [Array, String], default: () => [] },
})

const model = defineModel({ type: Array, default: () => [] })

// Issue #127 follow-up (smoke, 2026-09-10): klikanie kilku checkboxow pod
// rzad wywolywalo za kazdym razem create_or_update_standard_view +
// przeladowanie listy, wiec rownolegle zapisy blokowaly sie nawzajem
// (QueryDeadlockError). `lokalneWybrane` to stan UI, zmieniany NATYCHMIAST
// na kazdy klik (checkboxy odpowiadaja bez opoznienia); `model.value =`
// (czyli emisja `update:modelValue` do rodzica, ktora wyzwala zapis widoku)
// jest debounce'owana -- do rodzica trafia tylko OSTATNIA wartosc po
// CZAS_DEBOUNCE_MS pauzy w klikaniu. "Wyczysc" i zamkniecie popovera (patrz
// `@close="wyslijTeraz"` na <Popover> powyzej -- lapie klikniecie poza
// popover, Escape i wywolanie `close()`, nie tylko przycisk "Wyczysc")
// wysylaja ostatnia wartosc natychmiast, zeby zamkniecie przed uplywem
// debounce'a nie zgubilo wyboru.
const CZAS_DEBOUNCE_MS = 400

const lokalneWybrane = ref(Array.isArray(model.value) ? [...model.value] : [])
let debounceTimerWybor = null

// Zewnetrzna zmiana `model.value` (np. zaladowanie innego zapisanego widoku
// albo "Wyczysc wszystkie filtry" gdzie indziej) -- pomijana, gdy juz
// odpowiada lokalnemu stanowi (w tym echo naszej wlasnej wysylki), zeby nie
// przerywac w toku wpisywania niczym, co sami wlasnie wyslalismy.
watch(
  () => model.value,
  (nowaWartosc) => {
    const tablica = Array.isArray(nowaWartosc) ? nowaWartosc : []
    const bezZmian =
      tablica.length === lokalneWybrane.value.length &&
      tablica.every((v) => lokalneWybrane.value.includes(v))
    if (bezZmian) return
    clearTimeout(debounceTimerWybor)
    debounceTimerWybor = null
    lokalneWybrane.value = [...tablica]
  },
)

const wybrane = computed(() => lokalneWybrane.value)

const jestLink = computed(() => props.fieldtype === 'Link')

function jestZaznaczona(wartosc) {
  return wybrane.value.includes(wartosc)
}

// Bierze zaznaczona wprost ze zdarzenia checkboxa (nie przelacza wzgledem
// wlasnego stanu) -- patrz komentarz przy ustawWartoscWielokrotna w
// utils/filtrSzybki.js: frappe-ui's Checkbox.vue emituje update:modelValue
// DWA RAZY na jedno klikniecie (blad biblioteki, poza zakresem tej
// poprawki), a przelaczanie zamiast ustawiania kasowalo wlasny efekt przy
// drugiej, zbednej emisji tego samego klikniecia -- checkbox wygladal na
// zaznaczony (natywny stan DOM), ale do filtra nic nie trafialo.
function przelacz(wartosc, zaznaczona) {
  lokalneWybrane.value = ustawWartoscWielokrotna(lokalneWybrane.value, wartosc, zaznaczona)
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = setTimeout(wyslijTeraz, CZAS_DEBOUNCE_MS)
}

// Flush natychmiastowy -- no-op, gdy nie ma nic w toku (debounceTimerWybor
// juz wyzerowany), wiec bezpieczny do wywolania z @close nawet gdy popover
// zamyka sie bez zadnej oczekujacej zmiany.
function wyslijTeraz() {
  if (!debounceTimerWybor) return
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = null
  model.value = lokalneWybrane.value
}

function wyczysc() {
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = null
  lokalneWybrane.value = []
  model.value = []
}

function wyczyscIZamknij(close) {
  wyczysc()
  close()
}

onBeforeUnmount(wyslijTeraz)

// --- Select: opcje statyczne ---
const opcjeStatyczne = computed(() =>
  (Array.isArray(props.options) ? props.options : []).filter(
    (o) => o?.value !== '' && o?.value != null,
  ),
)

// --- Link: opcje z search_link ---
const zapytanie = ref('')
const znaneEtykiety = ref(new Map())

const zasob = createResource({
  url: 'frappe.desk.search.search_link',
  method: 'POST',
  params: {
    txt: '',
    doctype: jestLink.value ? props.options : '',
    filters: {},
  },
  transform: (data) => {
    const wynik = (data || []).map((o) => ({
      label: o.label || o.value,
      value: o.value,
    }))
    for (const opcja of wynik) znaneEtykiety.value.set(opcja.value, opcja)
    return wynik
  },
})

let debounceTimer = null
function naZmianeZapytania(txt) {
  zapytanie.value = txt
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    zasob.update({ params: { txt, doctype: props.options, filters: {} } })
    zasob.fetch()
  }, 300)
}

onMounted(() => {
  if (jestLink.value) zasob.fetch()
})

const opcjeLinku = computed(() => {
  const wyniki = zasob.data || []
  const brakujaceZnane = wybrane.value
    .filter((v) => !wyniki.some((o) => o.value === v))
    .map((v) => znaneEtykiety.value.get(v))
    .filter(Boolean)
  return scalOpcjeZZaznaczonymi([...wyniki, ...brakujaceZnane], wybrane.value)
})

const widoczneOpcje = computed(() =>
  jestLink.value ? opcjeLinku.value : opcjeStatyczne.value,
)

// Etykiety zaznaczonych wartości dla chipa, z listy widocznych opcji
// (rozpoznaje prawdziwą etykietę Linka, nie tylko wartość), z fallbackiem
// na samą wartość, gdyby jeszcze nie padło żadne zapytanie w tej sesji
// (np. Link z wczytanego zapisanego widoku).
const etykietyWybranych = computed(() =>
  wybrane.value.map(
    (v) => widoczneOpcje.value.find((o) => o.value === v)?.label ?? v,
  ),
)

const etykieta = computed(() =>
  etykietaChipaFiltraSzybkiego(props.label, etykietyWybranych.value),
)
</script>
