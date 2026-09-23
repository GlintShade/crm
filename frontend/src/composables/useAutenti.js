// Autenti e-signature composable — shared lifecycle + state between
// UmowaTab.vue and KredytTab.vue (and any future tab that gains its own
// signable document). This is a straight lift-and-parameterize of the
// Autenti block that originally lived inline in UmowaTab.vue: same status
// ref, same 30s polling loop, same derived computeds, same names.
//
// Why the interval cleanup lives HERE rather than in each tab: the poll
// handle (`autentiPollInterval`) is closed over by `startAutentiPolling` /
// `stopAutentiPolling`, and `onUnmounted` must stop it on the SAME closure
// that started it — splitting "start" and "stop" across the composable and
// the host component would risk a leaked interval if a future edit moves
// one but not the other. Keeping the whole lifecycle (mount → poll →
// unmount) inside one function is what makes it safe to reuse verbatim.
//
// `docId` (ops#163) accepts a plain string, a ref, or a getter function,
// call sites differ (a prop can be read directly inside `<script setup>`,
// but passing `props.dealId` by value here would freeze it at whatever the
// value was when the composable ran), `toValue()` normalizes all three at
// each call. `docParam` is the payload key it is sent under: `'deal'`
// (default) for a document keyed by the deal itself (UmowaTab.vue, still
// exactly 1:1 with its shansa), `'kredyt'` for a document keyed by its own
// record name (KredytTab.vue, one shansa can now carry several credit-form
// records, ops#158/#159). `dealId` is kept as a backwards-compatible alias
// for `docId` so UmowaTab.vue's existing call site (`dealId: () =>
// props.dealId`) needs no change; when both are given, `docId` wins. Every
// `call()` below sends `{ [docParam]: toValue(docId ?? dealId) }`.
//
// `statusMethod` / `sendMethod` are the full dotted whitelisted-API paths
// (e.g. 'crm.integrations.autenti.api.autenti_umowa_status') — see
// UmowaTab.vue's header comment for why a bare command name silently
// resolves only for Server Scripts and 417s for fork API methods.
//
// `dokument` ('umowa' | 'kredyt', defaults to 'umowa') is passed straight
// through to `badgeFor()` / `sendButtonLabel()` (see autentiStatus.js) so
// the badge and send-button copy uses the grammatically correct Polish
// wording for whichever document this instance is signing: "Umowa" is
// feminine ("Podpisana"), "Formularz kredytowy" is masculine ("Podpisany").
// KredytTab.vue passes `dokument: 'kredyt'`; UmowaTab.vue relies on the
// default and needs no change.
//
// Record-existence key: the status payload carries `dokument_exists` on
// every endpoint, and the umowa endpoint additionally carries the legacy
// `umowa_exists` (same value, kept for whichever consumers still read it).
// `showAutentiSendButton` below reads whichever is present so it works
// unchanged against both payload shapes.
//
// `restart()` (ops#163): stops any in-flight polling, clears the current
// `autenti` status, then reloads status for whatever `docId` currently
// resolves to and restarts polling if that document turns out to be
// in-flight. KredytTab.vue calls this whenever the rep switches to a
// different credit-form record in the picker: without it, a poll interval
// started for the PREVIOUSLY selected record keeps calling `statusMethod`
// with the old `docId` closed over at `startAutentiPolling()` time (the
// interval itself does not re-read `docId`, so switching forms would
// silently keep polling, and later overwrite, the wrong record's status).
import { call, toast } from 'frappe-ui'
import { computed, onMounted, onUnmounted, ref, toValue } from 'vue'
import { formatDate } from '@/utils'
import { badgeFor, canSend, groupRecipients, isInFlight, sendButtonLabel } from '@/utils/autentiStatus'

