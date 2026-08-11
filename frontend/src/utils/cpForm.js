export const POZIOMY = ['podstawowy', 'podwyzszony', 'najwyzszy']
export const STANDARDY = ['do80', 'od80do140', 'powyzej140']
export const ZRODLA = ['pompa_ciepla', 'pellet', 'zgazowujacy']
export const PRACE_M2 = ['elewacja', 'strop', 'dach', 'okna']
export const GOSPODARSTWA = ['jednoosobowe', 'wieloosobowe']
export const PROGI_DOCHODU = ['niski', 'sredni', 'wysoki']
// Progi z Programu Priorytetowego Czyste Powietrze (nabór od 2026-07-20), §8.2 pkt 2
// i §8.3 pkt 2 — warunek brzmi „nie przekracza kwoty", więc granice są domknięte (≤).
// Te liczby decydują o kwalifikacji prawnej klienta; nie zmieniać bez nowego regulaminu.
export const PROGI_KWOTY = {
  jednoosobowe: { niski: 1800, sredni: 3150 },
  wieloosobowe: { niski: 1300, sredni: 2250 },
}

/**
 * Create the initial state of the Czyste Powietrze form.
 * Every call returns a completely independent form tree.
 *
 * @returns {object} empty calculator form
 */
export function pustyFormularz() {
  return {
    standard: null,
    gospodarstwo: null,
    progDochodu: null,
    zrodlo: null,
    zrodloWlaczone: false,
    cwu: false,
    typGrzejnikow: null,
    iloscGrzejnikow: 0,
    powierzchnia: '',
    termoWlaczone: false,
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
 * Derive the subsidy level from household size and income bracket.
 *
 * Poziom przestaje być wyborem sprzedawcy — wynika wyłącznie z deklaracji
 * klienta. Próg `wysoki` zawsze daje `podstawowy`, `sredni` zawsze daje
 * `podwyzszony`, niezależnie od standardu budynku. `niski` przy standardzie
 * `powyzej140` daje `najwyzszy`; przy niższym standardzie ten poziom nie
 * jest osiągalny (wymaga budynku > 140 kWh/m²·rok, §8.3 pkt 1), więc funkcja
 * oddaje `podwyzszony` — klient kwalifikujący się do progu `niski`
 * (≤ 1800/1300 zł) mieści się też pod progiem `podwyzszony` (≤ 3150/2250 zł),
 * więc ten poziom mu się faktycznie należy; nie jest to błąd ani przypadek.
 *
 * @param {string|null} standard - selected energy standard
 * @param {string|null} gospodarstwo - household size
 * @param {string|null} progDochodu - income bracket
 * @returns {string|null} derived subsidy level, or null when not determinable
 */
export function wyliczPoziom(standard, gospodarstwo, progDochodu) {
  if (!gospodarstwo || !progDochodu) return null

  if (progDochodu === 'wysoki') return 'podstawowy'
  if (progDochodu === 'sredni') return 'podwyzszony'
  if (progDochodu === 'niski') {
    if (standard === 'powyzej140') return 'najwyzszy'
    if (standard === 'do80' || standard === 'od80do140') return 'podwyzszony'
    return null
  }

  return null
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
 * `okna` is a special case: windows scale off the derived facade area
 * (powierzchnia × mnozniki.elewacja), never off the building's floor area
 * directly and never off a manual `elewacja` override the user may have
 * typed for the facade itself. This is a deliberate product decision — do
 * not "simplify" it back to `powierzchnia × mnozniki.okna`.
 *
 * @param {string} kod - work code
 * @param {string} powierzchnia - building area input
 * @param {object} mnozniki - backend-provided area multipliers
 * @returns {number|null} calculated area, or null when it cannot be calculated
 */
export function autoM2(kod, powierzchnia, mnozniki) {
  const area = parseNumber(powierzchnia)
  if (area === null || area <= 0) return null

  if (kod === 'okna') {
    const elewacja = parseNumber(mnozniki?.elewacja)
    const oknaOdElewacji = parseNumber(mnozniki?.okna_od_elewacji)
    if (elewacja === null || oknaOdElewacji === null) return null
    return roundM2(area * elewacja * oknaOdElewacji)
  }

  const multiplier = parseNumber(mnozniki?.[kod])
  if (multiplier === null) return null
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
 * Coerce a form area to a non-negative decimal number.
 * Area is a continuous quantity (e.g. 120.5 m²), unlike door counts, so
 * fractional input is preserved rather than floored — this must not reuse
 * `countOrZero`, which floors.
 *
 * @param {*} value - area input
 * @returns {number} non-negative area
 */
function areaOrZero(value) {
  const area = parseNumber(value)
  if (area === null || area < 0) return 0
  return area
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
 * `zrodloWlaczone` / `termoWlaczone` gate whether each scope reaches the
 * server at all — turning a scope off zeroes/nulls it in the payload
 * without touching the form's own state, so switching it back on restores
 * exactly what the user had typed (see `pustyFormularz`/component toggle).
 * `cwu` is no longer driven by `form.cwu`: it is simply whether the
 * selected source allows it (pellet/zgazowujący), subject to the same
 * scope gate — the rep can no longer opt out of it.
 *
 * `powierzchnia_m2` is always coerced through `areaOrZero`, even when no
 * thermal work is selected — the server's `_decimal()` call is unconditional
 * and throws on a blank string, so a source-only quote with an empty area
 * field must still send `0`, not `''`.
 *
 * @param {object} form - calculator form state
 * @returns {object} server input payload
 */
export function buildWejscie(form) {
  const zrodloWlaczone = Boolean(form.zrodloWlaczone)
  const termoWlaczone = Boolean(form.termoWlaczone)
  const dodatki = dozwoloneDodatki(form.zrodlo)
  const prace = {}

  for (const kod of PRACE_M2) {
    const work = form.prace[kod]
    prace[kod] = {
      wybrana: termoWlaczone ? work.wybrana : false,
      m2: manualM2(work),
    }
  }

  prace.drzwi = {
    wybrana: termoWlaczone ? form.prace.drzwi.wybrana : false,
    ilosc: countOrZero(form.prace.drzwi.ilosc),
  }

  return {
    poziom: wyliczPoziom(form.standard, form.gospodarstwo, form.progDochodu),
    standard: form.standard,
    gospodarstwo: form.gospodarstwo,
    prog_dochodu: form.progDochodu,
    zrodlo_ciepla: zrodloWlaczone ? form.zrodlo : null,
    cwu: zrodloWlaczone ? dodatki.cwu : false,
    typ_grzejnikow: zrodloWlaczone && dodatki.grzejniki ? form.typGrzejnikow : null,
    ilosc_grzejnikow: zrodloWlaczone && dodatki.grzejniki
      ? countOrZero(form.iloscGrzejnikow)
      : 0,
    powierzchnia_m2: areaOrZero(form.powierzchnia),
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
