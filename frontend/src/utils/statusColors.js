/**
 * Kolorowanie przycisku statusu (Deal.vue / MobileDeal.vue, nagłówek strony
 * szansy) na kolor bieżącego statusu — tło + tekst w tonacji koloru, na wzór
 * subtelnego wariantu Badge.
 *
 * Tailwind JIT skanuje TYLKO literalny tekst źródeł — string budowany w
 * runtime (np. `bg-${name}-100`) jest dla skanera niewidoczny i zostaje
 * wypurgowany. Dlatego mapa niżej jest w całości wypisana literałami (por.
 * usunięty `DealStatusBar.vue` → `BG_CLASS_MAP`, oraz komentarz na górze
 * `DealPipelineBar.vue`).
 *
 * Klasy mają prefiks `!` (important): domyślny wariant przycisku
 * (`theme="gray" variant="subtle"` we frappe-ui `Button`) niesie własne
 * `bg-surface-gray-2` + hover/active klasy tej samej specyficzności — bez
 * `!` kolejność scalenia w wygenerowanym arkuszu Tailwind JIT jest
 * nieprzewidywalna i nasze tło potrafi po cichu przegrać z domyślnym.
 * `!bg-`/`!text-` z wariantami hover/active są już safelistowane w
 * `tailwind.config.js` z dokładnie tego powodu (por. `parseColor()` w
 * `utils/index.js`, która z tego samego powodu zwraca `!text-...`).
 */
export const COLOR_BUTTON_CLASS_MAP = {
  black: '!bg-gray-800 !text-white hover:!bg-gray-900',
  gray: '!bg-gray-100 !text-gray-800 hover:!bg-gray-200',
  blue: '!bg-blue-100 !text-blue-800 hover:!bg-blue-200',
  green: '!bg-green-100 !text-green-800 hover:!bg-green-200',
  red: '!bg-red-100 !text-red-800 hover:!bg-red-200',
  pink: '!bg-pink-100 !text-pink-800 hover:!bg-pink-200',
  orange: '!bg-orange-100 !text-orange-800 hover:!bg-orange-200',
  amber: '!bg-amber-100 !text-amber-800 hover:!bg-amber-200',
  yellow: '!bg-yellow-100 !text-yellow-800 hover:!bg-yellow-200',
  cyan: '!bg-cyan-100 !text-cyan-800 hover:!bg-cyan-200',
  teal: '!bg-teal-100 !text-teal-800 hover:!bg-teal-200',
  violet: '!bg-violet-100 !text-violet-800 hover:!bg-violet-200',
  purple: '!bg-purple-100 !text-purple-800 hover:!bg-purple-200',
}

const FALLBACK_CLASS = COLOR_BUTTON_CLASS_MAP.gray

/**
 * `statusesStore()`'s `dealStatuses`/`leadStatuses` list resources overwrite
 * the raw `CRM Deal Status.color` / `CRM Lead Status.color` Select value
 * (e.g. `"orange"`) with `parseColor()`'s output (e.g. `"!text-orange-600"`,
 * or `"!text-ink-gray-9"` for `black`) before the value ever reaches a
 * component — see `stores/statuses.js`. Recover the original color name
 * from that parsed string so it can be looked up in
 * `COLOR_BUTTON_CLASS_MAP` (same trick the deleted `DealStatusBar.vue` used
 * in its `colorNameFromParsed()`).
 *
 * @param {string|undefined} parsedColorClass e.g. `getDealStatus(name).color`
 * @returns {string} a key of `COLOR_BUTTON_CLASS_MAP`
 */
export function colorNameFromParsed(parsedColorClass) {
  if (parsedColorClass === '!text-ink-gray-9') return 'black'
  const match = parsedColorClass?.match(/^!text-([a-z]+)-\d+$/)
  return match && COLOR_BUTTON_CLASS_MAP[match[1]] ? match[1] : 'gray'
}

/**
 * Full literal class string for the status button body, given a status's
 * already-parsed `color` field (as returned by `getDealStatus()` /
 * `getLeadStatus()` from `statusesStore()`).
 *
 * @param {string|undefined} parsedColorClass e.g. `getDealStatus(name).color`
 * @returns {string}
 */
export function statusButtonClass(parsedColorClass) {
  return (
    COLOR_BUTTON_CLASS_MAP[colorNameFromParsed(parsedColorClass)] ||
    FALLBACK_CLASS
  )
}
