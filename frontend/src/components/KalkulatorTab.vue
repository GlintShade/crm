<!--
  Volteo Kalkulator — native-styled quote builder tab in the Klient view.
  Styled to match the CRM's frappe-ui design system exactly.
  ZERO pricing math in this file — all computed server-side.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div v-if="errorMsg" class="mb-2.5 flex items-center justify-between rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
        <span>{{ errorMsg }}</span>
        <button class="ml-2 text-base font-bold leading-none" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <div class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr)">

          <div>
            <div class="pb-3">
              <div>
                <div class="mb-1 text-sm font-medium text-ink-gray-5">Rodzaj instalacji</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="v in VARIANTS" :key="v"
                    class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                    :class="sel.variant === v
                      ? 'border-gray-900 bg-gray-900 text-white'
                      : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                    @click="sel.variant = v"
                  >{{ v }}</button>
                </div>
              </div>

              <div class="mt-2.5 grid grid-cols-2 gap-x-6 gap-y-2.5 kalk-row2">
                <div>
                  <div class="mb-1 text-sm font-medium text-ink-gray-5">Typ klienta</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="opt in TYP_KLIENTA_OPTIONS" :key="opt.value"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="sel.typKlienta === opt.value
                        ? 'border-gray-900 bg-gray-900 text-white'
                        : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                      @click="sel.typKlienta = opt.value"
                    >{{ opt.label }}</button>
                  </div>
                </div>

                <div class="max-w-[240px]">
                  <div class="mb-1 text-sm font-medium text-ink-gray-5">Roczne zużycie (kWh)</div>
                  <input
                    v-model.number="sel.consumption" type="number" min="0" step="1"
                    class="h-7 w-full rounded border border-gray-200 bg-gray-100 px-2 text-base text-gray-800 outline-none transition-colors hover:bg-gray-200 focus:border-gray-400 focus:bg-white focus:shadow-sm"
                  />
                  <div v-if="sel.consumption > 0" class="mt-1 text-xs leading-relaxed text-gray-500">
                    Sug. moc: <span class="font-medium text-gray-700">{{ suggestedKwp }} kW</span>
                    · magazyn: <span class="font-medium text-gray-700">{{ suggestedStorage }} kWh</span>
                    <button type="button" class="ml-1 font-medium text-blue-600 hover:underline" @click="applyFromConsumption">Ustaw</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="h-px bg-gray-200"></div>

            <div class="mt-3">
              <div class="mb-2 text-base font-semibold text-ink-gray-9">Konfiguracja</div>

              <div class="mb-2">
                <div class="mb-1 text-sm text-ink-gray-5">Producent</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="p in producentOptions" :key="p"
                    class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                    :class="sel.producent === p
                      ? 'border-gray-900 bg-gray-900 text-white'
                      : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
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
                    <div class="mb-0.5 text-sm text-ink-gray-5">Moc instalacji PV</div>
                    <select v-model.number="sel.mocPvKw" class="kalk-select">
                      <option :value="null">-- wybierz --</option>
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

              <div class="my-2.5 h-px bg-gray-200"></div>

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
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Kierunek montażu</div>
                  <select v-model="sel.kierunek" class="kalk-select">
                    <option value="">—</option>
                    <option v-for="c in kierunekOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
              </div>

              <div class="my-2.5 h-px bg-gray-200"></div>

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
                  <input v-model.number="sel.wplataWlasna" type="number" min="0" step="1" class="kalk-input" />
                </div>
              </div>
            </div>
          </div>

          <div class="kalk-output border-l border-gray-200 pl-5">
            <div class="sticky top-3">
              <div class="mb-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-sm font-medium text-ink-gray-7 transition-colors hover:bg-gray-100"
                  @click="showNarzut = !showNarzut"
                >
                  <span>{{ showNarzut ? 'Ukryj ustawienia niestandardowe' : 'Pokaż ustawienia niestandardowe' }}</span>
                  <FeatherIcon :name="showNarzut ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
                </button>
                <div v-if="showNarzut" class="mt-1.5">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Wysokość narzutu</div>
                  <input
                    v-model.number="sel.narzut" type="number" min="0" max="7000" step="1"
                    class="kalk-input"
                    @blur="sel.narzut = Math.min(7000, Math.max(0, Number(sel.narzut) || 0))"
                  />
                  <div v-if="!narzutValid" class="mt-0.5 text-xs text-red-600">Narzut musi być w zakresie 0–7000 zł.</div>
                </div>
              </div>

              <div class="mb-2 text-base font-semibold text-ink-gray-9">Wycena</div>

              <div v-if="summary.lines.length" class="mb-2">
                <div
                  v-for="(ln, i) in summary.lines" :key="i"
                  class="flex items-center gap-2 border-t border-gray-100 py-1.5 text-sm first:border-t-0"
                >
                  <span class="min-w-[88px] text-ink-gray-5">{{ ln.typ }}</span>
                  <span class="flex-1 text-ink-gray-8">{{ ln.nazwa }}</span>
                  <span class="tabular-nums text-ink-gray-7">×{{ formatQty(ln.ilosc) }}</span>
                </div>
              </div>
              <div v-else class="mb-2 text-sm text-ink-gray-5">Uzupełnij konfigurację, aby zobaczyć wycenę.</div>

              <template v-if="summary.lines.length">
                <div class="rounded-lg border border-gray-200 bg-gray-50 p-2.5">
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>Suma netto</span><span>{{ plnFmt(summary.netto) }}</span>
                  </div>
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>VAT ({{ summary.vat_rate }}%)</span><span>{{ plnFmt(summary.vat) }}</span>
                  </div>
                  <div class="mt-1 flex justify-between border-t border-gray-200 pt-1.5 text-base font-semibold tabular-nums text-ink-gray-9">
                    <span>Suma brutto</span><span>{{ plnFmt(summary.brutto) }}</span>
                  </div>

                  <template v-if="sel.typKlienta === 'indywidualny'">
                    <div class="mt-1.5 border-t border-dashed border-gray-300 pt-1.5">
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Dotacja Mój Prąd</span><span>− {{ plnFmt(summary.dotacja) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Cena po dotacji</span><span>{{ plnFmt(summary.cena_po_dotacji) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>Ulga termo. ({{ sel.ulgaPct }}%)</span><span>− {{ plnFmt(summary.ulga) }}</span>
                      </div>
                      <div class="mt-1 flex justify-between border-t border-gray-200 pt-1.5 text-base font-semibold tabular-nums text-ink-gray-9">
                        <span>Cena po uldze</span><span>{{ plnFmt(summary.cena_po_uldze) }}</span>
                      </div>
                      <div class="mt-0.5 flex justify-between py-0.5 text-xs tabular-nums text-ink-gray-5">
                        <span>Rata ({{ sel.okresLat }} lat)</span>
                        <span>{{ plnFmt(summary.raty.brutto) }} / {{ plnFmt(summary.raty.po_dotacji) }} / {{ plnFmt(summary.raty.po_uldze) }} /mies.</span>
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

              <div v-if="!c.name" class="mt-1 text-center text-xs text-red-600">
                Wybierz klienta, aby wygenerować ofertę.
              </div>

              <div v-if="summary.is_admin && summary.breakdown" class="mt-2.5 rounded-lg border border-dashed border-amber-300 bg-amber-50 p-2.5">
                <div class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-amber-700">Rozbicie kosztów (administrator)</div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Falownik</span><span>{{ plnFmt(summary.breakdown.k_falownik) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Bateria</span><span>{{ plnFmt(summary.breakdown.k_bateria) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Panele</span><span>{{ plnFmt(summary.breakdown.k_panele) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Konstrukcja</span><span>{{ plnFmt(summary.breakdown.k_konstrukcja) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Montaż PV</span><span>{{ plnFmt(summary.breakdown.k_montaz_pv) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Montaż magazynu</span><span>{{ plnFmt(summary.breakdown.k_montaz_mag) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Akcesoria</span><span>{{ plnFmt(summary.breakdown.k_akcesoria) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Kabel</span><span>{{ plnFmt(summary.breakdown.k_kabel) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Spółdzielnia</span><span>{{ plnFmt(summary.breakdown.k_spoldzielnia) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Sterownik</span><span>{{ plnFmt(summary.breakdown.k_sterownik) }}</span></div>
                <div class="mt-1 flex justify-between border-t border-amber-200 pt-1 text-sm font-semibold tabular-nums text-ink-gray-9"><span>Koszt bazowy (net_base)</span><span>{{ plnFmt(summary.breakdown.net_base) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Marża ProEnergy</span><span>{{ plnFmt(summary.breakdown.marza_proenergy) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Marża SPS</span><span>{{ plnFmt(summary.breakdown.marza_sps) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Bonus liderki</span><span>{{ plnFmt(summary.breakdown.bonus_liderki) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>Kilometrówka</span><span>{{ plnFmt(summary.breakdown.kilometrowka) }}</span></div>
              </div>
            </div>
          </div>

        </div>
      </template>

      <div v-else class="py-4">
        <div class="mb-2 text-base font-semibold text-ink-gray-9">Szansa utworzona</div>
        <p class="mb-3 text-sm text-ink-gray-7">{{ successSummary }}</p>
        <div class="flex gap-2">
          <a class="inline-flex items-center rounded bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800" :href="dealHref" target="_blank" rel="noopener">Otwórz szansę w CRM</a>
          <Button variant="ghost" @click="resetFlow">Nowa oferta</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { call, Button, FeatherIcon } from 'frappe-ui'

const props = defineProps({
  contact: { type: Object, default: () => ({}) },
})

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie', 'łódzkie',
  'małopolskie', 'mazowieckie', 'opolskie', 'podkarpackie', 'podlaskie',
  'pomorskie', 'śląskie', 'świętokrzyskie', 'warmińsko-mazurskie',
  'wielkopolskie', 'zachodniopomorskie',
]
const VARIANTS = ['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii']
const TYP_KLIENTA_OPTIONS = [
  { value: 'indywidualny', label: 'Indywidualny' },
  { value: 'biznesowy', label: 'Biznesowy' },
]

// Moc PV dropdown: 3.0–20.0 kW in 0.5 steps, label shows panel count (kW * 2).
// This is a display-label helper only — no cost/price is derived here.
const mocOptions = (() => {
  const out = []
  for (let tenths = 30; tenths <= 200; tenths += 5) {
    const kw = tenths / 10
    out.push({ value: kw, label: `${kw} kW (${Math.round(kw * 2)} paneli)` })
  }
  return out
})()

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

const hasPv = computed(() => sel.variant === 'Fotowoltaika' || sel.variant === 'Fotowoltaika + Magazyn')
const hasBat = computed(() => sel.variant === 'Fotowoltaika + Magazyn' || sel.variant === 'Magazyn energii')

// Cascade: PV-only forces FoxESS; PV+Magazyn / Magazyn only offer Sigenergy/Deye.
const producentOptions = computed(() => (sel.variant === 'Fotowoltaika' ? ['FoxESS'] : ['Sigenergy', 'Deye']))

watch(
  () => sel.variant,
  () => {
    if (!producentOptions.value.includes(sel.producent)) sel.producent = producentOptions.value[0]
    if (!hasPv.value) { sel.mocPvKw = null; sel.konstrukcja = '' }
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

// --- Auto-assembly suggestion from Roczne zużycie ---------------------------
// Mirrors the domain engine's sizing heuristic (display-only estimate — the
// server remains the source of truth for pricing/BOM once fields are set).
function roundHalf(x) {
  return Math.round(x * 2) / 2
}
function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

const suggestedKwp = computed(() => {
  const cons = Number(sel.consumption) || 0
  if (cons <= 0) return 0
  return clamp(roundHalf(cons / 1000), 3, 20) // ~1000 kWh/yr per kWp
})

const suggestedStorage = computed(() => {
  const cons = Number(sel.consumption) || 0
  const kwp = suggestedKwp.value
  if (cons <= 0 || kwp <= 0) return 0
  const daily = cons / 365
  const surplus = Math.max(0, kwp * 4.5 - daily * 0.4) // 4.5 sun-hours, 40% day self-use
  const nightNeed = daily * 0.6
  return clamp(Math.ceil(Math.min(surplus, nightNeed) * 1.2), 10, 60) // 1.2 headroom
})

// "Ustaw z zużycia" — fills a full Sigenergy TP2 PV+Magazyn setup from the
// suggestion. Never runs automatically; only on click. Everything stays
// editable afterwards. Base fields (variant/producent) are set first, then
// we await a tick so the cascade watchers above finish resetting downstream
// fields BEFORE we set the dependent picks — otherwise they'd get clobbered.
async function applyFromConsumption() {
  const kwp = suggestedKwp.value
  const storage = suggestedStorage.value
  if (!kwp) return

  sel.variant = 'Fotowoltaika + Magazyn'
  sel.producent = 'Sigenergy'
  await nextTick()

  sel.mocPvKw = kwp

  // Falownik: Sigenergy TP2, smallest moc_kw >= kwp, else largest TP2.
  const tp2 = byKat('Falownik')
    .filter((c) => c.producent === 'Sigenergy' && c.sigen_typ === 'TP2')
    .sort((a, b) => Number(a.moc_kw) - Number(b.moc_kw))
  const fal = tp2.find((c) => Number(c.moc_kw) >= kwp) || tp2[tp2.length - 1]
  if (fal) sel.falownik = fal.name

  // Bateria: Sigenergy, smallest pojemnosc_kwh >= storage, else largest.
  const bats = byKat('Magazyn energii')
    .filter((c) => c.producent === 'Sigenergy')
    .sort((a, b) => Number(a.pojemnosc_kwh) - Number(b.pojemnosc_kwh))
  const bat = bats.find((c) => Number(c.pojemnosc_kwh) >= storage) || bats[bats.length - 1]
  if (bat) sel.bateria = bat.name

  // Konstrukcja: prefer "…blacha", else first available.
  const ks = byKat('Konstrukcja')
  const k = ks.find((c) => (c.nazwa || '').toLowerCase().includes('blacha')) || ks[0]
  if (k) sel.konstrukcja = k.name
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

const successSummary = ref('')
const dealHref = ref('#')

// --- Narzut disclosure (collapsed by default; hidden while client is watching) ---
const showNarzut = ref(false)

// --- Completeness gate (mirrors the server-side validation) -----------------
const isComplete = computed(() => {
  if (!sel.typKlienta || !sel.variant || !sel.producent || !sel.falownik) return false
  if (hasPv.value && (!sel.mocPvKw || !sel.konstrukcja)) return false
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
    sel.mocPvKw, sel.konstrukcja, sel.kabelM, sel.spoldzielnia, sel.ulgaPct,
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
      'Szansa ' + result.deal + ' została utworzona. Suma brutto: ' + plnFmt(result.brutto) + '.'
    dealHref.value = '/crm/deals/' + result.deal
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
function plnFmt(val) {
  const n = Math.round(Number(val) || 0)
  const s = n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return s + ' zł'
}
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
  border: 1px solid #e5e5e5;
  background: #f5f5f5;
  padding: 0 8px;
  font-size: 14px;
  color: #383838;
  outline: none;
  transition: background-color 0.15s, border-color 0.15s;
  cursor: pointer;
}
.kalk-input { cursor: text; }
.kalk-input:hover,
.kalk-select:hover {
  background: #ededed;
}
.kalk-input:focus,
.kalk-select:focus {
  border-color: #a3a3a3;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: 1fr !important; }
  .kalk-row2 { grid-template-columns: 1fr !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
}
</style>
