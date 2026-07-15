<!--
  Zestaw tab (Szansa view) — the build behind this deal.
  Prefers the itemized BOM (CRM Deal.custom_zestaw -> Volteo Zestaw Item) when it
  exists; otherwise falls back to the linked Volteo Oferta (single product + params).
  The full BOM is populated once the D2D calculator lands (Phase 2+); until then the
  BOM child table is editable on the deal form and this tab reflects it.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <div v-if="loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <ZestawIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak zestawu') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Ta szansa nie ma jeszcze zestawu. Zestaw pojawi się po wygenerowaniu oferty w Kalkulatorze lub po dodaniu pozycji do zestawu na szansie.') }}
        </div>
      </div>

      <div v-else>
        <div class="mb-4 flex items-center justify-between">
          <div class="text-lg font-semibold text-ink-gray-8">{{ __('Zestaw') }}</div>
          <Badge v-if="ofertaName" variant="subtle" theme="gray" size="sm" :label="ofertaName" />
        </div>

        <div class="overflow-hidden rounded-lg border border-outline-gray-2">
          <table class="w-full border-collapse text-sm">
            <thead>
              <tr class="bg-surface-gray-2 text-ink-gray-5">
                <th class="px-4 py-2.5 text-left font-medium">{{ __('TYP') }}</th>
                <th class="px-4 py-2.5 text-left font-medium">{{ __('NAZWA') }}</th>
                <th class="w-20 px-4 py-2.5 text-right font-medium">{{ __('ILOŚĆ') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="i" class="border-t border-outline-gray-1">
                <td class="px-4 py-2.5 text-ink-gray-6">{{ row.typ }}</td>
                <td class="px-4 py-2.5 text-ink-gray-8">{{ row.nazwa || '—' }}</td>
                <td class="px-4 py-2.5 text-right text-ink-gray-6">{{ row.ilosc || '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="mt-3 text-xs text-ink-gray-4">{{ caption }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import ZestawIcon from '@/components/Icons/ZestawIcon.vue'
import { Badge, createResource } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

// Itemized BOM (preferred), from the deal's custom_zestaw child table.
const bom = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Zestaw Item',
    filters: { parenttype: 'CRM Deal', parentfield: 'custom_zestaw', parent: props.dealId },
    fields: ['typ', 'nazwa', 'ilosc'],
    order_by: 'idx asc',
    limit_page_length: 200,
  },
  auto: true,
})

// Fallback: the linked Oferta (single product + params).
const oferta = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Oferta',
    filters: { deal: props.dealId },
    fields: [
      'name', 'product_brand', 'product_model', 'capacity_kwh', 'inverter_power_kw',
      'warranty_years', 'installation_type', 'pv_power_kwp', 'tariff_type', 'subsidy_pln',
    ],
    order_by: 'creation desc',
    limit_page_length: 1,
  },
  auto: true,
})

const loading = computed(() => bom.loading || oferta.loading)
const bomRows = computed(() => bom.data || [])
const o = computed(() => oferta.data?.[0] || null)
const ofertaName = computed(() => (bomRows.value.length ? null : o.value?.name || null))

function plnFmt(val) {
  const n = Math.round(Number(val) || 0)
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' zł'
}

const ofertaRows = computed(() => {
  const d = o.value
  if (!d) return []
  const product = [d.product_brand, d.product_model].filter(Boolean).join(' ')
  return [
    { typ: 'Magazyn / Inwerter', nazwa: product, ilosc: '1' },
    { typ: 'Pojemność', nazwa: d.capacity_kwh ? d.capacity_kwh + ' kWh' : '', ilosc: '' },
    { typ: 'Moc falownika', nazwa: d.inverter_power_kw ? d.inverter_power_kw + ' kW' : '', ilosc: '' },
    { typ: 'Typ instalacji', nazwa: d.installation_type, ilosc: '' },
    { typ: 'Moc instalacji PV', nazwa: d.pv_power_kwp ? d.pv_power_kwp + ' kWp' : '', ilosc: '' },
    { typ: 'Taryfa', nazwa: d.tariff_type, ilosc: '' },
    { typ: 'Dotacja', nazwa: d.subsidy_pln ? plnFmt(d.subsidy_pln) : '', ilosc: '' },
    { typ: 'Gwarancja', nazwa: d.warranty_years ? d.warranty_years + ' lat' : '', ilosc: '' },
  ]
})

const rows = computed(() => (bomRows.value.length ? bomRows.value : ofertaRows.value))
const caption = computed(() =>
  bomRows.value.length
    ? __('Wykaz komponentów (BOM) zestawu.')
    : __('Podgląd na podstawie oferty z Kalkulatora. Pełny wykaz komponentów (BOM) — wkrótce.'),
)
</script>
