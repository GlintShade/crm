<!--
  Volteo Kalkulator — D2D "build a quote" tab in the Contact (Klient) view.

  The rep manually builds an installation from catalog components (wariant +
  magazyn / inwerter / panele + extras), sets a narzut (margin — kwotowy / procentowy)
  and a VAT band (8 / 23 %), sees a live Suma netto / VAT / Suma brutto / Narzut,
  and on "Generuj ofertę" creates a Szansa (Deal) + Volteo Oferta + Zestaw BOM.

  Company component prices are NEVER sent to the browser: the dropdowns come from
  `volteo_quote_components` (names only) and all pricing is computed server-side by
  `volteo_quote_calc` / `volteo_quote_generate`, which return only aggregates.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="voff-wrap">
      <div v-if="errorMsg" class="voff-banner voff-banner-error">
        <span>{{ errorMsg }}</span>
        <button class="voff-banner-close" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <!-- Wariant -->
        <section class="voff-card">
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
        </section>

        <!-- Komponenty -->
        <section class="voff-card">
          <h2>Komponenty (zestaw)</h2>

          <div class="voff-field">
            <label>Typ instalacji</label>
            <select v-model="sel.installType">
              <option value="">-- wybierz --</option>
              <option v-for="c in byKat('Typ instalacji')" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
            </select>
          </div>

          <template v-if="showPV">
            <div class="voff-grid2">
              <div class="voff-field">
                <label>Panel PV</label>
                <select v-model="sel.panel">
                  <option value="">-- wybierz --</option>
                  <option v-for="c in byKat('Panel PV')" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                </select>
              </div>
              <div class="voff-field">
                <label>Liczba modułów</label>
                <input v-model.number="sel.liczbaModulow" type="number" min="0" step="1" />
                <div v-if="suggestedModules" class="voff-hint">
                  Sugerowana ilość: {{ suggestedModules }}
                  <button class="voff-link" @click="sel.liczbaModulow = suggestedModules">Ustaw</button>
                </div>
              </div>
            </div>
          </template>

          <div class="voff-field">
            <label>Inwerter</label>
            <select v-model="sel.inverter">
              <option value="">-- wybierz --</option>
              <option v-for="c in byKat('Inwerter')" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
            </select>
          </div>

          <div v-if="showBattery" class="voff-field">
            <label>Magazyn energii</label>
            <select v-model="sel.battery">
              <option value="">-- wybierz --</option>
              <option v-for="c in byKat('Magazyn energii')" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
            </select>
          </div>

          <!-- Dodatki -->
          <h3 class="voff-subhead">Dodatki</h3>
          <div v-if="showPV" class="voff-grid2">
            <div class="voff-field">
              <label>Optymalizatory</label>
              <select v-model="sel.optymalizator">
                <option value="">-- brak --</option>
                <option v-for="c in byKat('Optymalizator')" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
              </select>
            </div>
            <div class="voff-field">
              <label>Ilość (szt)</label>
              <input v-model.number="sel.optSzt" type="number" min="0" step="1" />
            </div>
          </div>
          <div class="voff-field">
            <label>Dodatkowy kabel do falownika (m)</label>
            <input v-model.number="sel.kabelM" type="number" min="0" step="1" />
          </div>
          <div class="voff-checkboxes">
            <label><input type="checkbox" v-model="sel.podnosnik" /> Podnośnik / zwyżka</label>
            <label><input type="checkbox" v-model="sel.modernizacja" /> Modernizacja rozdzielnicy</label>
            <label><input type="checkbox" v-model="sel.bilansowanie" /> Bilansowanie energii SaveUP</label>
          </div>

          <h3 class="voff-subhead">Dane energetyczne</h3>
          <div class="voff-grid2">
            <div class="voff-field">
              <label>Operator energetyczny</label>
              <select v-model="sel.operator">
                <option value="">-- wybierz --</option>
                <option v-for="c in byKat('Operator')" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
              </select>
            </div>
            <div class="voff-field">
              <label>Kierunek montażu</label>
              <select v-model="sel.kierunek">
                <option value="">-- wybierz --</option>
                <option v-for="c in byKat('Kierunek montażu')" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
              </select>
            </div>
            <div class="voff-field">
              <label>Moc instalacji PV (kWp)</label>
              <input v-model.number="sel.pvPower" type="number" min="0" step="0.1" />
            </div>
            <div class="voff-field">
              <label>Roczne zużycie (kWh)</label>
              <input v-model.number="sel.consumption" type="number" min="0" step="1" />
            </div>
          </div>
        </section>

        <!-- Narzut + VAT -->
        <section class="voff-card">
          <h2>Narzut i VAT</h2>
          <div class="voff-grid2">
            <div class="voff-field">
              <label>Rodzaj narzutu</label>
              <select v-model="sel.narzutTyp">
                <option value="kwotowy">Kwotowy (PLN)</option>
                <option value="procentowy">Procentowy (%)</option>
              </select>
            </div>
            <div class="voff-field">
              <label>Wysokość narzutu {{ sel.narzutTyp === 'procentowy' ? '(%)' : '(PLN)' }}</label>
              <input v-model.number="sel.narzutValue" type="number" min="0" step="1" />
            </div>
            <div class="voff-field">
              <label>Stawka VAT</label>
              <select v-model="sel.vatRate">
                <option value="8">8% (do 300 m²)</option>
                <option value="23">23% (powyżej 300 m²)</option>
              </select>
            </div>
          </div>
        </section>

        <!-- Podsumowanie -->
        <section class="voff-card voff-summary-card">
          <h2>Podsumowanie</h2>
          <div v-if="summary.lines.length" class="voff-bom">
            <div v-for="(ln, i) in summary.lines" :key="i" class="voff-bom-row">
              <span class="voff-bom-typ">{{ ln.typ }}</span>
              <span class="voff-bom-nazwa">{{ ln.nazwa }}</span>
              <span class="voff-bom-ilosc">×{{ formatQty(ln.ilosc) }}</span>
            </div>
          </div>
          <div v-else class="voff-hint">Wybierz komponenty, aby zobaczyć wycenę.</div>

          <div class="voff-summary">
            <div class="voff-summary-row"><span>Suma netto</span><span>{{ plnFmt(summary.netto) }}</span></div>
            <div class="voff-summary-row"><span>Narzut</span><span>{{ plnFmt(summary.narzut) }}</span></div>
            <div class="voff-summary-row"><span>VAT ({{ sel.vatRate }}%)</span><span>{{ plnFmt(summary.vat) }}</span></div>
            <div class="voff-summary-row voff-summary-total"><span>Suma brutto</span><span>{{ plnFmt(summary.brutto) }}</span></div>
          </div>

          <button
            class="voff-btn voff-btn-accent"
            :disabled="!canGenerate || generating"
            @click="runGenerate"
          >
            {{ generating ? 'Generuję ofertę…' : 'Generuj ofertę' }}
          </button>
        </section>
      </template>

      <!-- Sukces -->
      <section v-else class="voff-card">
        <h2>Oferta utworzona</h2>
        <p>{{ successSummary }}</p>
        <a class="voff-btn voff-btn-primary" :href="dealHref" target="_blank" rel="noopener">Otwórz szansę w CRM</a>
        <button class="voff-btn voff-btn-accent" @click="downloadPdf">Pobierz PDF</button>
        <button class="voff-btn voff-btn-ghost" @click="resetFlow">Nowa oferta</button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
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


