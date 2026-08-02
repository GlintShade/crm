<!--
  Oferta tab (Szansa view) — e-signature status of offers sent via Autenti.
  Lists the Volteo Ofertas already created for this deal by the Kalkulator
  (including ones never sent yet), lets the rep trigger a send (or resend
  after an error/expiry/rejection) per offer, and polls while a signature
  is in flight.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <div v-if="loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <div
        v-else-if="enabled.data === false"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <FeatherIcon name="slash" class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">
          {{ __('Integracja Autenti nie jest skonfigurowana') }}
        </div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Skontaktuj się z administratorem, aby skonfigurować integrację Autenti.') }}
        </div>
      </div>

      <div v-else-if="!rows.length" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <FeatherIcon name="send" class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak ofert') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Wygeneruj ofertę w Kalkulatorze, aby wysłać ją do podpisu.') }}
        </div>
      </div>

      <div v-else>
        <div class="mb-4 text-lg font-semibold text-ink-gray-8">{{ __('Oferty') }}</div>

        <div class="flex flex-col gap-3">
          <div v-for="o in rows" :key="o.name" class="rounded-lg border border-outline-gray-1 p-4">
            <div class="mb-1.5 flex items-center justify-between">
              <Badge variant="subtle" :theme="statusTheme(o.autenti_status)" size="sm" :label="statusLabel(o.autenti_status)" />
              <Button
                v-if="canShowAction(o.autenti_status) && confirmingName !== o.name"
                variant="ghost"
                :label="needsInitialSend(o.autenti_status) ? __('Wyślij do podpisu') : __('Wyślij ponownie')"
                @click="openConfirm(o.name)"
              />
            </div>

            <div class="text-sm text-ink-gray-8">
              {{ displayName(o) }} <span class="text-ink-gray-5">{{ displayEmail(o) }}</span>
            </div>
            <div class="mt-1.5 text-xs text-ink-gray-4">{{ __('Utworzono') }}: {{ formatDate(o.creation) }}</div>
            <div v-if="o.sent_at" class="text-xs text-ink-gray-4">{{ __('Wysłano') }}: {{ formatDate(o.sent_at) }}</div>
            <div v-if="o.signed_at" class="text-xs text-ink-gray-4">{{ __('Podpisano') }}: {{ formatDate(o.signed_at) }}</div>
            <div v-if="o.error_message" class="mt-1.5 text-sm text-ink-red-5">{{ o.error_message }}</div>

            <div v-if="o.pdf_file || o.signed_pdf_file" class="mt-2 flex flex-wrap gap-3 text-sm">
              <a
                v-if="o.pdf_file"
                :href="o.pdf_file"
                target="_blank"
                rel="noopener"
                class="text-ink-blue-link underline"
              >
                {{ __('Oferta PDF') }}
              </a>
              <a
                v-if="o.signed_pdf_file"
                :href="o.signed_pdf_file"
                target="_blank"
                rel="noopener"
                class="text-ink-blue-link underline"
              >
                {{ __('Podpisany dokument') }}
              </a>
            </div>

            <div v-if="confirmingName === o.name" class="mt-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
              <div class="mb-2 text-sm font-medium text-ink-gray-8">{{ __('Potwierdź wysyłkę') }}</div>
              <div v-if="o.client_email" class="mb-3 text-sm text-ink-gray-6">
                {{ __('Oferta zostanie wysłana do podpisu na adres') }}:
                <span class="font-medium text-ink-gray-8">{{ o.client_name }} ({{ o.client_email }})</span>
              </div>
              <div v-else class="mb-3 text-sm text-ink-red-5">
                {{ __('Ta oferta nie ma adresu e-mail klienta.') }}
              </div>
              <div v-if="errorsByName[o.name]" class="mb-3 text-sm text-ink-red-5">{{ errorsByName[o.name] }}</div>
              <div class="flex gap-2">
                <Button
                  variant="solid"
                  :label="__('Wyślij')"
                  :loading="sendingNames[o.name]"
                  :disabled="!o.client_email"
                  @click="confirmSend(o)"
                />
                <Button variant="ghost" :label="__('Anuluj')" @click="cancelConfirm" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, FeatherIcon, call, createResource } from 'frappe-ui'
import { computed, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

const ofertas = createResource({
  url: 'crm.integrations.autenti.api.autenti_get_ofertas',
  params: { deal_name: props.dealId },
  auto: true,
})
const enabled = createResource({
  url: 'crm.integrations.autenti.api.autenti_is_enabled',
  auto: true,
})

const loading = computed(() => ofertas.loading || enabled.loading)
const rows = computed(() => ofertas.data || [])

// Per-offer UI state, keyed by oferta `name`.
const confirmingName = ref('')
const sendingNames = ref({})
const errorsByName = ref({})

function statusTheme(status) {
  if (status === 'Podpisana') return 'green'
  if (status === 'Wysłana') return 'blue'
  if (status === 'Wysyłanie') return 'amber'
  if (status === 'Odrzucona' || status === 'Błąd') return 'red'
  return 'gray'
}

function statusLabel(status) {
  return status || __('Niewysłana')
}

function needsInitialSend(status) {
  return !status
}

function isResendable(status) {
  return status === 'Błąd' || status === 'Odrzucona' || status === 'Wygasła'
}

function canShowAction(status) {
  return needsInitialSend(status) || isResendable(status)
}

// Before a send, the offer's own client data is the identity. Once it has
// been sent, prefer the signer fields — those are the values actually
// submitted to Autenti — falling back to the client fields if unset.
function displayName(o) {
  return o.autenti_status ? o.signer_name || o.client_name : o.client_name || o.signer_name
}
function displayEmail(o) {
  return o.autenti_status ? o.signer_email || o.client_email : o.client_email || o.signer_email
}

function openConfirm(name) {
  errorsByName.value = { ...errorsByName.value, [name]: '' }
  confirmingName.value = name
}
function cancelConfirm() {
  confirmingName.value = ''
}

async function confirmSend(o) {
  const method = isResendable(o.autenti_status)
    ? 'crm.integrations.autenti.api.autenti_resend_oferta'
    : 'crm.integrations.autenti.api.autenti_send_oferta'
  sendingNames.value = { ...sendingNames.value, [o.name]: true }
  errorsByName.value = { ...errorsByName.value, [o.name]: '' }
  try {
    await call(method, { oferta_name: o.name })
    confirmingName.value = ''
    await ofertas.reload()
  } catch (e) {
    errorsByName.value = {
      ...errorsByName.value,
      [o.name]: e?.messages?.[0] || e?.message || __('Wystąpił błąd podczas wysyłki'),
    }
  } finally {
    sendingNames.value = { ...sendingNames.value, [o.name]: false }
  }
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleString('pl-PL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

let pollInterval = null
watch(
  () => ofertas.data,
  (data) => {
    const hasPending = data?.some((o) => o.autenti_status === 'Wysyłanie' || o.autenti_status === 'Wysłana')
    if (hasPending && !pollInterval) {
      pollInterval = setInterval(() => ofertas.reload(), 30000)
    } else if (!hasPending && pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  },
  { immediate: true },
)
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>
