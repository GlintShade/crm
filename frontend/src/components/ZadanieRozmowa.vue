<!--
  Sekcja "Rozmowa" w oknie zadania (CRM Task, TaskModal.vue): lista datowanych
  wpisów z autorem zamiast ręcznego dopisywania dat w polu Opis. Montowana
  przez TaskModal.vue wyłącznie w trybie edycji (zadanie musi istnieć).

  Wpis rozmowy to zwykły Comment Frappe na CRM Task (crm.api.zadania_rozmowa,
  bez zmiany schematu): lista idzie przez crm.api.zadania_rozmowa.lista (z
  bramką odczytu zadania po stronie serwera), dodawanie przez
  crm.api.zadania_rozmowa.dodaj. Wpisy renderuje istniejący
  Activities/CommentArea.vue (nagłówek "dodał(a) wpis"), dodawanie istniejący
  CommentBox.vue (wzmianki @, załączniki) - jak w Modals/KomentarzeLeadaModal.vue.

  Decyzje właściciela (2026-11-16): autor może EDYTOWAĆ własny wpis (przez
  crm.api.zadania_rozmowa.edytuj, tylko autor; Comment nie ma dla D2D i
  Backend prawa write, więc frappe.client.set_value odmawiałoby), historia zmian
  wpisu jest pod małym przyciskiem przy wpisie, a USUWANIA wpisów nie ma
  (prop bezUsuwania wycina gałąź usuwania z menu wpisu).

  Nazwa zadania idzie do API jako STRING (CRM Task ma nazwy liczbowe, a Frappe
  waliduje typy argumentów metod whitelist w żądaniu HTTP).
-->
<template>
  <div
    class="flex flex-col gap-2 border-t border-outline-gray-2 pt-3 text-sm"
    data-testid="zadanie-rozmowa"
  >
    <div
      class="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-ink-gray-4"
    >
      {{ __('Rozmowa') }}
      <span
        class="rounded-full bg-surface-gray-2 px-1.5 py-0.5 text-[10px] font-semibold normal-case leading-none text-ink-gray-6"
        data-testid="rozmowa-licznik"
      >
        {{ wpisy.length }}
      </span>
    </div>

    <div
      ref="listaRef"
      class="flex max-h-56 flex-col gap-3 overflow-y-auto pr-1"
      data-testid="rozmowa-lista"
    >
      <div v-if="rozmowa.loading && !wpisy.length" class="text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="!wpisy.length" class="text-sm text-ink-gray-5">
        {{ __('Brak wpisów. Dodaj pierwszy poniżej.') }}
      </div>
      <template v-else>
        <div v-for="wpis in wpisy" :key="wpis.name">
          <CommentArea
            :activity="wpis"
            :rzeczownik-wpisu="__('wpis')"
            bez-usuwania
            :zapisz-edycje="zapiszEdycje"
            @reload="przeladuj"
            @historia="otworzHistorie"
          />
        </div>
      </template>
    </div>

    <CommentBox
      v-model="wpisDoc"
      v-model:content="nowaTresc"
      v-model:attachments="noweZalaczniki"
      card
      :editor-class="EDYTOR_KOMPAKTOWY"
      :editable="true"
      doctype="CRM Task"
      :placeholder="__('Dodaj wpis, @ oznacza osobę')"
      :submitLabel="__('Dodaj wpis')"
      :submitButtonProps="{
        variant: 'solid',
        onClick: dodajWpis,
        disabled: trescPusta || zapisuje,
        loading: zapisuje,
      }"
      :discardButtonProps="{
        onClick: wyczyscPole,
      }"
    />

    <Dialog v-model:open="historiaOtwarta" :title="__('Historia zmian wpisu')" size="lg">
      <div class="flex max-h-[60vh] flex-col gap-3 overflow-y-auto" data-testid="historia-wpisu">
        <div v-if="historiaLadowanie" class="text-sm text-ink-gray-5">
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
  </div>
</template>

<script setup>
import CommentArea from '@/components/Activities/CommentArea.vue'
import CommentBox from '@/components/CommentBox.vue'
import { sanitizeHTML } from '@/utils'
import { formatujTermin } from '@/utils/dataPolska'
import { Dialog, call, createResource, toast } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  // Nazwa zadania jako STRING (patrz komentarz w nagłówku pliku).
  zadanie: { type: String, required: true },
})

const listaRef = ref(null)

// Kompaktowe pole nowego wpisu: puste ma ok. 2 linii (3rem), rosnie z tekstem do
// ok. 8rem i dalej przewija sie w srodku (prop `editorClass` w CommentBox.vue;
// inne miejsca zostaja przy domyslnej, wyzszej wersji).
const EDYTOR_KOMPAKTOWY = ['prose-sm max-w-none min-h-[3rem] max-h-32 overflow-y-auto']

