<!--
  Volteo Kalkulator — native tab in the Contact (Klient) view.

  A faithful port of the /kalkulator Web Page into a Vue component: same flow
  (Dane klienta -> Parametry -> Przelicz -> wybór produktu + prowizja -> Generuj
  ofertę -> sukces) and the SAME backend contracts (volteo_calculate /
  volteo_generate_quote server scripts), but prefilled from the current contact
  and rendered inline in the CRM SPA instead of a standalone page.

  The commission is INTERNAL (hidden on the client PDF); the server re-quotes on
  generate and never trusts a client-supplied price.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="voff-wrap">
      <div v-if="errorMsg" class="voff-banner voff-banner-error">
        <span>{{ errorMsg }}</span>
        <button class="voff-banner-close" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <!-- Dane klienta -->
        <section class="voff-card">
          <h2>Dane klienta</h2>
          <div class="voff-field">
            <label>Imię*</label>
            <input v-model="form.firstName" type="text" />
          </div>
          <div class="voff-field">
            <label>Nazwisko</label>
            <input v-model="form.lastName" type="text" />
          </div>
          <div class="voff-field">
            <label>Telefon*</label>
            <input v-model="form.phone" type="tel" />
          </div>
          <div class="voff-field">
            <label>E-mail</label>
            <input v-model="form.email" type="email" />
          </div>
          <div class="voff-field">
            <label>Adres instalacji</label>
            <input v-model="form.address" type="text" />
          </div>
          <div class="voff-field">
            <label>Miejscowość</label>
            <input v-model="form.city" type="text" />
          </div>
          <div class="voff-field">
            <label>Kod pocztowy</label>
            <input v-model="form.postal" type="text" />
          </div>
          <div class="voff-field">
            <label>Województwo</label>
            <select v-model="form.voivodeship">
              <option value="">-- wybierz --</option>
              <option v-for="w in VOIVODESHIPS" :key="w" :value="w">{{ w }}</option>
            </select>
          </div>
        </section>

        <!-- Parametry instalacji -->
        <section class="voff-card">
          <h2>Parametry instalacji</h2>
          <div class="voff-field">
            <label>Typ instalacji</label>
            <select v-model="form.installationType">
              <option v-for="o in INSTALLATION_TYPES" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
          <div class="voff-field">
            <label>Moc instalacji PV (kWp)</label>
            <input v-model="form.pvPower" type="number" step="0.1" />
          </div>
          <div class="voff-field">
            <label>Roczne zużycie energii (kWh)</label>
            <input v-model="form.consumption" type="number" />
          </div>
          <div class="voff-field">
            <label>Taryfa</label>
            <select v-model="form.tariff">
              <option v-for="t in TARIFFS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div class="voff-field">
            <label>Dodatkowe potrzeby</label>
            <div class="voff-checkboxes">
              <label v-for="n in ADDITIONAL_NEEDS" :key="n.value">
                <input type="checkbox" :value="n.value" v-model="needsSelected" /> {{ n.label }}
              </label>
            </div>
          </div>
          <button
            class="voff-btn voff-btn-primary"
            :disabled="calculating"
            @click="runCalculate"
          >
            {{ calculating ? 'Przeliczam…' : 'Przelicz' }}
          </button>
        </section>

        <!-- Wybór produktu -->
        <section v-if="calcData" class="voff-card">
          <h2>Wybierz produkt</h2>
          <div>
            <div
              v-for="(p, idx) in products"
              :key="p.id"
              class="voff-product-card"
              :class="{ 'voff-product-selected': p.id === selectedProductId }"
              @click="selectProduct(p.id)"
            >
              <div class="voff-product-head">
                <span v-if="idx === 0" class="voff-badge voff-badge-reco">Rekomendowane</span>
                <strong>{{ p.brand }} {{ p.model }}</strong>
              </div>
              <div class="voff-product-row">Pojemność: {{ p.capacityKwh }} kWh</div>
              <div class="voff-product-row">Cena brutto: {{ plnFmt(p.pricing && p.pricing.grossPln) }}</div>
              <div class="voff-product-row">Dotacja: {{ plnFmt(p.pricing && p.pricing.subsidyPln) }}</div>
              <div class="voff-product-row">Cena po dotacji: {{ plnFmt(p.pricing && p.pricing.netPln) }}</div>
              <div class="voff-product-row">Rata/mies.: {{ plnFmt(p.pricing && p.pricing.monthlyPln) }}</div>
              <ul class="voff-product-reasons">
                <li v-for="(r, i) in (p.reasons || [])" :key="i">{{ r }}</li>
              </ul>
            </div>
          </div>

          <div class="voff-field">
            <label>
              Prowizja (wewnętrzna)
              <span class="voff-badge">Niewidoczna dla klienta</span>
            </label>
            <input v-model.number="commissionPln" type="number" min="0" step="1" @input="recalcDebounced" />
            <div class="voff-hint">{{ commissionHint }}</div>
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
        <button class="voff-btn voff-btn-disabled" disabled>Wyślij e-mailem (wkrótce)</button>
        <button class="voff-btn voff-btn-disabled" disabled>Wyślij przez Autenti (wkrótce)</button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
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
const INSTALLATION_TYPES = [
  { value: 'new', label: 'Nowa instalacja' },
  { value: 'add_to_pv', label: 'Rozbudowa istniejącej PV' },
  { value: 'standalone', label: 'Instalacja wolnostojąca' },
]
const TARIFFS = [
  { value: 'G11', label: 'G11' },
  { value: 'G12', label: 'G12' },
  { value: 'G12W', label: 'G12W' },
  { value: 'dynamic', label: 'Dynamiczna' },
]
const ADDITIONAL_NEEDS = [
  { value: 'ev_charger', label: 'Ładowarka EV' },
  { value: 'backup', label: 'Zasilanie awaryjne' },
  { value: 'heat_pump', label: 'Pompa ciepła' },
]

