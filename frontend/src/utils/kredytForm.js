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

// Canon of the 10 applicant fields (ops#157/#158), JS twin of
// crm/volteo_kredyt.py's `POLA_WNIOSKODAWCY` tuple, same order. These are
// ordinary doctype fieldnames (part of the save payload, see buildDane
// below), not `prefill` keys: PREFILL_KEYS above is the CURRENT contact
// card, POLA_WNIOSKODAWCY is the snapshot saved ON THE RECORD at the moment
// the form was created and editable afterwards from the "Dane wnioskodawcy"
// block.
export const POLA_WNIOSKODAWCY = [
  'wnioskodawca_pesel',
  'wnioskodawca_imiona',
  'wnioskodawca_nazwisko',
  'wnioskodawca_telefon',
  'wnioskodawca_email',
  'wnioskodawca_kod_pocztowy',
  'wnioskodawca_miejscowosc',
  'wnioskodawca_ulica',
  'wnioskodawca_nr_domu',
  'wnioskodawca_nr_lokalu',
]

// PL labels for POLA_WNIOSKODAWCY, JS twin of crm/volteo_kredyt.py's
// `ETYKIETY_WNIOSKODAWCY`, same 10 entries, same wording. Mixed into
// ETYKIETY_POL below (mirrors the Python canon's own
// `{**_ETYKIETY_KREDYT_POL, **ETYKIETY_WNIOSKODAWCY}`), and used directly
// wherever only the applicant block's own labels are needed (the "Dane
// wnioskodawcy" section, the missing-applicant-data banner).
export const ETYKIETY_WNIOSKODAWCY = {
  wnioskodawca_pesel: 'PESEL',
  wnioskodawca_imiona: 'Imiona',
  wnioskodawca_nazwisko: 'Nazwisko',
  wnioskodawca_telefon: 'Telefon',
  wnioskodawca_email: 'E-mail',
  wnioskodawca_kod_pocztowy: 'Kod pocztowy',
  wnioskodawca_miejscowosc: 'Miejscowość',
  wnioskodawca_ulica: 'Ulica',
  wnioskodawca_nr_domu: 'Nr domu',
  wnioskodawca_nr_lokalu: 'Nr lokalu',
}

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

