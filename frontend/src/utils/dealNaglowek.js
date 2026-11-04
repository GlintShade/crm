// Czysta logika nagłówka szansy v2 (DealNaglowek.vue): linia meta pod tytułem,
// czas w etapie, odmiana "etapy". Bez importów frappe/Vue, testowalna wprost.

const SKROTY_PRODUKTU = {
  Fotowoltaika: 'PV',
  'Fotowoltaika + Magazyn': 'PV + ME',
  'Magazyn energii': 'ME',
  'Czyste Powietrze': 'Czyste Powietrze',
}

/**
 * Krótka etykieta produktu z `custom_rodzaj_umowy`; nieznane rodzaje bez zmian.
 *
 * @param {string|null|undefined} rodzaj
 * @returns {string}
 */
export function skrotProduktu(rodzaj) {
  if (!rodzaj) return ''
  return SKROTY_PRODUKTU[rodzaj] ?? rodzaj
}

function liczba(wartosc) {
  const n = typeof wartosc === 'string' ? Number(wartosc.replace(',', '.')) : Number(wartosc)
  return Number.isFinite(n) && n > 0 ? n : null
}

function formatLiczby(n) {
  // do dwóch miejsc po przecinku, polski przecinek, bez zbędnych zer
  const tekst = String(Math.round(n * 100) / 100)
  return tekst.replace('.', ',')
}

/**
 * Linia meta pod tytułem: "PV + ME · 5,5 kWp · 33 kWh · Suchy Las".
 * Puste części są pomijane; zero w polach liczbowych oznacza brak.
 *
 * @param {Object|null|undefined} doc - szansa (CRM Deal)
 * @returns {string}
 */
export function metaSzansy(doc) {
  if (!doc) return ''
  const moc = liczba(doc.custom_pv_power_kwp)
  const pojemnosc = liczba(doc.custom_pojemnosc_kwh)
  const miasto = typeof doc.custom_install_city === 'string' ? doc.custom_install_city.trim() : ''
  return [
    skrotProduktu(doc.custom_rodzaj_umowy),
    moc !== null ? `${formatLiczby(moc)} kWp` : '',
    pojemnosc !== null ? `${formatLiczby(pojemnosc)} kWh` : '',
    miasto,
  ]
    .filter(Boolean)
    .join(' · ')
}

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
