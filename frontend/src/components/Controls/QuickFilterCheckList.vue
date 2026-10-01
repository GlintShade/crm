<template>
  <Popover placement="bottom-start" @close="wyslijTeraz">
    <template #target="{ togglePopover }">
      <button
        type="button"
        class="relative flex h-7 w-full items-center justify-between gap-1 rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1 text-base transition-colors hover:border-outline-elevation-2 hover:bg-surface-gray-3"
        @click="togglePopover()"
      >
        <span
          class="truncate"
          :class="wybrane.length ? 'text-ink-gray-7' : 'text-ink-gray-4'"
        >
          {{ etykieta }}
        </span>
        <span class="flex shrink-0 items-center gap-1">
          <FeatherIcon
            v-if="wybrane.length"
            name="x"
            class="h-3.5 w-3.5 text-ink-gray-5 hover:text-ink-gray-8"
            @click.stop="wyczysc()"
          />
          <FeatherIcon
            name="chevron-down"
            class="h-4 w-4 text-ink-gray-5"
          />
        </span>
      </button>
    </template>
    <template #body="{ close }">
      <div
        class="my-1 w-60 rounded-lg bg-surface-elevation-2 p-1 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        <div v-if="jestLink || jestWartosciSerwera" class="p-1">
          <FormControl
            type="text"
            :placeholder="__('Search')"
            :modelValue="jestLink ? zapytanie : zapytanieWartosciSerwera"
            @input="(e) => naZmianeWyszukiwania(e.target.value)"
          />
        </div>
        <div class="max-h-60 overflow-y-auto">
          <template v-for="(grupa, i) in grupyWidoczne" :key="grupa.group ?? i">
            <div
              v-if="grupa.group"
              class="truncate px-2 py-1 text-sm-medium text-ink-gray-5"
            >
              {{ __(grupa.group) }}
            </div>
            <div
              v-for="opcja in grupa.items"
              :key="`${grupa.group ?? i}:${opcja.value}`"
              class="rounded px-2 py-1 hover:bg-surface-gray-2"
            >
              <!-- Klucz łączy grupę z wartością, bo ta sama wartość statusu
                   (np. "Lead") może wystąpić w dwóch grupach naraz (OZE i
                   Czyste Powietrze) -- wiersze wszystkich grup są rodzeństwem
                   w tym samym przewijanym div, więc sam opcja.value dawałby
                   zdublowany klucz między grupami. -->
              <Checkbox
                :modelValue="jestZaznaczona(opcja.value)"
                :label="opcja.label"
                @update:modelValue="(zaznaczona) => przelacz(opcja.value, zaznaczona)"
              />
            </div>
          </template>
          <div
            v-if="(jestLink && zasob.loading) || (jestWartosciSerwera && ladowanieWartosciSerwera)"
            class="flex justify-center p-2"
          >
            <LoadingIndicator class="h-4 w-4" />
          </div>
          <div
            v-else-if="jestWartosciSerwera && bladWartosciSerwera"
            class="px-2 py-1.5 text-sm text-ink-red-4"
          >
            {{ bladWartosciSerwera }}
          </div>
          <div
            v-else-if="!widoczneOpcje.length"
            class="px-2 py-1.5 text-sm text-ink-gray-4"
          >
            {{ __('No results') }}
          </div>
        </div>
        <div class="mt-1 border-t pt-1">
          <Button
            variant="ghost"
            class="w-full justify-center"
            :label="__('Clear')"
            @click="wyczyscIZamknij(close)"
          />
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
// Chip szybkiego filtra dla pól Select i Link (poza User i datami, patrz
// czyWielokrotnyWybor w filtrWielokrotny.js) z wielokrotnym wyborem przez
// checkboxy (issue #127, decyzja właściciela 2026-09-10). Celowo NIE
// frappe-ui MultiSelect: właściciel chciał listę, która zostaje otwarta po
// każdym kliknięciu opcji, z filtrem stosowanym natychmiast po każdym
// przełączeniu: to własny, prosty i przewidywalny Popover + lista
// checkboxów zamiast polegania na wewnętrznej logice zamykania comboboksa
// wielokrotnego wyboru w frappe-ui (patrz JSDoc w LinkMultiSelect.vue: ten
// komponent to jego odpowiednik dla rozwijanego Filter.vue, tam zamykanie
// po wyborze nie przeszkadza, bo to inny wzorzec UI: pole z "chipami"
// wartości w środku, nie zwarty przycisk na pasku szybkich filtrów).
//
// Dwa tryby, zależnie od fieldtype:
//   Select: opcje statyczne z `options` (kształt {label, value}, tak jak
//            zwraca crm.api.doc.get_quick_filters, ALBO kształt pogrupowany
//            {group, items} -- pole „Etap" na CRM Deal, owner remark #37,
//            2026-09-28, patrz utils/etapFiltr.js::opcjeEtapu; oba kształty
//            normalizuje grupyOpcjiFiltraSzybkiego w utils/filtrSzybki.js.
//            Nagłówek grupy to zwykły, nieinteraktywny wiersz, tłumaczony
//            __() w momencie renderowania (nazwy grup "OZE"/"Czyste
//            Powietrze"/"Inne" nie mogą być tłumaczone w module, patrz
//            PUŁAPKA eager chunk w etapFiltr.js). Placeholder pustej
//            wartości '' pomijany wewnątrz każdej grupy, bo w liście
//            checkboxów jest bez sensu, czyszczenie idzie przez "x" na
//            chipie albo "Wyczyść" na dole.
//   Link: opcje z frappe.desk.search.search_link (ten sam wzorzec co
//            LinkMultiSelect.vue: debounce zapytania, scalanie wyników z
//            aktualnie zaznaczonymi wartościami przez scalOpcjeZZaznaczonymi,
//            żeby zaznaczenie zostało widoczne nawet gdy kolejne zapytanie
//            zawęzi wyniki i akurat pominie już wybraną wartość). Issue #214
//            (2026-10-01): gdy `options === 'User'` (np. custom_cc,
//            lead_owner), dochodzi zawężenie do poddrzewa Sales Hierarchy i
//            opcja "@me" jako pierwsza pozycja -- ten sam, wspólny,
//            frappe-free moduł `utils/zakresUzytkownikow.js`, z którego
//            korzysta też LinkMultiSelect.vue (popover "Filtr") i Link.vue
//            (wybór pojedynczy). Przed tym issue to pole w ogóle nie
//            docierało tutaj (patrz wyłączenie User w
//            utils/filtrWielokrotny.js::czyWielokrotnyWybor, usunięte tym
//            issue).
//   Wartości z serwera (issue #218, prop `serverValues`): trzeci tryb, dla
//            pól z `field.volteo_wartosci` (np. Powiat na CRM Lead,
//            zawężony do aktywnego filtra Województwo). W odróżnieniu od
//            Link (zapytanie do search_link za każdym wciśnięciem klawisza)
//            PEŁNA lista opcji jest pobierana RAZ (i ponownie przy każdej
//            zmianie zależnego filtra) z `serverValues.url`, a wyszukiwanie
//            w polu tekstowym filtruje ją WYŁĄCZNIE po stronie klienta --
//            katalog jest mały (rząd setek pozycji, nie tysięcy), więc
//            kolejne zapytanie do serwera na każdy znak byłoby niepotrzebne.
//            Licznik żądań (`numerZapytaniaWartosciSerwera`) chroni przed
//            wyścigiem, gdy zależny filtr zmienia się szybciej niż
//            odpowiada serwer -- ten sam wzorzec co
//            `LeadyPrzydzial.vue::numerZapytaniaPowiaty`. Żadnego `cache:`
//            w `createResource` poniżej: ten komponent montuje się
//            wielokrotnie na tej samej stronie (raz na pole filtra), a
//            współdzielony zasób nadpisywałby stan jednej instancji danymi
//            przeznaczonymi dla innej.
import {
  Button,
  Checkbox,
  FeatherIcon,
  FormControl,
  LoadingIndicator,
  Popover,
  createResource,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { scalOpcjeZZaznaczonymi } from '@/utils/filtrWielokrotny'
import { opcjeUzytkownikow } from '@/utils/etykietaUzytkownika'
import { dolozOpcjeMoje, filtrZakresuUzytkownikow } from '@/utils/zakresUzytkownikow'
import { usersStore } from '@/stores/users'
import {
  etykietaChipaFiltraSzybkiego,
  grupyOpcjiFiltraSzybkiego,
  ustawWartoscWielokrotna,
} from '@/utils/filtrSzybki'

const props = defineProps({
  label: { type: String, required: true },
  fieldtype: { type: String, required: true },
  // Select: tablica {label, value} (płaska) ALBO {group, items} (pogrupowana
  // -- Etap na CRM Deal, owner remark #37, patrz utils/etapFiltr.js::opcjeEtapu
  // i grupyOpcjiFiltraSzybkiego w utils/filtrSzybki.js, który oba kształty
  // normalizuje). Link: nazwa doctype'u do przeszukania.
  options: { type: [Array, String], default: () => [] },
  // Issue #214: etykieta opcji "@me" (utils/etykietaMoje.js), uwzględniana
  // wyłącznie gdy fieldtype==='Link' i options==='User'.
  meLabel: { type: String, default: '@me' },
  // Issue #218: konfiguracja trybu "wartości z serwera" --
  // `{ url, parametr, zaleznaWartosc }`. Obecność (nie-null) tego propa
  // WYMUSZA ten tryb niezależnie od `fieldtype`/`options` -- wołający
  // (QuickFilterField.vue/Filter.vue) ustala to z wyprzedzeniem na
  // podstawie `field.volteo_wartosci` (utils/filtrSzybki.js::
  // zaleznaWartoscFiltraSerwera), ten komponent sam nie zna żadnej nazwy
  // pola. `url`: whitelisted API frontu zwracające tablicę stringów.
  // `parametr`: nazwa parametru tego API, pod którym wysyłana jest
  // `zaleznaWartosc`. `zaleznaWartosc`: aktualnie rozpakowana wartość
  // filtra zależnego (tablica stringów, może być pusta -- "bez zawężenia").
  serverValues: { type: Object, default: null },
})

const { getUser } = usersStore()

const model = defineModel({ type: Array, default: () => [] })

// Issue #127 follow-up (smoke, 2026-09-10): klikanie kilku checkboxow pod
// rzad wywolywalo za kazdym razem create_or_update_standard_view +
// przeladowanie listy, wiec rownolegle zapisy blokowaly sie nawzajem
// (QueryDeadlockError). `lokalneWybrane` to stan UI, zmieniany NATYCHMIAST
// na kazdy klik (checkboxy odpowiadaja bez opoznienia); `model.value =`
// (czyli emisja `update:modelValue` do rodzica, ktora wyzwala zapis widoku)
// jest debounce'owana -- do rodzica trafia tylko OSTATNIA wartosc po
// CZAS_DEBOUNCE_MS pauzy w klikaniu. "Wyczysc" i zamkniecie popovera (patrz
// `@close="wyslijTeraz"` na <Popover> powyzej -- lapie klikniecie poza
// popover, Escape i wywolanie `close()`, nie tylko przycisk "Wyczysc")
// wysylaja ostatnia wartosc natychmiast, zeby zamkniecie przed uplywem
// debounce'a nie zgubilo wyboru.
const CZAS_DEBOUNCE_MS = 400

const lokalneWybrane = ref(Array.isArray(model.value) ? [...model.value] : [])
let debounceTimerWybor = null

// Zewnetrzna zmiana `model.value` (np. zaladowanie innego zapisanego widoku
// albo "Wyczysc wszystkie filtry" gdzie indziej) -- pomijana, gdy juz
// odpowiada lokalnemu stanowi (w tym echo naszej wlasnej wysylki), zeby nie
// przerywac w toku wpisywania niczym, co sami wlasnie wyslalismy.
watch(
  () => model.value,
  (nowaWartosc) => {
    const tablica = Array.isArray(nowaWartosc) ? nowaWartosc : []
    const bezZmian =
      tablica.length === lokalneWybrane.value.length &&
      tablica.every((v) => lokalneWybrane.value.includes(v))
    if (bezZmian) return
    clearTimeout(debounceTimerWybor)
    debounceTimerWybor = null
    lokalneWybrane.value = [...tablica]
  },
)

const wybrane = computed(() => lokalneWybrane.value)

const jestLink = computed(() => props.fieldtype === 'Link')
// Issue #214: pole Link do User (custom_cc, lead_owner, deal_owner,
// custom_opiekun...) -- zawężenie do poddrzewa hierarchii i opcja "@me".
const jestUser = computed(() => jestLink.value && props.options === 'User')
// Issue #218: tryb "wartości z serwera" -- patrz JSDoc propa serverValues.
const jestWartosciSerwera = computed(() => Boolean(props.serverValues))

function jestZaznaczona(wartosc) {
  return wybrane.value.includes(wartosc)
}

// Bierze zaznaczona wprost ze zdarzenia checkboxa (nie przelacza wzgledem
// wlasnego stanu) -- patrz komentarz przy ustawWartoscWielokrotna w
// utils/filtrSzybki.js: frappe-ui's Checkbox.vue emituje update:modelValue
// DWA RAZY na jedno klikniecie (blad biblioteki, poza zakresem tej
// poprawki), a przelaczanie zamiast ustawiania kasowalo wlasny efekt przy
// drugiej, zbednej emisji tego samego klikniecia -- checkbox wygladal na
// zaznaczony (natywny stan DOM), ale do filtra nic nie trafialo.
function przelacz(wartosc, zaznaczona) {
  lokalneWybrane.value = ustawWartoscWielokrotna(lokalneWybrane.value, wartosc, zaznaczona)
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = setTimeout(wyslijTeraz, CZAS_DEBOUNCE_MS)
}

// Flush natychmiastowy -- no-op, gdy nie ma nic w toku (debounceTimerWybor
// juz wyzerowany), wiec bezpieczny do wywolania z @close nawet gdy popover
// zamyka sie bez zadnej oczekujacej zmiany.
function wyslijTeraz() {
  if (!debounceTimerWybor) return
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = null
  model.value = lokalneWybrane.value
}

function wyczysc() {
  clearTimeout(debounceTimerWybor)
  debounceTimerWybor = null
  lokalneWybrane.value = []
  model.value = []
}

function wyczyscIZamknij(close) {
  wyczysc()
  close()
}

onBeforeUnmount(wyslijTeraz)

// --- Select: opcje statyczne, płaskie albo pogrupowane ---
const grupyStatyczne = computed(() => grupyOpcjiFiltraSzybkiego(props.options))

// --- Link: opcje z search_link ---
const zapytanie = ref('')
const znaneEtykiety = ref(new Map())

// Issue #214: zakres widocznych użytkowników (ten sam zasób/cache co
// Link.vue i LinkMultiSelect.vue, pobierany raz na stronę) -- WYŁĄCZNIE gdy
// jestUser.
const widoczniUzytkownicy = createResource({
  url: 'crm.api.volteo_uzytkownicy.widoczni_uzytkownicy',
  cache: ['widoczni_uzytkownicy'],
})

watch(
  jestUser,
  (aktywne) => {
    if (aktywne && !widoczniUzytkownicy.fetched && !widoczniUzytkownicy.loading) {
      widoczniUzytkownicy.fetch()
    }
  },
  { immediate: true },
)

// `null` = "jeszcze nie gotowe" (dopóki zakres dla doctype='User' nie
// dotarł) -- ten sam wzorzec co Link.vue::effectiveFilters i
// LinkMultiSelect.vue::effectiveFilters. `{}` dla każdego pola Link
// spoza User (zachowanie sprzed issue #214).
const effectiveFilters = computed(() => {
  if (!jestUser.value) return {}
  if (!widoczniUzytkownicy.fetched) return null
  return filtrZakresuUzytkownikow({}, widoczniUzytkownicy.data)
})

const zasob = createResource({
  url: 'frappe.desk.search.search_link',
  method: 'POST',
  params: {
    txt: '',
    doctype: jestLink.value ? props.options : '',
    filters: {},
  },
  transform: (data) => {
    let wynik = jestUser.value
      ? opcjeUzytkownikow(data, getUser)
      : (data || []).map((o) => ({
          label: o.label || o.value,
          value: o.value,
        }))
    if (jestUser.value) {
      // Issue #214: "@me" jako pierwsza pozycja, patrz
      // utils/zakresUzytkownikow.js::dolozOpcjeMoje.
      wynik = dolozOpcjeMoje(wynik, props.meLabel)
    }
    for (const opcja of wynik) znaneEtykiety.value.set(opcja.value, opcja)
    return wynik
  },
})

function wyszukajLink(txt) {
  // Issue #214: dopóki jestUser i zakres jeszcze nie dotarł
  // (effectiveFilters === null), nie odpytujemy -- watch(effectiveFilters)
  // niżej wywoła wyszukiwanie ponownie, gdy zakres dotrze.
  if (jestUser.value && effectiveFilters.value === null) return
  zasob.update({ params: { txt, doctype: props.options, filters: effectiveFilters.value } })
  zasob.fetch()
}

let debounceTimer = null
function naZmianeZapytania(txt) {
  zapytanie.value = txt
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => wyszukajLink(txt), 300)
}

