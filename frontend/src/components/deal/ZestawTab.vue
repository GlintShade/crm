<!--
  Zestaw tab (Szansa view) — the build behind this deal.
  Prefers the itemized BOM (CRM Deal.custom_zestaw -> Volteo Zestaw Item) when it
  exists; otherwise falls back to the linked Volteo Oferta (single product + params).
  The full BOM is populated once the D2D calculator lands (Phase 2+); until then the
  BOM child table is editable on the deal form and this tab reflects it.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <!--
      Wider than sibling tabs (Faktury/Montaz/Audyt/Umowa all use max-w-3xl):
      this table carries five columns, two of them long free-text labels, and
      needs the extra room to avoid wrapping. See the width budget in
      ZestawTab's PR/task notes.
    -->
    <div class="mx-auto w-full max-w-5xl">
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
          {{ __('Ta szansa nie ma jeszcze zestawu. Zestaw pojawi się po wygenerowaniu oferty w Kalkulatorze OZE lub Kalkulatorze Czyste Powietrze, lub po dodaniu pozycji do zestawu na szansie.') }}
        </div>
      </div>

      <div v-else>
        <div class="mb-4 flex items-center justify-between">
          <div class="text-lg font-semibold text-ink-gray-8">{{ __('Zestaw') }}</div>
          <Badge v-if="ofertaName" variant="subtle" theme="gray" size="sm" :label="ofertaName" />
        </div>

        <div class="overflow-hidden rounded-lg border border-outline-gray-2">
          <!-- Horizontal scroll lives on this inner wrapper, not the page body:
               whitespace-nowrap below means the table itself can exceed the
               viewport on narrow screens, and it must scroll inside its own
               box instead of widening the page. -->
          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-sm">
              <thead>
                <tr class="bg-surface-gray-2 text-ink-gray-5">
                  <th class="whitespace-nowrap px-3 py-2.5 text-left font-medium">{{ __('TYP') }}</th>
                  <th class="whitespace-nowrap px-3 py-2.5 text-left font-medium">{{ __('NAZWA') }}</th>
                  <th class="w-20 whitespace-nowrap px-3 py-2.5 text-right font-medium">{{ __('ILOŚĆ') }}</th>
                  <th v-if="hasMoney" class="w-24 whitespace-nowrap px-3 py-2.5 text-right font-medium">{{ __('NETTO') }}</th>
                  <th v-if="hasMoney" class="w-24 whitespace-nowrap px-3 py-2.5 text-right font-medium">{{ __('BRUTTO') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in rows" :key="i" class="border-t border-outline-gray-1">
                  <td class="whitespace-nowrap px-3 py-2.5 text-ink-gray-6">{{ row.typ }}</td>
                  <td class="whitespace-nowrap px-3 py-2.5 text-ink-gray-8">{{ row.nazwa || '—' }}</td>
                  <td class="whitespace-nowrap px-3 py-2.5 text-right text-ink-gray-6">{{ iloscLabel(row) }}</td>
                  <td v-if="hasMoney" class="whitespace-nowrap px-3 py-2.5 text-right text-ink-gray-6">
                    {{ row.netto ? formatPln(row.netto) : '—' }}
                  </td>
                  <td v-if="hasMoney" class="whitespace-nowrap px-3 py-2.5 text-right text-ink-gray-6">
                    {{ row.brutto ? formatPln(row.brutto) : '—' }}
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="hasMoney">
                <tr class="border-t border-outline-gray-2 bg-surface-gray-1 font-medium text-ink-gray-7">
                  <td colspan="3" class="whitespace-nowrap px-3 py-2.5 text-right">{{ __('Razem') }}</td>
                  <td class="whitespace-nowrap px-3 py-2.5 text-right">{{ totalNetto ? formatPln(totalNetto) : '—' }}</td>
                  <td class="whitespace-nowrap px-3 py-2.5 text-right">{{ totalBrutto ? formatPln(totalBrutto) : '—' }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <p class="mt-3 text-xs text-ink-gray-4">{{ caption }}</p>

        <!-- Full width, matching the table above (not max-w-xs like the amber
             box below): this is the customer-facing subsidy breakdown, so it
             aligns with the table as one visual block. -->
        <div v-if="hasGroupSubsidy" class="mt-3 w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-2.5 text-sm">
          <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Dotacja wg grup prac') }}</div>
          <div v-if="Number(dealFields.custom_cp_dotacja_zrodlo) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Źródło ciepła') }}</span><span>{{ formatPln(dealFields.custom_cp_dotacja_zrodlo) }}</span>
          </div>
          <div v-if="Number(dealFields.custom_cp_dotacja_co) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Centralne Ogrzewanie i Ciepła Woda Użytkowa') }}</span><span>{{ formatPln(dealFields.custom_cp_dotacja_co) }}</span>
          </div>
          <div v-if="Number(dealFields.custom_cp_dotacja_termo) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Termomodernizacja') }}</span><span>{{ formatPln(dealFields.custom_cp_dotacja_termo) }}</span>
          </div>
          <div v-if="Number(dealFields.custom_estimated_subsidy_pln) > 0" class="flex justify-between border-t border-outline-gray-2 py-0.5 pt-1 font-medium text-ink-gray-8">
            <span>{{ __('Razem') }}</span><span>{{ formatPln(dealFields.custom_estimated_subsidy_pln) }}</span>
          </div>
        </div>

        <!--
          PV-line offer summary (Wycena) -- mirrors the "Dotacja wg grup prac"
          box above, styled the same way, but for the fotowoltaika/magazyn
          product lines instead of Czyste Powietrze. In practice this block
          and the CP subsidy box above are mutually exclusive: a PV deal never
          populates custom_cp_*, and a CP deal never populates custom_netto or
          the calculator's deal_value, so no v-else coupling between the two
          is needed -- `showWycena` and `hasGroupSubsidy` simply never agree.
        -->
        <div v-if="showWycena" class="mt-3 w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-2.5 text-sm">
          <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Wycena') }}</div>

          <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Konfiguracja') }}</div>
          <div v-if="wycenaFields.custom_typ_klienta" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Typ klienta') }}</span><span>{{ wycenaFields.custom_typ_klienta }}</span>
          </div>
          <div v-if="wycenaFields.custom_producent" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Producent') }}</span><span>{{ wycenaFields.custom_producent }}</span>
          </div>
          <div v-if="wycenaFields.custom_falownik" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Falownik') }}</span><span>{{ wycenaFields.custom_falownik }}</span>
          </div>
          <div v-if="wycenaFields.custom_bateria" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Magazyn energii') }}</span><span>{{ wycenaFields.custom_bateria }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_pojemnosc_kwh) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Pojemność magazynu') }}</span><span>{{ wycenaFields.custom_pojemnosc_kwh }} kWh</span>
          </div>
          <div v-if="Number(wycenaFields.custom_panele) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Liczba paneli') }}</span><span>{{ wycenaFields.custom_panele }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_pv_power_kwp) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Moc instalacji PV') }}</span><span>{{ wycenaFields.custom_pv_power_kwp }} kWp</span>
          </div>
          <div v-if="wycenaFields.custom_konstrukcja" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Konstrukcja') }}</span><span>{{ wycenaFields.custom_konstrukcja }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_kabel_m) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Dodatkowy kabel') }}</span><span>{{ wycenaFields.custom_kabel_m }} m</span>
          </div>

          <div class="mb-1 mt-1 border-t border-outline-gray-2 pt-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Cena') }}</div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Cena netto') }}</span><span>{{ formatPln(wycenaFields.custom_netto) }}</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('VAT') }}</span><span>{{ Number(wycenaFields.custom_vat_pct) }}%</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Cena brutto') }}</span><span class="font-medium text-ink-gray-8">{{ formatPln(wycenaFields.deal_value) }}</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Dotacja') }}</span><span>{{ formatPln(wycenaFields.custom_dotacja) }}</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Cena po dotacji') }}</span><span>{{ formatPln(wycenaFields.custom_cena_po_dotacji) }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_ulga_pct) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Ulga termomodernizacyjna') }}</span><span>{{ wycenaFields.custom_ulga_pct }}% · {{ formatPln(wycenaFields.custom_ulga_kwota) }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_ulga_pct) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Cena po uldze') }}</span><span>{{ formatPln(wycenaFields.custom_cena_po_uldze) }}</span>
          </div>

          <!--
            No gotówka/kredyt label here on purpose (owner decision,
            2026-08-13): the financing method lives on Volteo Umowa, filled
            in on the Umowa tab, not derived from these calculator fields.
          -->
          <div class="mb-1 mt-1 border-t border-outline-gray-2 pt-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Finansowanie') }}</div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Wpłata własna') }}</span><span>{{ formatPln(wycenaFields.custom_wplata_wlasna) }}</span>
          </div>
          <div v-if="Number(wycenaFields.custom_okres_lat) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Okres kredytowania') }}</span><span>{{ wycenaFields.custom_okres_lat }} lat</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Rata brutto') }}</span><span>{{ formatPln(wycenaFields.custom_rata_brutto) }} /mies.</span>
          </div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Rata po dotacji') }}</span><span>{{ formatPln(wycenaFields.custom_rata_po_dotacji) }} /mies.</span>
          </div>
          <div v-if="Number(wycenaFields.custom_ulga_pct) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Rata po uldze') }}</span><span>{{ formatPln(wycenaFields.custom_rata_po_uldze) }} /mies.</span>
          </div>
        </div>

        <!--
          Sales commission — internal-only, permission-driven (see `hasCommission`
          below): the server strips this field for any role without permlevel-2
          read on CRM Deal, so a non-admin's dealSubsidy.data simply never has this
          key and the block below never renders for them. Deliberately styled with
          the amber "internal warning" treatment already used on this tab family
          (see AudytTab.vue / UmowaTab.vue), NOT the plain gray of the customer-
          facing subsidy box above, so nobody mistakes it for a quotable figure.
        -->
        <div
          v-if="hasCommission"
          class="mt-3 max-w-xs rounded-lg border border-outline-amber-3 bg-surface-amber-2 p-2.5 text-sm"
        >
          <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-amber-8">
            {{ __('Prowizja handlowa — widoczne tylko dla administratorów') }}
          </div>
          <div class="flex justify-between py-0.5 text-ink-amber-8">
            <span>{{ __('Prowizja') }}</span>
            <span class="font-medium">{{ formatPln(dealFields.custom_cp_prowizja_handlowa) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ZestawIcon from '@/components/Icons/ZestawIcon.vue'
import { Badge, createResource } from 'frappe-ui'
import { computed } from 'vue'
import { formatPln, roundPln } from '@/utils/money'

const props = defineProps({
  dealId: { type: String, required: true },
})

// Itemized BOM (preferred), from the deal's custom_zestaw child table.
const bom = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Zestaw Item',
    // Parent DOCTYPE NAME required by check_parent_permission() for child-table
    // get_list calls — distinct from filters.parent below, which is the deal ID.
    parent: 'CRM Deal',
    filters: { parenttype: 'CRM Deal', parentfield: 'custom_zestaw', parent: props.dealId },
    fields: ['typ', 'nazwa', 'ilosc', 'jednostka', 'netto', 'brutto'],
    order_by: 'idx asc',
    limit_page_length: 200,
  },
  auto: true,
})

