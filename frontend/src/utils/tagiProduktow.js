// Logika czysta (frappe-free/Vue-free) dla modelu "produkty leada jako
// tagi" (issue ops#150, decyzja właściciela 2026-09-16, model A+): pole
// Data (`custom_posiadane_produkty`/`custom_produkt_procesu` na `CRM
// Lead`) zostaje nośnikiem -- string tokenów ze słownika w kanonicznej
// kolejności, złączonych "+", bez wolnego tekstu -- a prezentacja, edycja
// i filtrowanie działają jak na zbiorze tagów.
//
// Kanoniczny słownik (KOLEJNOSC_PRODUKTOW / KOLEJNOSC_PRODUKTOW_PROCESU,
// `crm/volteo_leady_import.py`) NIE jest tu duplikowany: backend dokłada
// go jako `field.options` (string złączony "\n", dokładnie jak dla pola
// Select) i `field.volteo_tagi: 1` do wyników
// `crm.api.doc.get_quick_filters`/`get_filterable_fields` (ops#150 pkt 3)
// -- ten moduł tylko rozpoznaje/rozbija/składa na podstawie tego, co
// przyszło z serwera w `field`.
//
// `NAZWY_POL_TAGOW` poniżej jest jedynym dopuszczalnym wyjątkiem od "bez
// duplikowania słownika w JS": to lista dwóch NAZW PÓL (nie tokenów).
// Powód: `SidePanelLayout.vue` renderuje pole na podstawie definicji
// layoutu (`CRM Fields Layout`), która NIE przechodzi przez
// `get_filterable_fields`/`get_quick_filters` i więc nie niesie
// `field.volteo_tagi` -- bez tego fallbacku panel boczny nie rozpoznałby
// tych dwóch pól jako tagowych wcale. `opcjeTagow` mimo to NIGDY nie
// zgaduje tokenów z tej listy -- zawsze czyta je z `field.options`,
// dostarczonego przez wywołującego (patrz `TagiProduktowInput.vue`, która
// dociąga `options` osobnym zapytaniem do `get_filterable_fields`).
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js/filtrSzybki.js: eager chunk woła moduł przed i18n),
// testowalne bezpośrednio przez vitest.
//
// Issue ops#173: filtr złożony "zawiera i nie zawiera" jednym wierszem na
// pole tagów -- scenariusz właściciela "ma PV, nie ma AUDYT ani ME", nie do
// ułożenia dotychczasowym słownikiem {pole: wartość} (jedno pole = jeden
// warunek). Wire format (poza istniejącymi, które zostają bez zmian):
//   {"custom_posiadane_produkty": ["volteo_tagi", {"ma": ["PV"], "nie_ma": ["AUDYT", "ME"]}]}
// `OPERATOR_TAGOW`/`czyZlozonyFiltrTagow`/`rozpakujZlozonyFiltrTagow`/
// `spakujZlozonyFiltrTagow` poniżej odpowiadają dokładnie
// `crm.volteo_lista_szans.OPERATOR_TAGOW`/`rozpoznaj_filtry_tagu` po
// stronie backendu -- ten sam kształt, ta sama semantyka pustych
// list/kluczy.
import { parsujWartoscWielokrotna } from './filtrWielokrotny'

const NAZWY_POL_TAGOW = new Set([
  'custom_posiadane_produkty',
  'custom_produkt_procesu',
])

export const OPERATOR_TAGOW = 'volteo_tagi'

/**
 * Rozstrzyga, czy `field` jest polem "produktów leada" (tagów): prawda,
 * gdy backend dołożył `field.volteo_tagi` (List/Filter/QuickFilter --
 * `get_filterable_fields`/`get_quick_filters`, ops#150 pkt 3), ALBO gdy
 * `field.fieldname` jest jedną z dwóch znanych nazw (fallback dla
 * kontekstów, które nie przechodzą przez te dwie funkcje, np. panel
 * boczny -- patrz komentarz modułu wyżej).
 */
export function czyPoleTagow(field) {
  if (!field) return false
  return Boolean(field.volteo_tagi) || NAZWY_POL_TAGOW.has(field.fieldname)
}

