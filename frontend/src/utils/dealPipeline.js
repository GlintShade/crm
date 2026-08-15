// Pure node-state logic for the deal pipeline stepper band (DealPipelineBar.vue).
//
// Frappe-free by design (no `frappe-ui` / `@/` imports pulling in Vue or the
// app runtime) so it can be unit-tested directly, same convention as
// autentiStatus.js / cpForm.js / cpMarza.js / money.js.
//
// The backend (`crm.volteo_pipeline`) is the single source of truth for the
// pipeline shape per `rodzaj` (which steps exist, their order, their
// labels) and for the off-pipeline statuses ('Lost' / 'Won' / other). This
// module never hardcodes a pipeline shape or a status name — it only reads
// the payload's own `steps`, `current_index` and `off_pipeline*` fields and
// derives display state from them.

/**
 * Payload kształtu (dostarczanego przez backend):
 * {
 *   rodzaj, status,
 *   steps: [{ status, index }, ...],
 *   current_index,
 *   off_pipeline,
 *   off_pipeline_type, // 'Lost' | 'Won' | null
 *   note,
 * }
 */

/**
 * Wyznacza tryb renderowania całego paska etapów na podstawie payloadu.
 *
 * - 'hidden' — brak payloadu, albo `steps` puste/nieobecne (deal bez
 *   rodzaju albo z nierozpoznanym rodzajem — pasek się nie renderuje).
 * - 'lost' — deal poza pipeline'em, `off_pipeline_type === 'Lost'`.
 * - 'won' — deal poza pipeline'em, `off_pipeline_type === 'Won'`.
 * - 'unknown' — deal poza pipeline'em, ale z innym typem (obcy status spoza
 *   Lost/Won) — pasek renderuje się szaro z surową nazwą statusu.
 * - 'progress' — normalny przebieg wewnątrz pipeline'u.
 *
 * @param {{steps?: Array, off_pipeline?: boolean, off_pipeline_type?: string|null}|null|undefined} payload
 * @returns {'hidden'|'progress'|'won'|'lost'|'unknown'}
 */
export function bandMode(payload) {
  if (!payload) return 'hidden'
  if (!Array.isArray(payload.steps) || payload.steps.length === 0) return 'hidden'

  if (payload.off_pipeline) {
    if (payload.off_pipeline_type === 'Lost') return 'lost'
    if (payload.off_pipeline_type === 'Won') return 'won'
    return 'unknown'
  }

  return 'progress'
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
 * lub sam biały znak traktowany jak brak notatki.
 *
 * @param {{steps?: Array, off_pipeline?: boolean, off_pipeline_type?: string|null, note?: string|null}|null|undefined} payload
 * @returns {string|null}
 */
export function nextStepNote(payload) {
  if (bandMode(payload) !== 'progress') return null
  const note = payload.note
  if (typeof note !== 'string') return null
  if (note.trim() === '') return null
  return note
}

/**
 * Surowa nazwa statusu do pokazania w odznace paska poza pipeline'em
 * ('lost' / 'won' / 'unknown'); w trybie 'progress'/'hidden' brak odznaki.
 *
 * @param {{status?: string, steps?: Array, off_pipeline?: boolean, off_pipeline_type?: string|null}|null|undefined} payload
 * @returns {string|null}
 */
export function offPipelineBadge(payload) {
  const mode = bandMode(payload)
  if (mode === 'lost' || mode === 'won' || mode === 'unknown') {
    return payload.status
  }
  return null
}
