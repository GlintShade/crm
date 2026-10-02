// Logika czysta (bez importu frappe-ui / @) dla wielokrotnego wyboru w
// pasku szybkich filtrów (QuickFilterField.vue / ViewControls.vue, issue
// #127), dla pól Select i Link (poza polami User i datami, patrz
// czyWielokrotnyWybor w filtrWielokrotny.js, którego ten pasek też używa).
//
// Serializacja do backendu i do zapisanych widoków, w obu kierunkach:
//   0 wartości  -> klucz filtra usunięty (undefined tutaj, wywołujący
//                  kasuje klucz z obiektu filters)
//   1 wartość   -> dotychczasowy skalarny kształt (`filters[pole] = wartość`),
//                  bez zmian względem stanu sprzed tej zmiany
//   N wartości  -> `["in", [w1, w2, ...]]`, ten sam format co operator
//                  "jest jednym z" w rozwijanym Filter.vue (issue #103)
//
// Odczyt idzie tą samą drogą w drugą stronę: rozpakujWartoscFiltraSzybkiego
// rozpoznaje wyłącznie skalar i `["in", [...]]`, każdy inny kształt
// tablicowy (np. `["like", "%x%"]` z rozwijanego filtra) zostaje pusty,
// dokładnie tak jak zachowywał się pasek szybkich filtrów przed tą zmianą
// dla pól Select/Link/Date/Datetime (patrz quickFilterList w
// ViewControls.vue: każdy nierozpoznany kształt tablicowy zostawiał
// wartość domyślną).
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js/etykietaMoje.js: eager chunk woła moduł przed i18n),
// testowalne bezpośrednio przez vitest.

import { czyWielokrotnyWybor, parsujWartoscWielokrotna } from './filtrWielokrotny'
import { OPERATOR_TAGOW, czyZlozonyFiltrTagow, rozpakujZlozonyFiltrTagow } from './tagiProduktow'

/**
 * Rozpakowuje surową wartość filtra (`list.params.filters[fieldname]`,
 * kształt jakiego oczekuje backend) do tablicy zaznaczonych stringów, do
 * użytku jako stan checkboxów. Rozpoznaje skalar (pojedyncza wartość) i
 * `["in", [...]]` (wiele wartości, wielkość liter operatora bez znaczenia).
 * Każdy inny kształt tablicowy (np. `["like", "%x%"]`) zwraca pustą tablicę
 * nie ma z czego bezpiecznie odtworzyć zaznaczeń checkboxów.
 *
 * Issue ops#173: dla pól tagów wartość bywa też kształtem złożonym
 * (`["volteo_tagi", {"ma": [...], "nie_ma": [...]}]`) -- pasek szybki
 * pokazuje wtedy stronę "ma" jako zaznaczenia (strona "nie_ma" jest
 * niewidoczna na pasku, ale przeżywa edycję z paska, patrz
 * `czyFiltrSzybkiZablokowany`/`ViewControls.vue::applyQuickFilter`).
 */
export function rozpakujWartoscFiltraSzybkiego(rawValue) {
  if (rawValue === undefined || rawValue === null || rawValue === '') return []
  if (Array.isArray(rawValue)) {
    const operator = String(rawValue[0] ?? '').toLowerCase()
    if (operator === 'in') {
      return parsujWartoscWielokrotna(rawValue[1])
    }
    if (operator === OPERATOR_TAGOW) {
      return rozpakujZlozonyFiltrTagow(rawValue).ma
    }
    return []
  }
  return parsujWartoscWielokrotna(rawValue)
}

/**
 * Rozstrzyga, czy `raw` (aktualna wartość filtra pola tagów w
 * `list.params.filters`) jest kształtem, którego pasek szybki nie umie
 * bezpiecznie przepisać "od zera" z samych zaznaczeń checkboxów bez utraty
 * informacji: kształt złożony (`czyZlozonyFiltrTagow`, niesie "nie_ma", o
 * którym pasek szybki nic nie wie) i `["not in", [...]]` (checkboxy paska
 * reprezentują "ma", nie "nie_ma" -- przepisanie "od zera" zamieniłoby
 * wykluczenie w dołączenie). `ViewControls.vue::applyQuickFilter` używa
 * tego, żeby przy zablokowanym kształcie scalić nowe zaznaczenia w stronę
 * "ma", zachowując "nie_ma" bez zmian, zamiast nadpisywać cały filtr.
 */
export function czyFiltrSzybkiZablokowany(raw) {
  if (czyZlozonyFiltrTagow(raw)) return true
  if (Array.isArray(raw)) {
    return String(raw[0] ?? '').toLowerCase() === 'not in'
  }
  return false
}