/**
 * Rozbija string `+`-łączony (`"PV+PC+AUDYT"`) na tablicę tokenów, w
 * kolejności występowania w stringu (NIE kanonicznej -- patrz `zlaczTagi`
 * dla ustawienia w kanonicznej kolejności). Puste segmenty (string pusty,
 * podwójny `+`, białe znaki) odrzucone. Wartość nie będąca stringiem
 * (`null`/`undefined`/inne) -> pusta tablica.
 */
export function rozbijTagi(str) {
  if (typeof str !== 'string') return []
  return str
    .split('+')
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
}

/**
 * Składa listę tokenów z powrotem do stringu `+`-łączonego, w KANONICZNEJ
 * kolejności (`kolejnosc`, np. `opcjeTagow(field)`) -- nie w kolejności
 * `list`. Duplikaty w `list` scalane (Set). Token spoza `kolejnosc` jest
 * pominięty (model A+ zakłada wyłącznie wartości ze słownika, bez
 * wolnego tekstu -- patrz brief ops#150), więc `zlaczTagi` jest też
 * naturalnym filtrem odrzucającym nieznane tokeny, gdyby jakieś dotarły.
 */
export function zlaczTagi(list, kolejnosc) {
  const zbior = new Set(Array.isArray(list) ? list : [])
  const porzadek = Array.isArray(kolejnosc) ? kolejnosc : []
  return porzadek.filter((token) => zbior.has(token)).join('+')
}

/**
 * Zwraca kanoniczną listę tokenów dla `field` (kolejność prezentacji w
 * UI: checkboxy paska szybkich filtrów, opcje MultiSelect w Filter.vue,
 * opcje dodawania w TagiProduktowInput.vue), czytając `field.options`
 * (string złączony "\n", tak jak dla pola Select -- patrz
 * `Filter.vue::getSelectOptions`). Brak `field` albo `options` nie będące
 * stringiem -> pusta tablica (żaden token do zaoferowania).
 */
export function opcjeTagow(field) {
  if (!field || typeof field.options !== 'string' || !field.options) return []
  return field.options
    .split('\n')
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
}

/**
 * Rozstrzyga, czy `raw` (wartość filtra wprost z `list.params.filters`
 * albo z zapisanego widoku) ma kształt złożonego filtra tagów: tablica
 * dwuelementowa, pierwszy element to `OPERATOR_TAGOW` (bez względu na
 * wielkość liter), drugi element to obiekt (nie tablica, nie `null`).
 * Zawartość obiektu (klucze "ma"/"nie_ma") NIE jest tu sprawdzana --
 * `rozpakujZlozonyFiltrTagow` niżej robi to odpornie na śmieci.
 */
export function czyZlozonyFiltrTagow(raw) {
  return Boolean(
    Array.isArray(raw) &&
      String(raw[0]).toLowerCase() === OPERATOR_TAGOW &&
      raw[1] &&
      typeof raw[1] === 'object' &&
      !Array.isArray(raw[1]),
  )
}

/**
 * Rozpakowuje `raw` do `{ ma: string[], nie_ma: string[] }`, niezależnie
 * od tego, w jakim kształcie wartość dotarła: złożonym (`czyZlozonyFiltrTagow`
 * -- oba pola przez `parsujWartoscWielokrotna`, brakujący klucz/śmieci pod
 * "ma"/"nie_ma" dają pustą listę z tej strony), `["in", [...]]` (cała
 * wartość do "ma"), `["not in", [...]]` (cała wartość do "nie_ma"),
 * skalarem/inną tablicą-stringiem (przez `parsujWartoscWielokrotna` do
 * "ma", dla zgodności z dotychczasowym zapisem pola tagów). Każdy inny
 * kształt tablicowy (np. `["like", ...]`) -- śmieci, obie strony puste.
 */