// Single canon of PL labels for all 63 `Volteo Kredyt` data fields
// (BASE_FIELDS + every GRUPY toggle + every GRUPY field, plus the 10
// POLA_WNIOSKODAWCY fields mixed in at the end below), transcribed 1:1
// from the doctype's own labels (ops/crm-kredyt.py's `KREDYT_FIELDS`),
// which are themselves transcribed from the original PDF template. This is
// the JS twin of crm/volteo_kredyt.py's `ETYKIETY_POL` (Python). ops#148:
// the frontend form, the backend's PDF-blocking message, and the Desk
// doctype had each drifted to their own wording for the same field; the
// doctype was the one already correct against the paper, so it is the
// canon both sides now mirror. KredytTab.vue reads every field `label`
// (formSections/grupaPola) from here instead of carrying its own literal
// strings.
//
// EXCEPTION MECHANISM (the only kind of divergence this file allows): a
// screen label here may be SHORTER than the doctype canon only when the
// canon does not fit a form column. When that happens, add the full canon
// to ETYKIETY_PELNE below, keyed by the same fieldname. The missing-fields
// banner and a field's tooltip always resolve through etykietaPelna(),
// never through this object directly, so they never show a truncated
// label. Today ETYKIETY_PELNE has exactly one entry: `suma_zobowiazan`
// (K6, ops#148): the doctype/paper wording ("Suma miesięcznych zobowiązań
// kredytowych i finansowych") is too long for the form's 1/3-width column,
// so the on-screen label is shortened but keeps the word "miesięcznych"
// (owner requirement) so a rep can never mistake it for the running debt
// balance again.
//
// ONE deliberate divergence from ops/crm-kredyt.py itself: that doctype's
// `dzialalnosc_forma_inna` label joins its two clauses with an em dash
// (ends in "jaka?" after that dash). This project's zero-em-dash rule forbids it in
// code we write, so the canon here uses a colon instead ("Inna forma
// opodatkowania: jaka?"). Aligning the doctype's own label to match is a
// separate, deliberately deferred change (ops/crm-kredyt.py is not touched
// by this file).
export const ETYKIETY_POL = {
  miejsce_urodzenia: 'Miejsce urodzenia',
  rodzaj_dokumentu: 'Rodzaj dokumentu tożsamości',
  seria_numer_dokumentu: 'Seria i numer dokumentu tożsamości',
  data_wydania_dokumentu: 'Data wydania dokumentu tożsamości',
  data_waznosci_dokumentu: 'Data ważności dokumentu tożsamości',
  adres_zameldowania_taki_sam: 'Czy adres zamieszkania jest taki sam, jak adres zameldowania?',
  adres_zameldowania: 'Adres zamieszkania',
  adres_korespondencji_taki_sam: 'Czy adres do korespondencji jest taki sam, jak adres zameldowania?',
  adres_korespondencji: 'Adres do korespondencji',
  wyksztalcenie: 'Wykształcenie',
  stan_cywilny: 'Stan cywilny',
  liczba_osob_na_utrzymaniu: 'Liczba osób w gospodarstwie domowym na utrzymaniu',
  kwota_800_plus: 'Kwota świadczenia 800+',
  dochod_wspolmalzonka: 'Deklarowany dochód współmałżonka',
  zrodlo_dochodu_malzonka: 'Źródło dochodu małżonka',
  oplaty_miesieczne: 'Opłaty miesięczne',
  // K6, ops#148: etykieta ekranowa skrócona (patrz komentarz nad
  // ETYKIETY_POL). Pełny kanon "Suma miesięcznych zobowiązań kredytowych i
  // finansowych" żyje w ETYKIETY_PELNE.suma_zobowiazan i to jego widzi baner
  // braków oraz tooltip pola, nigdy tej krótszej wersji.
  suma_zobowiazan: 'Suma miesięcznych zobowiązań',
  numer_rachunku: 'Numer rachunku bankowego',
  praca_wlaczone: 'Dochód: umowa o pracę / zlecenie / dzieło',
  praca_forma: 'Forma zatrudnienia',
  praca_okres: 'Okres zatrudnienia',
  praca_okres_od: 'Zatrudnienie od',
  praca_okres_do: 'Zatrudnienie do',
  praca_nip: 'NIP zakładu pracy',
  praca_nazwa_zakladu: 'Nazwa zakładu pracy',
  praca_adres_telefon: 'Adres i numer telefonu zakładu pracy',
  praca_kwota_dochodu: 'Kwota dochodu',
  emerytura_wlaczone: 'Dochód: emerytura',
  emerytura_numer_swiadczenia: 'Numer świadczenia',
  emerytura_od_kiedy: 'Od kiedy przyznane jest świadczenie',
  emerytura_kwota_dochodu: 'Kwota dochodu',
  renta_wlaczone: 'Dochód: renta',
  renta_numer_swiadczenia: 'Numer świadczenia',
  renta_od_kiedy: 'Od kiedy przyznane jest świadczenie',
  renta_kwota_dochodu: 'Kwota dochodu',
  dzialalnosc_wlaczone: 'Dochód: działalność gospodarcza',
  dzialalnosc_forma_opodatkowania: 'Forma opodatkowania',
  dzialalnosc_forma_inna: 'Inna forma opodatkowania: jaka?',
  dzialalnosc_nip: 'NIP firmy',
  dzialalnosc_nazwa: 'Nazwa firmy',
  dzialalnosc_adres: 'Adres firmy',
  dzialalnosc_telefon: 'Numer telefonu do firmy',
  dzialalnosc_od_kiedy: 'Od kiedy prowadzona jest działalność?',
  dzialalnosc_kwota_dochodu: 'Kwota dochodu',
  gospodarstwo_wlaczone: 'Dochód: gospodarstwo rolne',
  gospodarstwo_nip: 'NIP gospodarstwa',
  gospodarstwo_od_kiedy: 'Od kiedy prowadzone jest gospodarstwo?',
  gospodarstwo_kwota_dochodu: 'Kwota dochodu',
  inne_wlaczone: 'Dochód: inne',
  inne_1_typ: 'Typ dochodu (1)',
  inne_1_kwota: 'Kwota dochodu (1)',
  inne_2_typ: 'Typ dochodu (2)',
  inne_2_kwota: 'Kwota dochodu (2)',
  // Mixed in from ETYKIETY_WNIOSKODAWCY (declared above): mirrors
  // crm/volteo_kredyt.py's `ETYKIETY_POL = {**_ETYKIETY_KREDYT_POL,
  // **ETYKIETY_WNIOSKODAWCY}`, so every consumer that already resolves a
  // fieldname through ETYKIETY_POL (etykietaPelna, the missing-fields
  // banner) also covers the 10 applicant fields for free.
  ...ETYKIETY_WNIOSKODAWCY,
}

