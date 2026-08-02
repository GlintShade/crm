<!--
  Oferta tab (Szansa view) — e-signature status of offers sent via Autenti.
  Shows the send history for the deal's Volteo Oferta, lets the rep trigger a
  send (or resend after an error/expiry/rejection), and polls while a signature
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
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak wysłanych ofert') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Wyślij ofertę do klienta do podpisu elektronicznego przez Autenti.') }}
        </div>

        <div v-if="showSendConfirm" class="mt-2 w-full max-w-sm rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4 text-left">
          <div class="mb-2 text-sm font-medium text-ink-gray-8">{{ __('Potwierdź wysyłkę') }}</div>
          <div v-if="signerEmail" class="mb-3 text-sm text-ink-gray-6">
            {{ __('Oferta zostanie wysłana do podpisu na adres') }}:
            <span class="font-medium text-ink-gray-8">{{ signerName }} ({{ signerEmail }})</span>
          </div>
          <div v-else class="mb-3 text-sm text-ink-red-5">
            {{ __('Ta szansa nie ma przypisanego klienta z adresem e-mail.') }}
          </div>
          <div v-if="sendError" class="mb-3 text-sm text-ink-red-5">{{ sendError }}</div>
          <div class="flex gap-2">
            <Button variant="solid" :label="__('Wyślij')" :loading="sending" :disabled="!signerEmail" @click="confirmSend" />
            <Button variant="ghost" :label="__('Anuluj')" @click="showSendConfirm = false" />
          </div>
        </div>
        <Button v-else variant="solid" :label="__('Wyślij ofertę')" @click="showSendConfirm = true" />
      </div>

      <div v-else>
        <div v-if="showSendConfirm" class="mb-4 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
          <div class="mb-2 text-sm font-medium text-ink-gray-8">{{ __('Potwierdź wysyłkę') }}</div>
          <div v-if="signerEmail" class="mb-3 text-sm text-ink-gray-6">
            {{ __('Oferta zostanie wysłana do podpisu na adres') }}:
            <span class="font-medium text-ink-gray-8">{{ signerName }} ({{ signerEmail }})</span>
          </div>
          <div v-else class="mb-3 text-sm text-ink-red-5">
            {{ __('Ta szansa nie ma przypisanego klienta z adresem e-mail.') }}
          </div>
          <div v-if="sendError" class="mb-3 text-sm text-ink-red-5">{{ sendError }}</div>
          <div class="flex gap-2">
            <Button variant="solid" :label="__('Wyślij')" :loading="sending" :disabled="!signerEmail" @click="confirmSend" />
            <Button variant="ghost" :label="__('Anuluj')" @click="showSendConfirm = false" />
          </div>
        </div>

        <div class="mb-4 flex items-center justify-between">
          <div class="text-lg font-semibold text-ink-gray-8">{{ __('Oferta') }}</div>
          <Button v-if="!showSendConfirm" variant="solid" :label="__('Wyślij ofertę')" @click="showSendConfirm = true" />
        </div>

        <div class="flex flex-col gap-3">
          <div v-for="o in rows" :key="o.name" class="rounded-lg border border-outline-gray-1 p-4">
            <div class="mb-1.5 flex items-center justify-between">
              <Badge variant="subtle" :theme="statusTheme(o.autenti_status)" size="sm" :label="o.autenti_status || '—'" />
              <Button
                v-if="isResendable(o.autenti_status)"
                variant="ghost"
                :label="__('Wyślij ponownie')"
                :loading="sending"
                @click="confirmSend"
              />
            </div>
            <div class="text-sm text-ink-gray-8">
              {{ o.signer_name }} <span class="text-ink-gray-5">{{ o.signer_email }}</span>
            </div>
            <div class="mt-1.5 text-xs text-ink-gray-4">{{ __('Wysłano') }}: {{ formatDate(o.sent_at) }}</div>
            <div v-if="o.signed_at" class="text-xs text-ink-gray-4">{{ __('Podpisano') }}: {{ formatDate(o.signed_at) }}</div>
            <div v-if="o.error_message" class="mt-1.5 text-sm text-ink-red-5">{{ o.error_message }}</div>
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
const dealContacts = createResource({
  url: 'crm.fcrm.doctype.crm_deal.api.get_deal_contacts',
  params: { name: props.dealId },
  auto: true,
})

const primaryContact = computed(() => {
  const list = dealContacts.data || []
  return list.find((c) => c.is_primary) || list[0] || null
})
const signerName = computed(() => primaryContact.value?.full_name || '')
const signerEmail = computed(() => primaryContact.value?.email || '')

const loading = computed(() => ofertas.loading || enabled.loading)
const rows = computed(() => ofertas.data || [])

const showSendConfirm = ref(false)
const sending = ref(false)
const sendError = ref('')

function statusTheme(status) {
  if (status === 'Podpisana') return 'green'
  if (status === 'Wysłana') return 'blue'
  if (status === 'Wysyłanie') return 'amber'
  if (status === 'Odrzucona' || status === 'Błąd') return 'red'
  return 'gray'
}

function isResendable(status) {
  return status === 'Błąd' || status === 'Odrzucona' || status === 'Wygasła'
}

async function confirmSend() {
  sending.value = true
  sendError.value = ''
  try {
    await call('crm.integrations.autenti.api.autenti_send_oferta', { deal_name: props.dealId })
    showSendConfirm.value = false
    await ofertas.reload()
  } catch (e) {
    sendError.value = e?.messages?.[0] || e?.message || __('Wystąpił błąd podczas wysyłki')
  } finally {
    sending.value = false
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
