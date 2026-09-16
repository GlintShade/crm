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
 * Kredyt-only label overrides for `AUTENTI_BADGE` above. The backend has
 * separate per-document Polish sentences for the same reason (see
 * `crm/integrations/autenti/api.py`'s `KONFIG_UMOWA` / `KONFIG_KREDYT`
 * comments): "Umowa" (the contract) is grammatically feminine, "Formularz
 * kredytowy" (the credit application) is masculine, so the same status
 * needs a different adjective ending per document.
 *
 * 'Wysyłanie' and 'Błąd' carry no gendered noun and are not listed here:
 * `badgeFor` falls back to the shared `AUTENTI_BADGE` label for them.
 */
const AUTENTI_BADGE_LABEL_KREDYT = {
  Wysłana: 'Wysłany do podpisu',
  Podpisana: 'Podpisany',
  Odrzucona: 'Odrzucony',
  Wygasła: 'Wygasły',
  Wycofana: 'Wycofany',
}

/**
 * Look up the badge entry ({label, theme}) for a status, or `null` when the
 * document was never sent (status is `null`/`undefined`/`''`), the caller
 * should render no badge at all in that case, not a "never sent" badge.
 *
 * `__()` is called here, inside the function body, never at module scope:
 * calling it while the object literals above are being built would risk
 * the eager-chunk `ReferenceError` described in CLAUDE.md → "Eager chunk a
 * __()" (see the same pattern in `edytorPrzyciski.js`'s `zbudujPrzycisk`).
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @param {'umowa'|'kredyt'} [dokument] - which document's wording to use;
 *   defaults to 'umowa' so every existing caller keeps behaving exactly as
 *   before
 * @returns {{label: string, theme: string}|null}
 */
export function badgeFor(status, dokument = 'umowa') {
  if (!status) return null
  const entry = AUTENTI_BADGE[status]
  if (!entry) return null
  const label = dokument === 'kredyt' ? AUTENTI_BADGE_LABEL_KREDYT[status] || entry.label : entry.label
  return { label: __(label), theme: entry.theme }
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
 * First-send button label, by document. "Podpisz umowę" only makes sense
 * for the umowa (contract); the kredyt (credit application) uses
 * "wniosek", mirroring the backend's per-document literals, see the
 * `AUTENTI_BADGE_LABEL_KREDYT` comment above.
 */
const SEND_LABEL_FIRST = {
  umowa: 'Podpisz umowę',
  kredyt: 'Podpisz wniosek',
}

// The resend label needs no gendered noun ("do podpisu"), so it is shared
// by both documents.
const SEND_LABEL_RESEND = 'Wyślij ponownie do podpisu'

/**
 * Label for the send/resend button, depending on whether the document has
 * ever been sent before, and which document this is for.
 *
 * `__()` is called here, inside the function body, see the note on
 * `badgeFor` above for why that matters.
 *
 * @param {string|null|undefined} status - raw `autenti_status` value
 * @param {'umowa'|'kredyt'} [dokument] - defaults to 'umowa' so every
 *   existing caller keeps behaving exactly as before
 * @returns {string} 'Podpisz umowę'/'Podpisz wniosek' for never-sent,
 *   'Wyślij ponownie do podpisu' otherwise
 */
export function sendButtonLabel(status, dokument = 'umowa') {
  if (status && RESEND_STATUSES.has(status)) {
    return __(SEND_LABEL_RESEND)
  }
  return __(SEND_LABEL_FIRST[dokument] || SEND_LABEL_FIRST.umowa)
}

/**
 * Groups the confirm panel's recipient list into signers and viewers.
 *
 * `recipients` is the new `proposed_recipients` payload (up to four entries:
 * client + co-signer as SIGNER, sending rep + archive mailbox as VIEWER,
 * already ordered/deduped/email-filtered server-side). When it's missing or
 * empty — an old backend payload mid-rollout, before this endpoint gains the
 * field — this falls back to treating `fallbackSigner` (the pre-existing
 * `proposed_signer` shape, `{full_name, email}`) as the sole signer, so the
 * confirm panel degrades to exactly what it rendered before this change
 * instead of ever showing an empty recipients block.
 *
 * @param {Array<{full_name: string, email: string, role: string}>|null|undefined} recipients
 * @param {{full_name: string, email: string}|null|undefined} fallbackSigner
 * @returns {{signers: Array, viewers: Array}}
 */
export function groupRecipients(recipients, fallbackSigner) {
  const list =
    Array.isArray(recipients) && recipients.length
      ? recipients
      : fallbackSigner
        ? [{ full_name: fallbackSigner.full_name, email: fallbackSigner.email, role: 'SIGNER' }]
        : []
  return {
    signers: list.filter((r) => r.role === 'SIGNER'),
    viewers: list.filter((r) => r.role === 'VIEWER'),
  }
}