// Pole dodawania: CommentBox (doctype 'CRM Task', v-model z { name: zadanie }).
const wpisDoc = ref({ name: props.zadanie })
const nowaTresc = ref('')
const noweZalaczniki = ref([])
const zapisuje = ref(false)

const trescPusta = computed(() => !nowaTresc.value || nowaTresc.value === '<p></p>')

// Najnowszy wpis ma być widoczny po załadowaniu i po dodaniu - lista rośnie
// w dół (najstarsze u góry), więc przewijamy na koniec. Po samej edycji
// wpisu (przeladuj) NIE przewijamy: użytkownik zostaje tam, gdzie był.
async function przewinNaDol() {
  await nextTick()
  const el = listaRef.value
  if (el) el.scrollTop = el.scrollHeight
}

let pierwszeLadowanie = true
const rozmowa = createResource({
  url: 'crm.api.zadania_rozmowa.lista',
  params: { zadanie: props.zadanie },
  auto: true,
  onSuccess: () => {
    if (!pierwszeLadowanie) return
    pierwszeLadowanie = false
    przewinNaDol()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Nie udało się pobrać wpisów.')),
})

// Mapowanie pól jak w Modals/KomentarzeLeadaModal.vue (owner_name z comment_by),
// plus załączniki i liczba zmian treści z API.
const wpisy = computed(() =>
  (rozmowa.data || []).map((c) => ({
    name: c.name,
    owner: c.owner,
    owner_name: c.comment_by || c.owner,
    creation: c.creation,
    content: c.content,
    attachments: c.attachments || [],
    liczba_zmian: c.liczba_zmian || 0,
  })),
)

function przeladuj() {
  return rozmowa.reload()
}

// Edycja własnego wpisu: dedykowany endpoint (tylko autor), bo Comment nie
// ma dla ról D2D i Backend prawa `write`, więc `frappe.client.set_value` z
// CommentArea odmawiałoby autorom. Błąd leci do CommentArea (toast).
function zapiszEdycje(komentarz, tresc) {
  return call('crm.api.zadania_rozmowa.edytuj', { komentarz, tresc })
}

// Okno zadania jest montowane na jedno zadanie, ale prop może się zmienić bez
// remontażu - wtedy lista i pole dodawania zaczynają od nowa.
watch(
  () => props.zadanie,
  (zadanie) => {
    wpisDoc.value = { name: zadanie }
    nowaTresc.value = ''
    noweZalaczniki.value = []
    pierwszeLadowanie = true
    rozmowa.update({ params: { zadanie } })
    rozmowa.reload()
  },
)

// Dodawanie: zapis przez crm.api.zadania_rozmowa.dodaj (zalaczniki = lista
// nazw plików); stan pola (wpisDoc, nowaTresc, noweZalaczniki) jest zadeklarowany
// wyżej, przed watcherem zmiany zadania.
async function dodajWpis() {
  if (trescPusta.value || zapisuje.value) return
  zapisuje.value = true
  try {
    await call('crm.api.zadania_rozmowa.dodaj', {
      zadanie: props.zadanie,
      tresc: nowaTresc.value,
      zalaczniki: noweZalaczniki.value.map((f) => f.name),
    })
    nowaTresc.value = ''
    noweZalaczniki.value = []
    await rozmowa.reload()
    await przewinNaDol()
  } catch (err) {
    toast.error(err?.messages?.[0] || __('Nie udało się dodać wpisu.'))
  } finally {
    zapisuje.value = false
  }
}

function wyczyscPole() {
  nowaTresc.value = ''
  noweZalaczniki.value = []
}

// Historia zmian wpisu: małe okno z wcześniejszymi wersjami treści, od
// najnowszej zmiany. API zwraca zmiany rosnąco po dacie, odwracamy.
const historiaOtwarta = ref(false)
const historiaLadowanie = ref(false)
const historia = ref([])
let numerZapytaniaHistorii = 0

async function otworzHistorie(komentarz) {
  const numer = ++numerZapytaniaHistorii
  historia.value = []
  historiaLadowanie.value = true
  historiaOtwarta.value = true
  try {
    const zmiany = await call('crm.api.zadania_rozmowa.historia', { komentarz })
    if (numer !== numerZapytaniaHistorii) return
    historia.value = [...(zmiany || [])].reverse()
  } catch (err) {
    if (numer !== numerZapytaniaHistorii) return
    historiaOtwarta.value = false
    toast.error(err?.messages?.[0] || __('Nie udało się pobrać historii zmian.'))
  } finally {
    if (numer === numerZapytaniaHistorii) historiaLadowanie.value = false
  }
}
</script>
