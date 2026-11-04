<!--
  VOLTEO (ops#328): sekcja "Notatki" w prawym panelu leada (Lead.vue) i w
  "Szybkim podgladzie" na mapie (LeadSzybkiPodglad.vue). Handlowiec i CC
  dodaja notatke i widza ostatnie bez przelaczania na zakladke "Komentarze".

  Notatka to zwykly `Comment` leada, ten sam magazyn co zakladka
  "Komentarze", pseudokolumna na liscie i KomentarzeLeadaModal.vue:
  - odczyt: crm.api.volteo_leady.komentarze (has_permission na leadzie +
    maskowanie tozsamosci CC przed Volteo D2D Sales po stronie serwera),
  - zapis: crm.api.comment.add_comment (ta sama sciezka co zakladka).
  Uprawnienia sa wiec dokladnie te same co przy komentarzach dzis.

  Po dodaniu podbijamy wspolny sygnal (utils/notatkiLeada.js), ktory
  obserwuje ten panel; zakladka "Komentarze" (CommunicationArea.vue) i
  modal podbijaja go tez, wiec obie strony sa zgodne bez odswiezania strony.
  Logika zyje tu, w SidePanelLayout.vue nie ma zadnego wpiecia (rownolegle
  zmiany innych sesji w tym pliku).
-->
<template>
  <div class="shrink-0 px-3 pb-2 pt-1" data-testid="notatki-leada">
    <KartaSekcji
      :label="__('Notatki')"
      nazwa="notatki"
      :summary="podsumowanie"
      :licznik="notatki.length || null"
      licznikMotyw="gray"
      :opened="otwarte"
      @toggle="otwarte = !otwarte"
    >
      <div class="flex flex-col gap-1.5">
        <textarea
          v-model="tekst"
          rows="2"
          class="w-full resize-y rounded border border-outline-gray-2 bg-surface-base px-2 py-1.5 text-[13px] text-ink-gray-8 placeholder:text-ink-gray-4 focus:border-outline-gray-4 focus:outline-none"
          :placeholder="__('Dodaj notatkę…')"
          data-testid="notatki-pole"
          @keydown="onKeydown"
        ></textarea>
        <div class="flex items-center justify-between gap-2">
          <span class="text-[11px] text-ink-gray-4">{{ skrotPodpowiedz }}</span>
          <Button
            variant="solid"
            size="sm"
            :label="__('Dodaj')"
            :disabled="pusta || zapisywanie"
            :loading="zapisywanie"
            data-testid="notatki-dodaj"
            @click="dodaj"
          />
        </div>
      </div>

      <div class="mt-2.5 flex flex-col">
        <div
          v-if="zasob.loading && !zasob.data"
          class="py-1 text-[12.5px] text-ink-gray-5"
        >
          {{ __('Ładowanie…') }}
        </div>
        <div
          v-else-if="!notatki.length"
          class="py-1 text-[12.5px] text-ink-gray-5"
        >
          {{ __('Brak notatek.') }}
        </div>
        <div
          v-else
          :class="[
            'flex flex-col gap-2',
            rozwiniete && 'max-h-64 overflow-y-auto pr-1',
          ]"
        >
          <div
            v-for="n in widoczne"
            :key="n.name"
            class="rounded bg-surface-gray-1 px-2.5 py-1.5"
            data-testid="notatki-wpis"
          >
            <div
              class="flex items-baseline justify-between gap-2 text-[11.5px]"
            >
              <span class="truncate font-medium text-ink-gray-8">{{
                autorNotatki(n)
              }}</span>
              <span class="shrink-0 text-ink-gray-5">{{
                formatDataCzas(n.creation)
              }}</span>
            </div>
            <!-- eslint-disable vue/no-v-html -->
            <div
              class="prose-f mt-0.5 break-words text-[12.5px] leading-5 text-ink-gray-8"
              :class="!rozwiniete && 'line-clamp-4'"
              v-html="sanitizeHTML(n.content)"
            />
            <!-- eslint-enable vue/no-v-html -->
          </div>
        </div>
        <button
          v-if="notatki.length > LIMIT_ZWINIETYCH"
          type="button"
          class="mt-1.5 flex w-full items-center gap-1 border-t border-dashed border-outline-gray-2 pt-1.5 text-left text-[12px] text-ink-gray-5 hover:text-ink-gray-8"
          data-testid="notatki-rozwin"
          @click="rozwiniete = !rozwiniete"
        >
          <span
            :class="[
              rozwiniete ? 'lucide-chevron-up' : 'lucide-chevron-down',
              'size-3.5 shrink-0',
            ]"
            aria-hidden="true"
          />
          {{
            rozwiniete
              ? __('Pokaż mniej')
              : __('Pokaż wszystkie ({0})', [notatki.length])
          }}
        </button>
      </div>
    </KartaSekcji>
  </div>
