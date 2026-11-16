<!--
  VOLTEO (Discord 91a, ops#364): okno historii zmian wpisu (komentarza), wspolne
  dla rozmowy zadania (ZadanieRozmowa.vue), komentarzy leada i szansy
  (CommentArea.vue). Pokazuje wczesniejsze wersje tresci, od najnowszej zmiany.
  Dane z endpointu `endpoint` (domyslnie `crm.api.komentarze.historia`; zadanie
  przekazuje `crm.api.zadania_rozmowa.historia`), wywolywanego z nazwa wpisu jako
  `komentarz`. Komponent nie importuje niczego, co siega `stores/settings.js`
  (ZadanieRozmowa jest ladowane leniwie, patrz TaskModal.vue).
-->
<template>
  <Dialog v-model:open="otwarte" :title="__('Historia zmian wpisu')" size="lg">
    <div class="flex max-h-[60vh] flex-col gap-3 overflow-y-auto" data-testid="historia-wpisu">
      <div v-if="ladowanie" class="text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="!historia.length" class="text-sm text-ink-gray-5">
        {{ __('Brak wcześniejszych wersji.') }}
      </div>
      <template v-else>
        <div
          v-for="(zmiana, i) in historia"
          :key="i"
          class="flex flex-col gap-1 rounded-lg border border-outline-gray-2 p-3"
        >
          <div class="flex flex-wrap items-center gap-x-1.5 text-sm">
            <span class="font-medium text-ink-gray-8">{{ zmiana.kto_nazwa || zmiana.kto }}</span>
            <span class="text-ink-gray-5">·</span>
            <span class="text-ink-gray-5">{{ formatujTermin(zmiana.kiedy) }}</span>
          </div>
          <div class="text-xs text-ink-gray-5">{{ __('Przed zmianą:') }}</div>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div class="prose-f rounded bg-surface-gray-1 px-3 py-2 text-base" v-html="sanitizeHTML(zmiana.przed)" />
        </div>
      </template>
    </div>
  </Dialog>
</template>

<script setup>
import { sanitizeHTML } from '@/utils'
import { formatujTermin } from '@/utils/dataPolska'
import { Dialog, call, toast } from 'frappe-ui'
import { ref, watch } from 'vue'

const props = defineProps({
  komentarz: { type: String, default: '' },
  endpoint: { type: String, default: 'crm.api.komentarze.historia' },
})

const otwarte = defineModel('open', { type: Boolean, default: false })

const ladowanie = ref(false)
const historia = ref([])
let numerZapytania = 0

// API zwraca zmiany rosnaco po dacie, odwracamy (najnowsza na gorze).
async function wczytaj() {
  const numer = ++numerZapytania
  historia.value = []
  ladowanie.value = true
  try {
    const zmiany = await call(props.endpoint, { komentarz: props.komentarz })
    if (numer !== numerZapytania) return
    historia.value = [...(zmiany || [])].reverse()
  } catch (err) {
    if (numer !== numerZapytania) return
    otwarte.value = false
    toast.error(err?.messages?.[0] || __('Nie udało się pobrać historii zmian.'))
  } finally {
    if (numer === numerZapytania) ladowanie.value = false
  }
}

watch(
  () => [otwarte.value, props.komentarz],
  ([czyOtwarte, komentarz]) => {
    if (czyOtwarte && komentarz) wczytaj()
  },
  { immediate: true },
)
</script>
