// Logika listy Zadan (`/crm/tasks`, Tasks.vue + TasksListView.vue), ops#357:
// oznaczanie zadan po terminie (wariant B: caly wiersz na czerwono) i zakladki
// Aktywne / Wykonane / Anulowane jako zwykly filtr statusu.
//
// Frappe-free (bez importu `__`, `frappe-ui`, dayjs ani `@/utils`), ten sam
// wzorzec co dataPolska.js i zadania.js: testowalne bezposrednio przez vitest.
// Termin parsowany regexem (lustro WZORZEC_DATY_CZASU z dataPolska.js), nigdy
// `new Date(string)`, bo to zinterpretowaloby tekst jako UTC i przesunelo
// godzine.

// Statusy koncowe: zadanie zamkniete nie jest "po terminie", nawet gdy termin minal.
const STATUSY_KONCOWE = ['Done', 'Canceled']

const MS_NA_DOBE = 86400000

// `YYYY-MM-DD HH:mm[:ss[.ffffff]]`, separator spacja albo `T`. Frappe zwraca
// Datetime z mikrosekundami ("2026-11-13 09:00:00.000000").
const WZORZEC_TERMINU =
  /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/

/**
 * Rozbiera termin na skladniki zegara scianowego (czas lokalny) i zwraca je jako
 * "naiwne" milisekundy UTC. Dzieki temu roznica dwoch takich wartosci liczy dni
 * kalendarzowo, bez przesuniec przy zmianie czasu (DST).
 *
 * @returns {number|null} null dla pustego lub niepoprawnego wejscia
 */
function naiwneMsTerminu(dueDate) {
  if (typeof dueDate !== 'string') return null
  const d = WZORZEC_TERMINU.exec(dueDate)
  if (!d) return null
  const [rok, miesiac, dzien, godzina, minuta] = [
    d[1],
    d[2],
    d[3],
    d[4],
    d[5],
  ].map(Number)
  const sekunda = d[6] === undefined ? 0 : Number(d[6])
  if (miesiac < 1 || miesiac > 12 || dzien < 1 || dzien > 31) return null
  if (godzina > 23 || minuta > 59 || sekunda > 59) return null
  const ms = Date.UTC(rok, miesiac - 1, dzien, godzina, minuta, sekunda)
  // Odrzuca daty nieistniejace (np. 31 lutego), ktore Date przesuwa po cichu.
  const z = new Date(ms)
  if (
    z.getUTCFullYear() !== rok ||
    z.getUTCMonth() !== miesiac - 1 ||
    z.getUTCDate() !== dzien
  ) {
    return null
  }
  return ms
}

function naiwneMsTeraz(teraz) {
  if (!(teraz instanceof Date) || Number.isNaN(teraz.getTime())) return null
  return Date.UTC(
    teraz.getFullYear(),
    teraz.getMonth(),
    teraz.getDate(),
    teraz.getHours(),
    teraz.getMinutes(),
    teraz.getSeconds(),
  )
}

/** Ile milisekund (czasu scianowego) temu minal termin; null gdy brak terminu, blad albo termin w przyszlosci. */
function msPoTerminie(dueDate, teraz) {
  const termin = naiwneMsTerminu(dueDate)
  const dzis = naiwneMsTeraz(teraz)
  if (termin === null || dzis === null) return null
  const roznica = dzis - termin
  return roznica > 0 ? roznica : null
}

/**
 * Zadanie jest po terminie, gdy termin (pelna data i godzina, czas lokalny)
 * minal i status nie jest koncowy (Done, Canceled).
 *
 * @param {string} dueDate surowy Datetime z Frappe
 * @param {string} status status zadania (angielska wartosc z bazy)
 * @param {Date} [teraz]
 * @returns {boolean}
 */
export function czyPrzeterminowane(dueDate, status, teraz = new Date()) {
  if (STATUSY_KONCOWE.includes(status)) return false
  return msPoTerminie(dueDate, teraz) !== null
}

/**
 * Dopisek pod data terminu: 'po terminie' dla mniej niz pelnej doby,
 * '1 dzień po terminie', 'N dni po terminie'. Pusty string, gdy termin nie minal
 * albo jest niepoprawny. Nie zna statusu: o pokazaniu dopisku decyduje
 * `czyPrzeterminowane`.
 *
 * @param {string} dueDate surowy Datetime z Frappe
 * @param {Date} [teraz]
 * @returns {string}
 */
export function tekstPoTerminie(dueDate, teraz = new Date()) {
  const ms = msPoTerminie(dueDate, teraz)
  if (ms === null) return ''
  const dni = Math.floor(ms / MS_NA_DOBE)
  if (dni < 1) return 'po terminie'
  if (dni === 1) return '1 dzień po terminie'
  return `${dni} dni po terminie`
}

// Zakladki nad lista: kazda to zwykly filtr statusu (widoczny w szybkim filtrze
// Status i w oknie Filtr), nie osobny stan.
export const ZAKLADKI_ZADAN = [
  {
    klucz: 'aktywne',
    etykieta: 'Aktywne',
    status: ['in', ['Todo', 'In Progress']],
  },
  { klucz: 'wykonane', etykieta: 'Wykonane', status: 'Done' },
  { klucz: 'anulowane', etykieta: 'Anulowane', status: 'Canceled' },
]

function listaWartosci(wartosc) {
  if (Array.isArray(wartosc)) return wartosc
  if (typeof wartosc === 'string')
    return wartosc.split(',').map((s) => s.trim())
  return null
}

function tenSamZbior(a, b) {
  const sa = new Set(a)
  const sb = new Set(b)
  return sa.size === sb.size && [...sa].every((x) => sb.has(x))
}

/**
 * Klucz zakladki odpowiadajacej filtrowi statusu albo null (inny filtr, brak filtra).
 * 'Done' daje wykonane, 'Canceled' anulowane, ['in', [...]] z dokladnie zbiorem
 * {Todo, In Progress} (dowolna kolejnosc) daje aktywne.
 *
 * @param {*} filtrStatusu wartosc `filters.status` z parametrow listy
 * @returns {string|null}
 */
export function zakladkaZFiltra(filtrStatusu) {
  if (filtrStatusu === 'Done') return 'wykonane'
  if (filtrStatusu === 'Canceled') return 'anulowane'
  if (Array.isArray(filtrStatusu) && filtrStatusu[0] === 'in') {
    const wartosci = listaWartosci(filtrStatusu[1])
    const aktywne = ZAKLADKI_ZADAN[0].status[1]
    if (wartosci && tenSamZbior(wartosci, aktywne)) return 'aktywne'
  }
  return null
}

/**
 * NOWY obiekt filtrow z podmienionym `status` na filtr zakladki. Nie mutuje
 * argumentu; nieznany klucz zakladki zwraca sama kopie filtrow.
 *
 * @param {object} filtry biezace filtry listy
 * @param {string} klucz klucz zakladki (aktywne, wykonane, anulowane)
 * @returns {object}
 */
export function filtryDlaZakladki(filtry, klucz) {
  const kopia = { ...(filtry || {}) }
  const zakladka = ZAKLADKI_ZADAN.find((z) => z.klucz === klucz)
  if (!zakladka) return kopia
  kopia.status = Array.isArray(zakladka.status)
    ? [zakladka.status[0], [...zakladka.status[1]]]
    : zakladka.status
  return kopia
}
