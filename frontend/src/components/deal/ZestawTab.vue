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
          Trify box, separate from the subsidy box above: this box is now
          Trify-first, not wkład-własny-first (owner decision, 2026-09-04).

          The fixed part (always shown once hasCpFinancing is true) carries
          only the Trify figures -- Kwota Trify, then Rata Trify gated on its
          own value being > 0 (see below). Wkład własny beneficjenta
          (custom_cp_wklad_wlasny) moved OUT of the fixed part and into the
          credit sub-block below, as its first row, right after the "Kredyt
          na wkład własny" sub-header: it is now shown only in the context of
          the loan that covers it, per the owner's call. That field itself
          stays WITHOUT a v-if (0 is a real value there -- it means the
          subsidy alone covers the own contribution -- unlike the Currency/
          Int columns below it that use 0 as "not set").

          The credit sub-block (Wkład własny beneficjenta through Rata
          wkładu własnego) stays gated on custom_cp_okres_lat > 0, not on
          presence of the fields: they are plain Int/Currency columns on CRM
          Deal, `NOT NULL DEFAULT 0` in SQL, so a deal created before this
          feature -- or one where the rep left financing switched off --
          reads 0 regardless, and that must hide the credit rows rather than
          render zeroed ones. See `hasCpFinancing` below for why it reads all
          three value families, not just custom_rodzaj_umowy.

          Note: custom_cp_wklad_wlasny itself is ALWAYS visible elsewhere
          regardless of this box's Kredyt gate -- the right-hand deal panel's
          own "Finansowanie" section (depends_on keyed off custom_rodzaj_umowy)
          always shows it. This box only controls whether Zestaw additionally
          surfaces it inside the credit context.
        -->
        <div v-if="hasCpFinancing" class="mt-3 w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-2.5 text-sm">
          <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Finansowanie Trify') }}</div>
          <div class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Kwota Trify') }}</span><span>{{ formatPln(dealFields.custom_cp_podstawa_trify) }}</span>
          </div>
          <!-- Rata Trify lives in the fixed part of the box, not the credit
               sub-block below: it is computed from the Trify basis alone and
               does not depend on the wkład-własny loan. It still needs its
               own v-if here, gated on the VALUE not the key, because
               custom_cp_rata_trify is only ever written by the API when the
               financing switch was on -- an unfinanced/pre-feature deal reads
               the SQL default 0, and 0 must hide the row rather than render
               "0,00 zł /mies.". -->
          <div v-if="Number(dealFields.custom_cp_rata_trify) > 0" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Rata Trify') }}</span><span>{{ formatPln(dealFields.custom_cp_rata_trify) }} /mies.</span>
          </div>

          <template v-if="Number(dealFields.custom_cp_okres_lat) > 0">
            <div class="mb-1 mt-1 border-t border-outline-gray-2 pt-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Kredyt na wkład własny') }}</div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Wkład własny beneficjenta') }}</span><span>{{ formatPln(dealFields.custom_cp_wklad_wlasny) }}</span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Wpłata gotówką') }}</span><span>{{ formatPln(dealFields.custom_cp_wplata_gotowka) }}</span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Kwota kredytu') }}</span><span>{{ formatPln(dealFields.custom_cp_kwota_kredytu) }}</span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Okres kredytowania') }}</span><span>{{ dealFields.custom_cp_okres_lat }} lat</span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Rata wkładu własnego') }}</span><span>{{ formatPln(dealFields.custom_cp_rata_wkladu) }} /mies.</span>
            </div>
          </template>
        </div>

        <!--
          PV-line offer summary (Wycena) -- mirrors the "Dotacja wg grup prac"
          box above, styled the same way, but for the fotowoltaika/magazyn
          product lines instead of Czyste Powietrze. In practice this block
          and the CP subsidy/financing boxes above are mutually exclusive: a
          PV deal never populates custom_cp_*, and a CP deal never populates
          custom_netto or the calculator's deal_value, so no v-else coupling
          between them is needed -- `showWycena`, `hasGroupSubsidy` and
          `hasCpFinancing` simply never agree.
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
          <div v-if="wycenaFields.custom_zasady_dotacji" class="flex justify-between py-0.5 text-ink-gray-7">
            <span>{{ __('Zasady dotacji') }}</span><span>{{ wycenaFields.custom_zasady_dotacji }}</span>
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
          Sales commission — permission-driven (see `hasCommission` below),
          but no longer admin-only (owner decision): visible to the deal's
          owning rep (`deal_owner`) as well as admins. The underlying field
          (`custom_cp_prowizja_handlowa`) is still permlevel 2 on every other
          path — that protection is unchanged, and the admin-OR-owner rule
          enforced server-side by the endpoint is unchanged too. This box
          instead reaches it through a dedicated endpoint
          (`crm.api.koszty.volteo_prowizja_szansy`, see the `dealCommission`
          fetch in the script) that enforces `admin OR deal_owner`
          server-side and throws for anyone else; a disallowed viewer's fetch
          fails silently (no toast, no console noise — see the fetch
          comment) and `hasCommission` stays false, so the block below simply
          never renders for them. Deliberately styled with the amber
          "internal warning" treatment already used on this tab family (see
          AudytTab.vue / UmowaTab.vue), NOT the plain gray of the
          customer-facing subsidy box above, so nobody mistakes it for a
          quotable figure.

          Issue #50: the box is now a TIER BREAKDOWN, not a single figure —
          the endpoint trims `prowizje` to the CALLING user's own commission
          level (`crm.api.koszty.volteo_prowizja_szansy`'s docstring), so a
          Handlowiec caller sees only their own base row, a Manager also sees
          their nadprowizja + a SUMA of the two, and a Partner/admin sees the
          full three-row breakdown + SUMA. The nadprowizja rows and the SUMA
          row are hidden individually when their value is `0` (`v-if`, not
          CSS) — see `commissionFields`/`hasNadprowizje` in the script — so
          an old (pre-b53) deal, or one where rates are still seeded at `0`,
          degrades to today's single-row look instead of showing misleading
          "0,00 zł" rows.

          Collapsible, collapsed by default (owner decision, same reasoning as
          KalkulatorTab.vue's showAdminBreakdown and MontazKosztyPanel.vue's
          own toggle below): this figure must not be visible by default during
          a screenshare. Only the expand/collapse is new here — the
          `hasCommission` gate itself still fully controls whether the toggle
          button (and everything inside it) exists at all, not merely
          whether it's collapsed.
        -->
        <div v-if="hasCommission" class="mt-3 max-w-xs">
          <button
            type="button"
            class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
            @click="showCommission = !showCommission"
          >
            <span>{{ __('Prowizja — rozkład wg poziomu — widoczne dla opiekuna szansy i administratorów') }}</span>
            <FeatherIcon :name="showCommission ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
          </button>
          <div v-show="showCommission" class="mt-1.5 rounded-lg border border-outline-amber-3 bg-surface-amber-2 p-2.5 text-sm">
            <div class="flex justify-between py-0.5 text-ink-amber-8">
              <span>{{ __('Prowizja handlowiec') }}</span>
              <span class="font-medium">{{ formatPln(commissionFields.handlowiec) }}</span>
            </div>
            <div v-if="commissionFields.nadprowizja_manager > 0" class="flex justify-between py-0.5 text-ink-amber-8">
              <span>{{ __('Nadprowizja manager') }}</span>
              <span class="font-medium">{{ formatPln(commissionFields.nadprowizja_manager) }}</span>
            </div>
            <div v-if="commissionFields.nadprowizja_partner > 0" class="flex justify-between py-0.5 text-ink-amber-8">
              <span>{{ __('Nadprowizja partner') }}</span>
              <span class="font-medium">{{ formatPln(commissionFields.nadprowizja_partner) }}</span>
            </div>
            <div v-if="hasNadprowizje" class="flex justify-between border-t border-outline-amber-3 py-0.5 pt-1 font-medium text-ink-amber-8">
              <span>{{ __('SUMA') }}</span>
              <span>{{ formatPln(commissionFields.suma) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!--
        Koszty rzeczywiste (montaż/realizacja) — admin-only panel, placed at
        the very bottom of this tab's content (owner decision, moved here
        from MontazTab.vue where it was originally placed by mistake). Lives
        outside the loading/empty/populated v-if chain above on purpose: the
        underlying snapshot (`CRM Deal.custom_koszty_json`) is independent of
        whether this deal has BOM rows to show, so the panel must still
        render for a deal with no zestaw. It renders nothing itself when
        there is no usable snapshot (permlevel-2 field absent for a
        non-admin, or a pre-b49 deal) — see the component's own header
        comment. Kept inside this `max-w-5xl` container (not full page
        width) so it scrolls with the rest of the tab's content and lines up
        with the table above.
      -->
      <MontazKosztyPanel :deal-id="dealId" />
    </div>
  </div>
</template>

<script setup>
import ZestawIcon from '@/components/Icons/ZestawIcon.vue'
import { Badge, FeatherIcon, createResource } from 'frappe-ui'
import MontazKosztyPanel from '@/components/deal/MontazKosztyPanel.vue'
import { computed, ref } from 'vue'
import { formatPln, roundPln } from '@/utils/money'

const props = defineProps({
  dealId: { type: String, required: true },
})

// Collapsed by default so the sales commission figure is not visible during
// screenshares — mirrors KalkulatorTab.vue's showAdminBreakdown and
// MontazKosztyPanel.vue's own toggle (see the template comment above).
const showCommission = ref(false)

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
//
// None of these subsidy fields carry a permlevel restriction (unlike the
// commission field below, which used to live in this same fetch — see
// `dealCommission` further down for why it was split out).
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
      'custom_cp_wklad_wlasny',
      'custom_cp_podstawa_trify',
      'custom_cp_okres_lat',
      'custom_cp_wplata_gotowka',
      'custom_cp_kwota_kredytu',
      'custom_cp_rata_wkladu',
      'custom_cp_rata_trify',
    ],
  },
  auto: true,
})

