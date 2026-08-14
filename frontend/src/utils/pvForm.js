// Sizing/selection helpers for the PV/storage quote builder (KalkulatorTab.vue).
// Pure, frappe-free display-level heuristics — no pricing math here, that
// stays server-side. Mirrors the style of cpForm.js.

export const VARIANT_PV = 'Fotowoltaika'
export const VARIANT_PV_BAT = 'Fotowoltaika + Magazyn'
export const VARIANT_BAT = 'Magazyn energii'
export const VARIANTS = [VARIANT_PV, VARIANT_PV_BAT, VARIANT_BAT]

export const PV_OVERSIZE_RATIO = 1.4 // sama PV: produkcja celowa = 140% zużycia
export const KWH_PER_KWP = 1000 // przyjęty roczny uzysk z 1 kWp
export const MOC_MIN_KW = 3
export const MOC_MAX_KW = 20
export const MOC_STEP_KW = 0.5

/**
 * Zaokrągla wartość do najbliższej połówki (siatka mocy PV co 0,5 kW).
 *
 * @param {number} x - wartość wejściowa
 * @returns {number} wartość zaokrąglona do 0,5
 */
export function roundHalf(x) {
  return Math.round(x * 2) / 2
}

/**
 * Ogranicza wartość do przedziału [lo, hi].
 *
 * @param {number} v - wartość wejściowa
 * @param {number} lo - dolna granica
 * @param {number} hi - górna granica
 * @returns {number} wartość ograniczona do przedziału
 */
export function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

/**
 * Sprawdza, czy dany wariant obejmuje instalację fotowoltaiczną.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy wariant zawiera PV
 */
export function variantHasPv(variant) {
  return variant === VARIANT_PV || variant === VARIANT_PV_BAT
}

/**
 * Sprawdza, czy dany wariant obejmuje magazyn energii.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy wariant zawiera magazyn
 */
export function variantHasBattery(variant) {
  return variant === VARIANT_PV_BAT || variant === VARIANT_BAT
}

/**
 * Zwraca listę dostępnych producentów dla danego wariantu.
 * Sama fotowoltaika wymusza FoxESS; pozostałe warianty oferują Sigenergy/Deye.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {string[]} dostępni producenci
 */
export function producentOptionsFor(variant) {
  return variant === VARIANT_PV ? ['FoxESS'] : ['Sigenergy', 'Deye']
}

/**
 * Buduje listę opcji mocy PV: MOC_MIN_KW–MOC_MAX_KW co MOC_STEP_KW, z etykietą
 * pokazującą szacowaną liczbę paneli (moc * 2). Wyłącznie prezentacja — nie
 * wylicza cen.
 *
 * Krok liczony w dziesiątych kW (liczby całkowite), żeby uniknąć błędów
 * zaokrągleń zmiennoprzecinkowych przy wielokrotnym dodawaniu 0,5 — takich
 * jak 7.000000000000001, które nie przejdą ścisłego porównania z wartością
 * opcji <select> ani z testami.
 *
 * @returns {{value: number, label: string}[]} opcje mocy PV
 */
export function buildMocOptions() {
  const out = []
  const stepTenths = Math.round(MOC_STEP_KW * 10)
  const minTenths = Math.round(MOC_MIN_KW * 10)
  const maxTenths = Math.round(MOC_MAX_KW * 10)
  for (let tenths = minTenths; tenths <= maxTenths; tenths += stepTenths) {
    const kw = tenths / 10
    out.push({ value: kw, label: `${kw} kW (${Math.round(kw * 2)} paneli)` })
  }
  return out
}

/**
 * Sugerowana moc instalacji PV na podstawie rocznego zużycia i wariantu.
 * Przy samej fotowoltaice nadwyżki produkcji idą do sieci, więc instalację
 * się przewymiarowuje (mnożnik 1,4). Przy PV + magazyn nadwyżkę zbiera
 * bateria, więc mnożnik zostaje 1 (bez przewymiarowania).
 *
 * @param {number} consumption - roczne zużycie energii w kWh
 * @param {string} variant - wybrany wariant instalacji
 * @returns {number} sugerowana moc PV w kW (0, gdy nie dotyczy)
 */
export function suggestedKwp(consumption, variant) {
  const cons = Number(consumption)
  if (!Number.isFinite(cons) || cons <= 0) return 0
  if (!variantHasPv(variant)) return 0

  const ratio = variant === VARIANT_PV ? PV_OVERSIZE_RATIO : 1
  return clamp(roundHalf((cons * ratio) / KWH_PER_KWP), MOC_MIN_KW, MOC_MAX_KW)
}

/**
 * Sugerowana pojemność magazynu energii na podstawie rocznego zużycia i mocy
 * PV. `kwp` jest jawnym argumentem (nie liczone z suggestedKwp wewnątrz), aby
 * przewymiarowanie ×1,4 przy samej fotowoltaice nie przeciekało do doboru
 * magazynu.
 *
 * @param {number} consumption - roczne zużycie energii w kWh
 * @param {number} kwp - moc instalacji PV w kW (bazowa, bez przewymiarowania)
 * @returns {number} sugerowana pojemność magazynu w kWh (0, gdy nie dotyczy)
 */