// Issue #218: dyspozytor pola wyszukiwania -- Link pyta serwer (debounce,
// naZmianeZapytania powyżej), wartości z serwera filtrują PO STRONIE
// KLIENTA listę już pobraną (patrz docstring modułu), bez żadnego
// zapytania dodatkowego.
function naZmianeWyszukiwania(txt) {
  if (jestLink.value) {
    naZmianeZapytania(txt)
  } else if (jestWartosciSerwera.value) {
    zapytanieWartosciSerwera.value = txt
  }
}

onMounted(() => {
  if (jestLink.value) wyszukajLink('')
  if (jestWartosciSerwera.value) wczytajWartosciSerwera()
})

// Issue #214: gdy effectiveFilters przechodzi z `null` na gotowy obiekt
// (zakres dotarł z serwera), uruchom wyszukiwanie od razu.
watch(effectiveFilters, (wartosc, poprzednia) => {
  if (poprzednia === null && wartosc !== null) {
    wyszukajLink(zapytanie.value)
  }
})

const opcjeLinku = computed(() => {
  const wyniki = zasob.data || []
  const brakujaceZnane = wybrane.value
    .filter((v) => !wyniki.some((o) => o.value === v))
    .map((v) => znaneEtykiety.value.get(v))
    .filter(Boolean)
  return scalOpcjeZZaznaczonymi([...wyniki, ...brakujaceZnane], wybrane.value)
})