// Sales commission — visible to the deal's owning rep (`deal_owner`) AND
// admins, not admins only (owner decision). `custom_cp_prowizja_handlowa`
// itself is still permlevel 2 (Volteo Core Admin / System Manager only, see
// ops/crm-zestaw-cp.py) on every OTHER path — that field-level protection is
// unchanged and still the reason it can never be fetched via a plain
// `frappe.client.get_value` for a rep. This tab reaches it instead through a
// dedicated whitelisted endpoint that re-derives the same value under an
// explicit `admin OR deal_owner` check server-side
// (`crm.api.koszty.volteo_prowizja_szansy`) — full dotted path is mandatory,
// a bare method name resolves only for Server Scripts (see the api-call-path
// trap documented in UmowaTab.vue).
//
// The endpoint THROWS PermissionError for anyone who is neither admin nor
// the deal owner (unlike the old permlevel-strip fetch above, which failed
// silently by omitting the key) — so unlike `dealSubsidy`, this fetch MUST
// swallow its error into "no commission shown" with no toast and no console
// noise: a backoffice user or a rep who doesn't own this particular deal is
// an entirely expected, non-exceptional viewer of this tab, not an error
// condition to surface. Mirrors MontazKosztyPanel.vue's own onError, which
// does exactly the same swallow-to-null for the same permission-denied-is-
// normal reason.
//
// Issue #50 (ops#48 server side): the response grew a second key, `prowizje`,
// a dict already TRIMMED SERVER-SIDE to the CALLER's own commission tier —
// Handlowiec gets `{handlowiec}`, Manager gets `{handlowiec,
// nadprowizja_manager, suma}`, Partner/admin get the full four keys
// (`handlowiec`, `nadprowizja_manager`, `nadprowizja_partner`, `suma`). The
// legacy top-level `prowizja` key is unchanged (handlowiec base, or `null`
// when it's zero/unset) and is kept specifically as the fallback for two
// cases this tab must not break on: a flag-off caller, where the endpoint
// silently degrades to `{prowizja: null, prowizje: null}` instead of
// throwing (see the endpoint's own docstring), and an old (pre-b53) response
// shape from a stale image, which has no `prowizje` key at all. See
// `commissionFields` below for how the fallback is applied once, not
// scattered across every read site.
const dealCommission = createResource({
  url: 'crm.api.koszty.volteo_prowizja_szansy',
  params: { deal: props.dealId },
  auto: true,
  onError: () => {
    /* PermissionError for a non-owner/non-admin viewer is expected — leave
       dealCommission.data unset so hasCommission below stays false. */
  },
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
      'custom_zasady_dotacji',
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
// render, not just after the fetch resolves. This is the same general rule
// applied everywhere in this file (and the codebase — see
// KalkulatorCPTab.vue's admin-cost-panel bug): a `computed` must never gate
// on key presence/absence on a `reactive` object (Vue's proxy defines no
// `getOwnPropertyDescriptor` trap, so a `hasOwnProperty`/`in` read registers
// no dependency and freezes at first evaluation) — plain `Number(...) > 0`
// reads the value itself, never the key.
const dealFields = computed(() => ({
  custom_cp_dotacja_zrodlo: 0,
  custom_cp_dotacja_co: 0,
  custom_cp_dotacja_termo: 0,
  custom_estimated_subsidy_pln: 0,
  custom_cp_wklad_wlasny: 0,
  custom_cp_podstawa_trify: 0,
  custom_cp_okres_lat: 0,
  custom_cp_wplata_gotowka: 0,
  custom_cp_kwota_kredytu: 0,
  custom_cp_rata_wkladu: 0,
  custom_cp_rata_trify: 0,
  ...(dealSubsidy.data || {}),
}))
const hasGroupSubsidy = computed(() =>
  Number(dealFields.value.custom_cp_dotacja_zrodlo) > 0 ||
  Number(dealFields.value.custom_cp_dotacja_co) > 0 ||
  Number(dealFields.value.custom_cp_dotacja_termo) > 0,
)
// Own-contribution / Trify / credit box gate — read by value, never by key
// presence (see the reactive-hasOwnProperty trap referenced throughout this
// file). Deliberately NOT gated on custom_rodzaj_umowy: a CP deal with no
// subsidy at all (so `hasGroupSubsidy` above is false) can still have a real
// wkład własny and Trify basis, and those must render regardless of whether
// the rep ever switched the credit sub-block on. An OZE deal never populates
// any of these three field families, so this stays false there the same way
// `hasGroupSubsidy` does.
const hasCpFinancing = computed(() =>
  Number(dealFields.value.custom_cp_wklad_wlasny) > 0 ||
  Number(dealFields.value.custom_cp_podstawa_trify) > 0 ||
  Number(dealFields.value.custom_cp_okres_lat) > 0,
)
// Issue #50: single source of truth for every field the commission box
// reads, mirroring the `dealFields`/`wycenaFields` explicit-defaults pattern
// elsewhere in this file — a `computed` must read values, never gate on key
// presence/absence on a resource's reactive `.data` (see the
// KalkulatorCPTab.vue admin-cost-panel bug referenced above; the same trap
// applies to `dealCommission.data` here). Each key resolves independently:
//   - `handlowiec` falls back from the trimmed `prowizje.handlowiec` to the
//     legacy top-level `prowizja` — covers a Handlowiec-tier caller (whose
//     `prowizje` has no `suma` but does carry `handlowiec`) and, further,
//     an old (pre-b53) response with no `prowizje` key at all.
//   - `nadprowizja_manager` / `nadprowizja_partner` default to `0` when the
//     caller's tier doesn't carry that key (Handlowiec sees neither, Manager
//     sees only the first) — `> 0` template guards below then simply never
//     fire, no separate "does this key exist" branch needed.
//   - `suma` falls back the same way `handlowiec` does: a Handlowiec-tier
//     `prowizje` has no `suma` key, so this resolves to the legacy
//     `prowizja` (their own base commission) — which is exactly the number
//     `hasCommission` below needs regardless of tier.
// A flag-off caller gets `{prowizja: null, prowizje: null}`: every key here
// then falls all the way through to its `0` default, so `hasCommission`
// stays false and the whole box stays absent — no silent "0 zł" render.
const commissionFields = computed(() => ({
  handlowiec: dealCommission.data?.prowizje?.handlowiec ?? dealCommission.data?.prowizja ?? 0,
  nadprowizja_manager: dealCommission.data?.prowizje?.nadprowizja_manager ?? 0,
  nadprowizja_partner: dealCommission.data?.prowizje?.nadprowizja_partner ?? 0,
  suma: dealCommission.data?.prowizje?.suma ?? dealCommission.data?.prowizja ?? 0,
}))

// Permission-driven, not role-driven: `dealCommission` (see above) is the
// dedicated endpoint result, gated server-side on admin OR deal_owner. A
// viewer who is neither gets a swallowed PermissionError and `.data` stays
// unset, so every `commissionFields` key defaults to `0` -> `hasCommission`
// is `false`. A deal where the commission was genuinely never computed (e.g.
// a PV deal, or any deal from before this field existed) reads back
// `prowizja: null` / an all-zero `prowizje` from the endpoint the same way --
// `> 0`, not a presence check, is what keeps both cases blank instead of
// rendering a misleading "0 zł" or throwing on `null`.
const hasCommission = computed(() => Number(commissionFields.value.suma) > 0)

// SUMA row (and, by the same signal, the two nadprowizja rows above it in
// the template) is shown only once there is a real level breakdown to show —
// a Handlowiec-tier caller's `prowizje` never carries either nadprowizja key
// (both default to `0` above), so this stays `false` and an old/base-only
// deal keeps today's single-row look, pixel-identical.
const hasNadprowizje = computed(() =>
  commissionFields.value.nadprowizja_manager > 0 || commissionFields.value.nadprowizja_partner > 0,
)

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
  custom_zasady_dotacji: '',
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
