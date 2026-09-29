<!--
  UmowaCPTab.vue - Czyste Powietrze variant of the deal's "Umowa" tab
  (issue GlintShade/proenergy-crm-ops#212). Renders instead of UmowaTab.vue
  (the OZE contract form) whenever `doc.custom_rodzaj_umowy === 'Czyste
  Powietrze'` - see Deal.vue's `tabs` computed, where the two tabs share the
  name-in-spirit ("Umowa") but are mutually exclusive, mirroring the
  existing Audyt/AudytCP pair.

  This is a SEPARATE, small form, NOT a trimmed copy wired to import from
  UmowaTab.vue - the two never share code, only the backend endpoints
  (crm.api.umowa.volteo_umowa_get/create/save/pdf,
  crm.integrations.autenti.api.autenti_umowa_status/autenti_send_umowa),
  which branch server-side by the deal's rodzaj. Structure (loading/
  loadError/empty/form, Autenti block, missing-fields banner, draft-safe
  save) is copied from UmowaTab.vue/KredytTab.vue's established pattern;
  see those files for the reasoning behind each piece this one reuses.

  API contract for CP (as specified by the backend worker building this in
  parallel - read defensively, the shapes below are not yet verified
  end-to-end against a live server):
    umowa.wynagrodzenie_wariant       "1" | "2" | "" | null
    umowa.wynagrodzenie_netto_pln     saved snapshot, read-only, may be null
    umowa.wynagrodzenie_brutto_pln    saved snapshot, read-only, may be null
    umowa.zgoda_przetwarzanie_danych  0/1
    umowa.zgoda_kontakt_telefoniczny  0/1
    umowa.zgoda_dzialania_promocyjne  0/1
    wyliczenia.warianty_wynagrodzenia [{wariant, netto, brutto}, ...]
    wyliczenia.klient                 {imie_nazwisko, adres, pesel, telefon, email}
    wyliczenia.brakujace_pola         e.g. ["wynagrodzenie_wariant"]
    wyliczenia.brakujace_dane_klienta Polish labels, e.g. ["PESEL", "E-mail"]

  `volteo_umowa_save` for CP accepts ONLY the 4 editable fields above (see
  buildPayload()) - never the OZE form's fieldnames.

  No cost/margin/commission values are shown here - contract data is
  client-facing only, same rule as UmowaTab.vue.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-2xl">
      <!-- Loading -->
      <div v-if="loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <!-- Load failed - bail out, never render a misleading state -->
      <div
        v-else-if="loadError"
        class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
      >
        {{ loadError }}
      </div>

      <!-- Empty state - no umowa yet -->
      <div
        v-else-if="!umowa"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <UmowaIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak formularza umowy') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{
            __(
              'Wygeneruj formularz umowy o świadczenie usług obsługi dofinansowania, aby zebrać dane potrzebne do jej przygotowania.',
            )
          }}
        </div>
        <Button
          variant="solid"
          :label="__('Wygeneruj umowę')"
          :disabled="creating"
          :loading="creating"
          @click="createUmowa"
        />
      </div>

      <!-- Form -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="text-lg font-semibold text-ink-gray-8">
              {{ __('Umowa o świadczenie usług obsługi dofinansowania (Czyste Powietrze)') }}
            </div>
            <Badge
              :theme="isKompletny ? 'green' : 'amber'"
              variant="subtle"
              size="lg"
              :label="recordStatus"
            />
            <Badge
              v-if="autentiEnabled && autentiBadgeEntry"
              :theme="autentiBadgeEntry.theme"
              variant="subtle"
              size="lg"
              :label="autentiBadgeEntry.label"
            />
          </div>
          <div class="flex items-center gap-3">
            <span v-if="saveState === 'saving'" class="text-xs text-ink-gray-4">
              {{ __('Zapisywanie…') }}
            </span>
            <span v-else-if="saveState === 'saved'" class="text-xs text-ink-green-6">
              {{ __('Zapisano') }} ✓
            </span>
            <span v-else-if="saveState === 'error'" class="text-xs text-ink-red-6">
              {{ __('Błąd zapisu') }}
            </span>
            <Button
              v-if="showAutentiSendButton"
              variant="outline"
              :label="autentiSendLabel"
              @click="toggleAutentiConfirm"
            />
            <Button
              v-if="autentiEnabled && autentiStatus === 'Podpisana' && autenti.signed_pdf_file"
              variant="outline"
              :label="__('Pobierz podpisaną umowę')"
              @click="openSignedPdf"
            />
            <Button
              variant="outline"
              :label="__('Generuj PDF umowy')"
              :disabled="generatingPdf"
              :loading="generatingPdf"
              @click="generatePdf"
            />
            <Button
              variant="solid"
              :label="__('Zapisz')"
              :disabled="saving"
              :loading="saving"
              @click="saveForm"
            />
          </div>
        </div>

        <!-- Autenti timestamps - small muted line under the header/badges -->
        <div
          v-if="autentiEnabled && (autentiSentAtDisplay || autentiSignedAtDisplay)"
          class="-mt-4 flex flex-wrap gap-3 text-xs text-ink-gray-4"
        >
          <span v-if="autentiSentAtDisplay">
            {{ __('Wysłano') }}: {{ autentiSentAtDisplay }}
          </span>
          <span v-if="autentiSignedAtDisplay">
            {{ __('Podpisano') }}: {{ autentiSignedAtDisplay }}
          </span>
        </div>

        <!-- Autenti error - shown only for a failed send -->
        <div
          v-if="autentiEnabled && autentiStatus === 'Błąd' && autenti.error_message"
          class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
        >
          {{ autenti.error_message }}
        </div>

        <!-- Autenti send confirmation - inline panel, not a modal -->
        <div
          v-if="showAutentiConfirm"
          class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4"
        >
          <div class="mb-2 text-sm font-medium text-ink-gray-8">
            {{ __('Potwierdź wysyłkę do podpisu') }}
          </div>

          <div v-if="signerMissingEmail" class="mb-3 text-sm text-ink-red-5">
            {{ __('Kontakt szansy nie ma adresu e-mail. Uzupełnij go w CRM.') }}
          </div>
          <div v-else class="mb-3 text-sm text-ink-gray-6">
            <div>{{ __('Umowa zostanie wysłana do:') }}</div>
            <div v-if="recipientGroups.signers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Podpisują:') }}
              </div>
              <div
                v-for="r in recipientGroups.signers"
                :key="'signer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
            <div v-if="recipientGroups.viewers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Do wglądu:') }}
              </div>
              <div
                v-for="r in recipientGroups.viewers"
                :key="'viewer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
          </div>

          <!-- Fail-safe warning: fires on anything that is NOT 'Production'
          (including an unconfigured Single), never only on the literal
          'Sandbox' string - see UmowaTab.vue's identical comment (ops#144, F8). -->
          <div
            v-if="autenti.environment !== 'Production'"
            class="mb-3 rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
          >
            {{
              __(
                'Środowisko testowe Autenti (albo brak konfiguracji środowiska). Podpis NIE jest prawnie wiążący.',
              )
            }}
          </div>

          <div class="flex gap-2">
            <Button
              variant="solid"
              :label="__('Wyślij')"
              :loading="sendingAutenti"
              :disabled="signerMissingEmail"
              :tooltip="signerMissingEmail ? __('Kontakt szansy nie ma adresu e-mail. Uzupełnij go w CRM.') : ''"
              @click="confirmSendAutenti"
            />
            <Button variant="ghost" :label="__('Anuluj')" @click="toggleAutentiConfirm" />
          </div>
        </div>

        <!-- Missing-fields summary (populated after the last save/load) -->
        <div
          v-if="missingLabels.length || missingClientLabels.length"
          class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-4 py-3 text-sm text-ink-amber-8"
        >
          <div v-if="missingLabels.length">
            {{ __('Brakujące pola:') }} {{ missingLabels.join(', ') }}
          </div>
          <div v-if="missingClientLabels.length">
            {{ __('Brakujące dane klienta:') }} {{ missingClientLabels.join(', ') }}
            {{ __('Uzupełnij je na karcie klienta.') }}
          </div>
        </div>

        <!-- Dane klienta - read-only, exactly what the PDF will print -->
        <section>
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ __('Dane klienta') }}
          </div>
          <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div v-for="row in klientRows" :key="row.key" class="min-w-0">
                <div class="text-xs text-ink-gray-5">{{ row.label }}</div>
                <TelefonLink
                  v-if="row.key === 'telefon' && row.value"
                  :numer="row.value"
                  klasa="text-sm text-ink-gray-8"
                />
                <div v-else class="break-words text-sm text-ink-gray-8">
                  {{ row.value || __('brak') }}
                </div>
              </div>
            </div>
            <div class="mt-3 text-xs text-ink-gray-4">
              {{ __('Te dane edytuje się na karcie klienta, nie w tym formularzu.') }}
            </div>
          </div>
        </section>

        <!-- Wynagrodzenie -->
        <section>
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ __('Wynagrodzenie') }}
          </div>
          <div
            :class="['max-w-sm rounded', missingSet.has('wynagrodzenie_wariant') ? 'ring-1 ring-outline-red-3' : '']"
          >
            <FormControl
              type="select"
              :label="__('Wariant wynagrodzenia')"
              :options="wariantOpcje"
              :disabled="saving"
              v-model="form.wynagrodzenie_wariant"
            />
          </div>
          <div class="mt-2 text-sm text-ink-gray-7">
            <template v-if="zapisaneWynagrodzenie">{{ zapisaneWynagrodzenie }}</template>
            <span v-else class="text-xs text-ink-gray-4">
              {{ __('Wybierz i zapisz wariant, aby zobaczyć wysokość wynagrodzenia.') }}
            </span>
          </div>
        </section>

        <!-- Zgody (Załącznik nr 1) -->
        <section>
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ __('Zgody (Załącznik nr 1)') }}
          </div>
          <div class="flex flex-col gap-3">
            <FormControl
              type="checkbox"
              :label="__('Zgoda na przetwarzanie danych osobowych w celu zawarcia i realizacji umowy')"
              :disabled="saving"
              v-model="form.zgoda_przetwarzanie_danych"
            />
            <FormControl
              type="checkbox"
              :label="__('Zgoda na kontakt telefoniczny')"
              :disabled="saving"
              v-model="form.zgoda_kontakt_telefoniczny"
            />
            <FormControl
              type="checkbox"
              :label="__('Zgoda na działania promocyjne')"
              :disabled="saving"
              v-model="form.zgoda_dzialania_promocyjne"
            />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import UmowaIcon from '@/components/Icons/UmowaIcon.vue'
