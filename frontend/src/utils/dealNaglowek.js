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
 * zwartej tylko bieżący etap (następny jest w linii "Dalej" pod paskiem; przy
 * statusie poza procesem żaden).
 *
 * @param {number} indeks
 * @param {number} biezacy - indeks bieżącego etapu (-1 poza procesem)
 * @param {boolean} zwarty
 * @returns {boolean}
 */
export function etykietaWidoczna(indeks, biezacy, zwarty) {
  if (!zwarty) return true
  if (biezacy < 0) return false
  return indeks === biezacy
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

export const WARIANTY_ETAPOW = ['kroki', 'pasek']
export const WARIANT_DOMYSLNY = 'pasek'

/**
 * Wariant widoku etapów z zapisanej wartości; nieznana lub pusta daje domyślny.
 *
 * @param {string|null|undefined} wartosc
 * @returns {'kroki'|'pasek'}
 */
export function normalizujWariant(wartosc) {
  return WARIANTY_ETAPOW.includes(wartosc) ? wartosc : WARIANT_DOMYSLNY
}

/**
 * Klasa wypełnienia segmentu paska etapów według stanu etapu.
 * Kolory jak w pasku listy szans (PasekEtapu.vue): niewypełniony to
 * `bg-surface-gray-3`; wypełnione (zielony dla ukończonych, ten sam niebieski
 * co przycisk dla bieżącego) jak przy kółkach kroków.
 *
 * @param {'done'|'current'|'future'|'muted'} stan
 * @returns {string}
 */
export function segmentKlasa(stan) {
  if (stan === 'done') return 'bg-green-500'
  if (stan === 'current') return 'bg-blue-500'
  return 'bg-surface-gray-3'
}

/**
 * "Etap 3 z 5" (bez nazwy), do lewego bloku wariantu paska.
 *
 * @param {number} biezacy - indeks bieżącego etapu
 * @param {number} liczba
 * @returns {string}
 */
export function tekstNumeruEtapu(biezacy, liczba) {
  return `Etap ${biezacy + 1} z ${liczba}`
}

/**
 * Ile rzędów segmentów ma mieć pasek etapów w formie zwartej: jeden, gdy
 * nieaktywny segment ma co najmniej `minSegment` px (przy aktywnym
 * `mnoznik` razy szerszym), inaczej dwa (pierwsza i druga połowa etapów).
 * Procesy do 6 etapów zawsze w jednym rzędzie.
 *
 * @param {number} liczba - liczba etapów
 * @param {number} szerokosc - szerokość obszaru segmentów w px (0 = nieznana)
 * @param {{odstep?: number, mnoznik?: number, minSegment?: number}} [opcje]
 * @returns {1|2}
 */
export function liczbaRzedowPaska(liczba, szerokosc, opcje = {}) {
  const { odstep = 6, mnoznik = 1.5, minSegment = 80 } = opcje
  if (liczba <= 6 || !szerokosc) return 1
  const nieaktywny = (szerokosc - (liczba - 1) * odstep) / (liczba - 1 + mnoznik)
  return nieaktywny >= minSegment ? 1 : 2
}

/**
 * Dzieli etapy na rzędy: jeden rząd albo dwie równe połowy (pierwszy rząd
 * większy przy nieparzystej liczbie).
 *
 * @template T
 * @param {T[]} elementy
 * @param {1|2} rzedy
 * @returns {T[][]}
 */
export function podzielNaRzedy(elementy, rzedy) {
  if (rzedy <= 1) return [elementy]
  const polowa = Math.ceil(elementy.length / 2)
  return [elementy.slice(0, polowa), elementy.slice(polowa)]
}