// --- Prefill from the current contact --------------------------------------
const c = props.contact || {}
function composeAddress() {
  const parts = [c.custom_ulica, c.custom_nr_domu].filter(Boolean).join(' ').trim()
  return c.custom_nr_mieszkania ? parts + '/' + c.custom_nr_mieszkania : parts
}
const voivodeshipPrefill = (() => {
  const w = (c.custom_wojewodztwo || '').toLowerCase().trim()
  return VOIVODESHIPS.indexOf(w) !== -1 ? w : ''
})()

const form = reactive({
  firstName: c.first_name || '',
  lastName: c.last_name || '',
  phone: c.mobile_no || '',
  email: c.email_id || '',
  address: composeAddress(),
  city: c.custom_miasto || '',
  postal: c.custom_kod_pocztowy || '',
  voivodeship: voivodeshipPrefill,
  installationType: 'new',
  pvPower: '',
  consumption: '',
  tariff: 'G11',
})
const needsSelected = ref([])

// --- Flow state ------------------------------------------------------------
const flow = ref('idle') // idle | results | done
const calcData = ref(null)
const selectedProductId = ref(null)
const commissionPln = ref(0)
const calculating = ref(false)
const generating = ref(false)
const errorMsg = ref('')
let commissionTimer = null

const successSummary = ref('')
const dealHref = ref('#')
const resultPdfUrl = ref(null)
const resultPdfPending = ref(false)
const resultOferta = ref('')

// --- Derived ---------------------------------------------------------------
const products = computed(() => (calcData.value && calcData.value.products) || [])
const commissionHint = computed(() => {
  const b = calcData.value && calcData.value.commissionBounds
  if (!b) return ''
  return 'od ' + plnFmt(b.min) + ' do ' + plnFmt(b.max)
})
const canGenerate = computed(
  () => !!form.firstName.trim() && !!form.phone.trim() && !!selectedProductId.value,
)

// --- Helpers ---------------------------------------------------------------
function plnFmt(val) {
  const n = Math.round(Number(val) || 0)
  const s = n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return s + ' zł'
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

function buildCalcArgs() {
  return {
    installationType: form.installationType,
    tariffType: form.tariff,
    selectedProductId: selectedProductId.value || '',
    pvPowerKwp: form.pvPower,
    annualConsumptionKwh: form.consumption,
    commissionPln: commissionPln.value || 0,
    additionalNeeds: JSON.stringify(needsSelected.value),
  }
}

async function runCalculate() {
  errorMsg.value = ''
  calculating.value = true
  try {
    const data = await call('volteo_calculate', buildCalcArgs())
    calcData.value = data
    flow.value = 'results'
    if (!selectedProductId.value && data && data.products && data.products.length) {
      selectedProductId.value = data.products[0].id
    }
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  } finally {
    calculating.value = false
  }
}

function selectProduct(id) {
  selectedProductId.value = id
  recalcDebounced()
}

function recalcDebounced() {
  if (commissionTimer) clearTimeout(commissionTimer)
  commissionTimer = setTimeout(() => {
    if (flow.value === 'results') runCalculate()
  }, 400)
}

async function runGenerate() {
  errorMsg.value = ''
  generating.value = true
  try {
    const result = await call('volteo_generate_quote', {
      first_name: form.firstName.trim(),
      last_name: form.lastName.trim(),
      phone: form.phone.trim(),
      email: form.email.trim(),
      install_address: form.address.trim(),
      install_city: form.city.trim(),
      install_postal_code: form.postal.trim(),
      voivodeship: form.voivodeship,
      selected_product_id: selectedProductId.value,
      commission_pln: commissionPln.value || 0,
      installationType: form.installationType,
      tariffType: form.tariff,
      pvPowerKwp: form.pvPower,
      annualConsumptionKwh: form.consumption,
      additionalNeeds: JSON.stringify(needsSelected.value),
      settlement: 'net_billing',
    })
    successSummary.value =
      'Szansa ' + result.deal + ' oraz oferta ' + result.oferta + ' zostały utworzone.'
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
</script>

<style scoped>
.voff-wrap {
  max-width: 720px;
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
.voff-btn-primary {
  background: #122566;
  color: #ffffff;
}
.voff-btn-accent {
  background: #c0ee2e;
  color: #122566;
}
.voff-btn-disabled,
.voff-btn:disabled {
  background: #e5e7eb;
  color: #9ca3af;
  cursor: not-allowed;
}
.voff-badge {
  display: inline-block;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  margin-left: 6px;
}
.voff-badge-reco {
  background: #c0ee2e;
  color: #122566;
  margin-left: 0;
  margin-right: 6px;
}
.voff-product-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
  cursor: pointer;
}
.voff-product-selected {
  border-color: #122566;
  box-shadow: 0 0 0 2px rgba(18, 37, 102, 0.15);
}
.voff-product-head {
  margin-bottom: 6px;
  font-size: 15px;
  color: #1a1a1a;
}
.voff-product-row {
  font-size: 13px;
  color: #374151;
  margin-bottom: 2px;
}
.voff-product-reasons {
  margin: 6px 0 0 18px;
  padding: 0;
  font-size: 12px;
  color: #6b7280;
  list-style: disc;
}
.voff-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
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