/**
 * Pakuje tablicę zaznaczonych stringów z powrotem do kształtu filtra
 * backendu: 0 wartości -> undefined (wywołujący usuwa klucz), 1 wartość ->
 * sam string (dotychczasowy kształt), N wartości -> `["in", [...]]`.
 */
export function spakujWartoscFiltraSzybkiego(wybrane) {
  const lista = parsujWartoscWielokrotna(wybrane)
  if (lista.length === 0) return undefined
  if (lista.length === 1) return lista[0]
  return ['in', lista]
}

/**
 * Buduje tekst chipa szybkiego filtra z etykiety pola i etykiet aktualnie
 * zaznaczonych wartości (nie ze stringów wartości: etykieta pochodzi z
 * katalogu opcji, np. dla pola Link etykieta może różnić się od wartości):
 * brak zaznaczeń -> sama etykieta pola (jak dziś dla pustego filtra), jedna
 * wartość -> `Etykieta: Wartość`, wiele -> `Etykieta: Pierwsza +N` (N =
 * liczba pozostałych, nie licząc pierwszej).
 */
export function etykietaChipaFiltraSzybkiego(etykietaPola, wybraneEtykiety) {
  const lista = (Array.isArray(wybraneEtykiety) ? wybraneEtykiety : [])
    .map((w) => (w == null ? '' : String(w)))
    .filter((w) => w.length > 0)
  if (lista.length === 0) return etykietaPola
  if (lista.length === 1) return `${etykietaPola}: ${lista[0]}`
  return `${etykietaPola}: ${lista[0]} +${lista.length - 1}`
}

/**
 * Rozstrzyga, czy dane pole na pasku szybkich filtrów dostaje wielokrotny
 * wybór (issue #127): Select lub Link poza User (patrz czyWielokrotnyWybor).
 *
 * Uwaga (owner remark #37, 2026-09-28): pole „Etap" (`status`) na `CRM Deal`
 * NIE jest już wyjątkiem tutaj -- dostaje wielokrotny wybór jak każdy inny
 * Link poza User. Jego własna, zawężona do aktywnego procesu lista opcji
 * (utils/etapFiltr.js, `opcjeEtapu`, płaska ALBO pogrupowana OZE/Czyste
 * Powietrze/Inne) jest teraz doprowadzana do `QuickFilterCheckList` przez
 * `QuickFilterField.vue::opcjeCheckList`, a kształt pogrupowany normalizuje
 * `grupyOpcjiFiltraSzybkiego` poniżej (ten sam plik, ta sama odpowiedzialność
 * co reszta serializacji szybkiego filtra). `doctype` zostaje w sygnaturze
 * wyłącznie dla stabilności trzech miejsc wywołania (QuickFilterField.vue,
 * ViewControls.vue x2) -- ciało go już nie używa.
 */
export function czyWielokrotnyFiltrSzybki(doctype, filter) {
  return czyWielokrotnyWybor(filter, 'in')
}

/**
 * Normalizuje opcje kontrolki wielokrotnego wyboru (QuickFilterCheckList) do
 * jednej, przewidywalnej postaci: tablicy grup `{ group: string|null, items:
 * Array<{label, value}> }`, niezależnie od tego, czy `options` przyszło
 * jako płaska lista `[{label,value}]` (zwykły Select/Link, kształt
 * `crm.api.doc.get_quick_filters`), czy jako lista pogrupowana
 * `[{group, items}]` (Etap na `CRM Deal`, `utils/etapFiltr.js::opcjeEtapu`,
 * owner remark #37, 2026-09-28).
 *
 * Rozpoznanie pogrupowanego kształtu mirroruje `groups` computed w
 * `components/frappe-ui/Autocomplete.vue`: wejście jest pogrupowane, gdy
 * pierwszy element niesie tablicę `items` ALBO prawdziwy `group` -- dwa
 * niezależne sygnały, bo grupa z pustym `group` (`''`) ma nadal `items`
 * jako tablicę i musi zostać rozpoznana jako pogrupowana, nie jako pojedynczy
 * płaski wpis.
 *
 * Płaska lista dostaje jedną grupę bez nagłówka (`group: null`) -- ten sam
 * wpis do renderowania checkboxów co dotychczasowy `opcjeStatyczne` w
 * `QuickFilterCheckList.vue`, tylko w jednolitym kształcie z grupami.
 *
 * Wewnątrz KAŻDEJ grupy (płaskiej i pogrupowanej identycznie) odrzucane są
 * wpisy z `value === ''`/`value == null` -- placeholder pustej wartości
 * Selecta jest bez sensu w liście checkboxów (dotychczasowa reguła
 * `opcjeStatyczne`, przeniesiona tutaj). Grupy, które po tym odrzuceniu
 * zostają puste, są usuwane z wyniku (np. `opcjeEtapu` przy wyścigu zimnego
 * ładowania store'u statusów potrafi zwrócić pustą grupę OZE/Czyste
 * Powietrze -- renderowanie pustego nagłówka byłoby mylące).
 *
 * Nie mutuje `options` (immutability): zawsze nowe tablice/obiekty.
 *
 * @param {Array<{label:string,value:string}>|Array<{group:string,items:Array<{label:string,value:string}>}>|null|undefined} options
 * @returns {Array<{group: string|null, items: Array<{label:string,value:string}>}>}
 */
