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
// wired up in DealPipelineBar.vue via `crm.api.pipeline.volteo_podzadania_get`
// / `volteo_podzadania_set` (b49 F3). The optimistic-write/rollback/payload
// logic below is pure so it can be unit-tested without mounting the
// component or mocking `frappe-ui`'s `call`/`createResource`.

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

/**
 * Builds the request body for `crm.api.pipeline.volteo_podzadania_set`
 * (b49 F3) from raw form inputs — the single place that decides which of
 * `data`/`note` actually get sent, mirroring the server's own rules:
 *
 * - `stan === 'brak'` (Wyczyść) never sends `data`/`note` — the backend's
 *   "brak" branch only pops the map entry, it never reads either field, and
 *   `volteo_podzadania_set` OVERWRITES the whole entry rather than patching
 *   it, so sending a stale `data`/`note` alongside an unrelated stan change
 *   would silently keep it (harmless here since it's dropped, but keeping
 *   the payload minimal for "brak" documents that intent).
 * - `data` is included only when the task definition takes a date
 *   (`zData`) AND a non-empty value was provided — tasks without `z_data`
 *   never carry a date, matching the server's own `frappe.throw` guard.
 * - `note` is trimmed and clamped to 500 chars client-side (the server
 *   enforces the same limit and would reject anything longer) and included
 *   only when non-empty after trimming.
 *
 * Never mutates its input; returns a fresh plain object each call.
 *
 * @param {{zadanie: string, stan: string, data?: string, note?: string, zData?: boolean}} input
 * @returns {{zadanie: string, stan: string, data?: string, note?: string}}
 */
export function buildPodzadaniePayload({ zadanie, stan, data, note, zData }) {
  const payload = { zadanie, stan }
  if (stan === 'brak') return payload

  if (zData && data) payload.data = data

  const trimmed = typeof note === 'string' ? note.trim().slice(0, 500) : ''
  if (trimmed) payload.note = trimmed

  return payload
}

/**
 * Derives the optimistic map entry a `buildPodzadaniePayload` result implies
 * — `null` for `stan === 'brak'` (entry removed), otherwise `{stan, data?,
 * note?}` with only the fields the payload actually carries. Deliberately
 * omits `by`/`at` (server-only bookkeeping fields, never read by this
 * component's rendering) since the optimistic write happens before the
 * server response is known.
 *
 * @param {{zadanie: string, stan: string, data?: string, note?: string}|null|undefined} payload
 * @returns {{stan: string, data?: string, note?: string}|null}
 */
export function entryFromPayload(payload) {
  if (!payload || payload.stan === 'brak') return null
  const { stan, data, note } = payload
  return { stan, ...(data ? { data } : {}), ...(note ? { note } : {}) }
}

/**
 * Applies an optimistic write to a subtask state map WITHOUT mutating the
 * input — returns a new map with `klucz` set to `wpis` (a shallow copy of
 * it), or removed entirely when `wpis` is `null`/`undefined` (mirrors the
 * server's "brak" branch, which pops the key rather than storing an empty
 * entry). Used both for the optimistic local write before a save round-trip
 * and, symmetrically, to roll back to a snapshot taken before it on failure
 * (the caller just calls this — or restores its own snapshot — either way
 * no mutation of a previously-rendered map ever happens in place).
 *
 * @param {Object<string, object>|null|undefined} mapa
 * @param {string} klucz
 * @param {{stan: string, data?: string, note?: string}|null|undefined} wpis
 * @returns {Object<string, object>}
 */
export function applyOptimistic(mapa, klucz, wpis) {
  const next = { ...(mapa || {}) }
  if (!wpis) {
    delete next[klucz]
  } else {
    next[klucz] = { ...wpis }
  }
  return next
}

// ---------------------------------------------------------------------------
// OZE (ops#381): pozycje zależne od formy finansowania, licznik etapu,
// etykiety stanów. Lustro `PODZADANIA_OZE` / `czy_pozycja_dla_formy` z
// `crm/volteo_pipeline.py`.
// ---------------------------------------------------------------------------

/** Dozwolone wartości `CRM Deal.custom_finansowanie_forma` (puste = nie wybrano). */
export const FORMY_FINANSOWANIA = ['100% Gotówka', '100% Kredyt', 'Gotówka + Kredyt']

/**
 * Etykiety stanów dla OZE: te same klucze i motywy co {@link STAN_META}.
 * Etykiety CP zostają w `STAN_META` bez zmian.
 */
