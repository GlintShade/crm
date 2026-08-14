<!--
  Umowa tab (Szansa view) — "Formularz informacji do umowy": the client-facing
  data later used to generate a PV+storage contract PDF. Modeled directly on
  AudytTab.vue (loading/empty/form structure, depOk-based conditional
  visibility, server error surfacing) but simpler: no photo slots, no
  multi-stage review workflow, no comments. Draft saves are always allowed —
  the server reports which fields are still missing (`brakujace`) rather than
  gating the save itself.

  API (fixed interface, built by another agent in parallel). These are
  whitelisted methods in the fork (crm/api/umowa.py), NOT Server Scripts, so
  every call() MUST use the full dotted path below — a bare command name
  (e.g. 'volteo_umowa_get') resolves only via frappe.handler's globals(),
  which Server Scripts populate automatically but whitelisted fork methods do
  not. AudytTab.vue calls its Server Script endpoints by bare name, which is
  why that pattern looks correct to copy here and silently isn't:
    crm.api.umowa.volteo_umowa_get(deal)         -> {umowa|null, prefill, wyliczenia}
    crm.api.umowa.volteo_umowa_create(deal)      -> {umowa, prefill, wyliczenia}
    crm.api.umowa.volteo_umowa_save(deal, dane)  -> {umowa, prefill, wyliczenia}
    crm.api.umowa.volteo_umowa_pdf(deal)         -> {file_url, file_name}
      wyliczenia = { miejsce_montazu, pokrycie_dachowe, ppoz_wymagane,
                      kwota_kredytu_pln, brakujace_pola }

  All three endpoints carry the missing-fields list, so it must be read the
  same way everywhere: `wyliczenia.brakujace_pola`, NOT a top-level
  `brakujace` key. Reading a nonexistent key here would fail silently (an
  Array.isArray guard turns "undefined" into "[]") and make a half-filled
  draft look complete the moment the tab opens.

  `prefill` is a flat object keyed by the same fieldnames as the umowa record
  itself (e.g. prefill.adres_zam_ulica, prefill.deal_value) — it only ever
  supplies a starting value, the record's own saved value always wins once set.

  No cost/margin/commission values are shown here — contract data is
  client-facing only.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <!-- Loading -->
      <div v-if="loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <!-- Load failed — bail out, never render a misleading state -->
      <div
        v-else-if="loadError"
        class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
      >
        {{ loadError }}
      </div>

      <!-- Empty state — no umowa yet -->
      <div
        v-else-if="!umowa"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <UmowaIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak formularza umowy') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{
            __(
              'Wygeneruj formularz informacji do umowy, aby zebrać dane potrzebne do przygotowania umowy fotowoltaicznej.',
            )
          }}
        </div>
        <Button
          variant="solid"
          :label="__('Wygeneruj umowę')"
          :disabled="creating"
          :loading="creating"
          @click="createUmowa"
        />
      </div>

      <!-- Form -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="text-lg font-semibold text-ink-gray-8">
              {{ __('Formularz informacji do umowy') }}
            </div>
            <Badge
              :theme="isKompletny ? 'green' : 'amber'"
              variant="subtle"
              size="lg"
              :label="recordStatus"
            />
            <Badge
              v-if="autentiEnabled && autentiBadgeEntry"
              :theme="autentiBadgeEntry.theme"
              variant="subtle"
              size="lg"
              :label="autentiBadgeEntry.label"
            />
          </div>
          <div class="flex items-center gap-3">
            <span v-if="saveState === 'saving'" class="text-xs text-ink-gray-4">
              {{ __('Zapisywanie…') }}
            </span>
            <span v-else-if="saveState === 'saved'" class="text-xs text-ink-green-6">
              {{ __('Zapisano') }} ✓
            </span>
            <span v-else-if="saveState === 'error'" class="text-xs text-ink-red-6">
              {{ __('Błąd zapisu') }}
            </span>
            <Button
              v-if="showAutentiSendButton"
              variant="outline"
              :label="autentiSendLabel"
              @click="toggleAutentiConfirm"
            />
            <Button
              variant="outline"
              :label="__('Generuj PDF umowy')"
              :disabled="generatingPdf"
              :loading="generatingPdf"
              @click="generatePdf"
            />
            <Button
              variant="solid"
              :label="__('Zapisz')"
              :disabled="saving"
              :loading="saving"
              @click="saveForm"
            />
          </div>
        </div>

        <!-- Autenti timestamps — small muted line under the header/badges -->
        <div
          v-if="autentiEnabled && (autentiSentAtDisplay || autentiSignedAtDisplay)"
          class="-mt-4 flex flex-wrap gap-3 text-xs text-ink-gray-4"
        >
          <span v-if="autentiSentAtDisplay">
            {{ __('Wysłano') }}: {{ autentiSentAtDisplay }}
          </span>
          <span v-if="autentiSignedAtDisplay">
            {{ __('Podpisano') }}: {{ autentiSignedAtDisplay }}
          </span>
        </div>

        <!-- Autenti error — shown only for a failed send -->
        <div
          v-if="autentiEnabled && autentiStatus === 'Błąd' && autenti.error_message"
          class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
        >
          {{ autenti.error_message }}
        </div>

        <!-- Autenti signed PDF download -->
        <div v-if="autentiEnabled && autentiStatus === 'Podpisana' && autenti.signed_pdf_file">
          <Button
            variant="outline"
            :label="__('Pobierz podpisaną umowę')"
            @click="openSignedPdf"
          />
        </div>

        <!-- Autenti send confirmation — inline panel, not a modal -->
        <div
          v-if="showAutentiConfirm"
          class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4"
        >
          <div class="mb-2 text-sm font-medium text-ink-gray-8">
            {{ __('Potwierdź wysyłkę do podpisu') }}
          </div>

          <div v-if="signerMissingEmail" class="mb-3 text-sm text-ink-red-5">
            {{ __('Kontakt szansy nie ma adresu e-mail — uzupełnij go w CRM.') }}
          </div>
          <div v-else class="mb-3 text-sm text-ink-gray-6">
            <div>{{ __('Umowa zostanie wysłana do:') }}</div>
            <div v-if="recipientGroups.signers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Podpisują:') }}
              </div>
              <div
                v-for="r in recipientGroups.signers"
                :key="'signer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
            <div v-if="recipientGroups.viewers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Do wglądu:') }}
              </div>
              <div
                v-for="r in recipientGroups.viewers"
                :key="'viewer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
          </div>

          <div
            v-if="autenti.environment === 'Sandbox'"
            class="mb-3 rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
          >
            {{
              __(
                'Środowisko testowe Autenti — podpis NIE jest prawnie wiążący, a e-mail do klienta przyjdzie z domeny testowej.',
              )
            }}
          </div>

          <div class="flex gap-2">
            <Button
              variant="solid"
              :label="__('Wyślij')"
              :loading="sendingAutenti"
              :disabled="signerMissingEmail"
              @click="confirmSendAutenti"
            />
            <Button variant="ghost" :label="__('Anuluj')" @click="toggleAutentiConfirm" />
          </div>
        </div>

        <!-- Missing-fields summary (populated after the last save attempt) -->
        <div
          v-if="missingLabels.length"
          class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-4 py-3 text-sm text-ink-amber-8"
        >
          {{ __('Brakujące pola:') }} {{ missingLabels.join(', ') }}
        </div>

        <section v-for="sec in formSections" :key="sec.key">
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ sec.label }}
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div
              v-for="f in visibleFields(sec)"
              :key="f.fieldname"
              :class="['rounded', missingSet.has(f.fieldname) ? 'ring-1 ring-outline-red-3' : '']"
            >
              <FormControl
                :type="f.type"
                :label="f.label"
                :options="f.options"
                :step="f.step"
                :required="!!f.required"
                :disabled="saving"
                v-model="form[f.fieldname]"
              />
            </div>
          </div>

          <!-- Read-only derived fields, positioned per-section -->
          <div v-if="sec.key === 'finansowanie' && showKwotaKredytu" class="mt-4 max-w-xs">
            <FormControl
              type="text"
              :label="__('Kwota kredytu (PLN)')"
              :model-value="kwotaKredytuDisplay"
              disabled
            />
            <div class="mt-1 text-xs text-ink-gray-4">
              {{
                __(
                  'Wartość orientacyjna, liczona jako wartość oferty minus wkład własny. Serwer przelicza ją ponownie i jest rozstrzygający.',
                )
              }}
            </div>
          </div>

          <div v-if="sec.key === 'warunki'" class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <FormControl
                type="text"
                :label="__('Miejsce montażu')"
                :model-value="miejsceMontazuDisplay"
                disabled
              />
              <div class="mt-1 text-xs text-ink-gray-4">
                {{ __('Ustalane automatycznie na podstawie konstrukcji wybranej w kalkulatorze.') }}
              </div>
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Rodzaj pokrycia dachowego')"
                :model-value="pokrycieDachoweDisplay"
                disabled
              />
              <div class="mt-1 text-xs text-ink-gray-4">
                {{ __('Ustalane automatycznie na podstawie konstrukcji wybranej w kalkulatorze.') }}
              </div>
            </div>
          </div>

          <div v-if="sec.key === 'istniejaca_pv'" class="mt-4 max-w-xs">
            <FormControl
              type="text"
              :label="__('PPOŻ wymagane')"
              :model-value="wyliczenia.ppoz_wymagane ? __('Tak') : __('Nie')"
              disabled
            />
            <div class="mt-1 text-xs text-ink-gray-4">
              {{
                __(
                  'Ustawiane automatycznie, gdy suma mocy nowej i istniejącej instalacji przekracza 6,5 kW.',
                )
              }}
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import UmowaIcon from '@/components/Icons/UmowaIcon.vue'
import { Badge, Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { formatPlnAmount } from '@/utils/money'
import { formatDate } from '@/utils'
import { badgeFor, canSend, groupRecipients, isInFlight, sendButtonLabel } from '@/utils/autentiStatus'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Static form definition ---------------------------------------------------
// Grouped exactly as the brief specifies. Conditional fields carry
// `depends_on`; an item with no `depends_on` is always visible so an older
// server payload degrades gracefully instead of hiding the whole form.
const TAK_NIE = ['', 'Tak', 'Nie']

const formSections = [
  {
    key: 'adres',
    label: __('Adres'),
    fields: [
      {
        fieldname: 'adres_zam_jak_montaz',
        label: __('Czy adres montażu jest taki sam jak adres zamieszkania?'),
        type: 'select',
        options: TAK_NIE,
        required: true,
      },
      {
        fieldname: 'adres_zam_ulica',
        label: __('Ulica (adres zamieszkania)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_zam_nr_domu',
        label: __('Nr domu (adres zamieszkania)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_zam_nr_mieszkania',
        label: __('Nr mieszkania (adres zamieszkania)'),
        type: 'text',
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_zam_kod',
        label: __('Kod pocztowy (adres zamieszkania)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_zam_miasto',
        label: __('Miasto (adres zamieszkania)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_montaz_ulica',
        label: __('Ulica (adres montażu)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_montaz_nr_domu',
        label: __('Nr domu (adres montażu)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_montaz_kod',
        label: __('Kod pocztowy (adres montażu)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
      {
        fieldname: 'adres_montaz_miasto',
        label: __('Miasto (adres montażu)'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'adres_zam_jak_montaz', value: 'Nie' },
      },
    ],
  },
  {
    key: 'budynek',
    label: __('Budynek'),
    fields: [
      {
        fieldname: 'typ_budynku',
        label: __('Typ budynku'),
        type: 'select',
        options: ['', 'Jednorodzinny', 'Wielorodzinny'],
        required: true,
      },
      {
        fieldname: 'powierzchnia_prog',
        label: __('Powierzchnia'),
        type: 'select',
        options: ['', 'do 300 m²', 'powyżej 300 m²'],
        required: true,
      },
      {
        fieldname: 'powierzchnia_m2',
        label: __('Powierzchnia (m²)'),
        type: 'number',
        required: true,
        depends_on: { fieldname: 'powierzchnia_prog', value: 'powyżej 300 m²' },
      },
    ],
  },
  {
    key: 'finansowanie',
    label: __('Finansowanie'),
    fields: [
      {
        fieldname: 'finansowanie',
        label: __('Sposób finansowania'),
        type: 'select',
        options: ['', 'Kredyt 100%', 'Gotówka 100%', 'Kredyt + gotówka'],
        required: true,
      },
      {
        fieldname: 'wklad_wlasny_pln',
        label: __('Wkład własny (PLN)'),
        type: 'number',
        step: '0.01',
        required: true,
        depends_on: { fieldname: 'finansowanie', value: 'Kredyt + gotówka' },
      },
    ],
  },
  {
    key: 'warunki',
    label: __('Warunki instalacyjne'),
    fields: [
      {
        fieldname: 'internet',
        label: __('Internet'),
        type: 'select',
        options: ['', 'Wi-Fi', 'Kablowy', 'Brak'],
        required: true,
      },
      {
        fieldname: 'instalacja_odgromowa',
        label: __('Instalacja odgromowa'),
        type: 'select',
        options: TAK_NIE,
        required: true,
      },
      {
        fieldname: 'moc_przylaczeniowa_kw',
        label: __('Moc przyłączeniowa (kW)'),
        type: 'number',
        step: '0.1',
        required: true,
      },
      {
        fieldname: 'liczba_faz',
        label: __('Liczba faz'),
        type: 'select',
        options: ['', '1', '3'],
        required: true,
      },
      {
        fieldname: 'osd',
        label: __('OSD'),
        type: 'select',
        options: ['', 'PGE', 'Tauron', 'Enea', 'Energa', 'Stoen (innogy)', 'Inny'],
        required: true,
      },
      {
        fieldname: 'przekop_gruntowy',
        label: __('Przekop gruntowy'),
        type: 'select',
        options: TAK_NIE,
        required: true,
      },
      {
        fieldname: 'przekop_mb',
        label: __('Przekop gruntowy (mb)'),
        type: 'number',
        step: '1',
        depends_on: { fieldname: 'przekop_gruntowy', value: 'Tak' },
      },
      {
        fieldname: 'dodatkowy_kabel',
        label: __('Dodatkowy kabel'),
        type: 'select',
        options: TAK_NIE,
      },
      {
        fieldname: 'dodatkowy_kabel_m',
        label: __('Dodatkowy kabel (m)'),
        type: 'number',
        step: '0.1',
        depends_on: { fieldname: 'dodatkowy_kabel', value: 'Tak' },
      },
    ],
  },
  {
    key: 'istniejaca_pv',
    label: __('Istniejąca instalacja fotowoltaiczna'),
    fields: [
      {
        fieldname: 'istniejaca_pv',
        label: __('Czy klient ma już instalację PV?'),
        type: 'select',
        options: TAK_NIE,
        required: true,
      },
      {
        fieldname: 'istniejaca_pv_moc_inwertera_kw',
        label: __('Moc inwertera (kW)'),
        type: 'number',
        step: '0.1',
        required: true,
        depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
      },
      {
        fieldname: 'istniejaca_pv_moc_kwp',
        label: __('Moc instalacji (kWp)'),
        type: 'number',
        step: '0.1',
        required: true,
        depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
      },
      {
        fieldname: 'istniejaca_pv_producent_inwertera',
        label: __('Producent inwertera'),
        type: 'text',
        required: true,
        depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
      },
    ],
  },
  {
    key: 'zgody',
    label: __('Zgody'),
    fields: [
      {
        fieldname: 'zgoda_kontakt_telefoniczny',
        label: __('Zgoda na kontakt telefoniczny'),
        type: 'checkbox',
      },
      {
        fieldname: 'zgoda_dzialania_promocyjne',
        label: __('Zgoda na działania promocyjne'),
        type: 'checkbox',
      },
      {
        fieldname: 'zgoda_realizacja_przed_odstapieniem',
        label: __(
          'Wnoszę o realizację Umowy przed upływem terminu na odstąpienie (Załącznik nr 3)',
        ),
        type: 'checkbox',
      },
    ],
  },
]

// Fields that are actually part of the editable payload (excludes the
// read-only derived values, which are never sent — see buildPayload()).
const allFieldnames = formSections.flatMap((s) => s.fields.map((f) => f.fieldname))
const fieldLabelByName = new Map(
  formSections.flatMap((s) => s.fields.map((f) => [f.fieldname, f.label])),
)
// Wyprowadzone z formSections zamiast wpisanego na sztywno literału nazw pól —
// kolejna kratka dodana do formularza automatycznie trafia do tego zbioru,
// więc hydrateForm() nie może już po cichu pominąć konwersji na bool.
const checkboxFieldnames = new Set(
  formSections.flatMap((s) => s.fields.filter((f) => f.type === 'checkbox').map((f) => f.fieldname)),
)

// Vue 3: `v-if` on the same node as `v-for` is evaluated BEFORE the loop
// variable exists, so it would throw at runtime with no build-time warning.
// Filter in script and keep the template to a bare `v-for="f in visibleFields(sec)"`.
function depOk(item) {
  const dep = item.depends_on
  if (!dep) return true
  return form[dep.fieldname] === dep.value
}
function visibleFields(sec) {
  return (sec.fields || []).filter(depOk)
}

// --- Load state ----------------------------------------------------------------
const loading = ref(true)
const loadError = ref('')
const umowa = ref(null)
const prefill = ref({})
const wyliczenia = ref({})
const creating = ref(false)
const saving = ref(false)
const saveState = ref('idle') // idle | saving | saved | error
const brakujace = ref([])

const form = reactive({})

// --- Autenti e-signature state ----------------------------------------------------
// Explicit `null` initial state (never a bare `reactive` key presence check —
// see the CLAUDE.md note on the hasOwnProperty/reactive trap that froze the
// CP admin panel). `autenti` is a plain ref holding the whole status payload
// as returned by autenti_umowa_status; it is replaced wholesale (never
// mutated in place) on every load/send so Vue always sees a fresh reference.
const autenti = ref(null)
const showAutentiConfirm = ref(false)
const sendingAutenti = ref(false)
let autentiPollInterval = null

onMounted(() => {
  loadUmowa()
  loadAutentiStatus().then(() => {
    if (isInFlight(autentiStatus.value)) startAutentiPolling()
  })
})
onUnmounted(stopAutentiPolling)

// The missing-fields list travels inside `wyliczenia.brakujace_pola` on
// EVERY endpoint (get/create/save) — there is no top-level `brakujace` key.
// Centralised here so all three call sites read it identically; getting this
// wrong makes a half-filled draft silently look complete (Array.isArray
// guard turns a wrong key into an empty array, not an error).
function extractBrakujace(data) {
  const list = data?.wyliczenia?.brakujace_pola
  return Array.isArray(list) ? list : []
}

async function loadUmowa() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await call('crm.api.umowa.volteo_umowa_get', { deal: props.dealId })
    umowa.value = data?.umowa || null
    prefill.value = data?.prefill || {}
    wyliczenia.value = data?.wyliczenia || {}
    brakujace.value = extractBrakujace(data)
    if (umowa.value) hydrateForm(umowa.value)
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
}

function valueOr(v, fallback) {
  if (v !== undefined && v !== null && v !== '') return v
  return fallback ?? ''
}

// `prefill` only ever supplies a starting value for a handful of fields
// (home address from the contact, install address + deal_value + cable
// length from the deal); everything else starts from the record itself.
function hydrateForm(u) {
  const p = prefill.value || {}
  allFieldnames.forEach((fn) => {
    const raw = u ? u[fn] : undefined
    if (checkboxFieldnames.has(fn)) {
      form[fn] = !!raw
    } else {
      form[fn] = valueOr(raw, p[fn])
    }
  })
}

// --- Derived / read-only values --------------------------------------------------
const showKwotaKredytu = computed(
  () => form.finansowanie === 'Kredyt 100%' || form.finansowanie === 'Kredyt + gotówka',
)
const kwotaKredytu = computed(() => {
  const dealValue = Number(prefill.value?.deal_value) || 0
  const wklad = Number(form.wklad_wlasny_pln) || 0
  return Math.max(0, dealValue - wklad)
})
const kwotaKredytuDisplay = computed(() => formatPlnAmount(kwotaKredytu.value))

// Server-authoritative derived values. `null` means the chosen konstrukcja in
// the calculator wasn't recognised — show a clear Polish note, not a blank gap.
const miejsceMontazuDisplay = computed(
  () => wyliczenia.value?.miejsce_montazu || __('nie ustalono z kalkulatora'),
)
const pokrycieDachoweDisplay = computed(
  () => wyliczenia.value?.pokrycie_dachowe || __('nie ustalono z kalkulatora'),
)

const missingSet = computed(() => new Set(brakujace.value))
const missingLabels = computed(() =>
  brakujace.value.map((fn) => fieldLabelByName.get(fn) || fn),
)

const recordStatus = computed(() => umowa.value?.status || 'Roboczy')
const isKompletny = computed(() => recordStatus.value === 'Kompletny')

// --- Autenti e-signature (derived) ------------------------------------------------
// `enabled === false` (integration off) OR `autenti === null` (not loaded yet /
// load failed) both mean: render NO signing UI at all — the feature must stay
// completely invisible rather than show a half-broken control.
const autentiEnabled = computed(() => autenti.value?.enabled === true)
const autentiStatus = computed(() => autenti.value?.autenti_status || null)
const autentiBadgeEntry = computed(() => badgeFor(autentiStatus.value))
const autentiSendLabel = computed(() => sendButtonLabel(autentiStatus.value))
// Gated on the status payload's OWN umowa_exists/pdf_exists (not the separate
// umowa/generatingPdf state above) — that's what the backend contract says to
// check, and it stays correct even if the two loads (umowa vs autenti status)
// settle in different order.
const showAutentiSendButton = computed(
  () =>
    autentiEnabled.value &&
    !!autenti.value?.umowa_exists &&
    !!autenti.value?.pdf_exists &&
    canSend(autentiStatus.value),
)
const proposedSigner = computed(() => autenti.value?.proposed_signer || null)
const signerMissingEmail = computed(() => !proposedSigner.value || !proposedSigner.value.email)
// Grouped SIGNER/VIEWER view of `proposed_recipients` for the confirm panel.
// Falls back to `proposedSigner` alone when the backend hasn't shipped
// `proposed_recipients` yet — see groupRecipients() for why.
const recipientGroups = computed(() =>
  groupRecipients(autenti.value?.proposed_recipients, proposedSigner.value),
)
const autentiSentAtDisplay = computed(() =>
  autenti.value?.sent_at ? formatDate(autenti.value.sent_at, null, true, true) : '',
)
const autentiSignedAtDisplay = computed(() =>
  autenti.value?.signed_at ? formatDate(autenti.value.signed_at, null, true, true) : '',
)

async function loadAutentiStatus() {
  try {
    const data = await call('crm.integrations.autenti.api.autenti_umowa_status', {
      deal: props.dealId,
    })
    autenti.value = data || null
  } catch (err) {
    // Non-fatal and silent on purpose: this is a background status check for
    // an optional feature, not a user-triggered action. Leaving `autenti`
    // unset simply keeps the signing UI hidden, same as "integration
    // disabled" — no toast for a control the rep hasn't touched.
    console.error(err)
  }
}

function startAutentiPolling() {
  if (autentiPollInterval) return
  autentiPollInterval = setInterval(async () => {
    await loadAutentiStatus()
    if (!isInFlight(autentiStatus.value)) stopAutentiPolling()
  }, 30000)
}

function stopAutentiPolling() {
  if (autentiPollInterval) {
    clearInterval(autentiPollInterval)
    autentiPollInterval = null
  }
}

function toggleAutentiConfirm() {
  showAutentiConfirm.value = !showAutentiConfirm.value
}

async function confirmSendAutenti() {
  if (sendingAutenti.value || signerMissingEmail.value) return
  sendingAutenti.value = true
  try {
    const data = await call('crm.integrations.autenti.api.autenti_send_umowa', {
      deal: props.dealId,
    })
    autenti.value = autenti.value
      ? { ...autenti.value, autenti_status: data?.autenti_status || 'Wysyłanie' }
      : autenti.value
    showAutentiConfirm.value = false
    toast.success(__('Umowa wysłana do podpisu'))
    startAutentiPolling()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    sendingAutenti.value = false
  }
}

function openSignedPdf() {
  if (autenti.value?.signed_pdf_file) {
    window.open(autenti.value.signed_pdf_file, '_blank')
  }
}

// --- Create ----------------------------------------------------------------------
async function createUmowa() {
  if (creating.value) return
  creating.value = true
  try {
    const data = await call('crm.api.umowa.volteo_umowa_create', { deal: props.dealId })
    umowa.value = data?.umowa || null
    prefill.value = data?.prefill || {}
    wyliczenia.value = data?.wyliczenia || {}
    brakujace.value = extractBrakujace(data)
    if (umowa.value) hydrateForm(umowa.value)
    toast.success(__('Utworzono formularz umowy'))
    // Refresh Autenti status so `umowa_exists` stops being stale — otherwise
    // the "Podpisz umowę" button stays hidden until a full page reload.
    await loadAutentiStatus()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

// --- Save (draft-safe: incomplete saves are allowed) -----------------------------
function buildPayload() {
  const payload = {}
  allFieldnames.forEach((fn) => {
    payload[fn] = form[fn]
  })
  return payload
}

async function saveForm() {
  if (saving.value || !umowa.value) return
  saving.value = true
  saveState.value = 'saving'
  try {
    const data = await call('crm.api.umowa.volteo_umowa_save', {
      deal: props.dealId,
      dane: buildPayload(),
    })
    umowa.value = data?.umowa || umowa.value
    prefill.value = data?.prefill || prefill.value
    wyliczenia.value = data?.wyliczenia || wyliczenia.value
    brakujace.value = extractBrakujace(data)
    hydrateForm(umowa.value)
    saveState.value = 'saved'
    if (brakujace.value.length) {
      toast.success(__('Zapisano jako roboczy — część pól nadal brakuje.'))
    } else {
      toast.success(__('Zapisano formularz umowy'))
    }
  } catch (err) {
    saveState.value = 'error'
    toast.error(extractErrorMessage(err))
  } finally {
    saving.value = false
  }
}

// --- Generate PDF ------------------------------------------------------------------
// Server-side only: no cost/margin/commission data is available to this tab in the
// first place, so there is nothing sensitive this call could leak client-side.
const generatingPdf = ref(false)

async function generatePdf() {
  if (generatingPdf.value || !umowa.value) return
  generatingPdf.value = true
  try {
    const data = await call('crm.api.umowa.volteo_umowa_pdf', { deal: props.dealId })
    if (data?.file_url) {
      // Private file served by Frappe under the caller's existing session cookie —
      // a plain relative-URL open (not a fetch/download) is enough, same-origin.
      window.open(data.file_url, '_blank')
      toast.success(__('Wygenerowano PDF umowy'))
      // Optimistic local flip so the Autenti send button can appear instantly
      // without waiting for the reload below — new object, not a mutation,
      // per the ref-replace convention used everywhere else in this file.
      if (autenti.value) {
        autenti.value = { ...autenti.value, pdf_exists: true }
      }
      // Follow up with a real reload so `umowa_exists` (stale if this PDF was
      // generated right after createUmowa() in the same session) and anything
      // else in the payload get corrected too.
      await loadAutentiStatus()
    } else {
      toast.error(__('Wystąpił błąd - spróbuj ponownie'))
    }
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    generatingPdf.value = false
  }
}

// --- Helpers -----------------------------------------------------------------------
function extractErrorMessage(err) {
  try {
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Wystąpił błąd - spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd - spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd - spróbuj ponownie')
}
</script>