</template>

<script setup>
import KartaSekcji from '@/components/KartaSekcji.vue'
import { sanitizeHTML } from '@/utils'
import { formatDataCzas } from '@/utils/panelBoczny'
import {
  LIMIT_ZWINIETYCH,
  autorNotatki,
  czyPustaNotatka,
  czySkrotZapisu,
  posortujNotatki,
  tekstNaHtml,
  wersjaKomentarzy,
  widoczneNotatki,
  zglosZmianeKomentarzy,
} from '@/utils/notatkiLeada'
import { Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  docname: { type: String, required: true },
  doctype: { type: String, default: 'CRM Lead' },
})

// `liczba`: aktualna liczba notatek po kazdym wczytaniu (np. etykieta
// przycisku "Komentarze (N)" w LeadSzybkiPodglad.vue). `dodano`: po zapisie
// notatki (Lead.vue przeladowuje wtedy zakladke Aktywnosci/Komentarze).
const emit = defineEmits(['liczba', 'dodano'])

const otwarte = ref(true)
const rozwiniete = ref(false)
const tekst = ref('')
const zapisywanie = ref(false)

const pusta = computed(() => czyPustaNotatka(tekst.value))

const czyMac =
  typeof navigator !== 'undefined' &&
  /Mac|iPhone|iPad/.test(navigator.platform || '')
const skrotPodpowiedz = czyMac
  ? __('Cmd+Enter zapisuje')
  : __('Ctrl+Enter zapisuje')

const zasob = createResource({
  url: 'crm.api.volteo_leady.komentarze',
  makeParams: () => ({ doctype: props.doctype, name: props.docname }),
  auto: true,
  onSuccess: (data) => emit('liczba', (data || []).length),
})

const notatki = computed(() => posortujNotatki(zasob.data))
const widoczne = computed(() =>
  widoczneNotatki(notatki.value, rozwiniete.value),
)

const podsumowanie = computed(() => {
  const ostatnia = notatki.value[0]
  if (!ostatnia) return __('Brak notatek')
  return __('Ostatnia: {0}', [formatDataCzas(ostatnia.creation)])
})

// Zmiana leada (Lead.vue nie montuje panelu od nowa przy przejsciu na inny
// lead) i zmiany z innych miejsc (zakladka, modal) przeladowuja liste.
watch(
  () => props.docname,
  () => {
    rozwiniete.value = false
    tekst.value = ''
    zasob.reload()
  },
)
watch(
  () => wersjaKomentarzy(props.doctype, props.docname),
  () => zasob.reload(),
)

function onKeydown(e) {
  if (!czySkrotZapisu(e)) return
  e.preventDefault()
  dodaj()
}

async function dodaj() {
  if (pusta.value || zapisywanie.value) return
  zapisywanie.value = true
  try {
    await call('crm.api.comment.add_comment', {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      content: tekstNaHtml(tekst.value),
    })
    tekst.value = ''
    zglosZmianeKomentarzy(props.doctype, props.docname)
    emit('dodano')
  } catch (err) {
    toast.error(err?.messages?.[0] || __('Nie udało się dodać notatki'))
  } finally {
    zapisywanie.value = false
  }
}
</script>
