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

  Lista wpisów siedzi w ramce jak pole Opis w oknie zadania (ta sama ramka
  rounded-lg i outline-gray-2) i ma pasek przewijania ZAWSZE widoczny, gdy
  wpisy się nie mieszczą (uwaga właściciela 2026-11-16: ma być widać, że jest
  więcej wiadomości; macOS chowa paski systemowe, patrz blok style na końcu pliku).
  Na desktopie (od sm) lista nie ma górnego limitu wysokości: bierze całe
  wolne miejsce w oknie zadania, a gdy go brakuje, kurczy się (min. 7rem) i
  przewija w swojej ramce, dzięki czemu samo okno się nie przewija (min-h-0 w
  całym łańcuchu kolumn, etykieta i pole nowego wpisu mają shrink-0). Na
  telefonie zostaje limit 16rem.
-->
<template>
  <div
    class="flex min-h-0 flex-col gap-2 border-t border-outline-gray-2 pt-3 text-sm"
    data-testid="zadanie-rozmowa"
  >
    <div
      class="flex shrink-0 items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-ink-gray-4"
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
      class="rozmowa-lista flex max-h-64 min-h-[7rem] flex-col gap-3 overflow-y-auto rounded-lg border border-outline-gray-2 py-3 pl-3 pr-2 sm:max-h-none"
      data-testid="rozmowa-lista"
      @scroll.passive="naPrzewiniecie"
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
            historia-zewnetrzna
            :zapisz-edycje="zapiszEdycje"
            @reload="przeladuj"
            @historia="otworzHistorie"
          />
        </div>
      </template>
    </div>

    <div class="shrink-0">
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
    </div>

    <HistoriaWpisuDialog
      v-model:open="historiaOtwarta"
      :komentarz="historiaKomentarz"
      endpoint="crm.api.zadania_rozmowa.historia"
    />
  </div>
</template>

<script setup>
import CommentArea from '@/components/Activities/CommentArea.vue'
import CommentBox from '@/components/CommentBox.vue'
import HistoriaWpisuDialog from '@/components/HistoriaWpisuDialog.vue'
import { call, createResource, toast } from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

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

// Przypięcie listy do końca (patrz komentarz przy naPrzewiniecie niżej).
let przypietaDoDolu = false
let obserwatorListy = null

// Najnowszy wpis ma być widoczny po załadowaniu i po dodaniu - lista rośnie
// w dół (najstarsze u góry), więc przewijamy na koniec. Po samej edycji
// wpisu (przeladuj) NIE przewijamy: użytkownik zostaje tam, gdzie był.
async function przewinNaDol() {
  przypietaDoDolu = true
  await nextTick()
  const el = listaRef.value
  if (el) el.scrollTop = el.scrollHeight
}

// Od sm wysokość listy jest elastyczna (kurczy się do wolnego miejsca w oknie
// zadania), a okno dociąga rozmiary już po pierwszym przewinięciu (edytor
// Opisu z treścią, historia, przycisk klienta). Mniejsza lista zostawiłaby
// najnowszy wpis częściowo pod dolną krawędzią, bo przeglądarka nie zmienia
// scrollTop przy kurczeniu: dopóki użytkownik sam nie przewinie w górę, każda
// zmiana wysokości listy przypina ją z powrotem do końca.
function naPrzewiniecie() {
  const el = listaRef.value
  if (!el) return
  przypietaDoDolu = el.scrollHeight - el.scrollTop - el.clientHeight < 8
}

onMounted(() => {
  const el = listaRef.value
  if (!el || typeof ResizeObserver === 'undefined') return
  obserwatorListy = new ResizeObserver(() => {
    if (przypietaDoDolu) el.scrollTop = el.scrollHeight
  })
  obserwatorListy.observe(el)
})

onBeforeUnmount(() => obserwatorListy?.disconnect())

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

// Historia zmian wpisu: wspolne okno HistoriaWpisuDialog (ladowanie i render).
const historiaOtwarta = ref(false)
const historiaKomentarz = ref('')

function otworzHistorie(komentarz) {
  historiaKomentarz.value = komentarz
  historiaOtwarta.value = true
}
</script>

<style scoped>
/*
  Pasek przewijania listy wpisow ZAWSZE widoczny, gdy wpisy sie nie mieszcza
  (uwaga wlasciciela 2026-11-16: ma byc widac, ze jest wiecej wiadomosci).
  Reguly ::-webkit-scrollbar wymuszaja klasyczny, staly pasek w Safari i
  Chrome takze przy systemowym ustawieniu "pokazuj paski przy przewijaniu".
  Wlasciwosci standardowe (scrollbar-width, scrollbar-color) tylko dla
  przegladarek bez ::-webkit-scrollbar (Firefox): w Chrome wylaczylyby reguly
  webkit i pasek znow by sie chowal. Kolory z tokenow (pelne wartosci oklch,
  wiec var() bez rgb()), dzialaja w jasnym i ciemnym motywie.
*/
.rozmowa-lista::-webkit-scrollbar {
  width: 10px;
}
.rozmowa-lista::-webkit-scrollbar-track {
  background: transparent;
}
.rozmowa-lista::-webkit-scrollbar-thumb {
  background-color: var(--outline-gray-4);
  border: 2px solid transparent;
  border-radius: 9999px;
  background-clip: content-box;
}
.rozmowa-lista::-webkit-scrollbar-thumb:hover {
  background-color: var(--ink-gray-5);
}
@supports not selector(::-webkit-scrollbar) {
  .rozmowa-lista {
    scrollbar-width: thin;
    scrollbar-color: var(--outline-gray-4) transparent;
  }
}
</style>
