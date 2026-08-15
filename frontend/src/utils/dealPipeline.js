// Pure node-state logic for the deal pipeline stepper band (DealPipelineBar.vue).
//
// Frappe-free by design (no `frappe-ui` / `@/` imports pulling in Vue or the
// app runtime) so it can be unit-tested directly, same convention as
// autentiStatus.js / cpForm.js / cpMarza.js / money.js.
//
// The backend (`crm.volteo_pipeline`, via `crm.api.pipeline.volteo_pipeline_get`)
// is the single source of truth for the pipeline SHAPE per `rodzaj` — which
// steps exist, their order, their labels, and the "what's next" note per
// status (`payload.steps`, `payload.notes`). It is deliberately NOT the
// source of truth for the CURRENT step: `payload.current_index` (and the
// other status-derived fields on the payload) are a snapshot taken at fetch
// time, and the component only re-fetches the payload when `rodzaj` changes,
// not on every status change — reloading on every status change is exactly
// what raced the in-flight status SAVE and caused the pipeline band to lag
// one step behind. Current step, mode, note and badge are derived HERE, at
// call time, from the caller's own `status` (client truth, e.g. `props.status`
// straight from the dropdown) and `statusType` (from the statuses store),
// never from `payload.current_index` / `payload.off_pipeline*` / `payload.status`.

/**
 * Payload kształtu (dostarczanego przez backend):
 * {
 *   rodzaj, status,
 *   steps: [{ status, index }, ...],
 *   notes: { [status]: noteText, ... },
 *   current_index, off_pipeline, off_pipeline_type, note, // migawka — patrz wyżej, NIEUŻYWANE tutaj
 * }
 */

/**
 * Wyznacza indeks statusu w krokach rurociągu.
 *
 * @param {Array<{status: string, index: number}>|null|undefined} steps
 * @param {string|null|undefined} status
 * @returns {number} indeks w `steps` (dopasowanie po `step.status`), albo -1 gdy brak/nie znaleziono.
 */
export function currentIndexFor(steps, status) {
  if (!Array.isArray(steps) || steps.length === 0) return -1
  if (!status) return -1
  const znaleziony = steps.find((step) => step?.status === status)
  return znaleziony ? znaleziony.index : -1
}

/**
 * Wyznacza tryb renderowania całego paska etapów na podstawie payloadu
 * (kształt), statusu (prawda kliencka) i typu tego statusu (ze store'u statusów).
 *
 * - 'hidden' — brak payloadu, albo `steps` puste/nieobecne (deal bez
 *   rodzaju albo z nierozpoznanym rodzajem — pasek się nie renderuje).
 * - 'progress' — `status` jest jednym z kroków rurociągu (niezależnie od
 *   tego, co mówi migawkowe `payload.current_index` — ono jest nieużywane).
 * - 'lost' — status POZA rurociągiem, `statusType === 'Lost'`.
 * - 'won' — status POZA rurociągiem, `statusType === 'Won'`.
 * - 'unknown' — status POZA rurociągiem, a `statusType` inny/nieznany
 *   (obcy status spoza Lost/Won, albo store statusów jeszcze nie załadowany).
 *
 * @param {{steps?: Array, notes?: Object}|null|undefined} payload
 * @param {string|null|undefined} status
 * @param {string|null|undefined} statusType
 * @returns {'hidden'|'progress'|'won'|'lost'|'unknown'}
 */
export function bandMode(payload, status, statusType) {
  if (!payload) return 'hidden'
  if (!Array.isArray(payload.steps) || payload.steps.length === 0) return 'hidden'

  if (currentIndexFor(payload.steps, status) >= 0) return 'progress'

  if (statusType === 'Lost') return 'lost'
  if (statusType === 'Won') return 'won'
  return 'unknown'
}

/**
 * Stan pojedynczego węzła w trybie 'progress': porównanie jego indeksu
 * z indeksem bieżącego etapu.
 *
 * @param {number} index - indeks węzła
 * @param {number} currentIndex - indeks bieżącego etapu
 * @returns {'done'|'current'|'future'}
 */
export function nodeState(index, currentIndex) {
  if (index < currentIndex) return 'done'
  if (index === currentIndex) return 'current'
  return 'future'
}

/**
 * Stan węzła z uwzględnieniem trybu całego paska:
 * - 'won' — wszystkie węzły renderują się jako ukończone.
 * - 'lost' / 'unknown' — wszystkie węzły wyciszone (szare), niezależnie od indeksu.
 * - 'progress' — deleguje do {@link nodeState}.
 * - 'hidden' — nieużywane (pasek się nie renderuje), ale dla bezpieczeństwa
 *   traktowane jak 'muted'.
 *
 * @param {'hidden'|'progress'|'won'|'lost'|'unknown'} mode
 * @param {number} index
 * @param {number} currentIndex
 * @returns {'done'|'current'|'future'|'muted'}
 */
export function nodeStateForMode(mode, index, currentIndex) {
  if (mode === 'won') return 'done'
  if (mode === 'lost' || mode === 'unknown') return 'muted'
  if (mode === 'progress') return nodeState(index, currentIndex)
  return 'muted'
}

/**
 * Numer wyświetlany przy węźle (1-based).
 *
 * @param {number} index
 * @returns {number}
 */
export function stepNumber(index) {
  return index + 1
}

/**
 * Notatka o następnym kroku — pokazywana tylko w trybie 'progress'; pusty
 * lub sam biały znak traktowany jak brak notatki. Czyta `payload.notes[status]`
 * (kształt, per rurociąg), NIE migawkowe `payload.note`.
 *
 * @param {{steps?: Array, notes?: Object}|null|undefined} payload
 * @param {string|null|undefined} status
 * @param {string|null|undefined} statusType
 * @returns {string|null}
 */
export function nextStepNote(payload, status, statusType) {
  if (bandMode(payload, status, statusType) !== 'progress') return null
  const note = payload.notes?.[status]
  if (typeof note !== 'string') return null
  if (note.trim() === '') return null
  return note
}

/**
 * Surowa nazwa statusu do pokazania w odznace paska poza pipeline'em
 * ('lost' / 'won' / 'unknown'); w trybie 'progress'/'hidden' brak odznaki.
 *
 * @param {{steps?: Array, notes?: Object}|null|undefined} payload
 * @param {string|null|undefined} status
 * @param {string|null|undefined} statusType
 * @returns {string|null}
 */
export function offPipelineBadge(payload, status, statusType) {
  const mode = bandMode(payload, status, statusType)
  if (mode === 'lost' || mode === 'won' || mode === 'unknown') {
    return status
  }
  return null
}
