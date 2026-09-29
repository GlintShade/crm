// Frappe-free helpers for UmowaCPTab.vue (issue ops#212): the Czyste
// Powietrze variant of the deal's "Umowa" tab, a small form for "Umowa o
// świadczenie usług obsługi dofinansowania (Czyste Powietrze)". Kept
// separate from utils/kredytForm.js and utils/money.js (imported, not
// duplicated) because this tab's own concepts (wynagrodzenie wariant 1/2,
// the read-only client-data grid) do not exist anywhere else.
//
// Amounts arrive from the server as strings (e.g. "1600.00", the shape
// `crm.api.umowa.volteo_umowa_get/create/save` returns inside
// `wyliczenia.warianty_wynagrodzenia` and on the saved `umowa` record
// itself), and may be `null` when the underlying constant on the backend
// is unset. `formatPln`/`formatPlnAmount` (utils/money.js) already coerce
// any input through `Number(...)`, treating anything non-numeric -
// including `null`/`undefined`/`''` - as zero (see money.js's
// `parseFiniteOrZero`); silently formatting a missing amount as "0,00 zł"
// would misrepresent an unset constant as a real zero-złoty variant, so
// every function below checks for a missing value explicitly FIRST and
// returns an empty/placeholder string instead of ever calling the money
// formatter on it.
import { formatPln } from '@/utils/money'

/**
 * True when a raw amount value should be treated as "not provided" by the
 * server (constant unset), as opposed to a real, meaningful zero.
 *
 * @param {*} value - raw netto/brutto value from the API
 * @returns {boolean}
 */
function brakKwoty(value) {
  return value === null || value === undefined || value === ''
}

/**
 * Format a single wariant's amounts for display, e.g.
 * "1 600,00 zł netto (1 968,00 zł brutto)". Returns a Polish placeholder
 * when either amount is missing, never "NaN,undefined zł" or a fabricated
 * "0,00 zł".
 *
 * `__()` is called here, inside the function body, never at module scope
 * (the eager-chunk trap: a module-top-level `__()` call throws
 * `ReferenceError` before the translation runtime has loaded - see
 * utils/kredytForm.js's `badgeStatusuFinansowania()` for the same pattern).
 *
 * @param {{netto: *, brutto: *}} [wariant]
 * @returns {string}
 */
export function etykietaWariantu(wariant) {
  const netto = wariant?.netto
  const brutto = wariant?.brutto
  if (brakKwoty(netto) || brakKwoty(brutto)) {
    return __('brak danych')
  }
  return `${formatPln(netto)} netto (${formatPln(brutto)} brutto)`
}

/**
 * Build the `FormControl type="select"` options for the "Wariant
 * wynagrodzenia" field from `wyliczenia.warianty_wynagrodzenia`
 * (`[{wariant, netto, brutto}, ...]`). Always starts with a blank option
 * (unset wariant is valid - the umowa can be saved as a draft before a
 * choice is made) and skips any entry without a usable `wariant` value.
 *
 * `value` is always coerced to a String so `v-model` comparisons against
 * `form.wynagrodzenie_wariant` (itself a string, "1"/"2"/"") never
 * mismatch a numeric 1 against the string "1".
 *
 * @param {Array<{wariant: *, netto: *, brutto: *}>} [warianty]
 * @returns {Array<{label: string, value: string}>}
 */
export function wariantOptions(warianty) {
  const blank = { label: '', value: '' }
  if (!Array.isArray(warianty)) return [blank]
  const opcje = warianty
    .filter((w) => w && w.wariant !== null && w.wariant !== undefined && w.wariant !== '')
    .map((w) => ({
      label: etykietaWariantu(w),
      value: String(w.wariant),
    }))
  return [blank, ...opcje]
}

/**
 * Format the SAVED amounts on the `umowa` record itself
 * (`umowa.wynagrodzenie_netto_pln` / `umowa.wynagrodzenie_brutto_pln`) as
 * one line, e.g. "1 600,00 zł netto / 1 968,00 zł brutto". Returns '' (not
 * a placeholder) when either amount is missing - the caller shows its own
 * "wybierz i zapisz wariant" hint in that case, see UmowaCPTab.vue.
 *
 * @param {*} netto
 * @param {*} brutto
 * @returns {string}
 */
export function formatujParaKwot(netto, brutto) {
  if (brakKwoty(netto) || brakKwoty(brutto)) return ''
  return `${formatPln(netto)} netto / ${formatPln(brutto)} brutto`
}
