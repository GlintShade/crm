<!--
  Volteo Kalkulator — D2D "build a quote" tab in the Contact (Klient) view.

  The rep picks a client type, installation variant, producent (cascaded),
  falownik/bateria/konstrukcja + a handful of extras (kabel, spółdzielnia,
  ulga termomodernizacyjna, okres finansowania, wpłata własna, narzut), sees
  a live price-free config summary + Suma netto/VAT/brutto (+ subsidy/rata
  block for indywidualny clients), and on "Generuj ofertę" creates ONLY a
  Szansa (CRM Deal) — the base record carrying the config, the client-facing
  quote (netto/brutto/dotacja/ulga/raty) and the Zestaw BOM. No separate
  Volteo Oferta record and no PDF are created here; sending the offer/PDF is
  a later action from within the Deal.

  ZERO pricing math happens in this file. Company component prices, subsidy
  rules, margins and PMT installments are computed server-side only:
  - `volteo_quote_components` returns component NAMES + non-secret tags
    (kategoria/producent/sigen_typ/moc_kw/pojemnosc_kwh) — never a price.
  - `volteo_quote_calc` / `volteo_quote_generate` take the user's selections
    (ids/enums/numbers the rep chose) and return only price AGGREGATES.
  - The optional `breakdown` (cost/margin decomposition) is only ever present
    in the response for admins (`is_admin: true`); this component never
    computes it, it only conditionally renders what the server already sent.

  Layout: two-pane — the "Konfiguracja" form on the left, a sticky "Wycena"
  panel on the right so the live quote never scrolls out of view. An energy
  card near the top lets the rep type Roczne zużycie and one-click assemble
  a full Sigenergy TP2 PV+Magazyn config from it ("Ustaw z zużycia") — a
  suggestion only, it never applies itself, and every field stays editable
  afterwards.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="voff-wrap">
      <div v-if="errorMsg" class="voff-banner voff-banner-error">
        <span>{{ errorMsg }}</span>
        <button class="voff-banner-close" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <!-- Rodzaj instalacji + Typ klienta -->
        <section class="voff-card">
          <div class="voff-top-row">
            <div>
              <h2>Rodzaj instalacji</h2>
              <div class="voff-variants">
                <button
                  v-for="v in VARIANTS"
                  :key="v"
                  class="voff-variant"
                  :class="{ 'voff-variant-active': sel.variant === v }"
                  @click="sel.variant = v"
                >
                  {{ v }}
                </button>
              </div>
            </div>
            <div>
              <h2>Typ klienta</h2>
              <div class="voff-variants">
                <button
                  v-for="opt in TYP_KLIENTA_OPTIONS"
                  :key="opt.value"
                  class="voff-variant"
                  :class="{ 'voff-variant-active': sel.typKlienta === opt.value }"
                  @click="sel.typKlienta = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Zużycie energii — auto-assembly suggestion -->
        <section class="voff-card voff-energy-card">
          <h2>Zużycie energii</h2>
          <div class="voff-field voff-energy-field">
            <label>Roczne zużycie (kWh)</label>
            <input v-model.number="sel.consumption" type="number" min="0" step="1" />
          </div>
          <div v-if="sel.consumption > 0" class="voff-suggestion">
            <span class="voff-suggestion-text">
              Sugerowana moc: {{ suggestedKwp }} kW ({{ suggestedKwp * 2 }} paneli) · magazyn:
              {{ suggestedStorage }} kWh
            </span>
            <button type="button" class="voff-btn voff-btn-ghost" @click="applyFromConsumption">
              Ustaw z zużycia
            </button>
          </div>
        </section>

        <!-- Konfiguracja (left) + Wycena (sticky right) -->
        <div class="voff-split">
          <section class="voff-card voff-left">
            <h2>Konfiguracja</h2>

            <div class="voff-field">
              <label>Producent</label>
              <div class="voff-variants">
                <button
                  v-for="p in producentOptions"
                  :key="p"
                  class="voff-variant"
                  :class="{ 'voff-variant-active': sel.producent === p }"
                  @click="sel.producent = p"
                >
                  {{ p }}
                </button>
              </div>
            </div>

            <div class="voff-grid2">
              <div class="voff-field">
                <label>Falownik</label>
                <select v-model="sel.falownik">
                  <option value="">-- wybierz --</option>
                  <option v-for="c in falownikOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                </select>
              </div>

              <div v-if="hasBat" class="voff-field">
                <label>Magazyn energii</label>
                <select v-model="sel.bateria">
                  <option value="">-- wybierz --</option>
                  <option v-for="c in bateriaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                </select>
              </div>

              <template v-if="hasPv">
                <div class="voff-field">
                  <label>Moc instalacji PV</label>
                  <select v-model.number="sel.mocPvKw">
                    <option :value="null">-- wybierz --</option>
                    <option v-for="o in mocOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                </div>
                <div class="voff-field">
                  <label>Konstrukcja</label>
                  <select v-model="sel.konstrukcja">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in konstrukcjaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                  </select>
                </div>
              </template>

              <div class="voff-field">
                <label>Dodatkowy kabel (m)</label>
                <input v-model.number="sel.kabelM" type="number" min="0" step="1" />
              </div>
              <div class="voff-field">
                <label>Spółdzielnia energetyczna</label>
                <select v-model="sel.spoldzielnia">
                  <option value="Nie">Nie</option>
                  <option value="Tak">Tak</option>
                </select>
              </div>

              <div class="voff-field">
                <label>Ulga termomodernizacyjna</label>
                <select v-model.number="sel.ulgaPct">
                  <option :value="12">12%</option>
                  <option :value="19">19%</option>
                </select>
              </div>
              <div class="voff-field">
                <label>Okres finansowania (lat)</label>
                <select v-model.number="sel.okresLat">
                  <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
                </select>
              </div>

              <div class="voff-field">
                <label>Wpłata własna (PLN)</label>
                <input v-model.number="sel.wplataWlasna" type="number" min="0" step="1" />
              </div>
              <div class="voff-field">
                <label>Narzut (PLN)</label>
                <input
                  v-model.number="sel.narzut"
                  type="number"
                  min="0"
                  max="7000"
                  step="1"
                  @blur="sel.narzut = Math.min(7000, Math.max(0, Number(sel.narzut) || 0))"
                />
                <div v-if="!narzutValid" class="voff-hint" style="color:#c0392b">Narzut musi być w zakresie 0–7000 zł.</div>
              </div>
            </div>

            <div class="voff-grp">
              <h3 class="voff-subhead">Dane energetyczne (opcjonalne)</h3>
              <div class="voff-grid2">
                <div class="voff-field">
                  <label>Operator energetyczny</label>
                  <select v-model="sel.operator">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in operatorOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
                <div class="voff-field">
                  <label>Kierunek montażu</label>
                  <select v-model="sel.kierunek">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in kierunekOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          <aside class="voff-quote">
            <section class="voff-card voff-quote-card">
              <h2>Wycena</h2>
              <div v-if="summary.lines.length" class="voff-bom">
                <div v-for="(ln, i) in summary.lines" :key="i" class="voff-bom-row">
                  <span class="voff-bom-typ">{{ ln.typ }}</span>
                  <span class="voff-bom-nazwa">{{ ln.nazwa }}</span>
                  <span class="voff-bom-ilosc">×{{ formatQty(ln.ilosc) }}</span>
                </div>
              </div>
              <div v-else class="voff-hint voff-quote-empty">Uzupełnij konfigurację, aby zobaczyć wycenę.</div>

              <template v-if="summary.lines.length">
                <div class="voff-summary">
                  <div class="voff-summary-row"><span>Suma netto</span><span>{{ plnFmt(summary.netto) }}</span></div>
                  <div class="voff-summary-row"><span>VAT ({{ summary.vat_rate }}%)</span><span>{{ plnFmt(summary.vat) }}</span></div>
                  <div class="voff-summary-row voff-summary-total"><span>Suma brutto</span><span>{{ plnFmt(summary.brutto) }}</span></div>

                  <div v-if="sel.typKlienta === 'indywidualny'" class="voff-summary-sub">
                    <div class="voff-summary-row"><span>Dotacja Mój Prąd</span><span>− {{ plnFmt(summary.dotacja) }}</span></div>
                    <div class="voff-summary-row"><span>Cena po dotacji</span><span>{{ plnFmt(summary.cena_po_dotacji) }}</span></div>
                    <div class="voff-summary-row"><span>Ulga termo. ({{ sel.ulgaPct }}%)</span><span>− {{ plnFmt(summary.ulga) }}</span></div>
                    <div class="voff-summary-row voff-summary-total"><span>Cena po uldze</span><span>{{ plnFmt(summary.cena_po_uldze) }}</span></div>
                    <div class="voff-summary-row">
                      <span>Rata ({{ sel.okresLat }} lat)</span>
                      <span>{{ plnFmt(summary.raty.brutto) }} / {{ plnFmt(summary.raty.po_dotacji) }} / {{ plnFmt(summary.raty.po_uldze) }} zł/mies.</span>
                    </div>
                  </div>
                </div>
              </template>

              <button
                class="voff-btn voff-btn-accent voff-gen"
                :disabled="!canGenerate || generating"
                @click="runGenerate"
              >
                {{ generating ? 'Generuję ofertę…' : 'Generuj ofertę' }}
              </button>

              <div v-if="summary.is_admin && summary.breakdown" class="voff-admin-panel">
                <h3 class="voff-subhead voff-admin-title">Rozbicie kosztów (tylko administrator)</h3>
                <div class="voff-summary-row"><span>Falownik</span><span>{{ plnFmt(summary.breakdown.k_falownik) }}</span></div>
                <div class="voff-summary-row"><span>Bateria</span><span>{{ plnFmt(summary.breakdown.k_bateria) }}</span></div>
                <div class="voff-summary-row"><span>Panele</span><span>{{ plnFmt(summary.breakdown.k_panele) }}</span></div>
                <div class="voff-summary-row"><span>Konstrukcja</span><span>{{ plnFmt(summary.breakdown.k_konstrukcja) }}</span></div>
                <div class="voff-summary-row"><span>Montaż PV</span><span>{{ plnFmt(summary.breakdown.k_montaz_pv) }}</span></div>
                <div class="voff-summary-row"><span>Montaż magazynu</span><span>{{ plnFmt(summary.breakdown.k_montaz_mag) }}</span></div>
                <div class="voff-summary-row"><span>Akcesoria</span><span>{{ plnFmt(summary.breakdown.k_akcesoria) }}</span></div>
                <div class="voff-summary-row"><span>Kabel</span><span>{{ plnFmt(summary.breakdown.k_kabel) }}</span></div>
                <div class="voff-summary-row"><span>Spółdzielnia</span><span>{{ plnFmt(summary.breakdown.k_spoldzielnia) }}</span></div>
                <div class="voff-summary-row"><span>Sterownik</span><span>{{ plnFmt(summary.breakdown.k_sterownik) }}</span></div>
                <div class="voff-summary-row voff-summary-total"><span>Koszt bazowy (net_base)</span><span>{{ plnFmt(summary.breakdown.net_base) }}</span></div>
                <div class="voff-summary-row"><span>Marża ProEnergy</span><span>{{ plnFmt(summary.breakdown.marza_proenergy) }}</span></div>
                <div class="voff-summary-row"><span>Marża SPS</span><span>{{ plnFmt(summary.breakdown.marza_sps) }}</span></div>
                <div class="voff-summary-row"><span>Bonus liderki</span><span>{{ plnFmt(summary.breakdown.bonus_liderki) }}</span></div>
                <div class="voff-summary-row"><span>Kilometrówka</span><span>{{ plnFmt(summary.breakdown.kilometrowka) }}</span></div>
              </div>
            </section>
          </aside>
        </div>
      </template>

      <!-- Sukces -->
      <section v-else class="voff-card">
        <h2>Szansa utworzona</h2>
        <p>{{ successSummary }}</p>
        <a class="voff-btn voff-btn-primary" :href="dealHref" target="_blank" rel="noopener">Otwórz szansę w CRM</a>
        <button class="voff-btn voff-btn-ghost" @click="resetFlow">Nowa oferta</button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { call } from 'frappe-ui'

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
const c = props.contact || {}
function composeAddress() {
  const parts = [c.custom_ulica, c.custom_nr_domu].filter(Boolean).join(' ').trim()
  return c.custom_nr_mieszkania ? parts + '/' + c.custom_nr_mieszkania : parts
}
const voivodeshipPrefill = (() => {
  const w = (c.custom_wojewodztwo || '').toLowerCase().trim()
  return VOIVODESHIPS.indexOf(w) !== -1 ? w : ''
})()

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