// --- Wartości z serwera (issue #218) ---
const zapytanieWartosciSerwera = ref('')
const opcjeSurowe = ref([])
const bladWartosciSerwera = ref('')
const ladowanieWartosciSerwera = ref(false)

// `auto: false` -- pobranie startuje jawnie z wczytajWartosciSerwera
// (onMounted/watch poniżej), nigdy przy samym utworzeniu zasobu. Bez
// `cache:`, patrz komentarz modułu u góry pliku.
//
// `url` jest ustalany RAZ, przy tworzeniu zasobu: frappe-ui's `update({url})`
// zmienia wyłącznie widoczną z zewnątrz (reaktywną) właściwość `url` zasobu,
// NIE adres faktycznie używany przez kolejne `fetch`/`submit` (ten zostaje
// zamknięty w `options` z chwili `createResource`, patrz `resources.js` w
// frappe-ui) -- wywołanie `.update({url: inny})` byłoby więc ciche i
// mylące, nie zmieniałoby faktycznego zapytania. Niegroźne tutaj: jedna
// instancja tego komponentu renderuje zawsze TO SAMO pole filtra przez cały
// swój cykl życia, więc `serverValues.url` jest de facto stały.
const zasobWartosciSerwera = createResource({
  url: props.serverValues?.url || '',
  auto: false,
})

