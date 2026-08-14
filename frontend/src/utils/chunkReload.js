// Detects "stale build artifact" errors caused by dynamic import() failures.
//
// Why this exists: every production deploy deletes the old hashed chunk
// files from the server. A browser that still holds the OLD document — an
// open tab, or the service worker's precached index.html (vite-plugin-pwa,
// registerType: 'autoUpdate') — then lazy-loads a route chunk that no
// longer exists on disk. The dynamic import rejects and the app is left on
// a blank page; the fix is a single reload to fetch the current document
// and its current chunk manifest. `autoUpdate` updates the *service
// worker*, it does not rescue a page that is already loaded and mid-navigation.
//
// This module is frappe-free and pure (no DOM access) so it is unit
// testable in isolation, same convention as autentiStatus.js. The
// DOM-touching parts (sessionStorage, window.location.reload) live in
// router.js, where they are wired to router.onError and the
// 'vite:preloadError' window event.
//
// Loop protection is time-based (a cooldown), not navigation-based. An
// earlier version cleared its "already reloaded" flag in router.afterEach,
// which looked safe but wasn't: `vite:preloadError` fires independently of
// navigation, so a successful navigation to an already-cached route can
// clear the flag while a *different*, still-missing lazy chunk keeps
// failing in the background (or the SW app-shell serves cached routes
// successfully while an offline user's uncached chunk keeps failing) —
// each clear re-arms the guard and the page reloads forever. A cooldown
// keyed only to wall-clock time cannot be shortened by any sequence of
// navigations, so that loop is structurally impossible. See `shouldReload`.

// Different browsers/bundler versions word this differently, so match a set
// of case-insensitive substrings rather than one exact string.
const STALE_CHUNK_PATTERNS = [
  'importing a module script failed',
  'failed to fetch dynamically imported module',
  'error loading dynamically imported module',
]

/**
 * Whether `error` looks like a failed dynamic import of a route/preload
 * chunk that no longer exists on the server (stale deploy), as opposed to
 * any other runtime error.
 *
 * @param {unknown} error - the value caught from router.onError or the
 *   'vite:preloadError' event's `event.payload`. May be a real Error, a
 *   plain object, null, or undefined.
 * @returns {boolean}
 */
export function isStaleChunkError(error) {
  const message = error?.message
  if (typeof message !== 'string' || !message) return false
  const lowerMessage = message.toLowerCase()
  return STALE_CHUNK_PATTERNS.some((pattern) => lowerMessage.includes(pattern))
}

/**
 * Whether enough time has passed since the last stale-chunk reload to allow
 * another one. Pure decision function over a raw sessionStorage read — the
 * caller owns actually reading/writing sessionStorage and reloading.
 *
 * `storedValue` is whatever sessionStorage.getItem() returned: null when no
 * reload has happened yet (or the tab is new), otherwise a string the
 * caller previously wrote via `String(Date.now())`. Anything that isn't a
 * finite timestamp (missing, empty, garbage, NaN) is treated as "no recent
 * reload" so the guard fails open toward allowing the first reload — never
 * open toward looping, since a fresh timestamp is written before the
 * reload happens.
 *
 * A stored timestamp in the future (clock skew, or a tab suspended across
 * a system clock change) is treated as recent — i.e. reload is withheld —
 * rather than as elapsed, so skew can only make the guard more
 * conservative, never trigger an extra reload.
 *
 * @param {string|null|undefined} storedValue - raw sessionStorage value
 * @param {number} now - current time in ms, typically Date.now()
 * @param {number} cooldownMs - minimum ms required since the last reload
 * @returns {boolean}
 */
export function shouldReload(storedValue, now, cooldownMs) {
  if (storedValue === null || storedValue === undefined || storedValue === '') return true
  const lastReloadAt = Number(storedValue)
  if (!Number.isFinite(lastReloadAt)) return true
  const elapsed = now - lastReloadAt
  if (elapsed < 0) return false // stored timestamp is in the future — clock skew, treat as recent
  return elapsed >= cooldownMs
}