export function useAutenti({
  dealId,
  docId = dealId,
  docParam = 'deal',
  statusMethod,
  sendMethod,
  sentToastLabel,
  dokument = 'umowa',
}) {
  // Explicit `null` initial state (never a bare `reactive` key presence
  // check — see the CLAUDE.md note on the hasOwnProperty/reactive trap that
  // froze the CP admin panel). `autenti` is a plain ref holding the whole
  // status payload as returned by statusMethod; it is replaced wholesale
  // (never mutated in place) on every load/send so Vue always sees a fresh
  // reference.
  const autenti = ref(null)
  const showAutentiConfirm = ref(false)
  const sendingAutenti = ref(false)
  let autentiPollInterval = null

  async function loadAutentiStatus() {
    try {
      const data = await call(statusMethod, { [docParam]: toValue(docId) })
      autenti.value = data || null
    } catch (err) {
      // Non-fatal and silent on purpose: this is a background status check
      // for an optional feature, not a user-triggered action. Leaving
      // `autenti` unset simply keeps the signing UI hidden, same as
      // "integration disabled" — no toast for a control the rep hasn't
      // touched.
      console.error(err)
    }
  }

  function startAutentiPolling() {
    if (autentiPollInterval) return
    autentiPollInterval = setInterval(async () => {
      await loadAutentiStatus()
      if (!isInFlight(autentiStatus.value)) stopAutentiPolling()
    }, 30000)
  }

  function stopAutentiPolling() {
    if (autentiPollInterval) {
      clearInterval(autentiPollInterval)
      autentiPollInterval = null
    }
  }

  // ops#163: switch this composable's instance to a different underlying
  // record (KredytTab.vue calls this when the rep picks a different
  // credit-form row). Stops any poll interval closed over the PREVIOUS
  // docId, clears the stale status so the UI never shows the old record's
  // badge/buttons for an instant, then reloads status for whatever docId
  // resolves to NOW and restarts polling if that fresh status is in-flight.
  async function restart() {
    stopAutentiPolling()
    autenti.value = null
    await loadAutentiStatus()
    if (isInFlight(autentiStatus.value)) startAutentiPolling()
  }

  function toggleAutentiConfirm() {
    showAutentiConfirm.value = !showAutentiConfirm.value
  }

  async function confirmSendAutenti() {
    if (sendingAutenti.value || signerMissingEmail.value) return
    sendingAutenti.value = true
    try {
      const data = await call(sendMethod, { [docParam]: toValue(docId) })
      autenti.value = autenti.value
        ? { ...autenti.value, autenti_status: data?.autenti_status || 'Wysyłanie' }
        : autenti.value
      showAutentiConfirm.value = false
      toast.success(sentToastLabel)
      startAutentiPolling()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      sendingAutenti.value = false
    }
  }

  function openSignedPdf() {
    if (autenti.value?.signed_pdf_file) {
      window.open(autenti.value.signed_pdf_file, '_blank')
    }
  }

  // --- Derived --------------------------------------------------------------
  // `enabled === false` (integration off) OR `autenti === null` (not loaded
  // yet / load failed) both mean: render NO signing UI at all — the feature
  // must stay completely invisible rather than show a half-broken control.
  const autentiEnabled = computed(() => autenti.value?.enabled === true)
  const autentiStatus = computed(() => autenti.value?.autenti_status || null)
  const autentiBadgeEntry = computed(() => badgeFor(autentiStatus.value, dokument))
  const autentiSendLabel = computed(() => sendButtonLabel(autentiStatus.value, dokument))
  // Gated on the status payload's own record-existence flag. The umowa
  // endpoint returns BOTH `dokument_exists` and the legacy `umowa_exists`
  // with the same value; the kredyt endpoint returns only `dokument_exists`.
  // Reading `dokument_exists` first (falling back to `umowa_exists`) makes
  // this computed work unchanged against either payload shape.
  const showAutentiSendButton = computed(
    () =>
      autentiEnabled.value &&
      !!(autenti.value?.dokument_exists ?? autenti.value?.umowa_exists) &&
      !!autenti.value?.pdf_exists &&
      canSend(autentiStatus.value),
  )
  const proposedSigner = computed(() => autenti.value?.proposed_signer || null)
  const signerMissingEmail = computed(() => !proposedSigner.value || !proposedSigner.value.email)
  // Grouped SIGNER/VIEWER view of `proposed_recipients` for the confirm
  // panel. Falls back to `proposedSigner` alone when the backend hasn't
  // shipped `proposed_recipients` yet — see groupRecipients() for why.
  const recipientGroups = computed(() =>
    groupRecipients(autenti.value?.proposed_recipients, proposedSigner.value),
  )
  const autentiSentAtDisplay = computed(() =>
    autenti.value?.sent_at ? formatDate(autenti.value.sent_at, null, true, true) : '',
  )
  const autentiSignedAtDisplay = computed(() =>
    autenti.value?.signed_at ? formatDate(autenti.value.signed_at, null, true, true) : '',
  )

  onMounted(() => {
    loadAutentiStatus().then(() => {
      if (isInFlight(autentiStatus.value)) startAutentiPolling()
    })
  })
  onUnmounted(stopAutentiPolling)

  return {
    autenti,
    showAutentiConfirm,
    sendingAutenti,
    loadAutentiStatus,
    startAutentiPolling,
    stopAutentiPolling,
    toggleAutentiConfirm,
    confirmSendAutenti,
    openSignedPdf,
    restart,
    autentiEnabled,
    autentiStatus,
    autentiBadgeEntry,
    autentiSendLabel,
    showAutentiSendButton,
    proposedSigner,
    signerMissingEmail,
    recipientGroups,
    autentiSentAtDisplay,
    autentiSignedAtDisplay,
  }
}

// Local copy of the same error-message extraction UmowaTab.vue and
// KredytTab.vue each already define for their own save/PDF calls — kept
// private to this composable so `confirmSendAutenti`'s toast matches the
// exact same Polish fallback copy without forcing either tab to export
// theirs or import a third shared module for one function.
// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) — but that
// pattern was blind to the actual shape of errors thrown by frappe-ui's
// call() (see frontend/node_modules/frappe-ui/src/utils/frappeRequest.js
// ~L82-124): call() consumes _server_messages itself and re-throws an
// error whose `message` is just "{url} {exc_type}" and whose `messages` is
// the already-parsed array of server message strings (the Polish text
// lives there, not under `_server_messages`/`exception`). Without the
// `err.messages` branch below, the name-mismatch ValidationError always
// fell through to the raw "{url} {exc_type}" fallback instead of the
// server's Polish message. The old `_server_messages`/`exception` branches
// are kept as a fallback for any caller that isn't call().
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Wystąpił błąd - spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd - spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd - spróbuj ponownie')
}
