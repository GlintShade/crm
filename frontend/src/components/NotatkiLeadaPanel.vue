<!--
  VOLTEO (ops#328): sekcja "Notatki" w prawym panelu leada (Lead.vue) i w
  "Szybkim podgladzie" na mapie (LeadSzybkiPodglad.vue). Handlowiec i CC
  widza ostatnie notatki bez przelaczania na zakladke "Komentarze".
  "Dodaj notatke" otwiera istniejacy popup komentarzy (KomentarzeLeadaModal,
  ten sam co przycisk "Komentarze": edytor, @wzmianki, zalaczniki), decyzja
  Jana zamiast osobnego pola tekstowego w karcie.

  Notatka to zwykly `Comment` leada, ten sam magazyn co zakladka
  "Komentarze", pseudokolumna na liscie i KomentarzeLeadaModal.vue:
  - odczyt: crm.api.volteo_leady.komentarze (has_permission na leadzie +
    maskowanie tozsamosci CC przed Volteo D2D Sales po stronie serwera),
  - zapis: w popupie, crm.api.comment.add_comment (ta sama sciezka co
    zakladka).
  Uprawnienia sa wiec dokladnie te same co przy komentarzach dzis.

  Po zamknieciu popupu lista sie przeladowuje (lapie tez edycje i usuniecia
  zrobione w popupie). Dodanie komentarza w zakladce "Komentarze"
  (CommunicationArea.vue) podbija wspolny sygnal (utils/notatkiLeada.js),
  ktory ten panel obserwuje, wiec obie strony sa zgodne bez odswiezania.
  Logika zyje tu, w SidePanelLayout.vue nie ma zadnego wpiecia (rownolegle
  zmiany innych sesji w tym pliku).

  Stan otwarcia (SEKCJA_NOTATKI) zyje bez zakresu widoku -- przelacznik
  "Synchronizuj sekcje" (b84, zadanie F) nigdy go nie przenosi: ta karta
  prawego panelu zawsze zostaje na dotychczasowym kluczu, zeby nic nie
  stracic. Odpowiednik w zakladce "Szczegoly" (KomentarzeLeadaSekcja.vue)
  bierze zakres WIDOK_SZCZEGOLY i przy wylaczonej synchronizacji ma wlasny,
  niezalezny zapis.
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
      @toggle="przelaczOtwarte"
    >
      <Button
        class="w-full"
        :label="__('Dodaj notatkę')"
        icon-left="lucide-message-square-plus"
        data-testid="notatki-dodaj"
        @click="otworzPopup"
      />

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
  <KomentarzeLeadaModal
    v-model="pokazPopup"
    :docname="docname"
    :doctype="doctype"
    @commentAdded="emit('dodano')"
  />
</template>

<script setup>
import KartaSekcji from '@/components/KartaSekcji.vue'
import KomentarzeLeadaModal from '@/components/Modals/KomentarzeLeadaModal.vue'
import { sanitizeHTML } from '@/utils'
import { formatDataCzas } from '@/utils/panelBoczny'
import { useStanSekcjiPanelu } from '@/composables/useStanSekcjiPanelu'
import { SEKCJA_NOTATKI } from '@/utils/stanSekcjiPanelu'
import {
  LIMIT_ZWINIETYCH,
  autorNotatki,
  posortujNotatki,
  wersjaKomentarzy,
  widoczneNotatki,
} from '@/utils/notatkiLeada'
import { Button, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  docname: { type: String, required: true },
  doctype: { type: String, default: 'CRM Lead' },
})

// `liczba`: aktualna liczba notatek po kazdym wczytaniu (np. etykieta
// przycisku "Komentarze (N)" w LeadSzybkiPodglad.vue). `dodano`: po dodaniu
// komentarza w popupie (Lead.vue przeladowuje wtedy zakladke
// Aktywnosci/Komentarze).
const emit = defineEmits(['liczba', 'dodano'])

// Stan karty w pamieci sekcji panelu (ops#330); bez zapisu domyslnie otwarta.
const stanSekcji = useStanSekcjiPanelu(() => props.doctype)
const otwarte = computed(() => stanSekcji.czyOtwarta(SEKCJA_NOTATKI, true))
function przelaczOtwarte() {
  stanSekcji.ustaw(SEKCJA_NOTATKI, !otwarte.value)
}
const rozwiniete = ref(false)
const pokazPopup = ref(false)

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

function otworzPopup() {
  pokazPopup.value = true
}

// Zmiana leada (Lead.vue nie montuje panelu od nowa przy przejsciu na inny
// lead), zamkniecie popupu (dodanie, edycja, usuniecie) i dodanie w zakladce
// "Komentarze" (sygnal) przeladowuja liste.
watch(
  () => props.docname,
  () => {
    rozwiniete.value = false
    pokazPopup.value = false
    zasob.reload()
  },
)
watch(pokazPopup, (teraz, wczesniej) => {
  if (wczesniej && !teraz) zasob.reload()
})
watch(
  () => wersjaKomentarzy(props.doctype, props.docname),
  () => zasob.reload(),
)
</script>