export function grupyOpcjiFiltraSzybkiego(options) {
  if (!Array.isArray(options)) return []

  const jestPogrupowany =
    Array.isArray(options[0]?.items) || Boolean(options[0]?.group)
  const grupyWejsciowe = jestPogrupowany
    ? options
    : [{ group: null, items: options }]

  return grupyWejsciowe
    .map((grupa) => ({
      group: grupa.group || null,
      items: (Array.isArray(grupa.items) ? grupa.items : []).filter(
        (opcja) => opcja?.value !== '' && opcja?.value != null,
      ),
    }))
    .filter((grupa) => grupa.items.length > 0)
}

/**
 * Przełącza pojedynczą wartość w tablicy zaznaczonych (dodaje, gdy jej nie
 * ma, usuwa, gdy jest), immutable, zwraca nową tablicę.
 *
 * UWAGA: to funkcja przełączająca (toggle), nie ustawiająca (set) -- wołana
 * dwa razy z tym samym argumentem daje inny wynik niż raz (dodaje, potem
 * usuwa). Bezpieczna tylko tam, gdzie wywołanie odpowiada dokładnie jednemu
 * kliknięciu użytkownika. Do obsługi zdarzenia checkboxa (który niesie
 * własny stan zaznaczenia) użyj ustawWartoscWielokrotna poniżej -- patrz
 * jej komentarz po co.
 */
export function przelaczWartoscWielokrotna(wybrane, wartosc) {
  const lista = parsujWartoscWielokrotna(wybrane)
  return lista.includes(wartosc)
    ? lista.filter((w) => w !== wartosc)
    : [...lista, wartosc]
}

/**
 * Ustawia przynależność pojedynczej wartości w tablicy zaznaczonych wprost
 * (dodaje, gdy zaznaczona=true i jej jeszcze nie ma; usuwa, gdy
 * zaznaczona=false i jest), immutable, zwraca nową tablicę.
 *
 * W przeciwieństwie do przelaczWartoscWielokrotna, ta funkcja jest
 * idempotentna: wywołana dwa razy z tymi samymi argumentami daje ten sam
 * wynik co raz. To naprawia regresję z QuickFilterCheckList.vue (issue
 * #127 follow-up, 2026-09-11): frappe-ui's Checkbox.vue (onChange) emituje
 * update:modelValue DWA RAZY na jedno kliknięcie (raz przez efekt uboczny
 * defineModel przy `model.value = next`, raz jawnym `emit(...)` zaraz po --
 * pre-existing błąd biblioteki, poza zakresem tej poprawki). Gdy handler
 * odbierający zdarzenie ignorował przekazaną wartość i tylko przełączał
 * (poprzednie `@update:modelValue="przelacz(opcja.value)"`), podwójna
 * emisja dodawała wartość i natychmiast ją usuwała w tym samym kliknięciu
 * -- checkbox wizualnie się zaznaczał (natywny stan DOM, którego Vue nie
 * nadpisywało, bo z jego punktu widzenia `:checked` się nie zmieniło), ale
 * filtr nigdy nie trafiał do żądania. Ustawianie zamiast przełączania
 * usuwa ten problem u źródła: dwie identyczne emisje dają dwukrotnie ten
 * sam, poprawny wynik.
 */
export function ustawWartoscWielokrotna(wybrane, wartosc, zaznaczona) {
  const lista = parsujWartoscWielokrotna(wybrane)
  const jestJuz = lista.includes(wartosc)
  if (zaznaczona) {
    return jestJuz ? lista : [...lista, wartosc]
  }
  return jestJuz ? lista.filter((w) => w !== wartosc) : lista
}

