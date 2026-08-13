// Autenti e-signature status helpers for the Umowa tab (UmowaTab.vue).
//
// Frappe-free by design (no `frappe-ui` / `@/` imports pulling in Vue or the
// app runtime) so it can be unit-tested directly, same convention as
// cpForm.js / cpMarza.js / money.js.
//
// The backend (`crm.integrations.autenti.api`) is the single source of
// truth for `autenti_status` values and their transitions; this module only
// maps a known status string to Polish display copy and to the small set of
// booleans the tab's template needs. It must NOT invent new statuses or
// re-derive send-eligibility logic independently of the backend's
// SEND_BLOCKED_STATUSES — see `canSend` below, which mirrors it.

/**
 * Display metadata for every known `autenti_status` value: the Polish label
 * shown in the badge and the `frappe-ui` `Badge` `theme` to render it with.
 *
 * Themes are restricted to what `Badge.vue` actually accepts (gray, blue,
 * green, amber, red, violet — `orange` is only a deprecated alias for
 * `amber`), so 'Wysłana' uses `amber` directly rather than the alias.
 * Never-sent (`null`/`''`) has no entry here — see `badgeFor`.
 */
export const AUTENTI_BADGE = {
  Wysyłanie: { label: 'Wysyłanie…', theme: 'blue' },
  Wysłana: { label: 'Wysłana do podpisu', theme: 'amber' },
  Podpisana: { label: 'Podpisana', theme: 'green' },
  Odrzucona: { label: 'Odrzucona', theme: 'red' },
  Wygasła: { label: 'Wygasła', theme: 'gray' },
  Wycofana: { label: 'Wycofana', theme: 'gray' },
  Błąd: { label: 'Błąd wysyłki', theme: 'red' },
}

/**
 * Look up the badge entry ({label, theme}) for a status, or `null` when the
 * umowa was never sent (status is `null`/`undefined`/`''`) — the caller
 * should render no badge at all in that case, not a "never sent" badge.
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @returns {{label: string, theme: string}|null}
 */
export function badgeFor(status) {
  if (!status) return null
  return AUTENTI_BADGE[status] || null
}

// Mirrors the backend's SEND_BLOCKED_STATUSES: sending (or resending) is
// blocked while a send is in flight or already succeeded. Every other
// status — including never-sent — is safe to (re)send from.
const SEND_BLOCKED_STATUSES = new Set(['Wysyłanie', 'Wysłana', 'Podpisana'])

/**
 * Whether the "Podpisz umowę" / "Wyślij ponownie" action should be
 * available for the given status. True for never-sent, 'Błąd', 'Odrzucona',
 * 'Wygasła', 'Wycofana'; false while in flight or already signed.
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @returns {boolean}
 */
export function canSend(status) {
  if (!status) return true
  return !SEND_BLOCKED_STATUSES.has(status)
}

// Statuses that mean "a send is currently in progress" — drives the 30s
// polling loop in UmowaTab.vue. Deliberately narrower than `!canSend`:
// 'Podpisana' is also blocked from sending but is a terminal state, not one
// that should keep polling.
const IN_FLIGHT_STATUSES = new Set(['Wysyłanie', 'Wysłana'])

/**
 * Whether a send is currently in progress and the tab should keep polling
 * `autenti_umowa_status` for an update.
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @returns {boolean}
 */
export function isInFlight(status) {
  if (!status) return false
  return IN_FLIGHT_STATUSES.has(status)
}

// Statuses after which a resend is offered — everything canSend() allows
// except the never-sent case, which gets its own first-send label.
const RESEND_STATUSES = new Set(['Błąd', 'Odrzucona', 'Wygasła', 'Wycofana'])

/**
 * Label for the send/resend button, depending on whether the umowa has
 * ever been sent before.
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @returns {string} 'Podpisz umowę' for never-sent, 'Wyślij ponownie do podpisu' otherwise
 */
export function sendButtonLabel(status) {
  if (status && RESEND_STATUSES.has(status)) {
    return 'Wyślij ponownie do podpisu'
  }
  return 'Podpisz umowę'
}