import TelefonLink from '@/components/TelefonLink.vue'
import { Badge, Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'
import { formatujParaKwot, wariantOptions } from '@/utils/umowaCpForm'
import { useAutenti } from '@/composables/useAutenti'

const props = defineProps({
  dealId: { type: String, required: true },
})

// Editable payload fields (see buildPayload()/hydrateForm() below) - the
// CP save endpoint accepts exactly these 4, nothing from the OZE form.
const EDITABLE_FIELDNAMES = [
  'wynagrodzenie_wariant',
  'zgoda_przetwarzanie_danych',
  'zgoda_kontakt_telefoniczny',
  'zgoda_dzialania_promocyjne',
]
const CHECKBOX_FIELDNAMES = new Set([
  'zgoda_przetwarzanie_danych',
  'zgoda_kontakt_telefoniczny',
  'zgoda_dzialania_promocyjne',
])

// --- Load state ----------------------------------------------------------------
const loading = ref(true)
const loadError = ref('')
const umowa = ref(null)
const wyliczenia = ref({})
const creating = ref(false)
const saving = ref(false)
const saveState = ref('idle') // idle | saving | saved | error
const brakujace = ref([])
const brakujaceKlienta = ref([])

const form = reactive({})

// --- Autenti e-signature state ----------------------------------------------------
// Same composable/endpoints as UmowaTab.vue (OZE) - the backend branches by
// the deal's rodzaj internally, so the CP form is a plain SIGNER/VIEWER
// send like any other, just with a different recipient set server-side
// (client + prezes as SIGNER, archive + Doradca as VIEWER, per the API
// contract in the header comment above).
const {
  autenti,
  showAutentiConfirm,
  sendingAutenti,
  loadAutentiStatus,
  toggleAutentiConfirm,
  confirmSendAutenti,
  openSignedPdf,
  autentiEnabled,
  autentiStatus,
  autentiBadgeEntry,
  autentiSendLabel,
  showAutentiSendButton,
  signerMissingEmail,
  recipientGroups,
  autentiSentAtDisplay,
  autentiSignedAtDisplay,
} = useAutenti({
  dealId: () => props.dealId,
  statusMethod: 'crm.integrations.autenti.api.autenti_umowa_status',
  sendMethod: 'crm.integrations.autenti.api.autenti_send_umowa',
  sentToastLabel: __('Umowa wysłana do podpisu'),
})

onMounted(() => {
  loadUmowa()
})

// Same reading rule as UmowaTab.vue's extractBrakujace(): the missing-
// fields list always travels inside `wyliczenia.brakujace_pola`, never a
// top-level `brakujace` key; Array.isArray guards a wrong/absent key into
// an empty array rather than a crash.
function extractBrakujace(data) {
  const list = data?.wyliczenia?.brakujace_pola
  return Array.isArray(list) ? list : []
}
function extractBrakujaceKlienta(data) {
  const list = data?.wyliczenia?.brakujace_dane_klienta
  return Array.isArray(list) ? list : []
}

async function loadUmowa() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await call('crm.api.umowa.volteo_umowa_get', { deal: props.dealId })
    umowa.value = data?.umowa || null
    wyliczenia.value = data?.wyliczenia || {}
    brakujace.value = extractBrakujace(data)
    brakujaceKlienta.value = extractBrakujaceKlienta(data)
    if (umowa.value) hydrateForm(umowa.value)
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
}

