<!--
  Faktury tab (Szansa view) — invoices for the deal (Volteo Faktura, N per deal).
  Lists existing invoices + an inline "add invoice" form with optional file upload.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div class="flex items-center justify-between">
        <div class="text-lg font-semibold text-ink-gray-8">{{ __('Faktury') }}</div>
        <Button
          v-if="canCreate"
          :label="showForm ? __('Anuluj') : __('Dodaj fakturę')"
          :iconLeft="showForm ? 'x' : 'plus'"
          @click="showForm = !showForm"
        />
      </div>

      <!-- Add form -->
      <div v-if="showForm && canCreate" class="rounded-lg border border-outline-gray-2 p-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl type="text" :label="__('Numer faktury')" v-model="draft.numer" />
          <FormControl type="select" :label="__('Typ')" :options="['', 'Proforma', 'VAT', 'Zaliczkowa', 'Końcowa']" v-model="draft.typ" />
          <FormControl type="select" :label="__('Status')" :options="['Wystawiona', 'Opłacona', 'Częściowo opłacona', 'Anulowana']" v-model="draft.status" />
          <FormControl type="number" :label="__('Kwota brutto (PLN)')" step="0.01" v-model="draft.kwota_brutto" />
          <FormControl type="date" :label="__('Data wystawienia')" v-model="draft.data_wystawienia" />
          <FormControl type="date" :label="__('Termin płatności')" v-model="draft.termin_platnosci" />
        </div>
        <div class="mt-3 flex items-center justify-between">
          <FileUploader @success="(file) => (draft.plik = file.file_url)">
            <template #default="{ openFileSelector, uploading }">
              <Button
                :label="draft.plik ? __('Plik dodany') : __('Załącz plik')"
                :iconLeft="draft.plik ? 'check' : 'paperclip'"
                :loading="uploading"
                @click="openFileSelector"
              />
            </template>
          </FileUploader>
          <Button
            variant="solid"
            :label="__('Zapisz fakturę')"
            :loading="saving"
            :disabled="!draft.numer.trim()"
            @click="addFaktura"
          />
        </div>
      </div>

      <!-- List -->
      <div v-if="fakturies.loading" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="!rows.length" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __('Brak faktur.') }}
      </div>
      <div v-else class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="bg-surface-gray-2 text-ink-gray-5">
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Numer') }}</th>
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Typ') }}</th>
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Status') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Kwota') }}</th>
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Data') }}</th>
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Plik') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in rows" :key="f.name" class="border-t border-outline-gray-1">
              <td class="px-4 py-2.5 text-ink-gray-8">{{ f.numer || '—' }}</td>
              <td class="px-4 py-2.5 text-ink-gray-6">{{ f.typ || '—' }}</td>
              <td class="px-4 py-2.5">
                <Badge :theme="statusTheme(f.status)" variant="subtle" size="sm" :label="f.status || '—'" />
              </td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ plnFmt(f.kwota_brutto) }}</td>
              <td class="px-4 py-2.5 text-ink-gray-6">{{ f.data_wystawienia || '—' }}</td>
              <td class="px-4 py-2.5">
                <a v-if="f.plik" :href="f.plik" target="_blank" rel="noopener" class="text-ink-blue-link underline">{{ __('otwórz') }}</a>
                <span v-else class="text-ink-gray-4">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, FormControl, FileUploader, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, computed } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

const showForm = ref(false)
const saving = ref(false)
const canCreate = computed(() => !!window.can_create_faktura)

function emptyDraft() {
  return {
    numer: '', typ: '', status: 'Wystawiona', kwota_brutto: '',
    data_wystawienia: '', termin_platnosci: '', plik: '',
  }
}
const draft = reactive(emptyDraft())

const fakturies = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Faktura',
    filters: { deal: props.dealId },
    fields: ['name', 'numer', 'typ', 'status', 'kwota_brutto', 'data_wystawienia', 'plik'],
    order_by: 'creation desc',
    limit_page_length: 200,
  },
  auto: true,
})

const rows = computed(() => fakturies.data || [])

async function addFaktura() {
  if (!canCreate.value) return
  if (!draft.numer.trim()) return
  saving.value = true
  try {
    await call('frappe.client.insert', {
      doc: { doctype: 'Volteo Faktura', deal: props.dealId, ...draft },
    })
    Object.assign(draft, emptyDraft())
    showForm.value = false
    await fakturies.reload()
  } catch (err) {
    toast.error((err && (err.messages?.[0] || err.message)) || __('Nie udało się zapisać faktury'))
  } finally {
    saving.value = false
  }
}

function statusTheme(status) {
  if (status === 'Opłacona') return 'green'
  if (status === 'Anulowana') return 'red'
  if (status === 'Częściowo opłacona') return 'orange'
  return 'gray'
}

function plnFmt(val) {
  if (val == null || val === '') return '—'
  const n = Math.round(Number(val) || 0)
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' zł'
}
</script>