const canGenerate = computed(() => isComplete.value && !!c.name && narzutValid.value)

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
      contact: c.name || '',
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      phone: c.mobile_no || '',
      email: c.email_id || '',
      install_address: composeAddress(),
      install_city: c.custom_miasto || '',
      install_postal_code: c.custom_kod_pocztowy || '',
      voivodeship: voivodeshipPrefill,
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
.voff-wrap {
  max-width: 1180px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 16px 40px;
}
.voff-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(18, 37, 102, 0.04);
}
.voff-card h2 {
  color: #122566;
  font-size: 16px;
  font-weight: 650;
  margin: 0 0 14px 0;
}
.voff-subhead {
  color: #374151;
  font-size: 12.5px;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 12px 0;
}

/* Rodzaj instalacji + Typ klienta, side by side */
.voff-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}

/* Segmented button rows (Rodzaj instalacji / Typ klienta / Producent) —
   uniform size everywhere they appear. */
.voff-variants {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.voff-variant {
  flex: 0 0 auto;
  min-width: 140px;
  padding: 11px 16px;
  border: 1px solid #d8dce3;
  border-radius: 9px;
  background: #ffffff;
  color: #3f4757;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.voff-variant-active {
  border-color: #122566;
  background: #122566;
  color: #ffffff;
}

/* Zużycie energii card */
.voff-energy-field {
  max-width: 320px;
}
.voff-energy-field input {
  font-size: 17px;
  font-weight: 650;
  padding: 12px 14px;
}
.voff-suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 6px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
}
.voff-suggestion-text {
  font-size: 13px;
  color: #374151;
}