function hydrateForm(u) {
  EDITABLE_FIELDNAMES.forEach((fn) => {
    const raw = u ? u[fn] : undefined
    if (CHECKBOX_FIELDNAMES.has(fn)) {
      form[fn] = !!raw
    } else {
      form[fn] = raw === undefined || raw === null ? '' : String(raw)
    }
  })
}

// --- Derived / read-only values --------------------------------------------------
// `wyliczenia.klient` is ready-to-display strings, exactly what the PDF
// will print; any field may be '' (missing), rendered as the Polish
// placeholder "brak" below rather than left blank, so an empty value reads
// as "known to be missing" instead of "maybe still loading".
const klientRowDefs = [
  { key: 'imie_nazwisko', label: __('Imię i nazwisko') },
  { key: 'adres', label: __('Adres') },
  { key: 'pesel', label: __('PESEL') },
  { key: 'telefon', label: __('Telefon') },
  { key: 'email', label: __('E-mail') },
]
const klientRows = computed(() =>
  klientRowDefs.map((def) => ({
    ...def,
    value: wyliczenia.value?.klient?.[def.key] || '',
  })),
)

const wariantOpcje = computed(() => wariantOptions(wyliczenia.value?.warianty_wynagrodzenia))
const zapisaneWynagrodzenie = computed(() =>
  formatujParaKwot(umowa.value?.wynagrodzenie_netto_pln, umowa.value?.wynagrodzenie_brutto_pln),
)

