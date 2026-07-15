<!--
  Zestaw tab (Szansa view) — shows the Kalkulator build behind this deal.
  Phase 1: reads the linked `Volteo Oferta` (single product + params) and renders it
  as a TYP / NAZWA / ILOŚĆ table. Phase 2 will replace this with a full itemized BOM
  (separate battery/inverter lines + extras: podnośnik, modernizacja rozdzielnicy,
  bilansowanie, operator).
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <div
        v-if="oferta.loading"
        class="py-16 text-center text-base text-ink-gray-5"
      >
        {{ __('Ładowanie…') }}
      </div>

      <div
        v-else-if="!o"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <ZestawIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">
          {{ __('Brak zestawu') }}
        </div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Ta szansa nie ma jeszcze zestawu. Zestaw pojawi się po wygenerowaniu oferty w Kalkulatorze klienta.') }}
        </div>
      </div>

      <div v-else>
        <div class="mb-4 flex items-center justify-between">
          <div class="text-lg font-semibold text-ink-gray-8">
            {{ __('Zestaw') }}
          </div>
          <Badge variant="subtle" theme="gray" size="sm" :label="o.name" />
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
              <tr
                v-for="(row, i) in rows"
                :key="i"
                class="border-t border-outline-gray-1"
              >
                <td class="px-4 py-2.5 text-ink-gray-6">{{ row.typ }}</td>
                <td class="px-4 py-2.5 text-ink-gray-8">{{ row.nazwa || '—' }}</td>
                <td class="px-4 py-2.5 text-right text-ink-gray-6">{{ row.ilosc || '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="mt-3 text-xs text-ink-gray-4">
          {{ __('Podgląd na podstawie oferty z Kalkulatora. Pełny wykaz komponentów (BOM) — wkrótce.') }}
        </p>
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

const oferta = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Oferta',
    filters: { deal: props.dealId },
    fields: [
      'name',
      'product_brand',
      'product_model',
      'capacity_kwh',
      'inverter_power_kw',
      'warranty_years',
      'installation_type',
      'pv_power_kwp',
      'tariff_type',
      'subsidy_pln',
    ],
    order_by: 'creation desc',
    limit_page_length: 1,
  },
  auto: true,
})

const o = computed(() => oferta.data?.[0] || null)

function plnFmt(val) {
  const n = Math.round(Number(val) || 0)
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' zł'
}

const rows = computed(() => {
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
</script>