/**
 * Buduje parametry zapytania dla pola z wartościami pobieranymi z serwera
 * (`field.volteo_wartosci`, issue #218 -- np. „Powiat” na `CRM Lead`
 * zawężony do aktywnego filtra `custom_voivodeship`): rozpakowuje aktualną
 * wartość filtra ZALEŻNEGO (`activeFilters[field.volteo_wartosci.zalezy_od]`)
 * tą samą funkcją co pasek szybki (`rozpakujWartoscFiltraSzybkiego`, więc
 * rozumie zarówno skalar jak i `["in", [...]]`) i zwraca tablicę jego
 * aktualnie zaznaczonych wartości -- pustą, gdy `field` nie ma flagi
 * `volteo_wartosci` albo zależny filtr nie jest ustawiony (front wtedy nie
 * zawęża zapytania, serwer zwraca pełną widoczną pulę, zgodnie z brzmieniem
 * issue #218: "Bez województwa: wszystkie widoczne powiaty").
 *
 * Współdzielona przez `QuickFilterField.vue` (pasek, `activeFilters` =
 * `list.params.filters`) i `Filter.vue` (popover, `activeFilters` =
 * `list.value?.params?.filters`) -- ten sam wzorzec co `opcjeEtapuFiltra`
 * dla Etapu, tylko zamiast zawężać STATYCZNĄ listę opcji, zwraca parametr,
 * który front wysyła do serwera (QuickFilterCheckList.vue), żeby TO SERWER
 * zawęził listę.
 *
 * Nie mutuje `activeFilters` (immutability, coding-style.md).
 *
 * @param {{volteo_wartosci?: {zalezy_od: string}}|null|undefined} field
 * @param {Object} activeFilters
 * @returns {string[]}
 */
export function zaleznaWartoscFiltraSerwera(field, activeFilters) {
  const konfiguracja = field?.volteo_wartosci
  if (!konfiguracja) return []
  return rozpakujWartoscFiltraSzybkiego(activeFilters?.[konfiguracja.zalezy_od])
}

/**
 * Buduje listę opcji "Dodaj filtr" do edycji paska szybkich filtrów
 * (`ViewControls.vue`, issue #219): zwęża pełną listę pól doctype'u
 * (`getMeta(doctype).getFields()`) do tych, które mają etykietę, mieszczą
 * się w `dozwolonePola` (lista nazw pól z uprawnieniem odczytu,
 * `crm.api.doc.pola_dozwolone` -- `null`/`undefined`, dopóki się ładuje,
 * oznacza "jeszcze nie wiadomo", stąd ostrożny fallback do
 * `!pole.permlevel`, ten sam wzorzec co `ColumnSettings.vue`'s `fields`
 * computed) i nie są już na pasku (`istniejaceNaPasku`, tablica
 * fieldnames).
 *
 * Zanim ten moduł istniał, edytor paska pokazywał WSZYSTKIE pola
 * doctype'u bez żadnego filtra uprawnień -- bezpieczne, dopóki edycję
 * widział tylko manager (`isManager()`), ale od issue #219 każdy
 * użytkownik może otworzyć edytor swojego WŁASNEGO paska, więc pole
 * permlevel > 0 (np. koszty/prowizje na `CRM Deal`) nie powinno się tam
 * już pojawiać dla handlowca.
 *
 * Zwraca opcje w kształcie `{label, value, fieldtype}` (kształt, jakiego
 * oczekuje `Autocomplete.vue`) -- etykieta pseudo-pola "name" zostaje po
 * stronie wołającego (ten moduł jest frappe-free, nie wywołuje `__()`, patrz
 * nagłówek pliku).
 *
 * Nie mutuje `polaDoctype`/`istniejaceNaPasku` (immutability).
 *
 * @param {Array<{fieldname:string,label?:string,fieldtype?:string,permlevel?:number}>|null|undefined} polaDoctype
 * @param {string[]|null|undefined} dozwolonePola
 * @param {string[]|null|undefined} istniejaceNaPasku
 * @returns {Array<{label:string,value:string,fieldtype:string}>}
 */
export function opcjeDodaniaFiltraSzybkiego(polaDoctype, dozwolonePola, istniejaceNaPasku) {
  const pola = Array.isArray(polaDoctype) ? polaDoctype : []
  const istniejace = new Set(
    Array.isArray(istniejaceNaPasku) ? istniejaceNaPasku : [],
  )

  const dostepne = Array.isArray(dozwolonePola)
    ? pola.filter((pole) => dozwolonePola.includes(pole.fieldname))
    : pola.filter((pole) => !pole.permlevel)

  return dostepne
    .filter((pole) => pole.label)
    .filter((pole) => !istniejace.has(pole.fieldname))
    .map((pole) => ({
      label: pole.label,
      value: pole.fieldname,
      fieldtype: pole.fieldtype,
    }))
}