const missingSet = computed(() => new Set(brakujace.value))
const FIELD_LABELS = {
  wynagrodzenie_wariant: __('Wariant wynagrodzenia'),
}
const missingLabels = computed(() => brakujace.value.map((fn) => FIELD_LABELS[fn] || fn))
// `brakujace_dane_klienta` already carries human-readable Polish labels
// from the server (mirrors ops#146 on the OZE form) - no fieldname-to-label
// lookup needed here.
const missingClientLabels = computed(() => brakujaceKlienta.value)

const recordStatus = computed(() => umowa.value?.status || 'Roboczy')
const isKompletny = computed(() => recordStatus.value === 'Kompletny')

// --- Create ----------------------------------------------------------------------
async function createUmowa() {
  if (creating.value) return
  creating.value = true
  try {
    const data = await call('crm.api.umowa.volteo_umowa_create', { deal: props.dealId })
    umowa.value = data?.umowa || null
    wyliczenia.value = data?.wyliczenia || {}
    brakujace.value = extractBrakujace(data)
    brakujaceKlienta.value = extractBrakujaceKlienta(data)
    if (umowa.value) hydrateForm(umowa.value)
    toast.success(__('Utworzono formularz umowy'))
    // Refresh Autenti status so `dokument_exists` stops being stale - same
    // reasoning as UmowaTab.vue's createUmowa().
    await loadAutentiStatus()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

// --- Save (draft-safe: incomplete saves are allowed) -----------------------------
function buildPayload() {
  const payload = {}
  EDITABLE_FIELDNAMES.forEach((fn) => {
    payload[fn] = form[fn]
  })
  return payload
}

async function saveForm() {
  if (saving.value || !umowa.value) return
  saving.value = true
  saveState.value = 'saving'
  try {
    const data = await call('crm.api.umowa.volteo_umowa_save', {
      deal: props.dealId,
      dane: buildPayload(),
    })
    umowa.value = data?.umowa || umowa.value
    wyliczenia.value = data?.wyliczenia || wyliczenia.value
    brakujace.value = extractBrakujace(data)
    brakujaceKlienta.value = extractBrakujaceKlienta(data)
    hydrateForm(umowa.value)
    saveState.value = 'saved'
    if (brakujace.value.length) {
      toast.success(__('Zapisano jako roboczy - część pól nadal brakuje.'))
    } else {
      toast.success(__('Zapisano formularz umowy'))
    }
  } catch (err) {
    saveState.value = 'error'
    toast.error(extractErrorMessage(err))
  } finally {
    saving.value = false
  }
}

// --- Generate PDF ------------------------------------------------------------------
const generatingPdf = ref(false)

async function generatePdf() {
  if (generatingPdf.value || !umowa.value) return
  generatingPdf.value = true
  try {
    const data = await call('crm.api.umowa.volteo_umowa_pdf', { deal: props.dealId })
    if (data?.file_url) {
      // Private file served under the caller's existing session cookie -
      // same-origin `window.open`, no fetch/download needed.
      window.open(data.file_url, '_blank')
      toast.success(__('Wygenerowano PDF umowy'))
      if (autenti.value) {
        autenti.value = { ...autenti.value, pdf_exists: true }
      }
      await loadAutentiStatus()
    } else {
      toast.error(__('Wystąpił błąd - spróbuj ponownie'))
    }
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    generatingPdf.value = false
  }
}

// --- Helpers -----------------------------------------------------------------------
// Copied verbatim from UmowaTab.vue's extractErrorMessage() - see that
// file's header comment for why the `err.messages` branch is load-bearing
// against frappe-ui's call().
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
</script>
