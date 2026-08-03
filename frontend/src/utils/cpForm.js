export const POZIOMY = ['podstawowy', 'podwyzszony', 'najwyzszy']
export const STANDARDY = ['do80', 'od80do140', 'powyzej140']
export const ZRODLA = ['pompa_ciepla', 'pellet', 'zgazowujacy']
export const PRACE_M2 = ['elewacja', 'strop', 'dach', 'okna']

/**
 * Create the initial state of the Czyste Powietrze form.
 * Every call returns a completely independent form tree.
 *
 * @returns {object} empty calculator form
 */
export function pustyFormularz() {
  return {
    poziom: null,
    standard: null,
    zrodlo: null,
    cwu: false,
    typGrzejnikow: null,
    iloscGrzejnikow: 0,
    powierzchnia: '',
    prace: {
      elewacja: { wybrana: false, reczne: false, m2: '' },
      strop: { wybrana: false, reczne: false, m2: '' },
      dach: { wybrana: false, reczne: false, m2: '' },
      okna: { wybrana: false, reczne: false, m2: '' },
      drzwi: { wybrana: false, ilosc: '' },
    },
  }
}

/**
 * Return the subsidy levels available for an energy standard.
 *
 * @param {string|null} standard - selected energy standard
 * @returns {string[]} available subsidy levels
 */
export function dostepnePoziomy(standard) {
  if (standard === 'do80' || standard === 'od80do140') {
    return POZIOMY.slice(0, 2)
  }
  return POZIOMY.slice()
}

/**
 * Return the add-ons supported by a selected heat source.
 *
 * @param {string|null} zrodlo - selected heat source
 * @returns {{grzejniki: boolean, cwu: boolean}} permitted add-ons
 */
export function dozwoloneDodatki(zrodlo) {
  if (zrodlo === 'pompa_ciepla') {
    return { grzejniki: true, cwu: false }
  }
  if (zrodlo === 'pellet' || zrodlo === 'zgazowujacy') {
    return { grzejniki: false, cwu: true }
  }
  return { grzejniki: false, cwu: false }
}

/**
 * Parse a finite numeric value while treating an empty string as invalid.
 *
 * @param {*} value - value to parse
 * @returns {number|null} parsed number or null
 */
function parseNumber(value) {
  if (
    (typeof value !== 'string' && typeof value !== 'number') ||
    (typeof value === 'string' && value.trim() === '')
  ) {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Round a display-only area value to two decimal places.
 *
 * @param {number} value - area value
 * @returns {number} rounded area
 */
function roundM2(value) {
  return Number((Math.round((value + Number.EPSILON) * 100) / 100).toFixed(2))
}

/**
 * Calculate the automatically displayed area for an area-based work.
 * This does not replace the server-side calculation.
 *
 * @param {string} kod - work code
 * @param {string} powierzchnia - building area input
 * @param {object} mnozniki - backend-provided area multipliers
 * @returns {number|null} calculated area, or null when it cannot be calculated
 */
export function autoM2(kod, powierzchnia, mnozniki) {
  const area = parseNumber(powierzchnia)
  const multiplier = parseNumber(mnozniki?.[kod])

  if (area === null || area <= 0 || multiplier === null) return null
  return roundM2(area * multiplier)
}

/**
 * Calculate the automatically displayed area for doors.
 * Door counts are whole counted items, so fractional input is rounded down.
 * This does not replace the server-side calculation.
 *
 * @param {string|number} ilosc - door count input
 * @param {string|number|null} m2NaDrzwi - area per door
 * @returns {number|null} calculated area, or null when it cannot be calculated
 */
export function drzwiM2(ilosc, m2NaDrzwi) {
  const count = parseNumber(ilosc)
  const multiplier = parseNumber(m2NaDrzwi)

  if (count === null || count <= 0 || multiplier === null) return null
  return roundM2(Math.floor(count) * multiplier)
}

/**
 * Coerce a form count to a non-negative whole number.
 *
 * @param {*} value - count input
 * @returns {number} non-negative integer
 */
function countOrZero(value) {
  const count = parseNumber(value)
  if (count === null || count < 0) return 0
  return Math.floor(count)
}

/**
 * Return a manual area only when the work is explicitly in manual mode.
 *
 * @param {object} work - area work state
 * @returns {string|null} raw manual area or null for automatic mode
 */
function manualM2(work) {
  if (work?.reczne === true && typeof work.m2 === 'string' && work.m2 !== '') {
    return work.m2
  }
  return null
}

/**
 * Build the payload accepted by the server's volteo_cp_calc method.
 * The returned payload is fresh and the form is never mutated.
 *
 * @param {object} form - calculator form state
 * @returns {object} server input payload
 */
export function buildWejscie(form) {
  const dodatki = dozwoloneDodatki(form.zrodlo)
  const prace = {}

  for (const kod of PRACE_M2) {
    const work = form.prace[kod]
    prace[kod] = {
      wybrana: work.wybrana,
      m2: manualM2(work),
    }
  }

  prace.drzwi = {
    wybrana: form.prace.drzwi.wybrana,
    ilosc: countOrZero(form.prace.drzwi.ilosc),
  }

  return {
    poziom: form.poziom,
    standard: form.standard,
    zrodlo_ciepla: form.zrodlo,
    cwu: dodatki.cwu ? Boolean(form.cwu) : false,
    typ_grzejnikow: dodatki.grzejniki ? form.typGrzejnikow : null,
    ilosc_grzejnikow: dodatki.grzejniki
      ? countOrZero(form.iloscGrzejnikow)
      : 0,
    powierzchnia_m2: form.powierzchnia,
    prace,
  }
}

/**
 * Convert a failed calculator call into a user-facing message.
 *
 * @param {*} error - caught call error
 * @returns {string} Polish error message
 */
export function opisBledu(error) {
  return (
    error?.messages?.[0] ||
    error?.message ||
    'Nie udało się obliczyć oferty.'
  )
}