/* Two-pane split: Konfiguracja (left) / sticky Wycena (right) */
.voff-split {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 1fr);
  gap: 16px;
  align-items: start;
}
@media (max-width: 880px) {
  .voff-split { grid-template-columns: 1fr; }
  .voff-top-row { grid-template-columns: 1fr; }
  .voff-quote { position: static; }
}

.voff-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 18px;
}
@media (max-width: 560px) {
  .voff-grid2 { grid-template-columns: 1fr; }
}
.voff-field {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
}
.voff-field label {
  font-size: 12.5px;
  color: #3f4757;
  margin-bottom: 5px;
}
.voff-field input,
.voff-field select {
  padding: 10px 12px;
  border: 1px solid #d8dce3;
  border-radius: 9px;
  font-size: 14px;
  width: 100%;
  box-sizing: border-box;
  background: #ffffff;
  color: #1a2233;
}
.voff-grp {
  border-top: 1px solid #e5e7eb;
  margin-top: 6px;
  padding-top: 14px;
}

.voff-btn {
  display: inline-block;
  padding: 12px 18px;
  border-radius: 8px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin: 4px 6px 4px 0;
  text-decoration: none;
  text-align: center;
}
.voff-btn-primary { background: #122566; color: #ffffff; }
.voff-btn-accent { background: #c0ee2e; color: #122566; }
.voff-btn-ghost { background: #f3f4f6; color: #374151; }
.voff-btn-disabled,
.voff-btn:disabled {
  background: #e5e7eb;
  color: #9ca3af;
  cursor: not-allowed;
}
.voff-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

/* Sticky Wycena panel — warm quote totals per the approved mockup */
.voff-quote {
  position: sticky;
  top: 16px;
}
.voff-quote-card {
  padding: 0;
  overflow: hidden;
}
.voff-quote-card h2 {
  padding: 16px 18px 0;
}
.voff-quote-empty {
  padding: 0 18px 18px;
}
.voff-bom {
  padding: 6px 18px 12px;
}
.voff-bom-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  border-top: 1px solid #f0f1f4;
}
.voff-bom-row:first-child { border-top: none; }
.voff-bom-typ { color: #7a8394; min-width: 118px; }
.voff-bom-nazwa { color: #1a2233; flex: 1; }
.voff-bom-ilosc { color: #3f4757; font-variant-numeric: tabular-nums; }

.voff-summary {
  background: #fbf5e6;
  border-top: 1px solid #eadfc2;
  padding: 14px 18px;
}
.voff-summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #3f4757;
  padding: 4px 0;
  font-variant-numeric: tabular-nums;
}
.voff-summary-total {
  font-size: 18px;
  font-weight: 700;
  color: #122566;
  border-top: 1px solid #eadfc2;
  margin-top: 6px;
  padding-top: 10px;
}
.voff-summary-sub {
  border-top: 1px dashed #eadfc2;
  margin-top: 10px;
  padding-top: 10px;
}

.voff-gen {
  display: block;
  width: calc(100% - 36px);
  margin: 4px 18px 18px;
  padding: 13px;
}
.voff-gen:hover:not(:disabled) { background: #a9d626; }

.voff-admin-panel {
  border: 1px dashed #b45309;
  background: #fffbeb;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 0 18px 18px;
}
.voff-admin-title {
  color: #92400e;
  margin-top: 0;
}

.voff-banner {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.voff-banner-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
.voff-banner-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-weight: bold;
  font-size: 16px;
  line-height: 1;
}
</style>
