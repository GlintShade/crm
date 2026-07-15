<!--
  Audyt tab (Szansa view) — technical audit form, 1:1 with the deal
  (Volteo Audyt, autoname field:deal so name == dealId). Find-or-create, then
  edit the grouped fields (Dane podstawowe / Dane elektryczne / Planowana
  instalacja) inline and save via frappe.client.set_value.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <div v-if="audyt.loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <!-- No audit yet -->
      <div
        v-else-if="!exists"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <AudytIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak audytu') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Ta szansa nie ma jeszcze audytu technicznego.') }}
        </div>
        <Button
          variant="solid"
          :label="__('Utwórz audyt techniczny')"
          :loading="creating"
          @click="createAudyt"
        />
      </div>

      <!-- Audit form -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex items-center justify-between">
          <div class="text-lg font-semibold text-ink-gray-8">{{ __('Audyt techniczny') }}</div>
          <div class="flex items-center gap-2">
            <FormControl
              type="select"
              :options="['Niekompletny', 'Kompletny']"
              v-model="form.status"
            />
            <Button
              variant="solid"
              :label="__('Zapisz')"
              :loading="saving"
              @click="save"
            />
          </div>
        </div>

        <section v-for="sec in SECTIONS" :key="sec.label">
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ sec.label }}
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormControl
              v-for="f in sec.fields"
              :key="f.fn"
              :type="f.type"
              :label="f.label"
              :options="f.options"
              :step="f.step"
              v-model="form[f.fn]"
            />
          </div>
        </section>

        <div>
          <FormControl type="textarea" :label="__('Uwagi technika')" v-model="form.uwagi" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import AudytIcon from '@/components/Icons/AudytIcon.vue'
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, computed, ref } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

const SECTIONS = [
  {
    label: 'Dane podstawowe',
    fields: [
      { fn: 'rodzaj_instalacji', label: 'Rodzaj instalacji', type: 'select', options: ['', 'Fotowoltaika', 'Magazyn energii', 'Fotowoltaika + Magazyn', 'Pompa ciepła', 'Inne'] },
      { fn: 'dotacja_moj_prad', label: 'Dotacja „Mój Prąd”', type: 'select', options: ['', 'Tak', 'Nie', 'W trakcie'] },
      { fn: 'operator_energetyczny', label: 'Operator Energetyczny', type: 'select', options: ['', 'PGE', 'Tauron', 'Enea', 'Energa', 'Stoen (innogy)', 'Inny'] },
    ],
  },
  {
    label: 'Dane elektryczne istniejącego budynku',
    fields: [
      { fn: 'rodzaj_umowy', label: 'Rodzaj umowy', type: 'select', options: ['', 'Kompleksowa', 'Rozdzielona (sprzedaż + dystrybucja)'] },
      { fn: 'umiejscowienie_licznika', label: 'Umiejscowienie licznika', type: 'select', options: ['', 'W budynku', 'Na granicy działki', 'W złączu kablowym', 'Inne'] },
      { fn: 'liczba_faz', label: 'Liczba faz', type: 'select', options: ['', '1', '3'] },
      { fn: 'moc_umowna_kw', label: 'Moc umowna (kW)', type: 'number', step: '0.01' },
      { fn: 'moc_przylaczeniowa_kw', label: 'Moc przyłączeniowa (kW)', type: 'number', step: '0.01' },
    ],
  },
  {
    label: 'Planowana instalacja fotowoltaiczna',
    fields: [
      { fn: 'odleglosc_falownika_m', label: 'Odległość falownika od rozdzielnicy (m)', type: 'number', step: '0.1' },
      { fn: 'odleglosc_magazynu_m', label: 'Odległość magazynu od rozdzielnicy (m)', type: 'number', step: '0.1' },
      { fn: 'pomieszczenie_ogrzewane', label: 'Pomieszczenie ogrzewane?', type: 'select', options: ['', 'Tak', 'Nie'] },
    ],
  },
]

const EDITABLE = [
  'status', 'uwagi',
  ...SECTIONS.flatMap((s) => s.fields.map((f) => f.fn)),
]

const form = reactive({ status: 'Niekompletny', uwagi: '' })
const creating = ref(false)
const saving = ref(false)

const audyt = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Audyt',
    filters: { deal: props.dealId },
    fields: ['*'],
    limit_page_length: 1,
  },
  auto: true,
  onSuccess: (data) => {
    const d = data?.[0]
    if (d) EDITABLE.concat('status').forEach((k) => { if (d[k] != null) form[k] = d[k] })
  },
})

const exists = computed(() => !!audyt.data?.[0]?.name)

async function createAudyt() {
  creating.value = true
  try {
    await call('frappe.client.insert', {
      doc: { doctype: 'Volteo Audyt', deal: props.dealId, status: 'Niekompletny' },
    })
    await audyt.reload()
  } catch (err) {
    toast.error(errMsg(err))
  } finally {
    creating.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {}
    EDITABLE.forEach((k) => { payload[k] = form[k] ?? '' })
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt',
      name: props.dealId,
      fieldname: payload,
    })
    toast.success(__('Zapisano audyt'))
    await audyt.reload()
  } catch (err) {
    toast.error(errMsg(err))
  } finally {
    saving.value = false
  }
}

function errMsg(err) {
  return (err && (err.messages?.[0] || err.message)) || __('Wystąpił błąd — spróbuj ponownie')
}
</script>
