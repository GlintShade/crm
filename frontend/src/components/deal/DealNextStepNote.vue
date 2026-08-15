<!--
  Notatka "Następny krok" — mieszka w panelu bocznym strony szansy, nad
  sekcją Zadania. Wcześniej renderowała się w pasku etapów (DealPipelineBar.vue),
  gdzie ściskała szerokość steppera; przeniesiona tutaj, bo to wskazówka co
  dalej, więc pasuje wprost nad Zadania.

  Własny fetch (ten sam URL/params co DealPipelineBar.vue, ten sam `cache`
  klucz — `createResource` z frappe-ui zwraca WSPÓLNY reaktywny obiekt dla
  drugiej instancji z tym samym kluczem, patrz `resources.js`), żeby ten
  komponent działał niezależnie od tego, czy pasek etapów jest w ogóle
  zamontowany.
-->
<template>
  <div v-if="note" class="border-b p-5">
    <div class="text-xs text-ink-gray-5">{{ __('Następny krok') }}</div>
    <div class="mt-1.5 text-sm text-ink-gray-8">{{ note }}</div>
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui'
import { computed, watch } from 'vue'
import { statusesStore } from '@/stores/statuses'
import { nextStepNote } from '@/utils/dealPipeline'

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

// Ta sama zasada braku odświeżania po zmianie statusu co w DealPipelineBar.vue
// (pełne uzasadnienie tam) — payload to tylko KSZTAŁT rurociągu per `rodzaj`,
// więc odpytujemy serwer ponownie wyłącznie, gdy `rodzaj` się zmienia.
watch(() => props.rodzaj, () => resource.reload())

// Null-safe tak samo jak w DealPipelineBar.vue — patrz komentarz tam.
const statusType = computed(() => getDealStatus?.(props.status)?.type)

const note = computed(() =>
  nextStepNote(resource.data || null, props.status, statusType.value),
)
</script>
