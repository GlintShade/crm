// Formularz kredytowy (Deal tab "Kredyt") — logika formularza, testowana bez
// mocka Vue. Modeled on `cpForm.js` (payload-builder-never-mutates,
// deepFreeze-safe), but with one deliberate divergence: form keys here ARE
// the doctype fieldnames (snake_case), not cpForm's camelCase UI-state
// names. The reason is different from CP: this form has no derived/computed
// fields and no server-side recalculation loop — it is a straight
// save-as-typed contact/income form, so there is no benefit to a separate
// UI vocabulary and a translation layer would just be one more place for a
// fieldname typo to hide.
//
// AUTHORITATIVE: every Select option array below (`*_OPCJE`) is transcribed
// verbatim from the source PDF (mirrored in ops/crm-kredyt.py and
// crm/volteo_kredyt_mapa.py) and is what the doctype schema stores — do not
// "normalize" casing or punctuation here, a mismatch breaks the round-trip
// of a saved value. Kept in this single block so all wording lives in
// exactly one place to reconcile against the backend.
//
// EXCEPTION: STAN_CYWILNY_OPCJE below is an owner override (post-click-test
// feedback), not a PDF transcription — the stored values follow the owner's
// wording, not the PDF's. Still transcribed verbatim from the owner's
// instruction and still authoritative for the round-trip; just not
// PDF-sourced like its siblings.

export const TAK_NIE_OPCJE = ['', 'Tak', 'Nie']

export const WYKSZTALCENIE_OPCJE = [
  '',
  'wyższe',
  'średnie',
  'zawodowe',
  'podstawowe/gimnazjalne',
]

export const RODZAJ_DOKUMENTU_OPCJE = ['', 'Dowód osobisty', 'Paszport', 'Karta pobytu']

export const STAN_CYWILNY_OPCJE = [
  '',
  'Kawaler/panna',
  'Rozwiedziony/a',
  'Małżeństwo - rozdzielność majątkowa',
  'Małżeństwo - wspólnota majątkowa',
  'Wdowiec/wdowa',
  'Separacja',
]

export const PRACA_FORMA_OPCJE = ['', 'Umowa o pracę', 'Umowa zlecenie', 'Umowa o dzieło']

export const PRACA_OKRES_OPCJE = ['', 'Czas określony', 'Czas nieokreślony']

// NOTE: all-lowercase, including 'inne' — the depends_on condition for
// dzialalnosc_forma_inna in KredytTab.vue must match this exactly ('inne',
// not 'Inne').
export const DZIALALNOSC_FORMA_OPCJE = [
  '',
  'ryczałt',
  'księga przychodów i rozchodów (KPiR)',
  'inne',
]

// `prefill` keys returned by crm.api.kredyt.volteo_kredyt_get/create/save —
// read-only CRM data (contact card), never part of the editable payload.
export const PREFILL_KEYS = [
  'pesel',
  'imiona',
  'nazwisko',
  'telefon',
  'email',
  'kod_pocztowy',
  'miejscowosc',
  'ulica',
  'nr_domu',
  'nr_lokalu',
]

// Fields that are always part of the payload, independent of any income-group
// toggle — identity, addresses, and the household/financial summary fields.
export const BASE_FIELDS = [
  'miejsce_urodzenia',
  'rodzaj_dokumentu',
  'seria_numer_dokumentu',
  'data_wydania_dokumentu',
  'data_waznosci_dokumentu',
  'adres_zameldowania_taki_sam',
  'adres_zameldowania',
  'adres_korespondencji_taki_sam',
  'adres_korespondencji',
  'wyksztalcenie',
  'stan_cywilny',
  'liczba_osob_na_utrzymaniu',
  'kwota_800_plus',
  'dochod_wspolmalzonka',
  'zrodlo_dochodu_malzonka',
  'oplaty_miesieczne',
  'suma_zobowiazan',
  'numer_rachunku',
]

