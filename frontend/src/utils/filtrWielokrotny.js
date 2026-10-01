// Logika czysta (bez importu frappe-ui / @) dla operatora "jest jednym z"
// (in / not in) w Filter.vue, przy polach typu Select i Link, obsługiwanych
// kontrolką wielokrotnego wyboru (frappe-ui MultiSelect) zamiast pola
// tekstowego z wartościami po przecinku (issue #103).
//
// Serializacja filtra do backendu i zapisanych widoków NIE zmienia się:
// wartość operatora in/not in to tablica stringów, dokładnie jak dotychczas
// po splicie po przecinku w Filter.vue::transformIn. Ten moduł tylko
// normalizuje wartość używaną jako `modelValue` kontrolki wielokrotnego
// wyboru (bez względu na to, czy przyszła jako tablica z zapisanego widoku,
// czy jako string sprzed tej zmiany) i scala listę opcji z aktualnie
// zaznaczonymi wartościami, żeby zaznaczenie było widoczne nawet zanim/gdy
// wyszukiwanie (Link) zawęzi listę wyników i akurat pominie już wybraną
// wartość.
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js / etykietaMoje.js: eager chunk wywołuje moduł przed
// zainicjowaniem i18n), testowalne bezpośrednio przez vitest.

import { czyPoleTagow } from './tagiProduktow'

/**
 * Normalizuje wartość filtra in/not in do tablicy niepustych stringów.
 * Przyjmuje zarówno tablicę (kształt zapisany przez transformIn / wczytany
 * z zapisanego widoku, np. `["in", ["Nowy", "Próba kontaktu"]]`), jak i
 * string sprzed tej zmiany (wartości rozdzielone przecinkiem, z polem
 * tekstowym): dla kompatybilności wstecz z dowolnym stanem `f.value`
 * napotkanym w locie. Wartości są przycinane (`trim`), puste odrzucane.
 */
export function parsujWartoscWielokrotna(value) {
  if (Array.isArray(value)) {
    return value
      .map((v) => String(v ?? '').trim())
      .filter((v) => v.length > 0)
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0)
  }
  return []
}

/**
 * Scala listę opcji (katalog Select albo wyniki wyszukiwania Link) z
 * aktualnie zaznaczonymi wartościami: każda zaznaczona wartość, która nie
 * jest (już/jeszcze) w `opcje`, dostaje opcję zastępczą `{ label: wartość,
 * value: wartość }`, dołączaną na końcu listy. Zachowuje kolejność `opcje`
 * i nie duplikuje wartości już tam obecnych.
 */
export function scalOpcjeZZaznaczonymi(opcje, zaznaczoneWartosci) {
  const listaOpcji = Array.isArray(opcje) ? opcje : []
  const listaZaznaczonych = parsujWartoscWielokrotna(zaznaczoneWartosci)
  const znaneWartosci = new Set(listaOpcji.map((opcja) => opcja.value))
  const brakujace = listaZaznaczonych
    .filter((wartosc) => !znaneWartosci.has(wartosc))
    .map((wartosc) => ({ label: wartosc, value: wartosc }))
  return [...listaOpcji, ...brakujace]
}

/**
 * Rozstrzyga, czy dana kombinacja pola i operatora dostaje w Filter.vue
 * kontrolkę wielokrotnego wyboru (MultiSelect dla Select, LinkMultiSelect
 * dla Link) zamiast pola tekstowego z wartościami po przecinku (issue
 * #103). Prawda dokładnie dla operatorów "in"/"not in" na polu Select albo
 * na polu Link, z JEDNYM wyłączeniem:
 *   - Dynamic Link: docelowy doctype zmienia się per wiersz, nie ma jednego
 *     stałego katalogu do przeszukania przez search_link.
 *
 * Issue #214 (2026-10-01, decyzja właściciela): pola Link do User (np.
 * lead_owner, custom_cc, deal_owner, custom_opiekun, _assign) dostają od
 * teraz TĘ SAMĄ kontrolkę wielokrotnego wyboru co każdy inny Link --
 * wcześniej były tu wyłączone, bo LinkMultiSelect/QuickFilterCheckList
 * pytały `frappe.desk.search.search_link` wprost, z pominięciem zakresu,
 * który dla pól User nakłada Link.vue (`userScope`,
 * `crm.api.volteo_uzytkownicy.widoczni_uzytkownicy`). Oba komponenty dostały
 * ten sam zakres (i opcję "@me") z nowego, wspólnego modułu
 * `utils/zakresUzytkownikow.js` -- patrz jego JSDoc -- więc wyłączenie
 * przestało być potrzebne. Zawężenie listy osób to nadal wyłącznie
 * ergonomia UI, nie granica uprawnień (patrz brief issue #214): widoczność
 * rekordów pilnują hooki `crm/permissions/*`, nie ta funkcja.
 *
 * Frappe-free: przyjmuje `field` w kształcie `{ fieldtype, options }` (ten
 * sam kształt, co `f.field` w Filter.vue), żadnej zależności od Vue ani
 * komponentów.
 *
 * Issue ops#150: pole "produktów leada" (tagów, `czyPoleTagow` w
 * `utils/tagiProduktow.js`) dostaje TĘ SAMĄ kontrolkę wielokrotnego wyboru
 * mimo `fieldtype === 'Data'`, nie 'Select' -- model A+ z briefu ops#150
 * celowo nie zmienia typu pola, więc rozpoznanie idzie przez osobną flagę
 * (`field.volteo_tagi`, dołożoną przez `crm.api.doc.get_filterable_fields`/
 * `get_quick_filters`) zamiast przez fieldtype.
 *
 * Issue #218: pole z wartościami pobieranymi z serwera (np. `custom_powiat`
 * na `CRM Lead`, zawężony do aktywnego filtra województwa) dostaje TĘ SAMĄ
 * kontrolkę z dokładnie tego samego powodu co pole tagów -- `field.fieldtype`
 * zostaje `'Data'` bez zmian, rozpoznanie idzie przez osobną flagę
 * (`field.volteo_wartosci`, ten sam kształt dołożenia co `volteo_tagi`, patrz
 * `crm.api.doc._dolacz_wartosci_serwera_lead`). Front NIE zna nazwy pola ani
 * adresu endpointu na sztywno -- rozpoznaje WYŁĄCZNIE obecność tej flagi.
 */