// Full doctype/paper canon for fields whose ETYKIETY_POL screen label above
// is deliberately shortened. Every consumer that needs the uncut wording
// (the missing-fields banner, a field's tooltip) goes through
// etykietaPelna(), never reads this object directly. See the header
// comment on ETYKIETY_POL for the exception mechanism this backs.
export const ETYKIETY_PELNE = {
  suma_zobowiazan: 'Suma miesięcznych zobowiązań kredytowych i finansowych',
}

/**
 * Resolve a fieldname to its full canon label: ETYKIETY_PELNE's entry when
 * one exists (a field with a shortened on-screen label), otherwise
 * ETYKIETY_POL's entry (screen label === canon for every other field), or
 * the fieldname itself as a last-resort fallback so an unknown key never
 * renders blank or throws. Use this wherever the FULL canon is required
 * (the missing-fields banner, a field's tooltip). Never ETYKIETY_POL
 * directly, which may be the shortened screen version.
 *
 * @param {string} fieldname - a Volteo Kredyt data fieldname
 * @returns {string} the full canon label
 */
export function etykietaPelna(fieldname) {
  return ETYKIETY_PELNE[fieldname] || ETYKIETY_POL[fieldname] || fieldname
}

// Declarative field-visibility rules, single source of truth for every
// conditional field in the Kredyt form (KredytTab.vue no longer carries
// inline depends_on entries: it reads this map through poleWidoczne()).
//
// MIRROR: the required-field rules this map's visibility must never
// contradict live in the backend, crm/volteo_kredyt.py `_pola_grupy()` /
// `brakujace_pola()`. INVARIANT: a field the backend requires in a given
// form state MUST be visible in the frontend in that same state. The
// ops#139 bug was exactly this invariant broken for praca_okres_od (backend
// requires it whenever the "praca" group is on, for either period type;
// the old frontend rule only showed it for 'Czas określony', so a rep
// filling 'Czas nieokreślony' could never clear the missing-fields banner).
// A rule here has either a `value` (equality) or a `values` (membership)
// key, never both.
export const WARUNKI_WIDOCZNOSCI = {
  praca_okres_od: { fieldname: 'praca_okres', values: ['Czas określony', 'Czas nieokreślony'] },
  praca_okres_do: { fieldname: 'praca_okres', value: 'Czas określony' },
  dzialalnosc_forma_inna: { fieldname: 'dzialalnosc_forma_opodatkowania', value: 'inne' },
  adres_zameldowania: { fieldname: 'adres_zameldowania_taki_sam', value: 'Nie' },
  adres_korespondencji: { fieldname: 'adres_korespondencji_taki_sam', value: 'Nie' },
}

/**
 * Pure visibility check for one field against the current form state, per
 * WARUNKI_WIDOCZNOSCI. A field with no rule is always visible. Never
 * mutates `form`.
 *
 * @param {object} form - current form state
 * @param {string} fieldname - field to check
 * @returns {boolean} whether the field's rule is satisfied
 */
export function poleWidoczne(form, fieldname) {
  const rule = WARUNKI_WIDOCZNOSCI[fieldname]
  if (!rule) return true
  if (Array.isArray(rule.values)) {
    return rule.values.includes(form[rule.fieldname])
  }
  return form[rule.fieldname] === rule.value
}

/**
 * Filter `fields` down to the ones that should render, given the current
 * form state and the server's latest missing-fields list.
 *
 * A field is visible when EITHER poleWidoczne(form, fieldname) is true, OR
 * its fieldname is present in `brakujace`, the safety net that keeps a
 * server/frontend rule mismatch from ever reproducing the ops#139 deadlock
 * again: whatever the server reports as missing is always rendered so the
 * rep can fill it in and the banner can clear.
 *
 * Pure: returns a new array, never mutates `fields`, `form`, or `brakujace`.
 * Preserves the input order.
 *
 * @param {Array<object>} fields - field definitions (objects with .fieldname)
 * @param {object} form - current form state
 * @param {Array<string>} [brakujace] - fieldnames the server reports missing
 * @returns {Array<object>} the visible field definitions, in original order
 */
