<!--
  Volteo Kalkulator — native-styled quote builder tab in the Klient view.
  Styled to match the CRM's frappe-ui design system exactly.
  ZERO pricing math in this file — all computed server-side.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div v-if="errorMsg" class="mb-2.5 flex items-center justify-between rounded border border-outline-red-3 bg-surface-red-2 px-3 py-2 text-sm text-ink-red-8">
        <span>{{ errorMsg }}</span>
        <button class="ml-2 text-base font-bold leading-none" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <div class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr)">

          <div>
            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">1</span>Instalacja
              </div>

              <div>
                <div class="mb-0.5 text-sm text-ink-gray-5">Rodzaj instalacji</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="v in VARIANTS" :key="v"
                    class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                    :class="sel.variant === v
                      ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                      : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                    @click="sel.variant = v"
                  >{{ v }}</button>
                </div>
              </div>

              <div class="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 kalk-row2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Typ klienta</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="opt in TYP_KLIENTA_OPTIONS" :key="opt.value"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="sel.typKlienta === opt.value
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="sel.typKlienta = opt.value"
                    >{{ opt.label }}</button>
                  </div>
                </div>

                <!-- Battery-only has no PV to size, so this input (a PV-sizing
                     parameter) is meaningless for that variant and is hidden. -->
                <div v-if="hasPv">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Roczne zużycie (kWh)</div>
                  <input
                    v-model.number="sel.consumption" type="number" min="0" step="1"
                    class="kalk-input"
                  />
                  <div v-if="sel.consumption > 0" class="mt-1 text-xs leading-relaxed text-ink-gray-4">
                    Sug. moc: <span class="font-medium text-ink-gray-6">{{ suggestedKwp }} kW</span>
                    <template v-if="hasBat">
                       · magazyn: <span class="font-medium text-ink-gray-6">{{ suggestedStorage }} kWh</span>
                    </template>
                    <button type="button" class="ml-1 font-medium text-ink-blue-link hover:underline" @click="applyFromConsumption">Ustaw</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">2</span>Konfiguracja
              </div>

              <div class="mb-2">
                <div class="mb-1 text-sm text-ink-gray-5">Producent</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="p in producentOptions" :key="p"
                    class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                    :class="sel.producent === p
                      ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                      : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                    @click="sel.producent = p"
                  >{{ p }}</button>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-x-3 gap-y-2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Falownik</div>
                  <select v-model="sel.falownik" class="kalk-select">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in falownikOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                  </select>
                </div>

                <div v-if="hasBat">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Magazyn energii</div>
                  <select v-model="sel.bateria" class="kalk-select">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in bateriaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                  </select>
                </div>

                <template v-if="hasPv">
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Panel fotowoltaiczny</div>
                    <select v-model="sel.panel" class="kalk-select">
                      <option value="">-- wybierz --</option>
                      <option v-for="c in panelOptions" :key="c.name" :value="c.name">{{ panelLabel(c) }}</option>
                    </select>
                  </div>
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Moc instalacji PV</div>
                    <select v-model.number="sel.mocPvKw" class="kalk-select" :disabled="!sel.panel">
                      <option :value="null">{{ sel.panel ? '-- wybierz --' : 'Najpierw wybierz panel' }}</option>
                      <option v-for="o in mocOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                    </select>
                  </div>
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Konstrukcja</div>
                    <select v-model="sel.konstrukcja" class="kalk-select">
                      <option value="">-- wybierz --</option>
                      <option v-for="c in konstrukcjaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                    </select>
                  </div>
                </template>
              </div>
            </div>

            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">3</span>Montaż i przyłącze
              </div>

              <div class="grid grid-cols-2 gap-x-3 gap-y-2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Dodatkowy kabel (m)</div>
                  <input v-model.number="sel.kabelM" type="number" min="0" step="1" class="kalk-input" />
                </div>
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Spółdzielnia energetyczna</div>
                  <select v-model="sel.spoldzielnia" class="kalk-select">
                    <option value="Nie">Nie</option>
                    <option value="Tak">Tak</option>
                  </select>
                </div>

                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Operator energetyczny</div>
                  <select v-model="sel.operator" class="kalk-select">
                    <option value="">—</option>
                    <option v-for="c in operatorOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
                <!-- Battery-only has no roof install, so there is no mounting
                     direction to choose for that variant. -->
                <div v-if="hasPv">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Kierunek montażu</div>
                  <select v-model="sel.kierunek" class="kalk-select">
                    <option value="">—</option>
                    <option v-for="c in kierunekOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">4</span>Finansowanie
              </div>

              <div class="grid grid-cols-2 gap-x-3 gap-y-2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Ulga termomodernizacyjna</div>
                  <select v-model.number="sel.ulgaPct" class="kalk-select">
                    <option :value="12">12%</option>
                    <option :value="19">19%</option>
                  </select>
                </div>
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Okres finansowania (lat)</div>
                  <select v-model.number="sel.okresLat" class="kalk-select">
                    <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>

                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Wpłata własna (PLN)</div>
                  <input v-model.number="sel.wplataWlasna" type="number" min="0" step="0.01" class="kalk-input" />
                </div>
              </div>
            </div>
          </div>

          <div class="kalk-output border-l border-outline-gray-2 pl-5">
            <div class="sticky top-3">
              <div class="mb-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-1.5 text-sm font-medium text-ink-gray-7 transition-colors hover:bg-surface-gray-2"
                  @click="showNarzut = !showNarzut"
                >
                  <span>{{ showNarzut ? 'Ukryj ustawienia niestandardowe' : 'Pokaż ustawienia niestandardowe' }}</span>
                  <FeatherIcon :name="showNarzut ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
                </button>
                <div v-if="showNarzut" class="mt-1.5">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Wysokość narzutu</div>
                  <input
                    v-model.number="sel.narzut" type="number" min="0" max="7000" step="0.01"
                    class="kalk-input"
                    @blur="sel.narzut = Math.min(7000, Math.max(0, Number(sel.narzut) || 0))"
                  />
                  <div v-if="!narzutValid" class="mt-0.5 text-xs text-ink-red-6">Narzut musi być w zakresie 0–7000 zł.</div>
                </div>
              </div>

              <div class="mb-2 text-base font-semibold text-ink-gray-9">Wycena</div>

              <div v-if="summary.lines.length" class="mb-2">
                <div
                  v-for="(ln, i) in summary.lines" :key="i"
                  class="flex items-center gap-2 border-t border-outline-gray-1 py-1.5 text-sm first:border-t-0"
                >
                  <span class="min-w-[88px] text-ink-gray-5">{{ ln.typ }}</span>
                  <span class="flex-1 text-ink-gray-8">{{ ln.nazwa }}</span>
                  <span class="tabular-nums text-ink-gray-7">×{{ formatQty(ln.ilosc) }}</span>
                </div>
              </div>
              <div v-else class="mb-2 text-sm text-ink-gray-5">Uzupełnij konfigurację, aby zobaczyć wycenę.</div>

              <template v-if="summary.lines.length">
                <div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-2.5">
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>Suma netto</span><span>{{ formatPln(summary.netto) }}</span>
                  </div>
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>VAT ({{ summary.vat_rate }}%)</span><span>{{ formatPln(summary.vat) }}</span>
                  </div>
                  <div class="mt-1 flex justify-between border-t border-outline-gray-2 pt-1.5 text-base font-semibold tabular-nums text-ink-gray-9">
                    <span>Suma brutto</span><span>{{ formatPln(summary.brutto) }}</span>
                  </div>

                  <template v-if="sel.typKlienta === 'indywidualny'">
                    <div class="mt-1.5 border-t border-dashed border-outline-gray-2 pt-1.5">
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Dotacja Przydomowe Magazyny Energii</span><span>− {{ formatPln(summary.dotacja) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Cena po dotacji</span><span>{{ formatPln(summary.cena_po_dotacji) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Ulga termo. ({{ sel.ulgaPct }}%)</span><span>− {{ formatPln(summary.ulga) }}</span>
                      </div>
                      <div class="mt-1 flex justify-between border-t border-outline-gray-2 pt-1.5 text-base font-semibold tabular-nums text-ink-gray-9">
                        <span>Cena po uldze</span><span>{{ formatPln(summary.cena_po_uldze) }}</span>
                      </div>
                      <div class="mt-0.5 flex justify-between py-0.5 text-xs tabular-nums text-ink-gray-5">
                        <span>Rata ({{ sel.okresLat }} lat)</span>
                        <span>{{ formatPln(summary.raty.brutto) }} / {{ formatPln(summary.raty.po_dotacji) }} / {{ formatPln(summary.raty.po_uldze) }} /mies.</span>
                      </div>
                    </div>
                  </template>
                </div>
              </template>

              <div v-if="$slots['client-picker']" class="mb-2">
                <div class="mb-0.5 text-sm text-ink-gray-5">Klient</div>
                <slot name="client-picker" />
              </div>

              <Button
                class="mt-2 w-full"
                variant="solid"
                :disabled="!canGenerate || generating"
                @click="runGenerate"
              >
                {{ generating ? 'Generuję ofertę…' : 'Generuj ofertę' }}
              </Button>

              <div v-if="!c.name" class="mt-1 text-center text-xs text-ink-red-6">
                Wybierz klienta, aby wygenerować ofertę.
              </div>

              <div v-if="summary.is_admin && summary.breakdown" class="mt-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
                  @click="showAdminBreakdown = !showAdminBreakdown"
                >
                  <span>Admin - Ustawienia Zaawansowane</span>
                  <FeatherIcon :name="showAdminBreakdown ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
                </button>
                <div v-show="showAdminBreakdown" class="mt-1.5 rounded-lg border border-dashed border-outline-amber-3 bg-surface-amber-2 p-2.5">
                <div class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">Rozbicie kosztów (administrator)</div>
                <div v-for="grupa in grupyBreakdown" :key="grupa.klucz">
                  <div :class="grupa.klucz === 'hurtownia' ? 'mt-0' : 'mt-2'" class="mb-0.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">{{ grupa.etykieta }}</div>
                  <div v-for="p in grupa.pozycje" :key="p.klucz" class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ p.etykieta }}</span><span>{{ formatPln(p.kwota) }}</span></div>
                  <div class="mt-1 flex justify-between border-t border-outline-amber-2 pt-1 text-sm font-semibold tabular-nums text-ink-gray-9"><span>Razem</span><span>{{ formatPln(grupa.suma) }}</span></div>
                </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </template>

      <div v-else class="py-4">
        <div class="mb-2 text-base font-semibold text-ink-gray-9">Szansa utworzona</div>
        <p class="mb-3 text-sm text-ink-gray-7">{{ successSummary }}</p>
        <div class="flex gap-2">
          <a class="inline-flex items-center rounded bg-surface-gray-10 px-3 py-1.5 text-sm font-medium text-ink-base hover:bg-surface-gray-9" :href="dealHref" target="_blank" rel="noopener">Otwórz szansę w CRM</a>
          <Button variant="ghost" @click="resetFlow">Nowa oferta</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { call, Button, FeatherIcon } from 'frappe-ui'
import {
  VARIANTS,
  VARIANT_PV,
  VARIANT_PV_BAT,
  variantHasPv,
  variantHasBattery,
  producentOptionsFor,
  panelLabel,
  buildMocOptionsForPanel,
  snapMocToPanel,
  pickMocForTarget,
  suggestedKwp as suggestedKwpFor,
  suggestedStorageKwh,
  pickBySpec,
  pickMounting,
} from '@/utils/pvForm'
import { formatPln } from '@/utils/money'
import { grupujBreakdown } from '@/utils/pvBreakdown'

const props = defineProps({
  contact: { type: Object, default: () => ({}) },
})

const router = useRouter()

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie', 'łódzkie',
  'małopolskie', 'mazowieckie', 'opolskie', 'podkarpackie', 'podlaskie',
  'pomorskie', 'śląskie', 'świętokrzyskie', 'warmińsko-mazurskie',
  'wielkopolskie', 'zachodniopomorskie',
]
const TYP_KLIENTA_OPTIONS = [
  { value: 'indywidualny', label: 'Indywidualny' },
  { value: 'biznesowy', label: 'Biznesowy' },
]

// --- Prefill client data from the current contact --------------------------
const c = computed(() => props.contact || {})
function composeAddress() {
  const parts = [c.value.custom_ulica, c.value.custom_nr_domu].filter(Boolean).join(' ').trim()
  return c.value.custom_nr_mieszkania ? parts + '/' + c.value.custom_nr_mieszkania : parts
}
const voivodeshipPrefill = computed(() => {
  const w = (c.value.custom_wojewodztwo || '').toLowerCase().trim()
  return VOIVODESHIPS.indexOf(w) !== -1 ? w : ''
})

// --- Selections --------------------------------------------------------------
const sel = reactive({
  typKlienta: 'indywidualny',
  variant: 'Fotowoltaika + Magazyn',
  producent: '',
  falownik: '',
  bateria: '',
  panel: '',
  mocPvKw: null,
  konstrukcja: '',
  kabelM: 0,
  spoldzielnia: 'Nie',
  ulgaPct: 19,
  okresLat: 5,
  wplataWlasna: 0,
  narzut: 0,
  operator: '',
  kierunek: '',
  consumption: null,
})

const hasPv = computed(() => variantHasPv(sel.variant))
const hasBat = computed(() => variantHasBattery(sel.variant))

// Cascade: PV-only forces FoxESS; PV+Magazyn / Magazyn only offer Sigenergy/Deye.
const producentOptions = computed(() => producentOptionsFor(sel.variant))

watch(
  () => sel.variant,
  () => {
    if (!producentOptions.value.includes(sel.producent)) sel.producent = producentOptions.value[0]
    if (!hasPv.value) { sel.panel = ''; sel.mocPvKw = null; sel.konstrukcja = ''; sel.kierunek = ''; sel.consumption = null }
    if (!hasBat.value) sel.bateria = ''
  },
  { immediate: true },
)

// Reset downstream picks whenever producent changes (cascade rule).
watch(
  () => sel.producent,
  () => { sel.falownik = ''; sel.bateria = '' },
)

// --- Catalog (names + non-secret tags only — no prices ever fetched) -------
const catMap = reactive({})
function byKat(kat) {
  return catMap[kat] || []
}
function compLabel(x) {
  return [x.nazwa, x.model].filter(Boolean).join(' ')
}

async function loadComponents() {
  try {
    const data = await call('volteo_quote_components')
    const comps = (data && data.components) || []
    const m = {}
    for (const x of comps) {
      ;(m[x.kategoria] = m[x.kategoria] || []).push(x)
    }
    for (const k in m) catMap[k] = m[k]
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  }
}
loadComponents()

const falownikOptions = computed(() => byKat('Falownik').filter((x) => x.producent === sel.producent))
const bateriaOptions = computed(() => byKat('Magazyn energii').filter((x) => x.producent === sel.producent))
const konstrukcjaOptions = computed(() => byKat('Konstrukcja'))
const operatorOptions = computed(() => byKat('Operator'))
const kierunekOptions = computed(() => byKat('Kierunek montazu'))
const panelOptions = computed(() => byKat('Panel PV'))

function panelMocWp(panelName) {
  const p = panelOptions.value.find((x) => x.name === panelName)
  return p ? Number(p.moc_wp) || 0 : 0
}

// Moc-PV dropdown is panel-dependent: the panel count the server derives is
// round(moc_pv_kw * 1000 / moc_wp), so the client must only ever offer moc
// values that came from buildMocOptionsForPanel() of the selected panel.
const mocOptions = computed(() => {
  const wp = panelMocWp(sel.panel)
  return wp > 0 ? buildMocOptionsForPanel(wp) : []
})

// Changing the panel re-snaps an already-chosen moc to the new panel's grid;
// clearing the panel clears the dependent moc pick (mirrors the variant-reset
// convention above).
watch(
  () => sel.panel,
  (newPanel) => {
    if (!newPanel) {
      sel.mocPvKw = null
      return
    }
    if (sel.mocPvKw) {
      sel.mocPvKw = snapMocToPanel(sel.mocPvKw, panelMocWp(newPanel))
    }
  },
)

// Default panel-card preselection: pick the first active card (lowest sort)
// once the catalog loads, and again whenever the current pick falls out of
// the active list. Never touches sel.panel for battery-only variants — the
// variant watcher above already owns clearing it there.
watch(
  [panelOptions, hasPv],
  ([opcje, pv]) => {
    if (!pv || !opcje.length) return
    if (!sel.panel || !opcje.some((c) => c.name === sel.panel)) {
      sel.panel = opcje[0].name
    }
  },
  { immediate: true },
)

// --- Auto-assembly suggestion from Roczne zużycie ---------------------------
// Sizing heuristics live in pvForm.js (display-only estimate — the server
// remains the source of truth for pricing/BOM once fields are set).
const suggestedKwp = computed(() => suggestedKwpFor(sel.consumption, sel.variant))

// Storage sizing always uses the ×1.0 (PV+Magazyn) power suggestion, never the
// ×1.4 PV-only oversizing — the oversize ratio is meant to push surplus PV
// production to the grid, not to inflate the battery.
const suggestedStorage = computed(() =>
  suggestedStorageKwh(sel.consumption, suggestedKwpFor(sel.consumption, VARIANT_PV_BAT)),
)

// "Ustaw z zużycia" — fills the configuration from the suggestion, respecting
// the currently selected variant. Never runs automatically; only on click.
// Everything stays editable afterwards. Base fields (variant/producent) are
// set first, then we await a tick so the cascade watchers above finish
// resetting downstream fields BEFORE we set the dependent picks — otherwise
// they'd get clobbered.
async function applyFromConsumption() {
  if (sel.variant === VARIANT_PV_BAT) {
    const kwp = suggestedKwp.value
    const storage = suggestedStorage.value
    if (!kwp) return

    sel.producent = 'Sigenergy'
    await nextTick()

    if (!sel.panel) {
      const firstPanel = byKat('Panel PV')[0]
      if (firstPanel) sel.panel = firstPanel.name
    }
    sel.mocPvKw = pickMocForTarget(kwp, panelMocWp(sel.panel))

    // Falownik: Sigenergy TP2, smallest moc_kw >= kwp, else largest TP2.
    const tp2 = byKat('Falownik').filter((c) => c.producent === 'Sigenergy' && c.sigen_typ === 'TP2')
    const fal = pickBySpec(tp2, 'moc_kw', kwp)
    if (fal) sel.falownik = fal.name

    // Bateria: Sigenergy, smallest pojemnosc_kwh >= storage, else largest.
    const bats = byKat('Magazyn energii').filter((c) => c.producent === 'Sigenergy')
    const bat = pickBySpec(bats, 'pojemnosc_kwh', storage)
    if (bat) sel.bateria = bat.name

    // Konstrukcja: prefer "…blacha", else first available.
    const k = pickMounting(byKat('Konstrukcja'))
    if (k) sel.konstrukcja = k.name
    return
  }

  if (sel.variant === VARIANT_PV) {
    const kwp = suggestedKwp.value
    if (!kwp) return

    // producentOptionsFor forces FoxESS for PV-only.
    sel.producent = 'FoxESS'
    await nextTick()

    if (!sel.panel) {
      const firstPanel = byKat('Panel PV')[0]
      if (firstPanel) sel.panel = firstPanel.name
    }
    sel.mocPvKw = pickMocForTarget(kwp, panelMocWp(sel.panel))

    // Falownik: FoxESS, smallest moc_kw >= kwp, else largest. No sigen_typ
    // filter — FoxESS rows carry no such field.
    const inverters = byKat('Falownik').filter((c) => c.producent === 'FoxESS')
    const fal = pickBySpec(inverters, 'moc_kw', kwp)
    if (fal) sel.falownik = fal.name

    // Konstrukcja: prefer "…blacha", else first available.
    const k = pickMounting(byKat('Konstrukcja'))
    if (k) sel.konstrukcja = k.name
    return
  }

  // Battery-only (VARIANT_BAT) has no consumption-based suggestion: the
  // "Roczne zużycie" input that triggered this function is hidden entirely
  // for that variant (owner decision 2026-08-13), so the rep picks the
  // battery directly from the list instead.
}

// --- Flow / result state ----------------------------------------------------
const flow = ref('idle') // idle | done
const generating = ref(false)
const errorMsg = ref('')
const summary = reactive({
  netto: 0, vat: 0, brutto: 0, narzut: 0, vat_rate: 0,
  dotacja: 0, cena_po_dotacji: 0, ulga: 0, cena_po_uldze: 0,
  raty: { brutto: 0, po_dotacji: 0, po_uldze: 0 },
  lines: [],
  is_admin: false,
  breakdown: null,
})
const grupyBreakdown = computed(() => grupujBreakdown(summary.breakdown))

const successSummary = ref('')
const dealHref = ref('#')

// --- Narzut disclosure (open by default so reps see the narzut setting immediately; still manually collapsible) ---
const showNarzut = ref(true)
// Collapsed by default so the admin cost breakdown is not visible during screenshares.
const showAdminBreakdown = ref(false)

// --- Completeness gate (mirrors the server-side validation) -----------------
const isComplete = computed(() => {
  if (!sel.typKlienta || !sel.variant || !sel.producent || !sel.falownik) return false
  if (hasPv.value && (!sel.panel || !sel.mocPvKw || !sel.konstrukcja)) return false
  if (hasBat.value && !sel.bateria) return false
  return true
})

const narzutValid = computed(() => {
  const n = Number(sel.narzut)
  return !isNaN(n) && n >= 0 && n <= 7000
})

const canGenerate = computed(() => isComplete.value && !!c.value.name && narzutValid.value)

function buildCalcPayload() {
  return {
    typ_klienta: sel.typKlienta,
    variant: sel.variant,
    producent: sel.producent,
    falownik: sel.falownik || '',
    bateria: hasBat.value ? sel.bateria || '' : '',
    panel: hasPv.value ? sel.panel || '' : '',
    konstrukcja: hasPv.value ? sel.konstrukcja || '' : '',
    moc_pv_kw: hasPv.value ? Number(sel.mocPvKw) || 0 : 0,
    kabel_m: Number(sel.kabelM) || 0,
    spoldzielnia: sel.spoldzielnia,
    ulga_pct: Number(sel.ulgaPct),
    okres_lat: Number(sel.okresLat),
    wplata_wlasna: Number(sel.wplataWlasna) || 0,
    narzut: Number(sel.narzut) || 0,
  }
}

function clearSummary() {
  summary.netto = 0; summary.vat = 0; summary.brutto = 0; summary.narzut = 0; summary.vat_rate = 0
  summary.dotacja = 0; summary.cena_po_dotacji = 0; summary.ulga = 0; summary.cena_po_uldze = 0
  summary.raty.brutto = 0; summary.raty.po_dotacji = 0; summary.raty.po_uldze = 0
  summary.lines = []
  summary.is_admin = false
  summary.breakdown = null
}

// --- Live pricing (server-side; debounced) ----------------------------------
let calcTimer = null
watch(
  () => [
    sel.typKlienta, sel.variant, sel.producent, sel.falownik, sel.bateria,
    sel.panel, sel.mocPvKw, sel.konstrukcja, sel.kabelM, sel.spoldzielnia, sel.ulgaPct,
    sel.okresLat, sel.wplataWlasna, sel.narzut,
  ],
  () => {
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(runCalc, 350)
  },
)

async function runCalc() {
  if (!isComplete.value) {
    clearSummary()
    return
  }
  try {
    const data = await call('volteo_quote_calc', buildCalcPayload())
    summary.netto = data.netto || 0
    summary.vat = data.vat || 0
    summary.brutto = data.brutto || 0
    summary.narzut = data.narzut || 0
    summary.vat_rate = data.vat_rate || 0
    summary.dotacja = data.dotacja || 0
    summary.cena_po_dotacji = data.cena_po_dotacji || 0
    summary.ulga = data.ulga || 0
    summary.cena_po_uldze = data.cena_po_uldze || 0
    summary.raty.brutto = (data.raty && data.raty.brutto) || 0
    summary.raty.po_dotacji = (data.raty && data.raty.po_dotacji) || 0
    summary.raty.po_uldze = (data.raty && data.raty.po_uldze) || 0
    summary.lines = data.lines || []
    summary.is_admin = !!data.is_admin
    summary.breakdown = data.is_admin ? data.breakdown || null : null
  } catch (err) {
    clearSummary()
    errorMsg.value = extractErrorMessage(err)
  }
}

// --- Generate ----------------------------------------------------------------
async function runGenerate() {
  errorMsg.value = ''
  generating.value = true
  try {
    const result = await call('volteo_quote_generate', {
      ...buildCalcPayload(),
      contact: c.value.name || '',
      first_name: c.value.first_name || '',
      last_name: c.value.last_name || '',
      phone: c.value.mobile_no || '',
      email: c.value.email_id || '',
      install_address: composeAddress(),
      install_city: c.value.custom_miasto || '',
      install_postal_code: c.value.custom_kod_pocztowy || '',
      voivodeship: voivodeshipPrefill.value,
      operator: sel.operator,
      kierunek: sel.kierunek,
      annual_consumption_kwh: sel.consumption || 0,
    })
    successSummary.value =
      'Szansa ' + result.deal + ' została utworzona. Suma brutto: ' + formatPln(result.brutto) + '.'
    dealHref.value = router.resolve({ name: 'Deal', params: { dealId: result.deal } }).href
    flow.value = 'done'
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  } finally {
    generating.value = false
  }
}

function resetFlow() {
  flow.value = 'idle'
  successSummary.value = ''
}

// --- Helpers -----------------------------------------------------------------
function formatQty(q) {
  const n = Number(q) || 0
  return Number.isInteger(n) ? String(n) : String(n)
}
function extractErrorMessage(err) {
  try {
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || 'Wystąpił błąd - spróbuj ponownie'
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || 'Wystąpił błąd - spróbuj ponownie'
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return 'Wystąpił błąd - spróbuj ponownie'
}
</script>

<style scoped>
.kalk-input,
.kalk-select {
  height: 28px;
  width: 100%;
  border-radius: 0.25rem;
  border: 1px solid var(--outline-gray-1);
  background: var(--surface-gray-2);
  padding: 0 8px;
  font-size: 14px;
  color: var(--ink-gray-8);
  outline: none;
  transition: background-color 0.15s, border-color 0.15s;
  cursor: pointer;
}
.kalk-input { cursor: text; }
.kalk-input:hover,
.kalk-select:hover {
  background: var(--surface-gray-3);
}
.kalk-input:focus,
.kalk-select:focus {
  border-color: var(--outline-gray-4);
  background: var(--surface-base);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
/* Bordered cards make visual grouping clearer than thin divider rules; the
   muted numeral chip is a non-interactive step/order indicator. */
.kalk-part-heading { letter-spacing: -0.01em; }
.kalk-part {
  border: 1px solid var(--outline-gray-1);
  border-radius: 0.75rem;
  background: var(--surface-elevation-1);
  padding: 1.25rem 1.25rem 1.375rem;
}
.kalk-part + .kalk-part { margin-top: 1rem; }
.kalk-part-number {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.375rem;
  height: 1.375rem;
  border-radius: 9999px;
  background: var(--surface-gray-2);
  color: var(--ink-gray-4);
  font-size: 0.7rem;
  font-weight: 700;
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: 1fr !important; }
  .kalk-row2 { grid-template-columns: 1fr !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
  .kalk-part { padding: 1rem; }
}
</style>
