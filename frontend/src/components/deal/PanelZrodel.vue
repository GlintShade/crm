<!--
  Panel źródeł zakładki "Notatki" (issue ops#206, wariant C) - desktop: kolumna
  200 px po lewej stronie listy kart; telefon (< 768 px): poziomo przewijany
  rząd chipów nad listą. Jeden komponent renderuje oba układy przez klasy
  Tailwind `md:` (ten sam wzorzec co `NotatkiTab.vue` samo - CSS decyduje,
  nie JS, bo `NotatkiTab.vue` jest montowany identycznie na desktopowej
  `Deal.vue` i mobilnej `MobileDeal.vue`, patrz komentarz w nagłówku tamtego
  pliku).

  CELOWO NIE jest to `FiltrZrodel.vue` przebudowane w miejscu, mimo że brief
  issue mówi dosłownie "FiltrZrodel.vue staje się panelem": `FiltrZrodel.vue`
  jest już dziś używany przez `PlikiTab.vue` (issue równoległe ops#203, już
  scalone do tego samego `volteo/b64-prep`) z INNYM kontraktem (popover z
  checkboxami + wbudowany dropdown sortu, `kierunek`/`update:kierunek`) -
  podmiana tego komponentu w miejscu złamałaby zakładkę Pliki, zupełnie poza
  zakresem tego issue. Nowy, osobny plik jest bezpieczniejszym wyborem niż
  zgadywanie, czy ktoś inny zdąży zaktualizować `PlikiTab.vue` w tym samym
  oknie scalania - zob. raport agenta, sekcja "odstępstwa od makiety".

  Sort ("Kolejność") NIE żyje tutaj - wyszedł do górnego paska
  (`NotatkiTab.vue`), zgodnie z briefem: ten komponent odpowiada wyłącznie
  za wybór źródeł.

  "Wszystkie {N}" zaznacza WSZYSTKIE klucze z `zrodla` (nie tylko te z
  liczbą > 0) i liczy `N` jako sumę `zrodlo.liczba` po wszystkich źródłach -
  to dokładnie tyle, ile wpisów jest w całym feedzie (każdy wpis ma dokładnie
  jedno źródło), więc nie trzeba osobnego propa z surową listą wpisów.
  Multi-select per źródło działa tak jak dawny popover `FiltrZrodel.vue`:
  klik przełącza pojedynczy klucz, kolejność emitowanej tablicy zawsze
  zgodna z kolejnością `zrodla` (czyli `ZRODLA_FEEDU` z backendu),
  niezależnie od kolejności kliknięć.

  Źródła z licznikiem 0 są wyszarzone (`opacity-60`), ale nadal klikalne -
  brief: "Źródła z liczbą 0 wyszarzone, nadal klikalne".
-->
<template>
  <div>
    <!-- Desktop: pionowy panel, 200 px -->
    <div class="hidden w-[200px] shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-outline-gray-2 p-3 md:flex">
      <div class="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
        {{ __('Źródła') }}
      </div>
      <button
        type="button"
        class="flex items-center gap-2 rounded px-2 py-1.5 text-left text-sm"
        :class="wszystkoZaznaczone ? 'bg-surface-gray-2 font-semibold text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-1'"
        @click="zaznaczWszystkie"
      >
        <span class="h-2.5 w-2.5 shrink-0 rounded-sm bg-ink-gray-9" aria-hidden="true" />
        <span class="flex-1 truncate">{{ __('Wszystkie {0}', [liczbaWszystkich]) }}</span>
      </button>
      <button
        v-for="zrodlo in zrodla"
        :key="zrodlo.klucz"
        type="button"
        class="flex items-center gap-2 rounded px-2 py-1.5 text-left text-sm"
        :class="[
          zaznaczoneSet.has(zrodlo.klucz)
            ? 'bg-surface-gray-2 font-semibold text-ink-gray-9'
            : 'text-ink-gray-7 hover:bg-surface-gray-1',
          zrodlo.liczba === 0 ? 'opacity-60' : '',
        ]"
        @click="przelacz(zrodlo.klucz)"
      >
        <span class="h-2.5 w-2.5 shrink-0 rounded-sm" :class="kolorZrodla(zrodlo.klucz).kwadracik" aria-hidden="true" />
        <span class="min-w-0 flex-1 truncate">{{ zrodlo.etykieta }}</span>
        <span class="shrink-0 text-xs text-ink-gray-4">{{ zrodlo.liczba }}</span>
      </button>
    </div>

    <!-- Telefon: poziomo przewijany rząd chipów -->
    <div class="flex gap-2 overflow-x-auto px-4 py-2 md:hidden">
      <button
        type="button"
        class="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs"
        :class="wszystkoZaznaczone ? 'border-outline-gray-4 bg-surface-gray-2 font-semibold text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6'"
        @click="zaznaczWszystkie"
      >
        <span class="h-2 w-2 shrink-0 rounded-sm bg-ink-gray-9" aria-hidden="true" />
        {{ __('Wszystkie {0}', [liczbaWszystkich]) }}
      </button>
      <button
        v-for="zrodlo in zrodla"
        :key="zrodlo.klucz"
        type="button"
        class="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs"
        :class="[
          zaznaczoneSet.has(zrodlo.klucz)
            ? 'border-outline-gray-4 bg-surface-gray-2 font-semibold text-ink-gray-9'
            : 'border-outline-gray-2 text-ink-gray-6',
          zrodlo.liczba === 0 ? 'opacity-60' : '',
        ]"
        @click="przelacz(zrodlo.klucz)"
      >
        <span class="h-2 w-2 shrink-0 rounded-sm" :class="kolorZrodla(zrodlo.klucz).kwadracik" aria-hidden="true" />
        {{ zrodlo.etykieta }} ({{ zrodlo.liczba }})
      </button>
    </div>
  </div>
</template>

<script setup>
import { kolorZrodla } from '@/utils/notatki'
import { computed } from 'vue'

const props = defineProps({
  // [{ klucz, etykieta, liczba }] - kształt `crm.api.notatki.feed().zrodla`.
  zrodla: { type: Array, default: () => [] },
  // Lista zaznaczonych kluczy źródeł (podzbiór `zrodla.map(z => z.klucz)`).
  modelValue: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const zaznaczoneSet = computed(() => new Set(props.modelValue))

const liczbaWszystkich = computed(() =>
  props.zrodla.reduce((suma, zrodlo) => suma + (zrodlo.liczba || 0), 0),
)

const wszystkoZaznaczone = computed(
  () => props.zrodla.length > 0 && props.zrodla.every((zrodlo) => zaznaczoneSet.value.has(zrodlo.klucz)),
)

function przelacz(klucz) {
  const nastepny = new Set(zaznaczoneSet.value)
  if (nastepny.has(klucz)) {
    nastepny.delete(klucz)
  } else {
    nastepny.add(klucz)
  }
  emit(
    'update:modelValue',
    props.zrodla.map((zrodlo) => zrodlo.klucz).filter((klucz) => nastepny.has(klucz)),
  )
}

function zaznaczWszystkie() {
  emit('update:modelValue', props.zrodla.map((zrodlo) => zrodlo.klucz))
}
</script>