export function widocznePola(fields, form, brakujace = []) {
  return (fields || []).filter(
    (f) => poleWidoczne(form, f.fieldname) || brakujace.includes(f.fieldname),
  )
}

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
  POLA_WNIOSKODAWCY.forEach((fn) => {
    form[fn] = ''
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

  // Applicant fields (ops#157/#158): unconditional, no toggle gates them,
  // always sent as typed, same as BASE_FIELDS above.
  POLA_WNIOSKODAWCY.forEach((fn) => {
    dane[fn] = form[fn]
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

  POLA_WNIOSKODAWCY.forEach((fn) => {
    form[fn] = r[fn] ?? ''
  })

  return form
}

// Fields required unconditionally, independent of every other answer in the
// form (owner decision, 2026-08-15). MIRROR: crm/volteo_kredyt.py's
// `_BAZA_WYMAGANE` tuple, same order. `numer_rachunku` is deliberately
// absent (owner decision, 2026-08-17): the field still exists and prints on
// the PDF if given, it just is not required.
//
// CONTRACT (ops#147): brakujacePola() below, together with BAZA_WYMAGANE, is
// a pure mirror of crm/volteo_kredyt.py's `_BAZA_WYMAGANE` / `_pola_grupy()`
// / `brakujace_pola()`. Any change to that backend module requires the
// matching change here, and vice versa. crm/test_volteo_kredyt_pdf.py's
// `TestBrakujacePola*` classes and this file's kredytForm.test.js mirror the
// same case matrix so a divergence fails on both sides.
export const BAZA_WYMAGANE = [
  'miejsce_urodzenia',
  'rodzaj_dokumentu',
  'seria_numer_dokumentu',
  'data_wydania_dokumentu',
  'data_waznosci_dokumentu',
  'adres_zameldowania_taki_sam',
  'adres_korespondencji_taki_sam',
  'wyksztalcenie',
  'stan_cywilny',
  'liczba_osob_na_utrzymaniu',
  'kwota_800_plus',
  'dochod_wspolmalzonka',
  'zrodlo_dochodu_malzonka',
  'oplaty_miesieczne',
  'suma_zobowiazan',
]

/**
 * Is a value "filled", for brakujacePola()'s purposes? MIRROR:
 * crm/volteo_kredyt.py `_jest_puste()`. `null`/`undefined`/a whitespace-only
 * string are empty; everything else (including the string "0") is filled.
 */
function jestPuste(wartosc) {
  if (wartosc === null || wartosc === undefined) return true
  if (typeof wartosc === 'string') return wartosc.trim() === ''
  return false
}

/**
 * Is an income-group toggle "on"? MIRROR: crm/volteo_kredyt.py `_wlaczone()`.
 * Accepts a real boolean (the shape the live form always carries, per
 * hydrateFrom's `!!r[fn]` coercion), or a number/string the way the raw API
 * payload might still carry it ('' and '0' are off, anything else is on).
 * Never throws.
 */
function jestWlaczone(wartosc) {
  if (typeof wartosc === 'boolean') return wartosc
  if (wartosc === null || wartosc === undefined) return false
  if (typeof wartosc === 'string') {
    const tekst = wartosc.trim()
    return tekst !== '' && tekst !== '0'
  }
  return Boolean(wartosc)
}

/**
 * Filter one income group's fields down to the ones actually required, given
 * the group is on. MIRROR: crm/volteo_kredyt.py `_pola_grupy()`, same three
 * exceptions, same "skip conditionally instead of appending at the end" so
 * the result preserves GRUPY's declared field order regardless of which
 * field is conditional. Never mutates `grupa` or `form`.
 */
function polaGrupyWymagane(grupa, form) {
  if (grupa.wlaczone === 'praca_wlaczone') {
    return grupa.fields.filter((pole) => {
      if (pole === 'praca_okres_do') return form.praca_okres === 'Czas określony'
      return true
    })
  }

  if (grupa.wlaczone === 'dzialalnosc_wlaczone') {
    // Pisownia "inne" (małą literą) jest celowa: dokładna transkrypcja
    // opcji Select z PDF-u, tak samo jak w backendzie i w
    // WARUNKI_WIDOCZNOSCI powyżej: porównanie jest case-sensitive.
    return grupa.fields.filter((pole) => {
      if (pole === 'dzialalnosc_forma_inna') {
        return form.dzialalnosc_forma_opodatkowania === 'inne'
      }
      return true
    })
  }

  if (grupa.wlaczone === 'inne_wlaczone') {
    return grupa.fields.filter((pole) => pole === 'inne_1_typ' || pole === 'inne_1_kwota')
  }

  return [...grupa.fields]
}

/**
 * Pure mirror of crm/volteo_kredyt.py `brakujace_pola()`, returns the
 * fieldnames required by the form and currently empty, in the same
 * deterministic order the backend produces (BAZA_WYMAGANE, then the two
 * conditional addresses, then each income group's fields in GRUPY order).
 *
 * Never mutates `form`. See the CONTRACT note above BAZA_WYMAGANE.
 *
 * @param {object} form - current form state (BASE_FIELDS + GRUPY fields + toggles)
 * @returns {string[]} fieldnames that are required and currently empty
 */
export function brakujacePola(form) {
  const dane = form || {}
  let wymagane = [...BAZA_WYMAGANE]

  if (dane.adres_zameldowania_taki_sam === 'Nie') wymagane.push('adres_zameldowania')
  if (dane.adres_korespondencji_taki_sam === 'Nie') wymagane.push('adres_korespondencji')

  GRUPY.forEach((grupa) => {
    if (!jestWlaczone(dane[grupa.wlaczone])) return
    wymagane = wymagane.concat(polaGrupyWymagane(grupa, dane))
  })

  return wymagane.filter((pole) => jestPuste(dane[pole]))
}

/**
 * Pure mirror of crm/volteo_kredyt.py `brakujace_dane_wnioskodawcy()`:
 * returns the subset of POLA_WNIOSKODAWCY (same order) that is required and
 * currently empty on `form`. Required is every applicant field EXCEPT
 * `wnioskodawca_nr_lokalu` (a client living in a detached house legitimately
 * has no flat number). Pustość jak w brakujacePola(): jestPuste() (`null`/
 * `undefined`/a whitespace-only string are empty; everything else, including
 * the string "0", is filled).
 *
 * Unlike brakujaceDaneKlienta() below (a legacy, server-round-trip check
 * against the CURRENT contact card's `prefill`), this reads LIVE from
 * `form`, the applicant block is now an editable part of the form itself
 * (ops#157/#158/#163), so its completeness must update instantly as the rep
 * types, exactly like brakujacePola() already does for the 53 base fields.
 *
 * Never mutates `form`.
 *
 * @param {object} form - current form state (POLA_WNIOSKODAWCY fields)
 * @returns {string[]} applicant fieldnames that are required and currently empty
 */
export function brakujaceDaneWnioskodawcy(form) {
  const dane = form || {}
  return POLA_WNIOSKODAWCY.filter(
    (pole) => pole !== 'wnioskodawca_nr_lokalu' && jestPuste(dane[pole]),
  )
}

/**
 * Maps the re-keyed `prefill`/`prefill_kontakt` block (short keys: pesel,
 * imiona, nazwisko, telefon, email, kod_pocztowy, miejscowosc, ulica,
 * nr_domu, nr_lokalu, the shape crm.api.kredyt's `_prefill()` returns) onto
 * the 10 POLA_WNIOSKODAWCY form fieldnames, for the "Przywróć dane klienta"
 * button: the caller merges the result into `form` (immutable update, e.g.
 * `Object.assign(form, prefillDoWnioskodawcy(prefillKontakt.value))`) to
 * overwrite the applicant block with the deal's CURRENT contact-card data.
 *
 * Never mutates `prefill`. A missing key or `null`/`undefined` value becomes
 * `''` in the result, same convention as hydrateFrom().
 *
 * @param {object} prefill - re-keyed prefill block (PREFILL_KEYS shape)
 * @returns {object} patch with the 10 wnioskodawca_* fieldnames set
 */
export function prefillDoWnioskodawcy(prefill) {
  const p = prefill || {}
  return {
    wnioskodawca_pesel: p.pesel ?? '',
    wnioskodawca_imiona: p.imiona ?? '',
    wnioskodawca_nazwisko: p.nazwisko ?? '',
    wnioskodawca_telefon: p.telefon ?? '',
    wnioskodawca_email: p.email ?? '',
    wnioskodawca_kod_pocztowy: p.kod_pocztowy ?? '',
    wnioskodawca_miejscowosc: p.miejscowosc ?? '',
    wnioskodawca_ulica: p.ulica ?? '',
    wnioskodawca_nr_domu: p.nr_domu ?? '',
    wnioskodawca_nr_lokalu: p.nr_lokalu ?? '',
  }
}

// Matches the leading "YYYY-MM-DD" of a Frappe `creation` timestamp
// ("2026-09-18 14:32:10.123456", or a plain ISO "2026-09-18T14:32:10Z"),
// deliberately not a full date-library parse: this module stays
// framework-free (see the file header), and a leading-digits match is all
// etykietaFormularza() below needs.
const WZORZEC_DATY_UTWORZENIA = /^(\d{4})-(\d{2})-(\d{2})/

/**
 * Formats a Frappe `creation` timestamp as "DD.MM.RRRR". Returns '' for a
 * missing/unparseable value; never throws.
 */
function formatujDateUtworzenia(creation) {
  if (typeof creation !== 'string') return ''
  const dopasowanie = creation.match(WZORZEC_DATY_UTWORZENIA)
  if (!dopasowanie) return ''
  const [, rok, miesiac, dzien] = dopasowanie
  return `${dzien}.${miesiac}.${rok}`
}

/**
 * Builds the label shown for one row of `volteo_kredyt_lista`'s
 * `formularze` array in the form picker: "Nazwisko Imiona (DD.MM.RRRR)"
 * when both are known, degrading gracefully (name only, date only, or a
 * fallback placeholder) when either is missing: a freshly created record
 * with the applicant block not yet typed still needs a usable row label.
 *
 * Never mutates `row`.
 *
 * @param {object} row - one entry of volteo_kredyt_lista's `formularze`
 *   (name, wnioskodawca_nazwisko, wnioskodawca_imiona, status,
 *   autenti_status, creation, modified)
 * @returns {string} display label for the form picker
 */
export function etykietaFormularza(row) {
  const r = row || {}
  const nazwisko = (r.wnioskodawca_nazwisko || '').trim()
  const imiona = (r.wnioskodawca_imiona || '').trim()
  const osoba = [nazwisko, imiona].filter(Boolean).join(' ')
  const data = formatujDateUtworzenia(r.creation)

  if (osoba && data) return `${osoba} (${data})`
  if (osoba) return osoba
  if (data) return data
  return 'Formularz bez danych wnioskodawcy'
}

// Polish labels for the 9 required `prefill` (contact-card) keys. MIRROR:
// crm/api/kredyt.py `_PREFILL_ETYKIETY`, same 9 keys, same wording,
// `nr_lokalu` deliberately absent (a client living in a detached house
// legitimately has no flat number, so it can never block PDF generation).
//
// LEGACY (ops#163): this checks the CURRENT contact card via a server round
// trip (`prefill`), from before the applicant block became an editable
// snapshot on the record. KredytTab.vue's live "Generuj PDF" gate now uses
// brakujaceDaneWnioskodawcy() above instead. Kept exported (and tested)
// because nothing forces every caller to migrate at once.
const PREFILL_ETYKIETY_KLIENTA = {
  pesel: 'PESEL',
  imiona: 'Imię/imiona',
  nazwisko: 'Nazwisko',
  telefon: 'Telefon',
  email: 'E-mail',
  kod_pocztowy: 'Kod pocztowy',
  miejscowosc: 'Miejscowość',
  ulica: 'Ulica',
  nr_domu: 'Nr domu',
}

/**
 * Pure mirror of crm/api/kredyt.py `volteo_kredyt_pdf`'s prefill-completeness
 * check (`brakujace_prefill = [klucz for klucz in _PREFILL_ETYKIETY if not
 * prefill.get(klucz)]`), the SAME falsy check, not a whitespace-trim check,
 * so a stray space in a contact field is not treated as missing here either;
 * matches the server exactly. Returns PL labels (not fieldnames), ready to
 * join straight into the banner's second line. Never mutates `prefill`.
 *
 * @param {object} prefill - the `prefill` block returned by the kredyt API
 * @returns {string[]} PL labels of the required prefill keys that are empty
 */
export function brakujaceDaneKlienta(prefill) {
  const dane = prefill || {}
  return Object.keys(PREFILL_ETYKIETY_KLIENTA)
    .filter((klucz) => !dane[klucz])
    .map((klucz) => PREFILL_ETYKIETY_KLIENTA[klucz])
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