export const STAN_META_OZE = {
  brak: { ...STAN_META.brak, label: 'Brak statusu' },
  waiting: { ...STAN_META.waiting, label: 'Oczekuje' },
  accepted: { ...STAN_META.accepted, label: 'Zaakceptowano' },
  error: { ...STAN_META.error, label: 'Błąd' },
  nd: { ...STAN_META.nd, label: 'Nie dotyczy' },
}

/**
 * Wpis metadanych stanu dla procesu: `STAN_META_OZE` dla 'OZE', inaczej
 * `STAN_META`. Nieznany stan daje wpis `brak`.
 *
 * @param {'OZE'|'CP'|null|undefined} proces
 * @param {string|null|undefined} stan
 * @returns {{theme: string, label: string, muted?: boolean}}
 */
export function metaStanu(proces, stan) {
  const tabela = proces === 'OZE' ? STAN_META_OZE : STAN_META
  return Object.hasOwn(tabela, stan ?? '') ? tabela[stan] : tabela.brak
}

/**
 * Czy pozycja jest widoczna dla formy finansowania. Brak pola `formy` (albo
 * nie-tablica) = zawsze widoczna; pusta forma ukrywa pozycje z `formy`.
 * Lustro `czy_pozycja_dla_formy`.
 *
 * @param {{formy?: string[]}|null|undefined} def
 * @param {string|null|undefined} forma
 * @returns {boolean}
 */
export function czyPozycjaDlaFormy(def, forma) {
  const formy = def?.formy
  if (!Array.isArray(formy)) return true
  return !!forma && formy.includes(forma)
}

/**
 * Pozycje widoczne dla formy finansowania (nowa tablica, wejście bez zmian).
 *
 * @param {object[]|null|undefined} zadania
 * @param {string|null|undefined} forma
 * @returns {object[]}
 */
export function pozycjeDlaFormy(zadania, forma) {
  if (!Array.isArray(zadania)) return []
  return zadania.filter((def) => czyPozycjaDlaFormy(def, forma))
}

/**
 * Licznik etapu OZE z pozycji JUŻ przefiltrowanych przez {@link pozycjeDlaFormy}:
 * `razem` = pozycje, których stan nie jest `nd`; `ok` = `accepted`; `err` = `error`.
 *
 * @param {object[]|null|undefined} zadania
 * @param {Object<string, object>|null|undefined} mapa
 * @returns {{ok: number, err: number, razem: number}}
 */
export function podsumowanieEtapu(zadania, mapa) {
  const lista = Array.isArray(zadania) ? zadania : []
  return lista.reduce(
    (acc, def) => {
      const stan = stanFor(mapa, def?.klucz)
      if (stan === 'nd') return acc
      return {
        ok: acc.ok + (stan === 'accepted' ? 1 : 0),
        err: acc.err + (stan === 'error' ? 1 : 0),
        razem: acc.razem + 1,
      }
    },
    { ok: 0, err: 0, razem: 0 },
  )
}

/**
 * Tekst licznika: "3/7 zaakceptowane", plus " \u00b7 błędy: 1" przy `err > 0`.
 * Pusty string dla null/undefined.
 *
 * @param {{ok: number, err: number, razem: number}|null|undefined} podsumowanie
 * @returns {string}
 */
export function tekstLicznika(podsumowanie) {
  if (!podsumowanie) return ''
  const { ok, err, razem } = podsumowanie
  const baza = `${ok}/${razem} zaakceptowane`
  return err > 0 ? `${baza} \u00b7 błędy: ${err}` : baza
}

/**
 * Nowa mapa stanów bez wpisów pozycji Finansowania, które nie należą do
 * wybranej formy (optymistyczna aktualizacja po zmianie formy). Pozycje bez
 * `formy` i klucze spoza katalogu zostają. Wejście bez zmian.
 *
 * @param {Object<string, object>|null|undefined} mapa
 * @param {object[]|null|undefined} zadaniaFinansowania
 * @param {string|null|undefined} forma
 * @returns {Object<string, object>}
 */
export function wyczyscPoZmianieFormy(mapa, zadaniaFinansowania, forma) {
  const wynik = { ...(mapa || {}) }
  ;(Array.isArray(zadaniaFinansowania) ? zadaniaFinansowania : []).forEach((def) => {
    if (Array.isArray(def?.formy) && !czyPozycjaDlaFormy(def, forma)) {
      delete wynik[def.klucz]
    }
  })
  return wynik
}