export function rozpakujZlozonyFiltrTagow(raw) {
  if (czyZlozonyFiltrTagow(raw)) {
    return {
      ma: parsujWartoscWielokrotna(raw[1].ma),
      nie_ma: parsujWartoscWielokrotna(raw[1].nie_ma),
    }
  }
  if (Array.isArray(raw)) {
    const operator = String(raw[0] ?? '').toLowerCase()
    if (operator === 'in') {
      return { ma: parsujWartoscWielokrotna(raw[1]), nie_ma: [] }
    }
    if (operator === 'not in') {
      return { ma: [], nie_ma: parsujWartoscWielokrotna(raw[1]) }
    }
    return { ma: [], nie_ma: [] }
  }
  if (typeof raw === 'string') {
    return { ma: parsujWartoscWielokrotna(raw), nie_ma: [] }
  }
  return { ma: [], nie_ma: [] }
}

/**
 * Odwrotność `rozpakujZlozonyFiltrTagow`: pakuje `{ ma, nie_ma }` z powrotem
 * do kształtu przesyłanego do backendu, w najprostszej postaci, jaka
 * niesie tę samą semantykę (zgodność z paskiem szybkim i z zapisanymi
 * widokami sprzed tej zmiany):
 *   - obie strony puste -> `undefined` (wołający usuwa klucz filtra);
 *   - tylko "ma" -> `['in', ma]` (dotychczasowy kształt "jest jednym z");
 *   - tylko "nie_ma" -> `['not in', nie_ma]`;
 *   - obie niepuste -> `[OPERATOR_TAGOW, { ma, nie_ma }]` (kształt złożony,
 *     jedyny, który niesie oba ograniczenia naraz).
 */
export function spakujZlozonyFiltrTagow({ ma, nie_ma } = {}) {
  const listaMa = parsujWartoscWielokrotna(ma)
  const listaNieMa = parsujWartoscWielokrotna(nie_ma)
  if (listaMa.length === 0 && listaNieMa.length === 0) return undefined
  if (listaNieMa.length === 0) return ['in', listaMa]
  if (listaMa.length === 0) return ['not in', listaNieMa]
  return [OPERATOR_TAGOW, { ma: listaMa, nie_ma: listaNieMa }]
}

/**
 * Wariant `spakujZlozonyFiltrTagow` UŻYWANY WYŁĄCZNIE przez
 * `Filter.vue::parseFilters`, NIGDY przez normalizujący wariant powyżej.
 * Powód istnienia dwóch wariantów (issue ops#173, naprawa błędu z klik-testu
 * 2026-09-24): w `Filter.vue` KAŻDA zmiana wartości/operatora woła `apply()`
 * natychmiast, a `filters` (`computed`) jest odtwarzane z powrotem z
 * `list.value.params.filters` przez `convertFilters` po każdym `apply()`.
 * Normalizujący `spakujZlozonyFiltrTagow` -- poprawny dla
 * `ViewControls.vue::applyQuickFilter`, gdzie normalizacja do "in"/"not in"
 * jest pożądanym skrótem dla paska szybkich filtrów -- w `Filter.vue`
 * niszczył jeszcze niedokończony wiersz w locie: obie strony puste (świeżo
 * dodany warunek) dawały `undefined` -> klucz znikał z `p` -> wiersz znikał
 * z ekranu w chwili wyboru operatora "Zawiera i nie zawiera"; tylko jedna
 * strona wypełniona dawała `["in", ma]`/`["not in", nie_ma]` ->
 * `convertFilters` odczytywał to z powrotem jako zwykły operator "in"/"not
 * in", cichy powrót do poprzedniego operatora. Użytkownik nie miał żadnej
 * ścieżki kliknięcia, żeby dotrzeć do obu MultiSelectów naraz. Ten wariant
 * ZAWSZE zwraca kształt złożony -- oba pola przez `parsujWartoscWielokrotna`
 * (puste listy dozwolone, `null`/`undefined`/śmieci -> pusta lista), nigdy
 * `undefined`, nigdy `["in", ...]`/`["not in", ...]` -- więc wiersz
 * przeżywa odtworzenie przez `convertFilters` (patrz `czyZlozonyFiltrTagow`:
 * obiekt, także pusty, jest "prawdziwy") niezależnie od tego, ile pól
 * użytkownik zdążył wypełnić.
 */
export function spakujZlozonyFiltrTagowWprost({ ma, nie_ma } = {}) {
  return [
    OPERATOR_TAGOW,
    { ma: parsujWartoscWielokrotna(ma), nie_ma: parsujWartoscWielokrotna(nie_ma) },
  ]
}
