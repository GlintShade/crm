// Zawężanie filtra „Etap” (pole `status` na `CRM Deal`) do procesu wybranej
// linii produktowej — filtr rozwijany (Filter.vue) i pasek filtrów szybkich
// (QuickFilterField.vue) na liście szans. Ten sam zabieg, co formularz
// szansy już robi (`grupaForRodzaj`/`filterKnown` w `dealPipeline.js`, patrz
// `pages/Deal.vue`), tylko po stronie filtra „Rodzaj umowy”
// (`custom_rodzaj_umowy`) zamiast po stronie dokumentu.
//
// Frappe-free (bez importu `frappe-ui` / `@/` poza `./dealPipeline`) — testowalne
// bezpośrednio przez vitest, ten sam wzorzec co dealPipeline.js/etykietaMoje.js.
//
// PUŁAPKA (eager chunk, patrz etykietaMoje.js): żadnego `__()` na poziomie
// modułu — tylko wewnątrz funkcji / `script setup`. Ten plik w ogóle nie
// woła `__()` — etykiety opcji to gołe nazwy statusów (już polskie w bazie),
// a nazwy grup ("OZE" / "Czyste Powietrze" / "Inne") tłumaczy dopiero
// wołający, jeśli chce (patrz Filter.vue / QuickFilterField.vue).

import { filterKnown } from './dealPipeline'

const RODZAJE_UMOWY_OZE = new Set([
  'Fotowoltaika',
  'Fotowoltaika + Magazyn',
  'Magazyn energii',
])
const RODZAJ_UMOWY_CP = 'Czyste Powietrze'

/**
 * Klucz procesu ('OZE'/'CP') dla pojedynczej wartości `custom_rodzaj_umowy`,
 * albo `null` gdy wartość nie należy do żadnego procesu (nieustawiona/
 * nierozpoznana — np. stary bundle albo literówka).
 *
 * @param {string} rodzaj
 * @returns {'OZE'|'CP'|null}
 */
function procesKluczDlaRodzaju(rodzaj) {
  if (RODZAJE_UMOWY_OZE.has(rodzaj)) return 'OZE'
  if (rodzaj === RODZAJ_UMOWY_CP) return 'CP'
  return null
}

/**
 * Rozpakowuje wartość filtra „Rodzaj umowy" (`list.value?.params?.filters?.custom_rodzaj_umowy`)
 * do tablicy kandydujących wartości rodzaju, albo `null` gdy filtr jest
 * pusty/nierozpoznanego kształtu. Operator `equals`/`=` (Frappe API zwraca
 * jawną parę `[operator, value]`, ale filtr bywa też zapisany jako goły
 * string, gdy to jedyna wartość) i `in` (para `[operator, [wartości]]`) —
 * inne operatory (np. `not equals`, `not in`, `like`) traktowane jak brak
 * filtra (zawężenie nie ma sensu dla wykluczeń), stąd `null`.
 *
 * @param {string|[string, string]|[string, string[]]|null|undefined} rodzajFilter
 * @returns {string[]|null}
 */
function wartosciFiltraRodzaju(rodzajFilter) {
  if (typeof rodzajFilter === 'string') {
    return rodzajFilter ? [rodzajFilter] : null
  }
  if (Array.isArray(rodzajFilter)) {
    const [operator, wartosc] = rodzajFilter
    if (operator === '=' || operator === 'equals') {
      return wartosc ? [wartosc] : null
    }
    if (operator === 'in') {
      return Array.isArray(wartosc) && wartosc.length > 0 ? wartosc : null
    }
  }
  return null
}

/**
 * Grupa statusów procesu (proces plus statusy terminalne, w kolejności
 * procesu) odpowiadająca aktywnemu filtrowi „Rodzaj umowy" — albo `null`,
 * gdy zawężenie się nie da: filtr pusty/nierozpoznany, wartość rodzaju
 * nieznana, albo (dla operatora `in`) wartości należą do RÓŻNYCH procesów
 * (np. OZE + Czyste Powietrze naraz — nie ma jednego procesu do pokazania).
 * `null` to sygnał "brak zawężenia" dla wołającego (`opcjeEtapu` poniżej
 * spada wtedy na pełną, pogrupowaną listę), ten sam konwencja co pusta
 * tablica w `grupaForRodzaj` (dealPipeline.js).
 *
 * @param {Object<string, string[]>|null|undefined} grupy - `{ [rodzaj]: string[] }`, kształt `crm.api.pipeline.volteo_pipeline_grupy`
 * @param {string|[string, string]|[string, string[]]|null|undefined} rodzajFilter - wartość filtra `custom_rodzaj_umowy`, string („=" domyślne) albo para `[operator, wartość]`
 * @returns {string[]|null}
 */