let numerZapytaniaWartosciSerwera = 0
async function wczytajWartosciSerwera() {
  if (!jestWartosciSerwera.value) return
  const tenNumer = ++numerZapytaniaWartosciSerwera
  bladWartosciSerwera.value = ''
  ladowanieWartosciSerwera.value = true
  try {
    const { parametr, zaleznaWartosc } = props.serverValues
    const dane = await zasobWartosciSerwera.submit({
      [parametr]: JSON.stringify(zaleznaWartosc || []),
    })
    // Odpowiedź na przestarzałe zapytanie (zależny filtr zmienił się
    // ponownie zanim ta odpowiedź wróciła) -- zignoruj, patrz komentarz
    // modułu u góry pliku (ten sam wzorzec co LeadyPrzydzial.vue).
    if (tenNumer !== numerZapytaniaWartosciSerwera) return
    opcjeSurowe.value = Array.isArray(dane) ? dane : []
  } catch (err) {
    if (tenNumer !== numerZapytaniaWartosciSerwera) return
    bladWartosciSerwera.value =
      err?.messages?.[0] || __('Nie udało się wczytać listy wartości')
    opcjeSurowe.value = []
  } finally {
    if (tenNumer === numerZapytaniaWartosciSerwera) ladowanieWartosciSerwera.value = false
  }
}