export function czyWielokrotnyWybor(field, operator) {
  if (!field) return false
  if (!['in', 'not in'].includes(operator)) return false
  if (field.fieldtype === 'Select') return true
  if (field.fieldtype === 'Link') return true
  if (czyPoleTagow(field)) return true
  if (field.volteo_wartosci) return true
  return false
}

/**
 * Operator domyślny wymuszony przez wielokrotny wybór (issue #215, decyzja
 * właściciela 2026-10-01): każde pole, dla którego
 * `czyWielokrotnyWybor(field, 'in')` zwraca prawdę (Select, Link poza
 * Dynamic Link, pola tagów -- patrz jej JSDoc), ma od razu otwierać listę
 * checkboxów z operatorem "jest jednym z" zamiast pojedynczej wartości
 * ("równa się"/"zawiera"), bez konieczności ręcznej zmiany operatora.
 *
 * Zwraca `'in'`, gdy wielokrotny wybór ma zastosowanie, albo `null`, gdy
 * wołający (Filter.vue::getDefaultOperator) ma zdecydować sam na
 * podstawie `fieldtype` -- `null`, nie `'equals'`/`'like'`, bo ta funkcja
 * nie zna reszty drabinki fieldtype'ów (Check/Number/Date/...) i nie
 * powinna jej duplikować.
 *
 * Frappe-free, ten sam kształt `field` co `czyWielokrotnyWybor`.
 *
 * @param {{fieldtype: string, options?: string}|null|undefined} field
 * @returns {'in'|null}
 */
export function domyslnyOperatorWielokrotny(field) {
  return czyWielokrotnyWybor(field, 'in') ? 'in' : null
}

/**
 * Wartość domyślna filtra, ZALEŻNA OD OPERATORA (naprawa regresji po
 * #215, zgłoszona w #218): `czyWielokrotnyWybor(field, operator)` zwraca
 * prawdę WYŁĄCZNIE dla operatorów "in"/"not in" -- dla każdego innego
 * operatora (np. "equals" na Select, "like" na Link/polu z wartościami z
 * serwera) wartość domyślna musi wrócić do skalarnych wartości sprzed
 * #215, a nie zostać przy pustej tablicy.
 *
 * `Filter.vue::updateOperator` wołał dotychczas `getDefaultValue(field)`
 * (bez operatora) w gałęzi "każdy inny operator", a `getDefaultValue`
 * sama w sobie sprawdzała WYŁĄCZNIE `domyslnyOperatorWielokrotny(field)`
 * (operator na sztywno `'in'`, patrz jej JSDoc) -- więc pole z
 * wielokrotnym wyborem (Select/Link/tagi/wartości z serwera) dostawało
 * `[]` przy PRZEŁĄCZENIU na "equals"/"like" zamiast właściwej skalarnej
 * wartości (pierwsza opcja Select, pusty string dla reszty), a
 * `transformIn`/kontrolka tekstowa dostawały tablicę zamiast stringa.
 *
 * Reguła (ta sama drabina co `Filter.vue::getDefaultValue` sprzed #215):
 *   - `czyWielokrotnyWybor(field, operator)` prawda -> `[]`;
 *   - fieldtype `'Select'` -> `pierwszaOpcja` (pierwszy element
 *     `field.options.split('\n')`, policzony przez wołającego -- ten
 *     moduł nie zna żadnej logiki UI rozbijania opcji, tylko przyjmuje
 *     gotową wartość) albo `''`, gdy `pierwszaOpcja` nie podano;
 *   - fieldtype `'Check'` -> `'Yes'`;
 *   - fieldtype `'Date'`/`'Datetime'` -> `null`;
 *   - każdy inny fieldtype (Link, Data, Int, Currency...) -> `''`
 *     (dotychczasowe pole tekstowe z wartością po przecinku).
 *
 * Pola tagów (`czyPoleTagow`) z operatorem `OPERATOR_TAGOW`
 * (`"volteo_tagi"`, kształt złożony `{ma, nie_ma}`) są świadomie POZA
 * zakresem tej funkcji -- `Filter.vue::updateOperator` ma dla nich
 * własną, wcześniejszą gałąź (zamiana kształtu wartości między
 * in/not in/volteo_tagi), niezmienioną tą poprawką.
 *
 * Frappe-free, ten sam kształt `field` co `czyWielokrotnyWybor`.
 *
 * @param {{fieldtype: string, options?: string}|null|undefined} field
 * @param {string} operator
 * @param {string} [pierwszaOpcja] pierwsza opcja Select (`field.options.split('\n')[0]`), policzona przez wołającego
 * @returns {string[]|string|null}
 */
export function domyslnaWartoscFiltra(field, operator, pierwszaOpcja) {
  if (!field) return ''
  if (czyWielokrotnyWybor(field, operator)) {
    return []
  }
  if (field.fieldtype === 'Select') {
    return pierwszaOpcja ?? ''
  }
  if (field.fieldtype === 'Check') {
    return 'Yes'
  }
  if (['Date', 'Datetime'].includes(field.fieldtype)) {
    return null
  }
  return ''
}
