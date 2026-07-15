<!--
  Montaż tab (Szansa view) — install-progress update stream (Volteo Montaz Update,
  N per deal). Timeline of updates from rep/backoffice + an inline "add update" box.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <!-- Add update -->
      <div class="rounded-lg border border-outline-gray-2 p-4">
        <div class="mb-3 flex items-center gap-2">
          <FormControl
            type="select"
            :options="TYPY"
            v-model="draft.typ"
            class="w-48"
          />
        </div>
        <FormControl
          type="textarea"
          :placeholder="__('Np. Umówiono termin montażu na 20.07…')"
          v-model="draft.tekst"
          :rows="2"
        />
        <div class="mt-3 flex justify-end">
          <Button
            variant="solid"
            :label="__('Dodaj aktualizację')"
            :loading="adding"
            :disabled="!draft.tekst.trim()"
            @click="addUpdate"
          />
        </div>
      </div>

      <!-- Timeline -->
      <div v-if="updates.loading" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div
        v-else-if="!rows.length"
        class="py-10 text-center text-sm text-ink-gray-5"
      >
        {{ __('Brak aktualizacji montażu.') }}
      </div>
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="u in rows"
          :key="u.name"
          class="rounded-lg border border-outline-gray-1 p-4"
        >
          <div class="mb-1.5 flex items-center justify-between">
            <Badge variant="subtle" theme="gray" size="sm" :label="u.typ || __('Notatka')" />
            <span class="text-xs text-ink-gray-4">{{ fmtDate(u.data_zdarzenia) }}</span>
          </div>
          <div class="whitespace-pre-wrap text-sm text-ink-gray-8">{{ u.tekst }}</div>
          <div class="mt-1.5 text-xs text-ink-gray-5">{{ userName(u.owner) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, computed } from 'vue'
import { usersStore } from '@/stores/users.js'

const props = defineProps({
  dealId: { type: String, required: true },
})

const TYPY = ['Notatka', 'Telefon', 'Wizyta', 'Termin montażu', 'Problem']

const { getUser } = usersStore()
const draft = reactive({ typ: 'Notatka', tekst: '' })
const adding = ref(false)

const updates = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Montaz Update',
    filters: { deal: props.dealId },
    fields: ['name', 'typ', 'data_zdarzenia', 'tekst', 'owner'],
    order_by: 'data_zdarzenia desc',
    limit_page_length: 200,
  },
  auto: true,
})

const rows = computed(() => updates.data || [])

async function addUpdate() {
  if (!draft.tekst.trim()) return
  adding.value = true
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Volteo Montaz Update',
        deal: props.dealId,
        typ: draft.typ,
        tekst: draft.tekst.trim(),
      },
    })
    draft.tekst = ''
    draft.typ = 'Notatka'
    await updates.reload()
  } catch (err) {
    toast.error((err && (err.messages?.[0] || err.message)) || __('Nie udało się dodać aktualizacji'))
  } finally {
    adding.value = false
  }
}

function userName(email) {
  return getUser(email)?.full_name || email || ''
}

function fmtDate(dt) {
  if (!dt) return ''
  return String(dt).slice(0, 16).replace('T', ' ')
}
</script>