export function suggestedStorageKwh(consumption, kwp) {
  const cons = Number(consumption) || 0
  const kw = Number(kwp) || 0
  if (cons <= 0 || kw <= 0) return 0

  const daily = cons / 365
  const surplus = Math.max(0, kw * 4.5 - daily * 0.4) // 4.5 godz. słońca, 40% autokonsumpcji dziennej
  const nightNeed = daily * 0.6
  return clamp(Math.ceil(Math.min(surplus, nightNeed) * 1.2), 10, 60) // 1.2 zapasu
}

/**
 * Wybiera z listy komponent o najmniejszej wartości pola >= minValue;
 * jeśli żaden nie spełnia progu, zwraca komponent o największej wartości.
 * Nie mutuje przekazanej listy.
 *
 * @param {object[]} list - lista komponentów
 * @param {string} field - nazwa pola liczbowego do porównania
 * @param {number} minValue - minimalna wymagana wartość
 * @returns {object|undefined} wybrany komponent lub undefined dla pustej listy
 */
export function pickBySpec(list, field, minValue) {
  if (!list || list.length === 0) return undefined

  const sorted = [...list].sort((a, b) => Number(a[field]) - Number(b[field]))
  const match = sorted.find((item) => Number(item[field]) >= minValue)
  return match || sorted[sorted.length - 1]
}

/**
 * Wybiera konstrukcję montażową: preferuje nazwę zawierającą "blacha",
 * w innym wypadku pierwszą dostępną.
 *
 * @param {object[]} list - lista konstrukcji
 * @returns {object|undefined} wybrana konstrukcja lub undefined dla pustej listy
 */
export function pickMounting(list) {
  if (!list || list.length === 0) return undefined

  return (
    list.find((item) => (item.nazwa || '').toLowerCase().includes('blacha')) ||
    list[0]
  )
}

/**
 * Buduje etykietę panelu z nazwą, modelem i mocą.
 * Puste pola pomija, a moc dopisuje tylko dla dodatniej liczby skończonej.
 *
 * @param {object|null} row - dane panelu
 * @returns {string} etykieta panelu
 */
export function panelLabel(row) {
  if (!row) return ''

  const parts = [row.nazwa, row.model].filter(Boolean)
  const power = row.moc_wp
  const suffix = Number.isFinite(power) && power > 0 ? ` (${power} Wp)` : ''
  return `${parts.join(' ')}${suffix}`
}

/**
 * Buduje listę mocy instalacji dopasowanych do mocy pojedynczego panelu.
 * Liczbę paneli wyznacza z granic MOC_MIN_KW–MOC_MAX_KW.
 *
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {{value: number, label: string, panele: number}[]} opcje mocy PV
 */
export function buildMocOptionsForPanel(wp) {
  if (!Number.isFinite(wp) || wp <= 0) return []

  const out = []
  const minPanels = Math.ceil((MOC_MIN_KW * 1000) / wp)
  const maxPanels = Math.floor((MOC_MAX_KW * 1000) / wp)
  if (
    !Number.isFinite(minPanels) ||
    !Number.isFinite(maxPanels) ||
    minPanels > maxPanels
  ) {
    return []
  }

  for (let panele = minPanels; panele <= maxPanels; panele += 1) {
    const value = (panele * wp) / 1000
    out.push({
      value,
      label: `${panele} paneli — ${value.toFixed(2)} kWp`,
      panele,
    })
  }
  return out
}

/**
 * Wybiera moc panelowej instalacji najbliższą podanej wartości.
 * Przy takiej samej odległości wybiera niższą moc.
 *
 * @param {number} kwp - docelowa moc instalacji w kWp
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {number|null} najbliższa dostępna moc lub null
 */
export function snapMocToPanel(kwp, wp) {
  if (!Number.isFinite(kwp) || kwp <= 0) return null

  const options = buildMocOptionsForPanel(wp)
  if (options.length === 0) return null

  let nearest = options[0].value
  let distance = Math.abs(nearest - kwp)
  for (const option of options.slice(1)) {
    const optionDistance = Math.abs(option.value - kwp)
    if (optionDistance < distance) {
      nearest = option.value
      distance = optionDistance
    }
  }
  return nearest
}

/**
 * Wybiera najmniejszą moc panelowej instalacji spełniającą cel.
 * Jeśli cel przekracza dostępne moce, zwraca największą dostępną moc.
 *
 * @param {number} targetKwp - docelowa moc instalacji w kWp
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {number|null} wybrana moc lub null
 */
export function pickMocForTarget(targetKwp, wp) {
  if (!Number.isFinite(targetKwp) || targetKwp <= 0) return null

  const options = buildMocOptionsForPanel(wp)
  if (options.length === 0) return null

  return (
    options.find((option) => option.value >= targetKwp) ||
    options[options.length - 1]
  ).value
}
