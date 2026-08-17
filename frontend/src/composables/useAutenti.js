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
// `dealId` accepts a plain string, a ref, or a getter function — call sites
// differ (a prop can be read directly inside `<script setup>`, but passing
// `props.dealId` by value here would freeze it at whatever the value was
// when the composable ran) — `toValue()` normalizes all three at each call.
//
// `statusMethod` / `sendMethod` are the full dotted whitelisted-API paths
// (e.g. 'crm.integrations.autenti.api.autenti_umowa_status') — see
// UmowaTab.vue's header comment for why a bare command name silently
// resolves only for Server Scripts and 417s for fork API methods.
//
// Record-existence key: the status payload carries `dokument_exists` on
// every endpoint, and the umowa endpoint additionally carries the legacy
// `umowa_exists` (same value, kept for whichever consumers still read it).
// `showAutentiSendButton` below reads whichever is present so it works
// unchanged against both payload shapes.
import { call, toast } from 'frappe-ui'
import { computed, onMounted, onUnmounted, ref, toValue } from 'vue'
import { formatDate } from '@/utils'
import { badgeFor, canSend, groupRecipients, isInFlight, sendButtonLabel } from '@/utils/autentiStatus'

export function useAutenti({ dealId, statusMethod, sendMethod, sentToastLabel }) {
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
      const data = await call(statusMethod, { deal: toValue(dealId) })
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

  function toggleAutentiConfirm() {
    showAutentiConfirm.value = !showAutentiConfirm.value
  }

  async function confirmSendAutenti() {
    if (sendingAutenti.value || signerMissingEmail.value) return
    sendingAutenti.value = true
    try {
      const data = await call(sendMethod, { deal: toValue(dealId) })
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
  const autentiBadgeEntry = computed(() => badgeFor(autentiStatus.value))
  const autentiSendLabel = computed(() => sendButtonLabel(autentiStatus.value))
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
function extractErrorMessage(err) {
  try {
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