// Post-cap group subsidy totals live on the deal itself, not on the BOM rows
// (see the comment above `hasMoney` below for why the rows can no longer
// carry a per-line `dotacja`). Fetched separately because it's a handful of
// scalar fields on CRM Deal, not part of the child-table listing.
const dealSubsidy = createResource({
  url: 'frappe.client.get_value',
  params: {
    doctype: 'CRM Deal',
    filters: props.dealId,
    fieldname: [
      'custom_cp_dotacja_zrodlo',
      'custom_cp_dotacja_co',
      'custom_cp_dotacja_termo',
      'custom_estimated_subsidy_pln',
      // permlevel 2 (Volteo Core Admin / System Manager only, see
      // ops/crm-zestaw-cp.py): Frappe silently drops this key from the response
      // for every other role instead of returning null or erroring -- verified
      // empirically via frappe.client.get_value during implementation. `hasCommission`
      // below treats "key absent" and "key present but 0" identically (both render
      // nothing), so this is safe to always request.
      'custom_cp_prowizja_handlowa',
    ],
  },
  auto: true,
})

// PV-line offer financials, persisted on the deal by the PV calculator (see
// crm-kalkulator-bom.py). Unlike dealSubsidy above, none of these fields
// carry a permlevel restriction, so there is no admin-only branch here --
// every role that can open this tab sees the same response.
// custom_narzut (internal rep markup) is deliberately NOT fetched: it must
// never reach this tab.
const dealWycena = createResource({
  url: 'frappe.client.get_value',
  params: {
    doctype: 'CRM Deal',
    filters: props.dealId,
    fieldname: [
      'custom_rodzaj_umowy',
      'custom_typ_klienta',
      'custom_producent',
      'custom_falownik',
      'custom_bateria',
      'custom_pojemnosc_kwh',
      'custom_panele',
      'custom_pv_power_kwp',
      'custom_konstrukcja',
      'custom_kabel_m',
      'custom_netto',
      'custom_vat_pct',
      'deal_value',
      'custom_dotacja',
      'custom_cena_po_dotacji',
      'custom_ulga_pct',
      'custom_ulga_kwota',
      'custom_cena_po_uldze',
      'custom_wplata_wlasna',
      'custom_okres_lat',
      'custom_rata_brutto',
      'custom_rata_po_dotacji',
      'custom_rata_po_uldze',
    ],
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

// Polish UI renders the stored ASCII unit 'm2' as 'm²'; 'szt' renders as-is.
function jednostkaLabel(jednostka) {
  return jednostka === 'm2' ? 'm²' : jednostka || ''
}

// Quantity cell: unit follows the number only when the row actually has one
// (legacy PV rows have no jednostka). A missing/zero quantity still renders
// blank, never a bare '0' — matches the previous `row.ilosc || ''` behaviour.
function iloscLabel(row) {
  if (!row.ilosc) return ''
  const jednostka = jednostkaLabel(row.jednostka)
  return jednostka ? `${row.ilosc} ${jednostka}` : `${row.ilosc}`
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
    { typ: 'Dotacja', nazwa: d.subsidy_pln ? formatPln(d.subsidy_pln) : '', ilosc: '' },
    { typ: 'Gwarancja', nazwa: d.warranty_years ? d.warranty_years + ' lat' : '', ilosc: '' },
  ]
})

const rows = computed(() => (bomRows.value.length ? bomRows.value : ofertaRows.value))
const caption = computed(() =>
  bomRows.value.length
    ? __('Wykaz pozycji zestawu.')
    : __('Podgląd na podstawie oferty z Kalkulatora OZE. Pełny wykaz komponentów — wkrótce.'),
)

// Money columns are Czyste Powietrze-only: the PV path never populates netto/
// brutto, and neither do the 34 rows that predate this schema change, so on a
// PV deal (and on every legacy row) this stays false and the table looks
// exactly as it did before these fields existed — two money columns, no
// '0 zł' noise. A single non-zero `brutto` anywhere in the zestaw is enough
// to reveal both columns for every row.
const hasMoney = computed(() => rows.value.some((row) => Number(row.brutto) > 0))
// Sumujemy zaokrąglone wartości wierszy, nie surowe — każdy wiersz wyświetla
// się już zaokrąglony do groszy, więc suma z surowych kwot potrafiłaby
// widocznie nie zgadzać się z kolumną nad nią o grosz.
const totalNetto = computed(() => rows.value.reduce((sum, row) => sum + roundPln(row.netto), 0))
const totalBrutto = computed(() => rows.value.reduce((sum, row) => sum + roundPln(row.brutto), 0))

// Group subsidy totals, fetched from the parent deal (see `dealSubsidy`
// above). Read by value, never `hasOwnProperty` — `dealFields` guards against
// the resource not having answered yet by declaring every key up front with
// a `0` fallback, so `Number(...)` checks below stay well-defined on every
// render, not just after the fetch resolves.
const dealFields = computed(() => ({
  custom_cp_dotacja_zrodlo: 0,
  custom_cp_dotacja_co: 0,
  custom_cp_dotacja_termo: 0,
  custom_estimated_subsidy_pln: 0,
  // Declared up front with a 0 fallback like every other field here, for the
  // same reason: a `computed` must never gate on key presence/absence on a
  // `reactive` object (Vue's proxy defines no `getOwnPropertyDescriptor` trap,
  // so a `hasOwnProperty`/`in` read registers no dependency and freezes at
  // first evaluation -- see KalkulatorCPTab.vue's admin-cost-panel bug). Plain
  // `Number(...) > 0` below reads the value itself, never the key.
  custom_cp_prowizja_handlowa: 0,
  ...(dealSubsidy.data || {}),
}))
const hasGroupSubsidy = computed(() =>
  Number(dealFields.value.custom_cp_dotacja_zrodlo) > 0 ||
  Number(dealFields.value.custom_cp_dotacja_co) > 0 ||
  Number(dealFields.value.custom_cp_dotacja_termo) > 0,
)
// Permission-driven, not role-driven: a non-admin's dealSubsidy.data never has
// this key at all (Frappe strips permlevel-2 fields server-side -- see the
// fetch comment above), so it falls through to the `0` default here and this
// stays false. An admin viewing a deal where the commission was genuinely
// never computed (e.g. a PV deal, or any deal from before this field existed)
// ALSO reads back an unset Currency column as `0` -- indistinguishable from a
// real zero at the SQL level -- so `> 0`, not a presence check, is what keeps
// that case blank too instead of rendering a misleading "0 zł".
const hasCommission = computed(() => Number(dealFields.value.custom_cp_prowizja_handlowa) > 0)

// PV offer financials, fetched from the parent deal (see `dealWycena`
// above). Same explicit-defaults pattern as `dealFields`: every key declared
// up front so `Number(...)`/truthiness checks below stay well-defined before
// the fetch resolves, and so nothing here ever reads via `hasOwnProperty`/`in`
// on the resource's reactive `.data` (Vue's reactive proxy defines no
// `getOwnPropertyDescriptor` trap, so that kind of read registers no
// dependency and freezes a computed at its first evaluation -- see the
// KalkulatorCPTab.vue admin-cost-panel bug referenced above). custom_ulga_pct
// is a Data field holding a numeric-looking string (e.g. "19"), so its
// default is `'0'`, not `0`.
const wycenaFields = computed(() => ({
  custom_rodzaj_umowy: '',
  custom_typ_klienta: '',
  custom_producent: '',
  custom_falownik: '',
  custom_bateria: '',
  custom_pojemnosc_kwh: 0,
  custom_panele: 0,
  custom_pv_power_kwp: 0,
  custom_konstrukcja: '',
  custom_kabel_m: 0,
  custom_netto: 0,
  custom_vat_pct: 0,
  deal_value: 0,
  custom_dotacja: 0,
  custom_cena_po_dotacji: 0,
  custom_ulga_pct: '0',
  custom_ulga_kwota: 0,
  custom_cena_po_uldze: 0,
  custom_wplata_wlasna: 0,
  custom_okres_lat: 0,
  custom_rata_brutto: 0,
  custom_rata_po_dotacji: 0,
  custom_rata_po_uldze: 0,
  ...(dealWycena.data || {}),
}))

// PV-line product interest values only -- CP deals never populate
// custom_rodzaj_umowy with one of these, so the box below stays hidden for
// them. See "Product-line switch" in CLAUDE.md.
const PV_RODZAJE = new Set(['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii'])
// Gated on rodzaj + a real priced amount, not just rodzaj: a PV deal that was
// switched to that rodzaj before ever running the calculator has no netto/
// deal_value yet and must render nothing rather than a box full of zeros.
const showWycena = computed(() =>
  PV_RODZAJE.has(wycenaFields.value.custom_rodzaj_umowy) &&
  (Number(wycenaFields.value.custom_netto) > 0 || Number(wycenaFields.value.deal_value) > 0),
)
</script>