// Zmiana zależnego filtra (np. innego Województwa) -- porównanie przez
// JSON.stringify, żeby nowa-ale-równa tablica z rodzica (nowa tożsamość
// przy każdym jego przeliczeniu) nie wywoływała zbędnego zapytania.
watch(
  () => JSON.stringify(props.serverValues?.zaleznaWartosc || []),
  () => {
    if (jestWartosciSerwera.value) wczytajWartosciSerwera()
  },
)

// Scalenie z zaznaczonymi PRZED filtrowaniem wyszukiwarką -- ten sam powód
// co scalOpcjeZZaznaczonymi dla Linku: zaznaczony powiat spoza aktualnie
// zawężonej (po Województwie) listy zostaje widoczny i zaznaczony
// (decyzja orkiestratora, issue #218), nie znika po cichu.
const opcjePelneWartosciSerwera = computed(() =>
  scalOpcjeZZaznaczonymi(
    opcjeSurowe.value.map((w) => ({ label: w, value: w })),
    wybrane.value,
  ),
)
const opcjeWidoczneWartosciSerwera = computed(() => {
  const tekst = zapytanieWartosciSerwera.value.trim().toLowerCase()
  if (!tekst) return opcjePelneWartosciSerwera.value
  return opcjePelneWartosciSerwera.value.filter((opcja) =>
    opcja.label.toLowerCase().includes(tekst),
  )
})

