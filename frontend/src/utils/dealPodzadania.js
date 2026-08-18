// Pure logic for the Czyste Powietrze pipeline subtasks band (DealPipelineBar.vue).
//
// Frappe-free by design (no `frappe-ui` / `@/` imports pulling in Vue or the
// app runtime) so it can be unit-tested directly, same convention as
// dealPipeline.js / audytWeryfikacja.js / cpForm.js.
//
// This module is a 1:1 JS mirror of the subtask-state helpers in
// `crm/volteo_pipeline.py` (`STANY_PODZADAN`, `dozwolone_stany`,
// `parsuj_podzadania`) — keep both in sync when either changes. The backend
// is the single source of truth for the CATALOGUE of subtasks per pipeline
// step (`PODZADANIA_CP`, delivered to the frontend as `payload.subtasks` by
// `crm.api.pipeline.volteo_pipeline_get`); this module only knows how to
// read/validate a STATE map against that catalogue.
//
// Persistence (reading/writing the actual state map from/to the server) is
// NOT part of this issue (b49 F2) — DealPipelineBar.vue keeps the state in a
// local mock for now. See the `// F3: zastąpić volteo_podzadania_get/set`
// comment in that component.

/** Valid subtask states — mirrors `STANY_PODZADAN` in `crm/volteo_pipeline.py`. */
export const STANY_PODZADAN = ['waiting', 'accepted', 'error', 'nd']

/**
 * Display metadata per subtask state, plus the synthetic `'brak'` state
 * (no entry in the state map yet — untouched, grey). Colors are expressed as
 * frappe-ui `Badge` theme names, the same tokenized palette already used by
 * `audytWeryfikacja.js`'s `VERDICT_META` and by `Badge.vue` itself — no raw
 * hex values here, and dark mode flips the underlying tokens for free.
 *
 * `nd` additionally carries `muted: true`, consumed by the component to draw
 * a dashed border / dimmed text instead of a solid fill — it shares the
 * `gray` theme with `brak` but must remain visually distinct from it.
 */
export const STAN_META = {
  brak: { theme: 'gray', label: 'Do zrobienia' },
  waiting: { theme: 'blue', label: 'Oczekuje na weryfikację' },
  accepted: { theme: 'green', label: 'Załatwione' },
  error: { theme: 'red', label: 'Nieprawidłowe' },
  nd: { theme: 'gray', label: 'Nie dotyczy', muted: true },
}

function isPlainObject(value) {
  if (value === null || typeof value !== 'object') return false
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

// Port of `_sparsowana_mapa` in `crm/volteo_pipeline.py` / `parsedMap` in
// `audytWeryfikacja.js`: tolerates None/undefined/empty string and
// double-encoded JSON, never throws.
function parsedMap(raw) {
  if (raw === null || raw === undefined || raw === '') return {}
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw)
      if (typeof raw === 'string') raw = JSON.parse(raw)
    } catch (e) {
      return {}
    }
  }
  return isPlainObject(raw) ? raw : {}
}

/**
 * Parses and validates a raw subtask state map (e.g. read from a document's
 * JSON field): tolerates None/string/double-encoded JSON (`parsedMap`),
 * rejects non-dict entries and entries whose `stan` is not in
 * `STANY_PODZADAN`. Port of `parsuj_podzadania` in `crm/volteo_pipeline.py`
 * — must stay 1:1 with it.
 *
 * Returns a NEW object; `raw` is never mutated, and entries in the result
 * are copies, not the same references as in the source.
 *
 * @param {unknown} raw
 * @returns {Object<string, object>}
 */
export function parsePodzadania(raw) {
  const source = parsedMap(raw)
  const result = {}
  Object.entries(source).forEach(([klucz, wpis]) => {
    if (!isPlainObject(wpis)) return
    if (!STANY_PODZADAN.includes(wpis.stan)) return
    result[klucz] = { ...wpis }
  })
  return result
}

/**
 * State of a single subtask: the entry's `stan` if the map has one and it
 * is valid, otherwise `'brak'` (no key = untouched, rendered grey).
 *
 * Deliberately plain property access (`mapa[klucz]`), never
 * `hasOwnProperty` — reading via `hasOwnProperty` on a Vue `reactive()`
 * object registers no dependency (no `getOwnPropertyDescriptor` trap in
 * Vue's `MutableReactiveHandler`) and freezes any `computed` built on it.
 * See the CP admin panel incident documented in `KalkulatorCPTab.vue`.
 *
 * @param {Object<string, object>|null|undefined} mapa
 * @param {string|null|undefined} klucz
 * @returns {'waiting'|'accepted'|'error'|'nd'|'brak'}
 */
export function stanFor(mapa, klucz) {
  if (!mapa || !klucz) return 'brak'
  const wpis = mapa[klucz]
  if (!isPlainObject(wpis)) return 'brak'
  return STANY_PODZADAN.includes(wpis.stan) ? wpis.stan : 'brak'
}

/**
 * Allowed target states for a subtask definition, in the order suitable for
 * rendering as buttons. Mirror of `dozwolone_stany` in
 * `crm/volteo_pipeline.py`, extended with the always-available `'brak'`
 * (clear) at the end — the Python side only concerns itself with the
 * "positive" states a reviewer can set; the "clear this back to untouched"
 * action is a frontend-only affordance.
 *
 * - `typ === 'weryfikacja'` → `waiting`, `accepted`, `error`
 * - anything else (`'odhaczenie'`) → `accepted`
 * - `+ 'nd'` when `nd_dozwolone` is truthy
 * - always `+ 'brak'` (wyczyść)
 *
 * @param {{typ?: string, nd_dozwolone?: boolean}|null|undefined} def
 * @returns {Array<'waiting'|'accepted'|'error'|'nd'|'brak'>}
 */
export function dozwoloneStany(def) {
  const podstawa = def?.typ === 'weryfikacja' ? ['waiting', 'accepted', 'error'] : ['accepted']
  const zNd = def?.nd_dozwolone ? [...podstawa, 'nd'] : podstawa
  return [...zNd, 'brak']
}

/**
 * Subtask definitions for a given pipeline step, straight from
 * `payload.subtasks` (`crm.volteo_pipeline.podzadania_for`, keyed by step
 * status name). `[]` when the step has no subtasks (e.g. "Lead", "Projekt
 * rozliczony", or any OZE step — OZE has no subtask catalogue at all).
 *
 * @param {Object<string, object[]>|null|undefined} subtasks
 * @param {string|null|undefined} status
 * @returns {object[]}
 */
export function tasksForStage(subtasks, status) {
  if (!subtasks || !status) return []
  const defs = subtasks[status]
  return Array.isArray(defs) ? defs : []
}

/**
 * Progress summary for a stage's subtasks — `accepted` and `nd` both count
 * as "done" (an "n/a" subtask is just as settled as an accepted one; only
 * `waiting`/`error`/`brak` leave the stage incomplete). Used for the small
 * counter shown next to the chevron / band header.
 *
 * @param {object[]|null|undefined} defs
 * @param {Object<string, object>|null|undefined} mapa
 * @returns {{zrobione: number, wszystkie: number}}
 */
export function stageSummary(defs, mapa) {
  const list = Array.isArray(defs) ? defs : []
  const zrobione = list.reduce((acc, def) => {
    const stan = stanFor(mapa, def?.klucz)
    return stan === 'accepted' || stan === 'nd' ? acc + 1 : acc
  }, 0)
  return { zrobione, wszystkie: list.length }
}
