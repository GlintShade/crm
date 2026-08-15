<!--
  Pasek etapów pipeline'u (Szansa) — pełnoszerokościowy, TYLKO DO ODCZYTU pasek
  między nagłówkiem strony a wierszem zakładek. Klikanie węzłów nic nie robi —
  jedynym ręcznym sterowaniem statusem pozostaje dropdown w nagłówku strony
  (Deal.vue / MobileDeal.vue, triggerStatusChange).

  Cała logika stanu (tryb paska, stan węzła, numer węzła, odznaka poza
  pipeline'em) żyje w `utils/dealPipeline.js` — ten komponent tylko renderuje
  wynik na podstawie payloadu SERWERA (KSZTAŁT rurociągu: `steps`/`notes`, z
  `crm.api.pipeline.volteo_pipeline_get`, WOŁANY PO PEŁNEJ KROPKOWANEJ
  ŚCIEŻCE — gołe nazwy dają HTTP 417 w runtime dla API forka) i `props.status`
  (prawda kliencka — patrz komentarz w <script>). Notatka "następny krok" NIE
  renderuje się tu — korzysta z tego samego payloadu i tej samej pochodnej
  logiki co reszta tego pliku, ale mieszka w panelu bocznym, patrz
  `DealNextStepNote.vue`.
-->
<template>
  <div
    v-if="!resource.loading && mode !== 'hidden'"
    class="w-full border-b px-5 py-3"
    :class="mode === 'lost' ? 'bg-red-50' : 'bg-surface-white'"
  >
    <!-- Zawartość ograniczona do ~80% szerokości kontenera i wyśrodkowana;
         na wąskich ekranach (mobile/wąskie okno) pełna szerokość, bo przy
         6 węzłach CP ograniczenie do 80% zostawiłoby za mało miejsca. -->
    <div class="mx-auto flex w-full max-w-full flex-wrap items-center gap-4 sm:max-w-[80%]">
      <!-- Stepper: węzły równo rozłożone na pełną szerokość, połączone linią -->
      <div class="flex flex-1 items-start overflow-x-auto">
        <template v-for="(step, i) in payload.steps" :key="i">
          <!-- Segment łącznika PRZED węzłem (pomijamy dla pierwszego węzła) -->
          <div
            v-if="i > 0"
            class="mt-3.5 h-0.5 flex-1 shrink-0"
            :class="connectorClass(i)"
          />
          <div class="flex shrink-0 flex-col items-center gap-1.5 px-1">
            <div
              class="flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium"
              :class="nodeCircleClass(i)"
            >
              <span
                v-if="nodeStateForMode(mode, i, currentIndex) === 'done'"
                class="lucide-check size-3.5"
                aria-hidden="true"
              />
              <span v-else>{{ stepNumber(i) }}</span>
            </div>
            <div
              class="w-24 whitespace-normal break-words text-center text-xs leading-tight"
              :class="nodeLabelClass(i)"
            >
              {{ __(step.status) }}
            </div>
          </div>
        </template>
      </div>

      <!-- Odznaka poza pipeline'em (Przegrana / Wygrana / inny status) -->
      <Badge
        v-if="badgeLabel"
        :label="__(badgeLabel)"
        :theme="badgeTheme"
        variant="subtle"
        class="shrink-0"
      />
    </div>
  </div>
</template>
<script setup>
// Dlaczego pasek NIGDY nie odświeża payloadu po zmianie `props.status`:
// wcześniejsza wersja miała `watch(() => props.status, () => resource.reload())`
// i to właśnie ono powodowało błąd „pasek o jeden krok za późno” — reload
// odpytuje serwer, ale zapis TEJ SAMEJ zmiany statusu (SAVE wywołany z
// dropdownu w nagłówku) jest wtedy jeszcze w locie; serwer potrafił oddać
// STARY status i pasek renderował poprzedni krok aż do kolejnej zmiany.
// Rozwiązanie: serwer (`volteo_pipeline_get`) dostarcza tylko KSZTAŁT
// rurociągu (`steps`, `notes`) dla `rodzaj` — payload odświeżamy WYŁĄCZNIE,
// gdy `rodzaj` się zmienia. Bieżący krok/tryb/notatkę/odznakę liczymy tu, w
// komponencie, synchronicznie z `props.status` (jedyna prawda kliencka —
// ustawiana przez dropdown natychmiast, bez czekania na round-trip) i z
// `statusType` ze store'u statusów (już załadowanego przez inny widok tej
// strony). Migawkowe pola payloadu (`current_index`, `off_pipeline*`, `note`,
// `status`) zostają w odpowiedzi API dla sond, ale ten komponent ich nie czyta.
import { Badge, createResource } from 'frappe-ui'
import { computed, watch } from 'vue'
import { statusesStore } from '@/stores/statuses'
import {
  bandMode,
  currentIndexFor,
  nodeStateForMode,
  stepNumber,
  offPipelineBadge,
} from '@/utils/dealPipeline'

const props = defineProps({
  dealId: { type: String, required: true },
  status: { type: String, default: '' },
  rodzaj: { type: String, default: '' },
})

const { getDealStatus } = statusesStore()

const resource = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_get',
  params: { deal: props.dealId },
  auto: true,
  cache: ['volteo-pipeline', props.dealId],
})

// Kształt rurociągu zależy tylko od `rodzaj` — to jedyna zmiana, po której
// warto odpytać serwer ponownie (np. zmiana linii produktowej na szansie).
watch(() => props.rodzaj, () => resource.reload())

const payload = computed(() => resource.data || null)

// Null-safe na dwa sposoby: nieznany `props.status` (getDealStatus zwraca
// undefined) i store statusów jeszcze niezaładowany (to samo zimne-wejście
// zjawisko, które wywalało render w Deal.vue — patrz commit 46397328;
// tu żaden odczyt nie rzuca, bo `?.type` na undefined daje po prostu undefined,
// a bandMode/offPipelineBadge (i notatka "następny krok" w panelu bocznym,
// zasilana tym samym payloadem) traktują undefined statusType jako 'unknown').
const statusType = computed(() => getDealStatus?.(props.status)?.type)

const currentIndex = computed(() => currentIndexFor(payload.value?.steps, props.status))
const mode = computed(() => bandMode(payload.value, props.status, statusType.value))
const badgeLabel = computed(() => offPipelineBadge(payload.value, props.status, statusType.value))

const badgeTheme = computed(() => {
  if (mode.value === 'lost') return 'red'
  if (mode.value === 'won') return 'green'
  return 'gray'
})

function connectorClass(index) {
  // Segment "ukończony" (zielony), jeśli węzeł PRZED nim jest już done.
  const prevState = nodeStateForMode(mode.value, index - 1, currentIndex.value)
  return prevState === 'done' || mode.value === 'won'
    ? 'bg-green-500'
    : 'bg-surface-gray-3'
}

function nodeCircleClass(index) {
  const state = nodeStateForMode(mode.value, index, currentIndex.value)
  if (state === 'done') return 'bg-green-500 text-white'
  if (state === 'current') return 'bg-blue-500 text-white'
  if (state === 'future') return 'bg-surface-gray-3 text-ink-gray-6'
  // 'muted' (lost / unknown)
  return 'bg-surface-gray-2 text-ink-gray-4'
}

function nodeLabelClass(index) {
  const state = nodeStateForMode(mode.value, index, currentIndex.value)
  if (state === 'current') return 'font-medium text-blue-600'
  if (state === 'done') return 'text-ink-gray-7'
  if (state === 'muted') return 'text-ink-gray-3'
  return 'text-ink-gray-5'
}
</script>