// Link nie ma grup: jedna grupa bez nagłówka, tak jak płaska lista Select w
// grupyOpcjiFiltraSzybkiego. `widoczneOpcje` (spłaszczone, bez podziału na
// grupy) zostaje jako jedyne źródło dla etykietyWybranych/warunku "No
// results" -- ich logika nie zależy od podziału na grupy.
const grupyWidoczne = computed(() => {
  if (jestLink.value) return [{ group: null, items: opcjeLinku.value }]
  if (jestWartosciSerwera.value) return [{ group: null, items: opcjeWidoczneWartosciSerwera.value }]
  return grupyStatyczne.value
})
const widoczneOpcje = computed(() =>
  grupyWidoczne.value.flatMap((grupa) => grupa.items),
)

// Etykiety zaznaczonych wartości dla chipa, z listy widocznych opcji
// (rozpoznaje prawdziwą etykietę Linka, nie tylko wartość), z fallbackiem
// na samą wartość, gdyby jeszcze nie padło żadne zapytanie w tej sesji
// (np. Link z wczytanego zapisanego widoku).
const etykietyWybranych = computed(() =>
  wybrane.value.map(
    (v) => widoczneOpcje.value.find((o) => o.value === v)?.label ?? v,
  ),
)

const etykieta = computed(() =>
  etykietaChipaFiltraSzybkiego(props.label, etykietyWybranych.value),
)
</script>
