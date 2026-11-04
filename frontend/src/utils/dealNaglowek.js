// Czysta logika nagłówka szansy (DealNaglowek.vue): czas w etapie, odmiana
// "etapy", teksty paska etapów. Bez importów frappe/Vue, testowalna wprost.

/**
 * Polska odmiana "N etap/etapy/etapów".
 *
 * @param {number} n
 * @returns {string}
 */
export function etapyLiczba(n) {
  const k = Math.abs(n)
  const ostatnie = k % 10
  const ostatnieDwie = k % 100
  let slowo = 'etapów'
  if (k === 1) slowo = 'etap'
  else if (ostatnie >= 2 && ostatnie <= 4 && !(ostatnieDwie >= 12 && ostatnieDwie <= 14)) slowo = 'etapy'
  return `${n} ${slowo}`
}

function parsujData(wartosc) {
  if (!wartosc) return null
  const d = wartosc instanceof Date ? wartosc : new Date(String(wartosc).replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * Moment wejścia w bieżący status z tabeli `status_change_log` szansy.
 * Ostatni wiersz z `from` równym statusowi niesie `from_date` (początek etapu).
 *
 * @param {Array<{from?: string, from_date?: string}>|null|undefined} log
 * @param {string|null|undefined} status
 * @returns {Date|null}
 */
export function poczatekEtapu(log, status) {
  if (!Array.isArray(log) || !status) return null
  for (let i = log.length - 1; i >= 0; i--) {
    const wpis = log[i]
    if (wpis && wpis.from === status) return parsujData(wpis.from_date)
  }
  return null
}

/**
 * Pełne dni kalendarzowe od `od` do `teraz`; null, gdy brak daty.
 *
 * @param {Date|null} od
 * @param {Date} [teraz]
 * @returns {number|null}
 */
export function dniWEtapie(od, teraz = new Date()) {
  if (!od) return null
  const dzien = (d) => Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
  return Math.max(0, Math.round((dzien(teraz) - dzien(od)) / 86400000))
}

/**
 * "dziś", "1 dzień", "N dni"; null, gdy czas nieznany.
 *
 * @param {number|null|undefined} dni
 * @returns {string|null}
 */
export function formatCzasWEtapie(dni) {
  if (dni === null || dni === undefined || Number.isNaN(dni)) return null
  if (dni <= 0) return 'dziś'
  if (dni === 1) return '1 dzień'
  return `${dni} dni`
}

/**
 * Czas w bieżącym etapie z logu zmian statusu, gotowy do pokazania.
 *
 * @param {Array|null|undefined} log
 * @param {string|null|undefined} status
 * @param {Date} [teraz]
 * @returns {string|null}
 */
export function czasWEtapie(log, status, teraz = new Date()) {
  return formatCzasWEtapie(dniWEtapie(poczatekEtapu(log, status), teraz))
}

/**
 * Nazwa statusu do etykiety w UI: typograficzne myślniki zamienione na zwykły
 * łącznik (sama nazwa zapisana w bazie zostaje nietknięta, to tylko wyświetlanie).
 *
 * @param {string|null|undefined} nazwa
 * @returns {string}
 */
export function etykietaStatusu(nazwa) {
  return String(nazwa ?? '').replace(/[\u2013\u2014]/g, '-')
}

/**
 * Czy pasek etapów ma przejść w formę zwartą (etykiety tylko przy bieżącym i
 * następnym etapie, resztę mówi linia tekstu pod paskiem): za dużo etapów
 * (Czyste Powietrze, 12) albo na jeden etap przypada za mało szerokości.
 *
 * @param {number} liczba - liczba etapów procesu
 * @param {number} szerokosc - szerokość kontenera paska w px (0 = jeszcze nieznana)
 * @param {number} [minNaEtap]
 * @param {number} [maxEtapow]
 * @returns {boolean}
 */
export function czyZwarty(liczba, szerokosc, minNaEtap = 90, maxEtapow = 6) {
  if (liczba > maxEtapow) return true
  if (!szerokosc || liczba <= 0) return false
  return szerokosc / liczba < minNaEtap
}

/**
 * Czy pokazać etykietę pod kółkiem etapu `indeks`. W formie pełnej zawsze; w
 * zwartej tylko bieżący i następny etap (przy statusie poza procesem żaden).
 *
 * @param {number} indeks
 * @param {number} biezacy - indeks bieżącego etapu (-1 poza procesem)
 * @param {boolean} zwarty
 * @returns {boolean}
 */
export function etykietaWidoczna(indeks, biezacy, zwarty) {
  if (!zwarty) return true
  if (biezacy < 0) return false
  return indeks === biezacy || indeks === biezacy + 1
}

/**
 * "od dziś", "od 1 dnia", "od N dni"; pusty tekst, gdy czas nieznany.
 *
 * @param {string|null|undefined} czas - wynik formatCzasWEtapie
 * @returns {string}
 */
export function czasOd(czas) {
  if (!czas) return ''
  if (czas === 'dziś') return 'od dziś'
  if (czas === '1 dzień') return 'od 1 dnia'
  return `od ${czas}`
}

/**
 * Linia stanu pod paskiem: "Etap 5 z 12: Wniosek o dotację · od 6 dni".
 *
 * @param {number} biezacy - indeks bieżącego etapu
 * @param {number} liczba - liczba etapów
 * @param {string} nazwa
 * @param {string|null|undefined} czas
 * @returns {string}
 */
export function tekstEtapu(biezacy, liczba, nazwa, czas) {
  const od = czasOd(czas)
  return `Etap ${biezacy + 1} z ${liczba}: ${nazwa}${od ? ` \u00b7 ${od}` : ''}`
}

/**
 * "Dalej: nazwa następnego etapu"; pusty tekst przy ostatnim etapie.
 *
 * @param {Array<{status: string, index: number}>} steps
 * @param {number} biezacy
 * @returns {string}
 */
export function tekstDalej(steps, biezacy) {
  const nast = Array.isArray(steps) ? steps[biezacy + 1] : null
  return nast ? `Dalej: ${nast.status}` : ''
}