export function procesDlaFiltraRodzaju(grupy, rodzajFilter) {
  if (!grupy) return null

  const wartosci = wartosciFiltraRodzaju(rodzajFilter)
  if (!wartosci) return null

  const klucze = wartosci.map(procesKluczDlaRodzaju)
  if (klucze.some((klucz) => klucz === null)) return null
  if (!klucze.every((klucz) => klucz === klucze[0])) return null

  return grupy[wartosci[0]] || null
}

/**
 * Jedna z trzech (identycznych w danych z backendu — `crm.volteo_pipeline`
 * gwarantuje ten sam `PIPELINE_OZE` + terminale dla każdego wariantu OZE)
 * grup OZE w `grupy` — którakolwiek jest obecna, w kolejności preferencji
 * pierwszej opcji Select (`Fotowoltaika`).
 *
 * @param {Object<string, string[]>|null|undefined} grupy
 * @returns {string[]}
 */
function grupaOze(grupy) {
  if (!grupy) return []
  return (
    grupy['Fotowoltaika'] ||
    grupy['Fotowoltaika + Magazyn'] ||
    grupy['Magazyn energii'] ||
    []
  )
}

/**
 * @param {string} name
 * @returns {{label: string, value: string}}
 */
function doOpcji(name) {
  return { label: name, value: name }
}

/**
 * Opcje dla kontrolki filtra „Etap" (`Autocomplete`, patrz `Autocomplete.vue`
 * — obsługuje zarówno płaską listę `[{label,value}]`, jak i pogrupowaną
 * `[{group, items}]`).
 *
 * Gdy filtr „Rodzaj umowy" zawęża do jednego procesu
 * ({@link procesDlaFiltraRodzaju} zwraca niepustą grupę): płaska lista, w
 * kolejności procesu.
 *
 * Bez zawężenia (rodzaj nieustawiony/nierozpoznany/mieszany): pogrupowana
 * lista OZE / Czyste Powietrze / Inne — „Inne" to znane statusy spoza obu
 * procesów (np. status dodany ręcznie w Desk, poza `crm.volteo_pipeline`),
 * dołączana WYŁĄCZNIE gdy niepusta. `wszystkieStatusy` (pełna lista nazw
 * znanych statusów, np. `dealStatuses.data.map(s => s.name)` ze
 * `stores/statuses.js`) jest tu potrzebna właśnie do wyliczenia „Inne" —
 * ani `grupy`, ani sam predykat `isKnown` nie umożliwiają wyliczenia
 * dopełnienia (predykat odpowiada tylko "tak/nie" dla podanej nazwy, nie
 * umie wymienić wszystkich znanych nazw).
 *
 * Wszystkie trzy grupy przechodzą przez {@link filterKnown} (dealPipeline.js:199)
 * — nazwa nieobecna jeszcze w załadowanym store statusów (wyścig zimnego
 * ładowania) nie trafia do opcji zamiast dawać zepsuty wpis.
 *
 * @param {Object<string, string[]>|null|undefined} grupy - kształt `crm.api.pipeline.volteo_pipeline_grupy`
 * @param {string|[string, string]|[string, string[]]|null|undefined} rodzajFilter - wartość filtra `custom_rodzaj_umowy`
 * @param {(name: string) => boolean} isKnown - predykat "czy nazwa statusu jest znana załadowanemu store'owi" (patrz `dealStatuses` w `stores/statuses.js`)
 * @param {string[]} [wszystkieStatusy] - pełna lista nazw znanych statusów, tylko do wyliczenia grupy „Inne" bez rodzaju
 * @returns {Array<{label: string, value: string}>|Array<{group: string, items: Array<{label: string, value: string}>}>}
 */
export function opcjeEtapu(grupy, rodzajFilter, isKnown, wszystkieStatusy = []) {
  const proces = procesDlaFiltraRodzaju(grupy, rodzajFilter)
  if (proces) {
    return filterKnown(proces, isKnown).map(doOpcji)
  }

  const oze = filterKnown(grupaOze(grupy), isKnown)
  const cp = filterKnown(grupy?.[RODZAJ_UMOWY_CP], isKnown)
  const wProcesie = new Set([...oze, ...cp])
  const inne = filterKnown(wszystkieStatusy, isKnown).filter(
    (name) => !wProcesie.has(name),
  )

  const wynik = [
    { group: 'OZE', items: oze.map(doOpcji) },
    { group: 'Czyste Powietrze', items: cp.map(doOpcji) },
  ]
  if (inne.length > 0) {
    wynik.push({ group: 'Inne', items: inne.map(doOpcji) })
  }
  return wynik
}
