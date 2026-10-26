// Autenti e-signature composable - shared lifecycle + state between
// UmowaTab.vue, UmowaCPTab.vue and KredytTab.vue (and any future tab that
// gains its own signable document).
//
// Odświeżanie statusu (ops#303): BEZ odpytywania co 30 s. Status w bazie
// zmienia wyłącznie serwer (zadanie wysyłki i poller co 10 min), a każdy taki
// zapis publikuje zdarzenie `volteo_autenti_status` do pokoju dokumentu
// szansy (`CRM Deal`/<deal>). Składowa subskrybuje ten pokój przy montowaniu,
// po zdarzeniu dla swojej szansy pobiera stan istniejącym endpointem
// (uprawnienia sprawdza on, zdarzenie niesie tylko nazwę szansy), a odsubskrybowuje
// przy odmontowaniu. Dla martwego gniazda: dodatkowe odświeżenie gdy karta
// znów jest widoczna, po `connect` (z ponowną subskrypcją, bo pokoje giną wraz
// z połączeniem) i jednorazowo ok. 10 s po udanej wysyłce. Powód: stare
// odpytywanie trafiało w wyścig limitera Frappe, dostawało HTTP 429, a porzucony
// timer odpytywania żył do przeładowania strony.
//
// Flaga `aktywny`: każda asynchroniczna kontynuacja po odmontowaniu jest no-op,
// nic nie startuje po `onUnmounted`.
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
// (e.g. 'crm.integrations.autenti.api.autenti_umowa_status') - see
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
// `restart()` (ops#163): czyści bieżący status i przeładowuje go dla tego, na co
// `docId` wskazuje TERAZ. KredytTab.vue woła to, gdy przedstawiciel przełącza
// się na inny formularz kredytowy w pickerze.
//
// `dealId` jest nazwą szansy (pokój zdarzeń); dla KredytTab.vue, gdzie `docId`
// to nazwa formularza, trzeba go podać osobno.
import { call, toast } from 'frappe-ui'
import { computed, getCurrentInstance, onMounted, onUnmounted, ref, toValue, watch } from 'vue'
import { formatDate } from '@/utils'
import { badgeFor, canSend, groupRecipients, sendButtonLabel } from '@/utils/autentiStatus'

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
  // check - see the CLAUDE.md note on the hasOwnProperty/reactive trap that
  // froze the CP admin panel). `autenti` is a plain ref holding the whole
  // status payload as returned by statusMethod; it is replaced wholesale
  // (never mutated in place) on every load/send so Vue always sees a fresh
  // reference.
  const autenti = ref(null)
  const showAutentiConfirm = ref(false)
  const sendingAutenti = ref(false)
  // `aktywny`: true od utworzenia do odmontowania; po odmontowaniu każda
  // kontynuacja asynchroniczna jest no-op.
  let aktywny = true
  let odswiezeniePoWysylce = null
  const socket = getCurrentInstance()?.appContext.config.globalProperties.$socket || null
  const nazwaSzansy = () => toValue(dealId ?? docId)

  async function loadAutentiStatus() {
    // Guard, ops#163 follow-up: KredytTab.vue's docId getter is
    // `() => wybrany.value?.name`, and `wybrany` starts as `null` until the
    // initial list/record fetch resolves. Without this check, the
    // composable's own onMounted below fires this function immediately with
    // `toValue(docId)` still undefined; `JSON.stringify` then drops the
    // `undefined` value entirely from the request body, so the server sees
    // no `kredyt` key at all, not an empty one, and
    // `autenti_kredyt_status(kredyt: str)` (a required, non-default
    // parameter at the time this guard was added) throws a raw
    // `TypeError: missing 1 required positional argument`, surfaced to the
    // browser as an unhandled HTTP 500 on every ordinary tab visit. Skipping
    // the call and resetting `autenti` to null when there is no record name
    // yet is exactly the "no-op" behaviour KredytTab.vue's own comment above
    // its useAutenti() call already assumed was in place.
    const nazwa = toValue(docId ?? dealId)
    if (!nazwa) {
      autenti.value = null
      return
    }
    try {
      const data = await call(statusMethod, { [docParam]: nazwa })
      if (!aktywny) return
      autenti.value = data || null
    } catch (err) {
      // Non-fatal and silent on purpose: this is a background status check
      // for an optional feature, not a user-triggered action. Leaving
      // `autenti` unset simply keeps the signing UI hidden, same as
      // "integration disabled" - no toast for a control the rep hasn't
      // touched.
      console.error(err)
    }
  }

  function onAutentiZdarzenie(payload) {
    if (!aktywny) return
    if (!payload || payload.deal !== nazwaSzansy()) return
    loadAutentiStatus()
  }

  function subskrybuj(deal) {
    if (socket && deal) socket.emit('doc_subscribe', 'CRM Deal', deal)
  }

  function odsubskrybuj(deal) {
    if (socket && deal) socket.emit('doc_unsubscribe', 'CRM Deal', deal)
  }

  function onWidocznosc() {
    if (aktywny && document.visibilityState === 'visible') loadAutentiStatus()
  }

  function onPolaczenie() {
    if (!aktywny) return
    // Pokoje socket.io giną razem z połączeniem, po reconnect trzeba je odtworzyć.
    subskrybuj(nazwaSzansy())
    loadAutentiStatus()
  }

  // ops#163: przełączenie instancji na inny rekord (KredytTab.vue, picker
  // formularzy). Czyści nieaktualny status, żeby UI nie pokazał na chwilę
  // badge'a poprzedniego rekordu, i ładuje stan dla bieżącego `docId`.
  async function restart() {
    autenti.value = null
    await loadAutentiStatus()
  }

  function toggleAutentiConfirm() {
    showAutentiConfirm.value = !showAutentiConfirm.value
  }

  async function confirmSendAutenti() {
    if (sendingAutenti.value || signerMissingEmail.value) return
    // Same guard as loadAutentiStatus: in practice `showAutentiSendButton`
    // already keeps this unreachable with a falsy docId (it requires
    // `dokument_exists`, which only comes from a status payload that could
    // not have loaded yet), but the send endpoint is a legally binding
    // action, so this stays defensive rather than relying on that UI gate
    // alone.
    const nazwa = toValue(docId ?? dealId)
    if (!nazwa) return
    sendingAutenti.value = true
    try {
      const data = await call(sendMethod, { [docParam]: nazwa })
      autenti.value = autenti.value
        ? { ...autenti.value, autenti_status: data?.autenti_status || 'Wysyłanie' }
        : autenti.value
      showAutentiConfirm.value = false
      toast.success(sentToastLabel)
      // Zapas na martwe gniazdo: jedno odświeżenie ok. 10 s po wysyłce.
      clearTimeout(odswiezeniePoWysylce)
      odswiezeniePoWysylce = setTimeout(() => {
        odswiezeniePoWysylce = null
        if (aktywny) loadAutentiStatus()
      }, 10000)
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
  // yet / load failed) both mean: render NO signing UI at all - the feature
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
  // shipped `proposed_recipients` yet - see groupRecipients() for why.
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
    loadAutentiStatus()
    subskrybuj(nazwaSzansy())
    if (socket) {
      socket.on('volteo_autenti_status', onAutentiZdarzenie)
      socket.on('connect', onPolaczenie)
    }
    document.addEventListener('visibilitychange', onWidocznosc)
  })

  // Ta sama składowa może dostać inną szansę (prop się zmienia bez remontu).
  watch(nazwaSzansy, (nowa, stara) => {
    if (!aktywny) return
    odsubskrybuj(stara)
    subskrybuj(nowa)
  })

  onUnmounted(() => {
    aktywny = false
    clearTimeout(odswiezeniePoWysylce)
    odswiezeniePoWysylce = null
    document.removeEventListener('visibilitychange', onWidocznosc)
    if (socket) {
      socket.off('volteo_autenti_status', onAutentiZdarzenie)
      socket.off('connect', onPolaczenie)
    }
    odsubskrybuj(nazwaSzansy())
  })

  return {
    autenti,
    showAutentiConfirm,
    sendingAutenti,
    loadAutentiStatus,
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
// KredytTab.vue each already define for their own save/PDF calls - kept
// private to this composable so `confirmSendAutenti`'s toast matches the
// exact same Polish fallback copy without forcing either tab to export
// theirs or import a third shared module for one function.
// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) - but that
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