// --- Selections ------------------------------------------------------------
const sel = reactive({
  variant: 'Fotowoltaika + Magazyn',
  installType: '',
  panel: '',
  liczbaModulow: 0,
  inverter: '',
  battery: '',
  optymalizator: '',
  optSzt: 0,
  kabelM: 0,
  podnosnik: false,
  modernizacja: false,
  bilansowanie: false,
  operator: '',
  kierunek: '',
  pvPower: null,
  consumption: null,
  narzutTyp: 'kwotowy',
  narzutValue: 0,
  vatRate: '8',
})

const showPV = computed(() => sel.variant === 'Fotowoltaika' || sel.variant === 'Fotowoltaika + Magazyn')
const showBattery = computed(() => sel.variant === 'Fotowoltaika + Magazyn' || sel.variant === 'Magazyn energii')

// --- Catalog (names only — no prices ever fetched) --------------------------
const catMap = reactive({})
function byKat(kat) {
  return catMap[kat] || []
}
function firstId(kat) {
  const list = catMap[kat] || []
  return list.length ? list[0].name : ''
}
function findComp(name) {
  for (const k in catMap) {
    const hit = (catMap[k] || []).find((x) => x.name === name)
    if (hit) return hit
  }
  return null
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

// --- Flow / result state ---------------------------------------------------
const flow = ref('idle') // idle | done
const generating = ref(false)
const errorMsg = ref('')
const summary = reactive({ netto: 0, vat: 0, brutto: 0, narzut: 0, lines: [] })

const successSummary = ref('')
const dealHref = ref('#')
const resultPdfUrl = ref(null)
const resultPdfPending = ref(false)
const resultOferta = ref('')

// --- Derived ---------------------------------------------------------------
const suggestedModules = computed(() => {
  const panel = findComp(sel.panel)
  const w = panel && Number(panel.moc_w)
  const kwp = Number(sel.pvPower)
  if (!w || !kwp) return 0
  return Math.ceil((kwp * 1000) / w)
})

const items = computed(() => {
  const out = []
  if (sel.installType) out.push({ component: sel.installType, qty: 1 })
  if (showPV.value && sel.panel && Number(sel.liczbaModulow) > 0)
    out.push({ component: sel.panel, qty: Number(sel.liczbaModulow) })
  if (sel.inverter) out.push({ component: sel.inverter, qty: 1 })
  if (showBattery.value && sel.battery) out.push({ component: sel.battery, qty: 1 })
  if (showPV.value && sel.optymalizator && Number(sel.optSzt) > 0)
    out.push({ component: sel.optymalizator, qty: Number(sel.optSzt) })
  const kabel = firstId('Kabel')
  if (Number(sel.kabelM) > 0 && kabel) out.push({ component: kabel, qty: Number(sel.kabelM) })
  const pod = firstId('Podnośnik')
  if (sel.podnosnik && pod) out.push({ component: pod, qty: 1 })
  const mod = firstId('Modernizacja rozdzielnicy')
  if (sel.modernizacja && mod) out.push({ component: mod, qty: 1 })
  const bil = firstId('Bilansowanie SaveUP')
  if (sel.bilansowanie && bil) out.push({ component: bil, qty: 1 })
  return out
})

const canGenerate = computed(() => !!c.name && items.value.length > 0)

// --- Live pricing (server-side; debounced) ---------------------------------
let calcTimer = null
watch(
  () => [items.value, sel.narzutTyp, sel.narzutValue, sel.vatRate],
  () => {
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(runCalc, 350)
  },
  { deep: true },
)

async function runCalc() {
  if (!items.value.length) {
    summary.netto = 0; summary.vat = 0; summary.brutto = 0; summary.narzut = 0; summary.lines = []
    return
  }
  try {
    const data = await call('volteo_quote_calc', {
      items: JSON.stringify(items.value),
      narzut_typ: sel.narzutTyp,
      narzut_value: sel.narzutValue || 0,
      vat_rate: sel.vatRate,
    })
    summary.netto = data.netto || 0
    summary.vat = data.vat || 0
    summary.brutto = data.brutto || 0
    summary.narzut = data.narzut || 0
    summary.lines = data.lines || []
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  }
}

// --- Generate --------------------------------------------------------------
async function runGenerate() {
  errorMsg.value = ''
  generating.value = true
  try {
    const result = await call('volteo_quote_generate', {
      contact: c.name || '',
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      phone: c.mobile_no || '',
      email: c.email_id || '',
      install_address: composeAddress(),
      install_city: c.custom_miasto || '',
      install_postal_code: c.custom_kod_pocztowy || '',
      voivodeship: voivodeshipPrefill,
      variant: sel.variant,
      operator: sel.operator,
      kierunek: sel.kierunek,
      pv_power_kwp: sel.pvPower || 0,
      annual_consumption_kwh: sel.consumption || 0,
      items: JSON.stringify(items.value),
      narzut_typ: sel.narzutTyp,
      narzut_value: sel.narzutValue || 0,
      vat_rate: sel.vatRate,
    })
    successSummary.value =
      'Szansa ' + result.deal + ' oraz oferta ' + result.oferta +
      ' zostały utworzone. Suma brutto: ' + plnFmt(result.brutto) + '.'
    dealHref.value = '/crm/deals/' + result.deal
    resultPdfUrl.value = result.pdf_url
    resultPdfPending.value = result.pdf_pending
    resultOferta.value = result.oferta
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

function downloadPdf() {
  if (resultPdfUrl.value) {
    window.open(resultPdfUrl.value, '_blank')
  } else if (resultPdfPending.value) {
    window.open(
      '/api/method/frappe.utils.print_format.download_pdf?doctype=Volteo%20Oferta&name=' +
        encodeURIComponent(resultOferta.value) +
        '&format=' +
        encodeURIComponent('Volteo Oferta PDF'),
      '_blank',
    )
  }
}

// --- Helpers ---------------------------------------------------------------
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
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 16px 40px;
}
.voff-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}
.voff-card h2 {
  color: #122566;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 14px 0;
}
.voff-subhead {
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin: 16px 0 10px 0;
}
.voff-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
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
  font-size: 13px;
  color: #374151;
  margin-bottom: 4px;
}
.voff-field input,
.voff-field select {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  width: 100%;
  box-sizing: border-box;
  background: #ffffff;
  color: #1a1a1a;
}
.voff-checkboxes label {
  display: block;
  font-size: 14px;
  color: #374151;
  margin-bottom: 6px;
}
.voff-checkboxes input {
  margin-right: 6px;
}
.voff-variants {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.voff-variant {
  flex: 1 1 auto;
  min-width: 150px;
  padding: 12px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.voff-variant-active {
  border-color: #122566;
  background: #122566;
  color: #ffffff;
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
.voff-link {
  background: none;
  border: none;
  color: #122566;
  font-weight: 600;
  cursor: pointer;
  padding: 0 0 0 6px;
  font-size: 12px;
}
.voff-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}
.voff-summary-card {
  border-color: #122566;
}
.voff-bom {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 14px;
}
.voff-bom-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  border-top: 1px solid #f3f4f6;
}
.voff-bom-row:first-child { border-top: none; }
.voff-bom-typ { color: #6b7280; min-width: 130px; }
.voff-bom-nazwa { color: #1a1a1a; flex: 1; }
.voff-bom-ilosc { color: #374151; font-variant-numeric: tabular-nums; }
.voff-summary {
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
  margin-bottom: 14px;
}
.voff-summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #374151;
  padding: 4px 0;
  font-variant-numeric: tabular-nums;
}
.voff-summary-total {
  font-size: 18px;
  font-weight: 700;
  color: #122566;
  border-top: 1px solid #e5e7eb;
  margin-top: 6px;
  padding-top: 10px;
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