// Six income-source groups. Each carries its own on/off toggle fieldname
// (`wlaczone`) plus the doctype fields it owns. Turning a group off nulls
// its fields in the save payload (see buildDane) without touching what the
// rep already typed, so switching it back on restores exactly that input —
// same "gate zeroes the payload, not the form" pattern as cpForm's
// zrodloWlaczone/termoWlaczone.
export const GRUPY = [
  {
    key: 'praca',
    wlaczone: 'praca_wlaczone',
    label: 'Umowa o pracę / zlecenie / dzieło',
    fields: [
      'praca_forma',
      'praca_data_zatrudnienia',
      'praca_okres',
      'praca_okres_od',
      'praca_okres_do',
      'praca_nip',
      'praca_nazwa_zakladu',
      'praca_adres_telefon',
      'praca_kwota_dochodu',
    ],
  },
  {
    key: 'emerytura',
    wlaczone: 'emerytura_wlaczone',
    label: 'Emerytura',
    fields: ['emerytura_numer_swiadczenia', 'emerytura_od_kiedy', 'emerytura_kwota_dochodu'],
  },
  {
    key: 'renta',
    wlaczone: 'renta_wlaczone',
    label: 'Renta',
    fields: ['renta_numer_swiadczenia', 'renta_od_kiedy', 'renta_kwota_dochodu'],
  },
  {
    key: 'dzialalnosc',
    wlaczone: 'dzialalnosc_wlaczone',
    label: 'Działalność gospodarcza',
    fields: [
      'dzialalnosc_forma_opodatkowania',
      'dzialalnosc_forma_inna',
      'dzialalnosc_nip',
      'dzialalnosc_nazwa',
      'dzialalnosc_adres',
      'dzialalnosc_telefon',
      'dzialalnosc_od_kiedy',
      'dzialalnosc_kwota_dochodu',
    ],
  },
  {
    key: 'gospodarstwo',
    wlaczone: 'gospodarstwo_wlaczone',
    label: 'Gospodarstwo rolne',
    fields: ['gospodarstwo_nip', 'gospodarstwo_od_kiedy', 'gospodarstwo_kwota_dochodu'],
  },
  {
    key: 'inne',
    wlaczone: 'inne_wlaczone',
    label: 'Inne źródła dochodu',
    fields: ['inne_1_typ', 'inne_1_kwota', 'inne_2_typ', 'inne_2_kwota'],
  },
]

/**
 * Create the initial state of the Kredyt form. Every call returns a
 * completely independent object (own copy, no shared references) — mirrors
 * cpForm's `pustyFormularz()`.
 *
 * @returns {object} empty kredyt form: every field '', every toggle false
 */
export function defaultForm() {
  const form = {}
  BASE_FIELDS.forEach((fn) => {
    form[fn] = ''
  })
  GRUPY.forEach((grupa) => {
    form[grupa.wlaczone] = false
    grupa.fields.forEach((fn) => {
      form[fn] = ''
    })
  })
  return form
}

/**
 * Build the save payload accepted by crm.api.kredyt.volteo_kredyt_save.
 * Never mutates `form` — always returns a fresh object.
 *
 * Every income group whose toggle is off has its fields sent as `null`
 * (not omitted, not left as stale typed text) so a save while a group is
 * switched off actually clears it server-side rather than silently keeping
 * whatever was last saved. Toggles themselves are always sent as booleans.
 *
 * @param {object} form - current form state (as produced by defaultForm/hydrateFrom)
 * @returns {object} save payload — fresh object, `form` untouched
 */
export function buildDane(form) {
  const dane = {}

  BASE_FIELDS.forEach((fn) => {
    dane[fn] = form[fn]
  })

  GRUPY.forEach((grupa) => {
    const wlaczone = Boolean(form[grupa.wlaczone])
    dane[grupa.wlaczone] = wlaczone
    grupa.fields.forEach((fn) => {
      dane[fn] = wlaczone ? form[fn] : null
    })
  })

  return dane
}

/**
 * Build a fresh form object from a saved kredyt record. Toggles coerce to
 * real booleans (`!!record[x]`); every other field coerces a null/undefined
 * server value to '' so text inputs never render the literal string "null".
 * Never mutates `record`.
 *
 * @param {object|null} record - saved kredyt record (or null/undefined)
 * @returns {object} new form object, independent of `record`
 */
export function hydrateFrom(record) {
  const form = defaultForm()
  const r = record || {}

  BASE_FIELDS.forEach((fn) => {
    form[fn] = r[fn] ?? ''
  })

  GRUPY.forEach((grupa) => {
    form[grupa.wlaczone] = !!r[grupa.wlaczone]
    grupa.fields.forEach((fn) => {
      form[fn] = r[fn] ?? ''
    })
  })

  return form
}

// Matches a plain amount: an integer part (digits, optionally interspersed
// with spaces/NBSP thousands grouping — never touched, only the decimal
// part is normalized) plus an optional decimal separator (',' or '.')
// followed by zero or more digits. Anything that doesn't fit this shape
// (letters, multiple separators, a leading separator with no digits before
// it) fails the match and is left for the server to reject.
const WZORZEC_KWOTY = /^(\d[\d\s]*?)(?:([.,])(\d*))?$/

/**
 * Normalize an amount typed by the rep, on blur, to the "123,45" shape the
 * server expects — owner-requested UX so the field visibly confirms what
 * was understood before save, without silently changing the number.
 *
 * Rules (see kredytForm.test.js for the exhaustive matrix):
 *  - no decimal part ("123")       -> append ",00"       ("123,00")
 *  - 1 decimal digit ("123,4")     -> pad to 2            ("123,40")
 *  - 2 decimal digits ("123,90")   -> unchanged
 *  - trailing separator ("123,")   -> treated as 0 decimals ("123,00")
 *  - dot decimal ("123.4")         -> comma, padded        ("123,40")
 *  - thousands grouping the user typed ("12 300,5") is preserved verbatim;
 *    only the decimal part is touched ("12 300,50")
 *  - empty/whitespace-only text    -> returned unchanged
 *  - more than 2 decimal digits    -> returned unchanged (no silent rounding)
 *  - anything not matching a plain amount shape (e.g. "abc", "1,2,3")
 *    -> returned unchanged; the server validates and rejects it
 *
 * Never mutates its argument (a string is immutable anyway); always
 * returns a value, never throws.
 *
 * @param {string} tekst - raw text from the amount input's blur event
 * @returns {string} normalized "calość,dd" text, or `tekst` unchanged
 */
