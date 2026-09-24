<!--
  Mapa leadów D2D (b52, ops#26) - piny geokodowanych leadów na Leaflet/OSM.

  Od issue #100 to NIE osobna strona: jedna pozycja menu "Leady" ma
  przełącznik widoku Tabela/Mapa w ViewControls.vue (route.params.viewType
  == 'mapa' na trasie 'Leads'), a ten komponent renderuje się z Leads.vue
  obok LeadsListView/KanbanView, dzieląc LayoutHeader/ViewBreadcrumbs oraz
  filtry/quick filters/zapisane widoki z Tabelą - stąd BRAK tu własnego
  LayoutHeader, ViewBreadcrumbs, usePageMeta i własnych filtrów po stronie
  klienta (dawne pola "Handlowiec"/"Miasto" usunięte, bo dubluje je teraz
  prawdziwy Filter/QuickFilterField w ViewControls). Prop `list` to WPROST
  ten sam zasób `crm.api.doc.get_data`, który napędza Tabelę (przekazywany
  przez Leads.vue jako `:list="leads"`) - ten komponent czyta z niego
  WYŁĄCZNIE `list.params.filters`/`list.params.default_filters` (bieżące
  filtry), nigdy `list.data` (dane Tabeli), i odpytuje `mapa()` osobno z
  tymi samymi filtrami. Watcher na `list.data` (nie na `.params`) czeka, aż
  Tabela SKOŃCZY odświeżanie z nowymi filtrami, zanim mapa() zostanie
  wywołana z tymi parametrami - bez tego mapa ścigałaby się z Tabelą o to,
  które `.params` są aktualne.

  Dane: `crm.api.volteo_leady.mapa(filters, default_filters)` (frappe.get_list,
  więc scoping ról robi serwer przez crm/permissions/org_hierarchy.py: rep
  dostaje tylko swoje leady, admin/backend wszystkie; serwer też odrzuca
  filtrowanie po polu bez uprawnień, np. custom_cc dla Volteo D2D Sales).
  Endpoint zwraca WYŁĄCZNIE leady z ustawionym geokodem (custom_lat != 0).

  Leaflet ładowany leniwie (wzorzec: Controls/GeolocationControl.vue
  L203-272) - tylko warstwa OSM, `preferCanvas: true` bo ~11 tys. pinów.
  Piny to L.circleMarker (wektor na canvasie), więc - inaczej niż w
  GeolocationControl - nie trzeba łatać ikon markerów przez ?url.

  Kolory pinów: hex są w porządku na canvasie Leafleta (to rysowanie na
  mapie, nie UI motywu) - CLAUDE.md pozwala na to wyraźnie. Reszta interfejsu
  wokół mapy (filtry, stopka, spinner) trzyma się wyłącznie tokenów
  ink-*/surface-*/outline-* jak wszędzie indziej.
-->
<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <ErrorMessage class="mx-4 mt-3" :message="blad" />

    <!-- Filtry (wyłącznie chipy widoczności statusów, lokalne dla mapy - patrz
         docstring wyżej dlaczego pola Handlowiec/Miasto zniknęły stąd). -->
    <div
      class="flex flex-wrap items-center gap-3 border-b border-outline-gray-2 px-4 py-3"
    >
      <div class="flex flex-wrap items-center gap-1.5">
        <button
          v-for="s in statusyZListy"
          :key="s.status"
          type="button"
          class="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"
          :class="
            !wylaczoneStatusy.has(s.status)
              ? 'border-outline-gray-3 bg-surface-gray-3 text-ink-gray-8'
              : 'border-outline-gray-2 text-ink-gray-5 hover:bg-surface-gray-1'
          "
          @click="toggleStatus(s.status)"
        >
          <span
            class="h-2 w-2 shrink-0 rounded-full"
            :style="{ backgroundColor: kolorStatusu(s.status) }"
          />
          <span>{{ s.status }}</span>
          <span class="text-ink-gray-4">({{ s.liczba }})</span>
        </button>
      </div>

      <Popover placement="bottom-end">
        <template #target="{ togglePopover }">
          <Button
            icon="settings"
            :label="__('Ustawienia mapy')"
            @click="togglePopover"
          />
        </template>
        <template #body>
          <div
            class="my-2 flex w-72 flex-col gap-4 rounded-lg bg-surface-elevation-2 p-3 text-sm shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
          >
            <div>
              <div class="mb-1.5 font-medium text-ink-gray-8">
                {{ __('Kolor pinezek według') }}
              </div>
              <FormControl
                v-model="trybKolorowania"
                type="select"
                variant="outline"
                class="w-full"
                :options="opcjeKolorowania"
              />
            </div>

            <div>
              <div class="mb-1.5 font-medium text-ink-gray-8">
                {{ __('Wyświetlanie pinezek') }}
              </div>
              <FormControl
                v-model="klastrowanie"
                type="checkbox"
                :label="__('Klastrowanie przy oddaleniu')"
              />
            </div>

            <div>
              <div class="mb-1.5 font-medium text-ink-gray-8">
                {{ __('Pola w dymku pinezki') }}
              </div>
              <div class="flex flex-col gap-1.5">
                <FormControl
                  v-model="ustawieniaDymka.zrodlo"
                  type="checkbox"
                  :label="__('Źródło')"
                />
                <FormControl
                  v-model="ustawieniaDymka.produkty"
                  type="checkbox"
                  :label="__('Obecne produkty')"
                />
                <FormControl
                  v-model="ustawieniaDymka.statusZrodla"
                  type="checkbox"
                  :label="__('Status źródła')"
                />
                <FormControl
                  v-model="ustawieniaDymka.terminSpotkania"
                  type="checkbox"
                  :label="__('Termin spotkania')"
                />
              </div>
            </div>
          </div>
        </template>
      </Popover>

      <div class="ml-auto shrink-0 text-sm text-ink-gray-5">
        {{ __('{0} z {1} leadów z lokalizacją', [leadyPrzefiltrowane.length, stan.leady.length]) }}
      </div>
    </div>

    <!-- Legenda kolorowania wg Handlowca/CC (issue #101). Tryb Status ma już
         swoją legendę w chipach filtrów statusu powyżej, więc tutaj się nie
         powtarza. -->
    <div
      v-if="legendaAktywna.length"
      class="flex flex-wrap items-center gap-3 border-b border-outline-gray-2 px-4 py-2 text-sm"
    >
      <div
        v-for="wpis in legendaAktywna"
        :key="wpis.klucz"
        class="flex items-center gap-1.5"
      >
        <span
          class="h-2 w-2 shrink-0 rounded-full"
          :style="{ backgroundColor: wpis.kolor }"
        />
        <span class="text-ink-gray-7">{{ etykietaLegendy(wpis.klucz) }}</span>
        <span class="text-ink-gray-4">({{ wpis.liczba }})</span>
      </div>
    </div>

    <!-- Mapa -->
    <div class="relative min-h-0 flex-1">
      <div
        v-if="initialLoading"
        class="absolute inset-0 z-[1000] flex items-center justify-center bg-surface-elevation-1/70"
      >
        <LoadingIndicator class="size-8" />
      </div>
      <div :id="mapId" class="h-full w-full" />

      <!-- VOLTEO (issue #97, L08): panel "Szybki podglad" po kliknieciu
           pinezki -- LeadSzybkiPodglad.vue pozycjonuje sie sam (absolute
           inset-y-0 right-0 z-[1000], nad kontrolkami Leafleta), zeby
           otwarcie nie zmienialo pozycji/zoomu mapy (brak invalidateSize,
           mapa nie kurczy sie w flexie). Pozycjonowanie NIE jest przekazane
           przez `class` z tego miejsca, bo komponent ma wiecej niz jeden
           korzen (panel + LostReasonModal + KomentarzeLeadaModal) -- Vue
           cicho gubi attrs przekazane do multi-root komponentu. Klucz
           :key="wybranyLead.name" wymusza pelny remount przy zmianie
           zaznaczonego leada, zeby wewnetrzny useDocument() w panelu
           zaladowal wlasciwy dokument zamiast trzymac poprzedni. -->
      <LeadSzybkiPodglad
        v-if="wybranyLead"
        :key="wybranyLead.name"
        :lead="wybranyLead"
        @zamknij="wybranyLead = null"
        @zaktualizowano="patchujLeada"
      />
    </div>

    <!-- Atrybucje (wymóg licencyjny OSM + GeoNames; geokodowanie GUGiK/Nominatim
         dopisane issue #102 - GUGiK jest usługą państwową bez wymogu atrybucji,
         ale Nominatim (OSM) tego wymaga, więc jeden wspólny wiersz dla obu. -->
    <div
      class="border-t border-outline-gray-2 px-4 py-1.5 text-xs text-ink-gray-4"
    >
      {{ __('© OpenStreetMap contributors') }}
      ·
      {{ __('kody pocztowe: GeoNames, CC-BY 4.0') }}
      ·
      {{ __('geokodowanie: GUGiK (UUG), OpenStreetMap Nominatim') }}
    </div>
  </div>
</template>

<script setup>
import LeadSzybkiPodglad from '@/components/LeadSzybkiPodglad.vue'
import { usersStore } from '@/stores/users'
import { statusesStore } from '@/stores/statuses'
import { colorNameFromParsed } from '@/utils/statusColors'
import { widocznyLead } from '@/utils/mapaFiltry'
import { rozbijTagi } from '@/utils/tagiProduktow'
import { formatDate } from '@/utils'
import {
  KOLOR_BRAK,
  hashString,
  kolorDlaUzytkownika,
  legenda,
  poleObecneWDanych,
  wczytajKlastrowanie,
  wczytajTrybKolorowania,
  wczytajUstawieniaDymka,
  zapiszKlastrowanie,
  zapiszTrybKolorowania,
  zapiszUstawieniaDymka,
} from '@/utils/mapaKolory'
import {
  KOLOR_OBWODKI,
  KOLOR_WYBRANEJ,
  STYL_PINEZKI,
  geometriaPinezki,
  kropkaPinezki,
  sciezkaPinezki,
  stylPinezki,
} from '@/utils/mapaPinezka'
import {
  Button,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  Popover,
  createResource,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  // Zasób ViewControls (crm.api.doc.get_data) - patrz docstring pliku. Ten
  // komponent czyta z niego wyłącznie .params.filters/.params.default_filters.
  list: { type: Object, required: true },
})

// Nie wołany w tej iteracji (chipy statusów to lokalny przełącznik
// widoczności, patrz komentarz przy wylaczoneStatusy niżej) - zdefiniowany,
// żeby nasłuch @ustawFiltr w Leads.vue miał do czego się podpiąć w
// przyszłej iteracji, bez kolejnej zmiany kontraktu tego komponentu.
const emit = defineEmits(['ustawFiltr'])

const mapId = `mapa-leadow-${Math.random().toString(36).slice(2)}`

const { getUser } = usersStore()
const { getLeadStatus } = statusesStore()

// --- Dane z API --------------------------------------------------------------

const stan = reactive({ leady: [] })
const blad = ref('')

// VOLTEO (fix wyscigu, klik-test wlasciciela): createResource() woła RÓWNOCZEŚNIE
// options.onSuccess/onError bazowe ORAZ tempOptions.onSuccess/onError przekazane
// do submit() (frappe-ui resources.js, fetch()) - i robi to w kolejności
// ROZSTRZYGNIĘCIA promise'a, nie wysłania żądania. Gdy przełączenie Lista->Mapa
// z aktywnym filtrem wysyła dwa zbędne zapytania z pustymi filtrami (zanim
// zasób `list` ma jeszcze ustawione `.params`, patrz guard w watchu niżej) i
// dopiero potem trzecie, poprawne, odpowiedzi mogą wrócić w innej kolejności
// niż zapytania poszły - dla dużych zbiorów (np. Administrator, ~10 849 pinów)
// niefiltrowana odpowiedź bywa wolniejsza i nadpisuje `stan.leady` PO tym, jak
// filtrowana już się wyświetliła. Rozwiązanie: każde submit() dostaje własny
// numer w `zadanieSeq`, zamknięty w tempOptions.onSuccess/onError - handler
// stosuje wynik TYLKO gdy jego numer wciąż jest najnowszym wysłanym, więc
// spóźniona odpowiedź starszego zapytania jest po prostu odrzucana. Handlery
// bazowe (options.onSuccess/onError) są celowo puste - cała logika żyje w
// tempOptions per-submit, żeby mieć dostęp do domkniętego numeru sekwencji.
const mapaResource = createResource({
  url: 'crm.api.volteo_leady.mapa',
})

let zadanieSeq = 0

// VOLTEO (issue #100): odpytanie mapy dopiero PO tym, jak Tabela skończy
// własne odświeżenie z nowymi filtrami (.data, nie .params) - patrz
// docstring pliku po pełne wyjaśnienie wyścigu, którego to unika.
// `immediate: true`, żeby pierwsze wejście na widok Mapa (zanim Tabela w
// ogóle zdąży coś załadować) też odpytało od razu, z filtrami, jakie
// ViewControls ustawiło synchronicznie przy tworzeniu zasobu `list`.
watch(
  () => props.list.data,
  () => {
    // VOLTEO (fix wyscigu): świeżo utworzony/jeszcze nieodpytany zasób `list`
    // ma `list.params` == null (frappe-ui resources.js: `params: null` w
    // stanie początkowym, ustawiane dopiero synchronicznie na starcie
    // pierwszego fetch()/reload()) - w tym oknie zapytanie do mapa() poszłoby
    // z pustymi filters/default_filters, czyli TYM SAMYM źródłem dwóch
    // zbędnych zapytań opisanych wyżej. Pomijamy submit, dopóki `list.params`
    // nie istnieje. To NIGDY nie blokuje prawdziwego pierwszego wejścia na
    // Mapę z już załadowaną Tabelą: skoro `list.data` jest wypełnione, to
    // `list.params` musiało już zostać ustawione synchronicznie PRZED tymi
    // danymi (ten sam fetch() ustawia najpierw .params, potem, po odpowiedzi,
    // .data) - `immediate: true` powyżej nadal odpytuje od razu w tym
    // przypadku, tak jak dotychczas.
    if (!props.list.params) return

    const tenZadanieSeq = ++zadanieSeq
    mapaResource.submit(
      {
        filters: JSON.stringify(props.list.params?.filters || {}),
        default_filters: JSON.stringify(props.list.params?.default_filters || {}),
      },
      {
        onSuccess: (data) => {
          if (tenZadanieSeq !== zadanieSeq) return // spóźniona odpowiedź, nowsze zadanie już w locie
          stan.leady = data || []
          blad.value = ''
        },
        onError: (err) => {
          if (tenZadanieSeq !== zadanieSeq) return
          blad.value = extractErrorMessage(err) || __('Nie udało się wczytać leadów z mapy')
        },
      },
    )
  },
  { immediate: true },
)

const initialLoading = computed(() => mapaResource.loading && !mapaResource.data)

// Precedent: DokumentyLista.vue's extractErrorMessage() - call()/createResource
// throw an error whose Polish server message lives in err.messages[0], not
// under _server_messages/exception.
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || ''
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || ''
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return ''
}

// --- Kolory statusów -----------------------------------------------------------

const BRAK_STATUSU = __('(brak)')

// Leaflet rysuje na <canvas> - potrzebuje realnego koloru CSS, nie klasy
// Tailwind. Mapa nazwa->hex odpowiada w przybliżeniu odcieniowi, jaki
// parseColor() (utils/index.js) generuje dla statusów w reszcie CRM (-600,
// poza gray/green -700 i black -> ink-gray-9) - piny są więc spójne
// kolorystycznie z badge'ami/przyciskami statusów gdzie indziej w appce.
const HEX_PO_NAZWIE_KOLORU = {
  black: '#18181b',
  gray: '#374151',
  blue: '#2563eb',
  green: '#15803d',
  red: '#dc2626',
  pink: '#db2777',
  orange: '#ea580c',
  amber: '#d97706',
  yellow: '#ca8a04',
  cyan: '#0891b2',
  teal: '#0d9488',
  violet: '#7c3aed',
  purple: '#9333ea',
}

function kolorStatusu(status) {
  const parsed = getLeadStatus(status)?.color
  const nazwa = colorNameFromParsed(parsed)
  return HEX_PO_NAZWIE_KOLORU[nazwa] || HEX_PO_NAZWIE_KOLORU.gray
}

// --- Ustawienia mapy: kolor pinezek + pola dymku (issue #101) --------------------

// "Kolor pinezek według": Status CC (domyślny, jak dotąd) / Handlowiec
// (lead_owner) / CC (custom_cc). Wybór zapamiętany w localStorage, żeby CC
// nie musiał ustawiać go po każdym wejściu na mapę.
const trybKolorowania = ref(wczytajTrybKolorowania())
watch(trybKolorowania, (tryb) => {
  zapiszTrybKolorowania(tryb)
  rysujMarkery()
})

// "Klastrowanie przy oddaleniu" (issue #101): grupuje pinezki w klastry
// przy niskim zoomie (L.markerClusterGroup zamiast L.featureGroup) - ważne
// przy ~9900 pinezkach dla admina, mniej istotne dla CC/handlowca z
// kilkudziesięcioma. Domyślnie włączone. Przełączenie w locie przebudowuje
// TYLKO warstwę Leafleta (przebudujWarstwe), dane z API zostają w pamięci -
// bez ponownego odpytania serwera.
const klastrowanie = ref(wczytajKlastrowanie())
watch(klastrowanie, (wlaczone) => {
  zapiszKlastrowanie(wlaczone)
  przebudujWarstwe()
})

// `custom_cc` jest na permlevel 2 -- `frappe.get_list` w mapa() wycina go z
// odpowiedzi dla ról bez odczytu (Volteo D2D Sales). Gdy klucza nie ma w
// ogóle w danych, opcja "CC" znika z selecta zamiast pokazywać tryb, który
// zawsze koloruje wszystko na szaro.
const czyCcDostepne = computed(() => poleObecneWDanych(stan.leady, 'custom_cc'))

const opcjeKolorowania = computed(() => {
  const opcje = [
    { label: __('Status CC'), value: 'status' },
    { label: __('Handlowiec'), value: 'handlowiec' },
  ]
  if (czyCcDostepne.value) opcje.push({ label: 'CC', value: 'cc' })
  return opcje
})

// Serwer wycofał opcję spod nóg (rola się zmieniła / dane odświeżone) --
// cofamy do domyślnego trybu zamiast zostawiać "cc" wybrane na zawsze na szaro.
watch(czyCcDostepne, (dostepne) => {
  if (!dostepne && trybKolorowania.value === 'cc') {
    trybKolorowania.value = 'status'
  }
})

function kolorLeada(lead) {
  if (trybKolorowania.value === 'handlowiec') {
    return lead.lead_owner ? kolorDlaUzytkownika(lead.lead_owner) : KOLOR_BRAK
  }
  if (trybKolorowania.value === 'cc') {
    return lead.custom_cc ? kolorDlaUzytkownika(lead.custom_cc) : KOLOR_BRAK
  }
  return kolorStatusu(lead.status)
}

// Legenda nad mapą: tylko dla Handlowiec/CC -- tryb Status ma już swoją
// legendę w chipach filtrów statusu (statusyZListy powyżej), powtarzanie
// jej tutaj byłoby zbędne. Liczona z leadów PO filtrach, żeby liczniki
// odpowiadały temu, co faktycznie widać na mapie.
const legendaAktywna = computed(() => {
  if (trybKolorowania.value === 'status') return []
  return legenda(leadyPrzefiltrowane.value, trybKolorowania.value, {
    brakEtykiety: BRAK_STATUSU,
  })
})

function etykietaLegendy(klucz) {
  if (klucz === BRAK_STATUSU) return BRAK_STATUSU
  return getUser(klucz).full_name || klucz
}

// "Pola w dymku pinezki": cztery pola opcjonalne, zapamiętane w localStorage.
// Tytuł/miasto/status w dymku zostają zawsze widoczne (to nie są pola z tej
// listy w issue, tylko podstawowa tożsamość pinezki).
const ustawieniaDymka = reactive(wczytajUstawieniaDymka())
watch(ustawieniaDymka, (wartosc) => zapiszUstawieniaDymka({ ...wartosc }), { deep: true })

// --- Filtry (chipy widoczności statusów) ----------------------------------------

const statusyZListy = computed(() => {
  const liczniki = new Map()
  for (const lead of stan.leady) {
    const status = lead.status || BRAK_STATUSU
    liczniki.set(status, (liczniki.get(status) || 0) + 1)
  }
  return [...liczniki.entries()]
    .map(([status, liczba]) => ({ status, liczba }))
    .sort((a, b) => b.liczba - a.liczba)
})

// Zbiór statusów WYŁĄCZONYCH przez użytkownika (ops#113), nie AKTYWNYCH.
// Domyślnie pusty -- lead jest widoczny, dopóki jego status nie zostanie
// wyłączony ręcznie kliknięciem chipa. To LOKALNY (nieserwerowy) przełącznik
// widoczności pinezek na tej mapie -- w odróżnieniu od Filter/QuickFilterField
// w ViewControls, który steruje tym, JAKIE leady w ogóle przychodzą z serwera
// (issue #100). Zobacz komentarz w mapaFiltry.js po pełne wyjaśnienie,
// dlaczego poprzednia (odwrotna) semantyka gubiła pinezkę po zmianie statusu
// z panelu "Szybki podgląd".
const wylaczoneStatusy = ref(new Set())

function toggleStatus(status) {
  const next = new Set(wylaczoneStatusy.value)
  if (next.has(status)) {
    next.delete(status)
  } else {
    next.add(status)
  }
  wylaczoneStatusy.value = next
}

const leadyPrzefiltrowane = computed(() => {
  const filtry = { wylaczone: wylaczoneStatusy.value }
  return stan.leady.filter((lead) => widocznyLead(lead, filtry, BRAK_STATUSU))
})

watch(leadyPrzefiltrowane, () => rysujMarkery())

// --- Panel "Szybki podgląd" (issue #97, L08) ------------------------------

const wybranyLead = ref(null)

// Powiększenie pinezki wybranego leada (issue z klik-testu b62, pozycja 9):
// styl leży TEŻ tutaj, nie tylko w rysujMarkery(), bo watch(leadyPrzefiltrowane, ...)
// i inne przebudowy warstwy (patrz niżej) wołają rysujMarkery() na każdą
// zmianę danych/trybu/klastrowania -- gdyby styl "wybrany" żył wyłącznie w
// click handlerze, kolejna przebudowa zgubiłaby go bez zmiany wybranyLead.
// Porównanie po `name`, nie po referencji: patchujLeada() podmienia obiekt
// leada w stan.leady na NOWY (immutability), więc stary===nowy byłoby zawsze
// false mimo że to wciąż ten sam lead.
watch(wybranyLead, (nowy, stary) => {
  if (stary) ustawStylWybranego(stary.name, false)
  if (nowy) ustawStylWybranego(nowy.name, true)
})

// Immutable patch (coding-style.md: nowe obiekty, nie mutacja) -- panel
// emituje tylko status i/lub lead_owner (jedyne pola, po ktorych mapa
// przebarwia/filtruje pinezke), wiec merge'ujemy wylacznie te dwa klucze,
// jesli sa obecne w patchu.
function patchujLeada(patch) {
  if (!patch?.name) return
  const idx = stan.leady.findIndex((lead) => lead.name === patch.name)
  if (idx === -1) return

  const zaktualizowany = { ...stan.leady[idx] }
  if (Object.hasOwn(patch, 'status')) zaktualizowany.status = patch.status
  if (Object.hasOwn(patch, 'lead_owner')) {
    zaktualizowany.lead_owner = patch.lead_owner
  }

  stan.leady = [
    ...stan.leady.slice(0, idx),
    zaktualizowany,
    ...stan.leady.slice(idx + 1),
  ]

  if (wybranyLead.value?.name === patch.name) {
    wybranyLead.value = zaktualizowany
  }
}

// --- Mikro-jitter deterministyczny ---------------------------------------------

// Piny z tego samego kodu pocztowego geokodują się na (prawie) identyczne
// współrzędne i inaczej stałyby jeden na drugim. Hash nazwy leada (stabilny
// identyfikator, np. CRM-LEAD-2026-00123) daje deterministyczne przesunięcie:
// ten sam lead zawsze ląduje w tym samym miejscu między przeładowaniami.
// `hashString` (issue #101) przeniesiony do utils/mapaKolory.js, żeby
// kolorowanie wg użytkownika mogło użyć tego samego algorytmu.

// Issue #102: jitter ma sens tylko tam, gdzie wiele leadów faktycznie dzieli
// JEDEN punkt - centroid kodu pocztowego (dokładność "kod"), albo brak
// dokładnego geokodu w ogóle (dokładność "brak", albo pusta/nieustawiona,
// gdy skrypt schematu jeszcze nie poszedł albo lead nie był jeszcze
// przetworzony wsadem). Pin geokodowany po prawdziwym adresie ("adres") albo
// po samej ulicy ("ulica") ma już własną, w praktyce unikalną współrzędną -
// jitter przesunąłby go z prawdziwej lokalizacji bez żadnego powodu.
const JITTER_DEG = 0.005
const DOKLADNOSCI_Z_JITTEREM = new Set(['kod', 'miejscowosc', 'brak', ''])

function potrzebujeJitteru(dokladnosc) {
  return DOKLADNOSCI_Z_JITTEREM.has(dokladnosc || '')
}

function jitterOffset(name, sol) {
  const h = hashString(`${name}:${sol}`)
  // h jest 32-bit signed; % 2000 daje -1999..1999, normalizacja do [-1, 1).
  return ((h % 2000) / 2000) * JITTER_DEG
}

// --- Leaflet ---------------------------------------------------------------------

let L = null
let mapInstance = null
let markerLayer = null
let dopasowanoWidok = false
// Nazwa leada -> { marker, lead }, przebudowywana przy każdym rysujMarkery().
// Pozwala ustawStylWybranego() zmienić styl JEDNEGO markera in-place (klik
// w inną pinezkę, zamknięcie panelu) bez przebudowy całej warstwy.
let markeryPoNazwie = new Map()
// Podklasa L.CircleMarker rysująca pinezkę (patrz utworzKlasePinezki niżej) --
// tworzona raz, dopiero gdy `L` jest już dostępne (klasa dziedziczy po
// L.CircleMarker, więc nie da się jej zbudować przed leniwym importem).
let PinezkaLeada = null

// Podklasa L.CircleMarker rysująca teardrop-pinezkę zamiast kółka, wciąż
// wektorowa na wspólnym canvasie (preferCanvas: true) -- z ~10 849 leadami
// dla admina L.marker + divIcon/SVG (osobny element DOM na marker) byłby
// zbyt wolny, patrz komentarz na górze pliku o preferCanvas. _updateBounds
// i _containsPoint są nadpisane, bo domyślna geometria CircleMarker to
// symetryczne kółko wokół kotwicy -- pinezka jest wysoka i wąska, z kotwicą
// w czubku, nie w środku główki.
function utworzKlasePinezki(Lref) {
  return Lref.CircleMarker.extend({
    // Prostokąt pikseli musi objąć całą kroplę (główkę NAD kotwicą), inaczej
    // Canvas.js przy częściowym przerysowaniu (_redrawBounds, patrz
    // _extendRedrawBounds w Canvas.js) obcina pinezki leżące na krawędzi
    // przerysowywanego obszaru.
    _updateBounds: function () {
      const r = this._radius
      const w = this._clickTolerance()
      const g = geometriaPinezki(r)
      this._pxBounds = new Lref.Bounds(
        this._point.subtract([r + w, -g.srodekY + r + w]),
        this._point.add([r + w, w]),
      )
    },
    // Trafienie kursora/kliknięcia: główka (koło) albo trzon (zwężający się
    // od środka główki do czubka pas) -- przybliżenie kształtu kropli,
    // wystarczające jako tolerancja kliknięcia/hover.
    _containsPoint: function (p) {
      const r = this._radius + this._clickTolerance()
      const g = geometriaPinezki(this._radius)
      const srodek = this._point.add([0, g.srodekY])
      if (p.distanceTo(srodek) <= r) return true
      const dy = p.y - srodek.y
      if (dy < 0 || dy > -g.srodekY) return false
      const polSzer = r * (1 - dy / -g.srodekY)
      return Math.abs(p.x - this._point.x) <= Math.max(polSzer, 2)
    },
    // Rysowanie na canvasie: ścieżka kropli (sciezkaPinezki) plus
    // wypełnienie/obwódka przez ten sam _fillStroke co reszta warstw
    // wektorowych Leafleta, plus biała kropka w środku główki na wierzchu.
    // Poświata (halo) tylko dla wybranej pinezki (options.wybrany, ustawiane
    // przez stylPinezki), żeby wyróżniała się nawet na gęsto upakowanej
    // mapie po przeniesieniu wzroku na panel "Szybki podgląd" i z powrotem.
    _updatePath: function () {
      const renderer = this._renderer
      if (!renderer._drawing || this._empty()) return
      const ctx = renderer._ctx
      const p = this._point
      const r = Math.max(Math.round(this._radius), 1)

      if (this.options.wybrany) {
        ctx.beginPath()
        ctx.arc(p.x, p.y + geometriaPinezki(r).srodekY, r * 1.9, 0, Math.PI * 2, false)
        ctx.fillStyle = KOLOR_WYBRANEJ
        ctx.globalAlpha = 0.25
        ctx.fill()
      }

      sciezkaPinezki(ctx, p.x, p.y, r)
      renderer._fillStroke(ctx, this)

      ctx.globalAlpha = 1
      kropkaPinezki(ctx, p.x, p.y, r)
      ctx.fillStyle = KOLOR_OBWODKI
      ctx.fill()
    },
  })
}

async function initMap() {
  if (!L) {
    await import('leaflet/dist/leaflet.css')
    // leaflet.markercluster CSS (spiderfy/coverage) - ikona samego klastra
    // jest własna (ikonaKlastra, divIcon na tokenach Tailwind), ale te dwa
    // arkusze niosą pozostałe style pluginu (np. nogi "spiderfy").
    await import('leaflet.markercluster/dist/MarkerCluster.css')
    await import('leaflet.markercluster/dist/MarkerCluster.Default.css')
    const leafletModule = await import('leaflet')
    L = leafletModule.default ?? leafletModule
    // Wzorzec identyczny jak leaflet-draw w Controls/GeolocationControl.vue:
    // plugin dołącza się efektem ubocznym do tego samego singletona L, więc
    // import dopiero PO przypisaniu L.
    await import('leaflet.markercluster')
    PinezkaLeada = utworzKlasePinezki(L)
  }

  mapInstance = L.map(mapId, { preferCanvas: true }).setView([52.0, 19.3], 6)

  // TYLKO warstwa OSM (Stadia wymaga klucza na niedev domenach - nie używać).
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapInstance)

  markerLayer = utworzWarstweMarkerow().addTo(mapInstance)

  rysujMarkery()
}

// Warstwa markerów zależna od ustawienia "Klastrowanie przy oddaleniu":
// L.markerClusterGroup gdy włączone, zwykły L.featureGroup jak dotąd gdy
// wyłączone. L.circleMarker (wektor na canvasie) działa w obu - markercluster
// wymaga tylko getLatLng(), którą circleMarker implementuje.
function utworzWarstweMarkerow() {
  if (klastrowanie.value) {
    return L.markerClusterGroup({
      chunkedLoading: true,
      disableClusteringAtZoom: 13,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      maxClusterRadius: 60,
      iconCreateFunction: ikonaKlastra,
    })
  }
  return L.featureGroup()
}

// Ikona klastra: divIcon na tokenach semantycznych frappe-ui (dopasowanie do
// ciemnego motywu), nie domyślny zielono-żółty styl pluginu - domyślny
// className pluginu ('marker-cluster*') celowo pominięty, więc
// MarkerCluster.Default.css nie nadpisuje wyglądu.
function ikonaKlastra(cluster) {
  const liczba = cluster.getChildCount()
  const rozmiar =
    liczba < 10 ? 'h-8 w-8 text-xs' : liczba < 100 ? 'h-10 w-10 text-sm' : 'h-12 w-12 text-base'
  return L.divIcon({
    html: `<div class="flex ${rozmiar} items-center justify-center rounded-full border-2 border-outline-gray-3 bg-surface-gray-3 font-semibold text-ink-gray-9 shadow-md">${liczba}</div>`,
    // Nadpisuje domyślny className opcji divIcon ('leaflet-div-icon', tło
    // #fff + obramowanie w leaflet.css) - bez tego wewnętrzny div dostawałby
    // sprzeczne białe tło spod spodu.
    className: 'volteo-mapa-klaster',
    iconSize: L.point(40, 40, true),
  })
}

// Przełączenie klastrowania w locie (watch(klastrowanie, ...) wyżej): usuwa
// starą warstwę z mapy, tworzy nową wg aktualnego ustawienia i rysuje z
// danych już w pamięci (stan.leady) - bez ponownego zapytania do serwera.
// rysujMarkery() zawsze robi clearLayers()+odtwarza WSZYSTKIE markery od
// zera (już tak działało dla zmiany trybu kolorowania), więc nie trzeba
// clusterGroup.refreshClusters() - jest teraz dokładnie jeden marker, na
// którym robimy setStyle in-place: wybrany lead (patrz ustawStylWybranego
// i watch(wybranyLead, ...) wyżej), stylowany od razu wewnątrz
// rysujMarkery() poniżej, żeby przebudowa nie gubiła powiększenia.
function przebudujWarstwe() {
  if (!L || !mapInstance) return
  if (markerLayer) {
    mapInstance.removeLayer(markerLayer)
  }
  markerLayer = utworzWarstweMarkerow().addTo(mapInstance)
  rysujMarkery()
}

function rysujMarkery() {
  if (!L || !mapInstance || !markerLayer) return

  markerLayer.clearLayers()
  markeryPoNazwie.clear()

  for (const lead of leadyPrzefiltrowane.value) {
    const jitter = potrzebujeJitteru(lead.custom_geo_dokladnosc)
    const lat = Number(lead.custom_lat) + (jitter ? jitterOffset(lead.name, 'lat') : 0)
    const lng = Number(lead.custom_lng) + (jitter ? jitterOffset(lead.name, 'lng') : 0)
    if (!isFinite(lat) || !isFinite(lng)) continue

    const kolor = kolorLeada(lead)
    const wybrany = lead.name === wybranyLead.value?.name
    const marker = new PinezkaLeada([lat, lng], stylPinezki(kolor, wybrany))
    // Dymek nad główką, nie na czubku pinezki -- direction 'top' domyślnie
    // stawia dolną krawędź dymku dokładnie na kotwicy (czubku), a główka
    // pinezki jest NAD kotwicą, więc bez dodatkowego przesunięcia dymek
    // nachodziłby na główkę. Offset odpowiada pełnej wysokości pinezki
    // (geometriaPinezki().wysokosc), patrz komentarz przy geometriaPinezki.
    marker.bindTooltip(() => budujDymek(lead), {
      direction: 'top',
      offset: L.point(0, geometriaPinezki(STYL_PINEZKI.radius).srodekY - STYL_PINEZKI.radius),
    })
    marker.on('click', () => {
      wybranyLead.value = lead
    })
    marker.addTo(markerLayer)
    markeryPoNazwie.set(lead.name, { marker, lead })
    if (wybrany) marker.bringToFront()
  }

  if (!dopasowanoWidok && leadyPrzefiltrowane.value.length) {
    const bounds = markerLayer.getBounds()
    if (bounds.isValid()) {
      mapInstance.fitBounds(bounds, { padding: [20, 20] })
    }
    dopasowanoWidok = true
  }
}

// Styl "wybrany" na jednej pinezce, in-place, bez przebudowy warstwy (klik w
// inną pinezkę, zamknięcie panelu przyciskiem X albo Escape -- oba robią
// wybranyLead = null w komponencie nadrzędnym patrz watch(wybranyLead, ...)
// wyżej). Brak wpisu w mapie jest normalny: lead odfiltrowany albo bez
// współrzędnych po prostu nie ma markera.
function ustawStylWybranego(nazwa, wybrany) {
  const wpis = markeryPoNazwie.get(nazwa)
  if (!wpis) return
  wpis.marker.setStyle(stylPinezki(kolorLeada(wpis.lead), wybrany))
  if (wybrany) wpis.marker.bringToFront()
}

// Etykieta wiersza "Dokładność" w dymku (issue #102) - tylko cztery wartości
// niosące realną informację o precyzji geokodu; "brak"/pusty custom_geo_dokladnosc
// (backend jeszcze nie policzył albo nie znalazł trafienia) celowo bez etykiety,
// żeby `if (!value) continue` w pętli budującej dymek pominęło ten wiersz.
function etykietaDokladnosciGeokodu(dokladnosc) {
  const etykiety = {
    adres: __('adres'),
    ulica: __('ulica'),
    miejscowosc: __('miejscowość'),
    kod: __('kod pocztowy'),
  }
  return etykiety[dokladnosc] || ''
}

// Dymek pinezki (hover, Leaflet Tooltip) -- skrot: nazwa, miasto, status,
// zrodlo importu, obecne produkty, status zrodla. Klik w pinezke otwiera
// panel LeadSzybkiPodglad.vue (patrz marker.on('click', ...) wyzej) zamiast
// nawigowac -- "Otworz leada" zyje teraz w naglowku tego panelu, nie tutaj.
// Budowane przez DOM (nie string HTML) - bezpieczne wobec lead_name z
// dowolną treścią i nie wymaga v-html.
function budujDymek(lead) {
  const container = document.createElement('div')
  container.className = 'flex flex-col gap-0.5'

  const title = document.createElement('div')
  title.className = 'text-sm font-medium text-ink-gray-9'
  title.textContent = lead.lead_name || lead.name
  container.appendChild(title)

  const city = document.createElement('div')
  city.className = 'text-sm text-ink-gray-6'
  city.textContent = lead.custom_install_city || '-'
  container.appendChild(city)

  const status = document.createElement('div')
  status.className = 'text-sm text-ink-gray-6'
  status.textContent = lead.status || BRAK_STATUSU
  container.appendChild(status)

  // Pola w dymku (issue #101): tylko te, które użytkownik zostawił zaznaczone
  // w popoverze ustawień (domyślnie wszystkie cztery). Termin spotkania
  // formatowany przez formatDate() -- Datetime z serwera, nie surowy string.
  // Trzeci element (opcjonalny, `true`) oznacza wiersz "produktów leada"
  // (ops#150) -- tokeny renderowane jako span-chipy zamiast surowego
  // stringa "PV+PC" (patrz `rozbijTagi` w utils/tagiProduktow.js).
  const wiersze = [
    ustawieniaDymka.zrodlo && [__('Źródło'), lead.custom_import_source],
    ustawieniaDymka.produkty && [__('Obecne produkty'), lead.custom_posiadane_produkty, true],
    ustawieniaDymka.produkty && [__('Produkt w procesie'), lead.custom_produkt_procesu, true],
    ustawieniaDymka.statusZrodla && [__('Status źródła'), lead.custom_status_zrodla],
    ustawieniaDymka.terminSpotkania && [
      __('Termin spotkania'),
      lead.custom_termin_spotkania ? formatDate(lead.custom_termin_spotkania) : '',
    ],
    // Issue #102: wiersz dokładności geokodu. Etykieta "brak"/pusta nie ma
    // sensu do pokazania w dymku (to brak dokładnego geokodu, nie wartość
    // do zaprezentowania), więc mapa etykiet nie zna tego klucza i wiersz
    // po prostu nie trafi tu przez `if (!value) continue` niżej.
    [__('Dokładność'), etykietaDokladnosciGeokodu(lead.custom_geo_dokladnosc)],
  ].filter(Boolean)
  for (const [label, value, tagi] of wiersze) {
    if (!value) continue
    const row = document.createElement('div')
    row.className = 'text-xs text-ink-gray-5'
    if (tagi) {
      const etykieta = document.createElement('span')
      etykieta.textContent = `${label}: `
      row.appendChild(etykieta)
      for (const token of rozbijTagi(value)) {
        const chip = document.createElement('span')
        chip.className = 'inline-block rounded bg-surface-gray-3 px-1 mr-1 text-ink-gray-7'
        chip.textContent = token
        row.appendChild(chip)
      }
    } else {
      row.textContent = `${label}: ${value}`
    }
    container.appendChild(row)
  }

  return container
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markerLayer = null
  }
}

onMounted(() => initMap())
onBeforeUnmount(() => destroyMap())
</script>
