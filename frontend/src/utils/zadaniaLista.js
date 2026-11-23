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

// ops#411: osoby "Do wiadomosci" na liscie zadan.

/**
 * Tekst kolumny "Do wiadomosci": do dwoch nazwisk, reszta jako "+N"
 * ("Jan Kowalski, Anna Nowak +2"). Pusta lista daje pusty tekst.
 *
 * @param {string[]} nazwiska pelne nazwy osob (kolejnosc z serwera)
 * @returns {string}
 */
export function tekstDoWiadomosci(nazwiska) {
  const lista = (Array.isArray(nazwiska) ? nazwiska : []).filter(Boolean)
  const reszta = lista.length - 2
  const poczatek = lista.slice(0, 2).join(', ')
  return reszta > 0 ? `${poczatek} +${reszta}` : poczatek
}

const KLUCZE_ROL = ['assigned_to', '_dw', '_rola_ja']

function czyMoje(wartosc, ja) {
  if (wartosc === ja) return true
  return (
    Array.isArray(wartosc) &&
    ((wartosc[0] === '=' && wartosc[1] === ja) ||
      (String(wartosc[0]).toLowerCase() === 'in' &&
        Array.isArray(wartosc[1]) &&
        wartosc[1].length === 1 &&
        wartosc[1][0] === ja))
  )
}

/**
 * Stan dwoch szybkich filtrow rol z filtrow listy: `moje` (jestem osoba
 * odpowiedzialna) i `dw` (jestem w "Do wiadomosci"). Suma obu to jeden filtr
 * serwera `_rola_ja`, wiec tez zapala oba przyciski.
 *
 * @param {object} filtry biezace filtry listy
 * @param {string} ja login biezacego uzytkownika
 * @returns {{moje: boolean, dw: boolean}}
 */
export function stanRol(filtry, ja) {
  const f = filtry || {}
  if (!ja) return { moje: false, dw: false }
  if (f._rola_ja) return { moje: true, dw: true }
  return { moje: czyMoje(f.assigned_to, ja), dw: czyMoje(f._dw, ja) }
}

/**
 * NOWY obiekt filtrow z filtrami rol ustawionymi wg `moje` i `dw` (inne filtry
 * zostaja). Tylko "moje": `assigned_to = ja`; tylko "dw": `_dw = ja`; oba: jeden
 * filtr `_rola_ja` (serwer bierze biezacego uzytkownika z sesji, wartosc `1`
 * jest tylko znacznikiem), bo suma "albo" nie da sie zapisac jako dwa filtry
 * laczone "i". Zadne: bez filtrow rol. Nie mutuje argumentu.
 *
 * @param {object} filtry biezace filtry listy
 * @param {string} ja login biezacego uzytkownika
 * @param {{moje: boolean, dw: boolean}} stan zadany stan przyciskow
 * @returns {object}
 */
export function filtryDlaRol(filtry, ja, { moje, dw }) {
  const kopia = { ...(filtry || {}) }
  KLUCZE_ROL.forEach((k) => delete kopia[k])
  if (moje && dw) kopia._rola_ja = 1
  else if (moje) kopia.assigned_to = ja
  else if (dw) kopia._dw = ja
  return kopia
}