export function normalizujKwote(tekst) {
  if (typeof tekst !== 'string') return tekst
  if (tekst.trim() === '') return tekst

  const dopasowanie = tekst.match(WZORZEC_KWOTY)
  if (!dopasowanie) return tekst

  const [, calaCzesc, separator, dziesietneSurowe] = dopasowanie
  const dziesietne = dziesietneSurowe ?? ''

  if (dziesietne.length > 2) return tekst
  if (!separator) return `${calaCzesc},00`

  return `${calaCzesc},${dziesietne.padEnd(2, '0')}`
}

// Strips every whitespace character, including the non-breaking space a
// pasted bank-format number often carries (JS `\s` already matches U+00A0,
// but the class is spelled out explicitly so that stays true regardless of
// engine quirks).
const WZORZEC_BIALE_ZNAKI = /[\s ]/g

/**
 * Group a raw digit string into Polish NRB display shape: 2 digits, then
 * groups of 4, single spaces between. Length-agnostic (partial and >26
 * digit inputs both format, no padding/truncation) — this is a live-typing
 * mask, not a validator.
 *
 * @param {string} cyfry - digits only, already stripped of whitespace
 * @returns {string} grouped string
 */
function grupujCyfryRachunku(cyfry) {
  if (cyfry.length <= 2) return cyfry
  const grupy = [cyfry.slice(0, 2)]
  for (let i = 2; i < cyfry.length; i += 4) {
    grupy.push(cyfry.slice(i, i + 4))
  }
  return grupy.join(' ')
}

/**
 * Format a bank account number (`numer_rachunku`) into Polish NRB grouping
 * for display: "61 1090 1014 0000 0712 1981 2874". Pure and idempotent —
 * formatting an already-formatted value returns it unchanged, and partial
 * input formats progressively as the rep types.
 *
 * The server stores this field verbatim with no format validation, so
 * anything that isn't purely digits after stripping whitespace (a "PL"
 * IBAN prefix, a dash, letters) is returned EXACTLY as given — we must
 * never mangle a non-standard value the rep intentionally typed.
 *
 * Never throws; a non-string argument is returned unchanged (mirrors
 * `normalizujKwote`'s defensive shape).
 *
 * @param {string} tekst - raw text from the account-number input
 * @returns {string} grouped text, or `tekst` unchanged when not purely digits
 */
export function formatujNumerRachunku(tekst) {
  if (typeof tekst !== 'string') return tekst

  const oczyszczony = tekst.replace(WZORZEC_BIALE_ZNAKI, '')
  if (oczyszczony === '') return ''
  if (!/^\d+$/.test(oczyszczony)) return tekst

  return grupujCyfryRachunku(oczyszczony)
}

/**
 * Format `tekst` like `formatujNumerRachunku` while keeping the text
 * caret glued to the digit the rep just typed/deleted, instead of it
 * jumping to the end of the input on every keystroke (the naive
 * "reformat the whole string" approach).
 *
 * Method: count how many digits sit strictly before `kursor` in the raw
 * input, then walk the freshly formatted string until that many digits
 * have been passed — the new caret lands right after the last one counted.
 * Caret 0 always stays 0. When the value is returned verbatim (non-digit
 * content, e.g. a "PL" prefix), there is nothing to re-flow, so the
 * original `kursor` is kept as-is.
 *
 * @param {string} tekst - raw text from the input's current value
 * @param {number} kursor - caret position (selectionStart) in `tekst`
 * @returns {{tekst: string, kursor: number}} formatted text and new caret
 */
export function formatujNumerRachunkuZKursorem(tekst, kursor) {
  const sformatowany = formatujNumerRachunku(tekst)

  if (typeof tekst !== 'string') {
    return { tekst: sformatowany, kursor }
  }

  const oczyszczony = tekst.replace(WZORZEC_BIALE_ZNAKI, '')
  const jestCyfrowy = oczyszczony !== '' && /^\d+$/.test(oczyszczony)
  if (!jestCyfrowy) {
    return { tekst: sformatowany, kursor }
  }

  let cyfrPrzedKursorem = 0
  for (let i = 0; i < Math.min(kursor, tekst.length); i++) {
    if (/\d/.test(tekst[i])) cyfrPrzedKursorem++
  }

  let nowyKursor = 0
  if (cyfrPrzedKursorem > 0) {
    let widzianeCyfry = 0
    nowyKursor = sformatowany.length
    for (let i = 0; i < sformatowany.length; i++) {
      if (/\d/.test(sformatowany[i])) {
        widzianeCyfry++
        if (widzianeCyfry === cyfrPrzedKursorem) {
          nowyKursor = i + 1
          break
        }
      }
    }
  }

  return { tekst: sformatowany, kursor: nowyKursor }
}
