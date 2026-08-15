<!--
  Pasek etapów pipeline'u (Szansa) — pełnoszerokościowy, TYLKO DO ODCZYTU pasek
  między nagłówkiem strony a wierszem zakładek. Klikanie węzłów nic nie robi —
  jedynym ręcznym sterowaniem statusem pozostaje dropdown w nagłówku strony
  (Deal.vue / MobileDeal.vue, triggerStatusChange).

  Cała logika stanu (tryb paska, stan węzła, numer węzła, notatka "następny
  krok", odznaka poza pipeline'em) żyje w `utils/dealPipeline.js` — ten
  komponent tylko renderuje payload zwrócony przez backend
  (`crm.api.pipeline.volteo_pipeline_get`, WOŁANY PO PEŁNEJ KROPKOWANEJ
  ŚCIEŻCE — gołe nazwy dają HTTP 417 w runtime dla API forka).
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
                v-if="nodeStateForMode(mode, i, payload.current_index) === 'done'"
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

      <!-- Notatka o następnym kroku, tylko w trybie 'progress' -->
      <div
        v-if="note"
        class="max-w-xs shrink-0 truncate text-sm text-ink-gray-5"
        :title="note"
      >
        {{ __('Następny krok: {0}', [note]) }}
      </div>
    </div>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui'
import { computed, watch } from 'vue'
import {
  bandMode,
  nodeStateForMode,
  stepNumber,
  nextStepNote,
  offPipelineBadge,
} from '@/utils/dealPipeline'

const props = defineProps({
  dealId: { type: String, required: true },
  status: { type: String, default: '' },
  rodzaj: { type: String, default: '' },
})

const resource = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_get',
  params: { deal: props.dealId },
  auto: true,
})

// Zmiana statusu z dropdownu w nagłówku ORAZ automatyka po stronie serwera
// (doc `status` jest realtime) — obie ścieżki muszą odświeżyć pasek.
watch(() => props.status, () => resource.reload())
watch(() => props.rodzaj, () => resource.reload())

const payload = computed(() => resource.data || null)
const mode = computed(() => bandMode(payload.value))
const note = computed(() => nextStepNote(payload.value))
const badgeLabel = computed(() => offPipelineBadge(payload.value))

const badgeTheme = computed(() => {
  if (mode.value === 'lost') return 'red'
  if (mode.value === 'won') return 'green'
  return 'gray'
})

function connectorClass(index) {
  // Segment "ukończony" (zielony), jeśli węzeł PRZED nim jest już done.
  const prevState = nodeStateForMode(mode.value, index - 1, payload.value?.current_index)
  return prevState === 'done' || mode.value === 'won'
    ? 'bg-green-500'
    : 'bg-surface-gray-3'
}

function nodeCircleClass(index) {
  const state = nodeStateForMode(mode.value, index, payload.value?.current_index)
  if (state === 'done') return 'bg-green-500 text-white'
  if (state === 'current') return 'bg-blue-500 text-white'
  if (state === 'future') return 'bg-surface-gray-3 text-ink-gray-6'
  // 'muted' (lost / unknown)
  return 'bg-surface-gray-2 text-ink-gray-4'
}

function nodeLabelClass(index) {
  const state = nodeStateForMode(mode.value, index, payload.value?.current_index)
  if (state === 'current') return 'font-medium text-blue-600'
  if (state === 'done') return 'text-ink-gray-7'
  if (state === 'muted') return 'text-ink-gray-3'
  return 'text-ink-gray-5'
}
</script>
