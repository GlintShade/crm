<!--
  Kredyt tab (Szansa view) — credit-application data collection form for the
  bank/leasing partner, plus PDF generation. Cloned from UmowaTab.vue's
  skeleton (loading/loadError/empty/form states, declarative sections +
  depOk()/visibleFields() filtering, missing-fields banner with red rings,
  extractErrorMessage, window.open for the PDF) — simpler than UmowaTab: no
  e-signature integration, draft saves are always allowed, and PDF
  generation is additionally gated on completeness (disabled while
  brakujace_pola is non-empty) rather than always available.

  API (fixed interface, built by another agent in parallel). These are
  whitelisted methods in the fork (crm/api/kredyt.py), NOT Server Scripts,
  so every call() MUST use the full dotted path below — a bare command name
  resolves only via frappe.handler's globals(), which Server Scripts
  populate automatically but whitelisted fork methods do not (see
  UmowaTab.vue's header comment / CLAUDE.md "Ścieżka wywołania API" for the
  full story: this exact mistake shipped a 417 on every Umowa-tab load):
    crm.api.kredyt.volteo_kredyt_get({ deal })    -> { kredyt, prefill, brakujace_pola }
    crm.api.kredyt.volteo_kredyt_create({ deal }) -> { kredyt, prefill, brakujace_pola }
    crm.api.kredyt.volteo_kredyt_save({ deal, dane }) -> { kredyt, prefill, brakujace_pola }
    crm.api.kredyt.volteo_kredyt_pdf({ deal })    -> { file_url, file_name }
      (throws with a Polish message when the record is incomplete)

  `prefill` is a flat, read-only object (contact-card data: pesel, imiona,
  nazwisko, telefon, email, kod_pocztowy, miejscowosc, ulica, nr_domu,
  nr_lokalu) shown for reference at the top of the form — it is NEVER part
  of the editable payload and is edited on the contact card, not here.

  `brakujace_pola` (unlike UmowaTab's `wyliczenia.brakujace_pola`) is a
  TOP-LEVEL key on every one of the three endpoints above — do not nest a
  lookup under a `wyliczenia` key here, there is no such key in this
  contract.

  Form-state logic (defaultForm/buildDane/hydrateFrom/GRUPY/option arrays)
  lives in @/utils/kredytForm.js so it is unit-testable without mounting
  Vue — this file only wires that logic to the template.
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

      <!-- Empty state — no kredyt record yet -->
      <div
        v-else-if="!kredyt"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <KredytIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">
          {{ __('Brak wniosku kredytowego') }}
        </div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{
            __(
              'Utwórz formularz danych do wniosku kredytowego, aby zebrać informacje potrzebne bankowi.',
            )
          }}
        </div>
        <Button
          variant="solid"
          :label="__('Utwórz wniosek')"
          :disabled="creating"
          :loading="creating"
          @click="createKredyt"
        />
      </div>

      <!-- Form -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="text-lg font-semibold text-ink-gray-8">
            {{ __('Wniosek kredytowy') }}
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
              variant="outline"
              :label="__('Generuj PDF')"
              :disabled="generatingPdf || missingLabels.length > 0"
              :loading="generatingPdf"
              :tooltip="
                missingLabels.length > 0
                  ? __('Uzupełnij wszystkie wymagane pola')
                  : ''
              "
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

        <!-- Read-only client data from CRM -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
          <div class="mb-3 text-sm font-semibold text-ink-gray-7">
            {{ __('Dane klienta (z CRM)') }}
          </div>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div v-for="p in prefillDisplay" :key="p.key">
              <div class="text-xs text-ink-gray-5">{{ p.label }}</div>
              <div class="text-sm text-ink-gray-8">{{ p.value || '—' }}</div>
            </div>
          </div>
          <div class="mt-3 text-xs text-ink-gray-4">
            {{ __('Te dane edytuje się na karcie kontaktu, nie w tym formularzu.') }}
          </div>
        </div>

        <!-- Missing-fields summary -->
        <div
          v-if="missingLabels.length"
          class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-4 py-3 text-sm text-ink-amber-8"
        >
          {{ __('Brakujące pola:') }} {{ missingLabels.join(', ') }}
        </div>

        <!-- §1-3: base sections -->
        <section v-for="sec in formSections" :key="sec.key">
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ sec.label }}
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div
              v-for="f in visibleFields(sec.fields)"
              :key="f.fieldname"
              :class="[
                'rounded',
                missingSet.has(f.fieldname) ? 'ring-1 ring-outline-red-3' : '',
                f.fullWidth ? 'sm:col-span-3' : '',
              ]"
            >
              <FormControl
                :type="f.type"
                :label="f.label"
                :options="f.options"
                :inputmode="f.inputmode"
                :placeholder="f.placeholder"
                :disabled="saving"
                v-model="form[f.fieldname]"
                @blur="onKwotaBlur(f)"
              />
            </div>
          </div>
        </section>

        <!-- §4-9: income groups -->
        <section v-for="grupa in GRUPY" :key="grupa.key" class="kalk-part">
          <div class="kalk-part-heading mb-4 flex items-center justify-between gap-2 border-b border-gray-100 pb-2.5 text-base font-semibold text-ink-gray-9">
            <div>{{ grupa.label }}</div>
            <button
              type="button"
              role="switch"
              :aria-checked="form[grupa.wlaczone]"
              :aria-label="grupa.label"
              class="kalk-switch shrink-0"
              :class="form[grupa.wlaczone] ? 'kalk-switch-on' : 'kalk-switch-off'"
              :disabled="saving"
              @click="form[grupa.wlaczone] = !form[grupa.wlaczone]"
            ><span class="kalk-switch-knob" /></button>
          </div>

          <div
            v-if="form[grupa.wlaczone]"
            :class="[
              'grid grid-cols-1 gap-4',
              grupa.key === 'inne' ? 'sm:grid-cols-2' : 'sm:grid-cols-3',
            ]"
          >
            <div
              v-for="f in visibleFields(grupaPola[grupa.key])"
              :key="f.fieldname"
              :class="['rounded', missingSet.has(f.fieldname) ? 'ring-1 ring-outline-red-3' : '']"
            >
              <FormControl
                :type="f.type"
                :label="f.label"
                :options="f.options"
                :inputmode="f.inputmode"
                :placeholder="f.placeholder"
                :disabled="saving"
                v-model="form[f.fieldname]"
                @blur="onKwotaBlur(f)"
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import KredytIcon from '@/components/Icons/KredytIcon.vue'
import { Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'
import {
  GRUPY,
  PREFILL_KEYS,
  TAK_NIE_OPCJE,
  WYKSZTALCENIE_OPCJE,
  RODZAJ_DOKUMENTU_OPCJE,
  STAN_CYWILNY_OPCJE,
  PRACA_FORMA_OPCJE,
  PRACA_OKRES_OPCJE,
  DZIALALNOSC_FORMA_OPCJE,
  defaultForm,
  buildDane,
  hydrateFrom,
  normalizujKwote,
} from '@/utils/kredytForm'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Static form definition (§1-3, base fields) ---------------------------
// Same Vue 3 trap as UmowaTab: `v-if` + `v-for` on one node is evaluated
// before the loop variable exists, so filtering happens in script
// (visibleFields()) and the template stays a bare `v-for`.
const formSections = [
  {
    key: 'podstawowe',
    label: __('Dane podstawowe'),
    fields: [
      { fieldname: 'miejsce_urodzenia', label: __('Miejsce urodzenia'), type: 'text' },
      {
        fieldname: 'rodzaj_dokumentu',
        label: __('Rodzaj dokumentu'),
        type: 'select',
        options: RODZAJ_DOKUMENTU_OPCJE,
      },
      {
        fieldname: 'seria_numer_dokumentu',
        label: __('Seria i numer dokumentu tożsamości'),
        type: 'text',
      },
      { fieldname: 'data_wydania_dokumentu', label: __('Data wydania dokumentu'), type: 'date' },
      {
        fieldname: 'data_waznosci_dokumentu',
        label: __('Data ważności dokumentu'),
        type: 'date',
      },
    ],
  },
  {
    key: 'adresy',
    label: __('Adresy'),
    fields: [
      {
        fieldname: 'adres_zameldowania_taki_sam',
        label: __('Czy adres zamieszkania jest taki sam, jak adres zameldowania?'),
        type: 'select',
        options: TAK_NIE_OPCJE,
      },
      {
        fieldname: 'adres_zameldowania',
        label: __('Adres zameldowania'),
        type: 'text',
        depends_on: { fieldname: 'adres_zameldowania_taki_sam', value: 'Nie' },
      },
      {
        fieldname: 'adres_korespondencji_taki_sam',
        label: __('Czy adres do korespondencji jest taki sam, jak adres zameldowania?'),
        type: 'select',
        options: TAK_NIE_OPCJE,
      },
      {
        fieldname: 'adres_korespondencji',
        label: __('Adres do korespondencji'),
        type: 'text',
        depends_on: { fieldname: 'adres_korespondencji_taki_sam', value: 'Nie' },
      },
    ],
  },
  {
    key: 'wnioskodawca',
    label: __('Informacje o wnioskodawcy'),
    fields: [
      {
        fieldname: 'wyksztalcenie',
        label: __('Wykształcenie'),
        type: 'select',
        options: WYKSZTALCENIE_OPCJE,
      },
      {
        fieldname: 'stan_cywilny',
        label: __('Stan cywilny'),
        type: 'select',
        options: STAN_CYWILNY_OPCJE,
      },
      {
        fieldname: 'liczba_osob_na_utrzymaniu',
        label: __('Liczba osób na utrzymaniu'),
        type: 'text',
        inputmode: 'numeric',
      },
      {
        fieldname: 'kwota_800_plus',
        label: __('Kwota 800+'),
        type: 'text',
        inputmode: 'decimal',
        placeholder: '0,00',
      },
      {
        fieldname: 'dochod_wspolmalzonka',
        label: __('Dochód współmałżonka'),
        type: 'text',
        inputmode: 'decimal',
        placeholder: '0,00',
      },
      {
        fieldname: 'zrodlo_dochodu_malzonka',
        label: __('Źródło dochodu małżonka'),
        type: 'text',
      },
      {
        fieldname: 'oplaty_miesieczne',
        label: __('Opłaty miesięczne'),
        type: 'text',
        inputmode: 'decimal',
        placeholder: '0,00',
      },
      {
        fieldname: 'suma_zobowiazan',
        label: __('Suma zobowiązań'),
        type: 'text',
        inputmode: 'decimal',
        placeholder: '0,00',
      },
      {
        fieldname: 'numer_rachunku',
        label: __('Numer rachunku'),
        type: 'text',
        // Full-width — at the shared 1/3-column width the last digits of a
        // 26-digit IBAN-style account number were getting visually cut off
        // (owner feedback after click-testing).
        fullWidth: true,
      },
    ],
  },
]

// --- Income group field metadata (§4-9) ------------------------------------
// Keyed by GRUPY[].key from kredytForm.js — the fieldname LIST there is the
// single source of truth for which fields exist per group (and what
// buildDane()/hydrateFrom() operate on); this map only adds the per-field
// label/type/depends_on needed to render them, so the two can never drift
// on fieldnames (a missing/extra field here would leave a hole in the grid,
// not a data-shape bug).
const grupaPola = {
  praca: [
    { fieldname: 'praca_forma', label: __('Forma zatrudnienia'), type: 'select', options: PRACA_FORMA_OPCJE },
    { fieldname: 'praca_data_zatrudnienia', label: __('Data zatrudnienia'), type: 'date' },
    { fieldname: 'praca_okres', label: __('Okres zatrudnienia'), type: 'select', options: PRACA_OKRES_OPCJE },
    {
      fieldname: 'praca_okres_od',
      label: __('Okres zatrudnienia od'),
      type: 'date',
      depends_on: { fieldname: 'praca_okres', value: 'Czas określony' },
    },
    {
      fieldname: 'praca_okres_do',
      label: __('Okres zatrudnienia do'),
      type: 'date',
      depends_on: { fieldname: 'praca_okres', value: 'Czas określony' },
    },
    { fieldname: 'praca_nip', label: __('NIP zakładu pracy'), type: 'text' },
    { fieldname: 'praca_nazwa_zakladu', label: __('Nazwa zakładu pracy'), type: 'text' },
    { fieldname: 'praca_adres_telefon', label: __('Adres i telefon zakładu pracy'), type: 'text' },
    {
      fieldname: 'praca_kwota_dochodu',
      label: __('Kwota dochodu'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
  emerytura: [
    { fieldname: 'emerytura_numer_swiadczenia', label: __('Numer świadczenia'), type: 'text' },
    { fieldname: 'emerytura_od_kiedy', label: __('Od kiedy pobierane'), type: 'date' },
    {
      fieldname: 'emerytura_kwota_dochodu',
      label: __('Kwota dochodu'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
  renta: [
    { fieldname: 'renta_numer_swiadczenia', label: __('Numer świadczenia'), type: 'text' },
    { fieldname: 'renta_od_kiedy', label: __('Od kiedy pobierane'), type: 'date' },
    {
      fieldname: 'renta_kwota_dochodu',
      label: __('Kwota dochodu'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
  dzialalnosc: [
    {
      fieldname: 'dzialalnosc_forma_opodatkowania',
      label: __('Forma opodatkowania'),
      type: 'select',
      options: DZIALALNOSC_FORMA_OPCJE,
    },
    {
      fieldname: 'dzialalnosc_forma_inna',
      label: __('Inna forma opodatkowania — jaka?'),
      type: 'text',
      depends_on: { fieldname: 'dzialalnosc_forma_opodatkowania', value: 'inne' },
    },
    { fieldname: 'dzialalnosc_nip', label: __('NIP'), type: 'text' },
    { fieldname: 'dzialalnosc_nazwa', label: __('Nazwa działalności'), type: 'text' },
    { fieldname: 'dzialalnosc_adres', label: __('Adres firmy'), type: 'text' },
    { fieldname: 'dzialalnosc_telefon', label: __('Numer telefonu do firmy'), type: 'text' },
    { fieldname: 'dzialalnosc_od_kiedy', label: __('Od kiedy prowadzona'), type: 'date' },
    {
      fieldname: 'dzialalnosc_kwota_dochodu',
      label: __('Kwota dochodu'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
  gospodarstwo: [
    { fieldname: 'gospodarstwo_nip', label: __('NIP gospodarstwa'), type: 'text' },
    { fieldname: 'gospodarstwo_od_kiedy', label: __('Od kiedy prowadzone'), type: 'date' },
    {
      fieldname: 'gospodarstwo_kwota_dochodu',
      label: __('Kwota dochodu'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
  inne: [
    { fieldname: 'inne_1_typ', label: __('Inne źródło 1 — typ'), type: 'text' },
    {
      fieldname: 'inne_1_kwota',
      label: __('Inne źródło 1 — kwota'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
    { fieldname: 'inne_2_typ', label: __('Inne źródło 2 — typ'), type: 'text' },
    {
      fieldname: 'inne_2_kwota',
      label: __('Inne źródło 2 — kwota'),
      type: 'text',
      inputmode: 'decimal',
      placeholder: '0,00',
    },
  ],
}

// Polish labels for the missing-fields banner — combines both static
// section fields and every income-group field so any fieldname the server
// reports in brakujace_pola resolves to a readable label.
const fieldLabelByName = new Map([
  ...formSections.flatMap((s) => s.fields.map((f) => [f.fieldname, f.label])),
  ...Object.values(grupaPola).flatMap((fields) => fields.map((f) => [f.fieldname, f.label])),
])

function depOk(form, item) {
  const dep = item.depends_on
  if (!dep) return true
  return form[dep.fieldname] === dep.value
}
function visibleFields(fields) {
  return (fields || []).filter((f) => depOk(form, f))
}

// Amount fields (inputmode: 'decimal') get their typed text normalized to
// "123,45" on blur — owner feedback after click-testing: the rep should see
// what was understood before saving, not just find out server-side. Every
// non-amount field is a no-op here (inputmode check).
function onKwotaBlur(f) {
  if (f.inputmode !== 'decimal') return
  form[f.fieldname] = normalizujKwote(form[f.fieldname])
}

// --- Load state --------------------------------------------------------------
const loading = ref(true)
const loadError = ref('')
const kredyt = ref(null)
const prefill = ref({})
const creating = ref(false)
const saving = ref(false)
const saveState = ref('idle') // idle | saving | saved | error
const brakujace = ref([])

const form = reactive(defaultForm())

const prefillLabels = {
  pesel: __('PESEL'),
  imiona: __('Imiona'),
  nazwisko: __('Nazwisko'),
  telefon: __('Telefon'),
  email: __('E-mail'),
  kod_pocztowy: __('Kod pocztowy'),
  miejscowosc: __('Miejscowość'),
  ulica: __('Ulica'),
  nr_domu: __('Nr domu'),
  nr_lokalu: __('Nr lokalu'),
}
const prefillDisplay = computed(() =>
  PREFILL_KEYS.map((key) => ({
    key,
    label: prefillLabels[key] || key,
    value: prefill.value?.[key] || '',
  })),
)

onMounted(loadKredyt)

// brakujace_pola is a TOP-LEVEL key on every kredyt endpoint (unlike
// UmowaTab's nested wyliczenia.brakujace_pola) — centralised here so all
// three call sites read it identically.
function extractBrakujace(data) {
  const list = data?.brakujace_pola
  return Array.isArray(list) ? list : []
}

async function loadKredyt() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_get', { deal: props.dealId })
    kredyt.value = data?.kredyt || null
    prefill.value = data?.prefill || {}
    brakujace.value = extractBrakujace(data)
    Object.assign(form, hydrateFrom(kredyt.value))
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
}

const missingSet = computed(() => new Set(brakujace.value))
const missingLabels = computed(() =>
  brakujace.value.map((fn) => fieldLabelByName.get(fn) || fn),
)

// --- Create --------------------------------------------------------------------
async function createKredyt() {
  if (creating.value) return
  creating.value = true
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_create', { deal: props.dealId })
    kredyt.value = data?.kredyt || null
    prefill.value = data?.prefill || {}
    brakujace.value = extractBrakujace(data)
    Object.assign(form, hydrateFrom(kredyt.value))
    toast.success(__('Utworzono wniosek kredytowy'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

// --- Save (draft-safe: incomplete saves are allowed) -----------------------------
async function saveForm() {
  if (saving.value || !kredyt.value) return
  saving.value = true
  saveState.value = 'saving'
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_save', {
      deal: props.dealId,
      dane: buildDane(form),
    })
    kredyt.value = data?.kredyt || kredyt.value
    prefill.value = data?.prefill || prefill.value
    brakujace.value = extractBrakujace(data)
    Object.assign(form, hydrateFrom(kredyt.value))
    saveState.value = 'saved'
    if (brakujace.value.length) {
      toast.success(__('Zapisano jako roboczy — część pól nadal brakuje.'))
    } else {
      toast.success(__('Zapisano wniosek kredytowy'))
    }
  } catch (err) {
    saveState.value = 'error'
    toast.error(extractErrorMessage(err))
  } finally {
    saving.value = false
  }
}

// --- Generate PDF ------------------------------------------------------------------
const generatingPdf = ref(false)

async function generatePdf() {
  if (generatingPdf.value || !kredyt.value || missingLabels.value.length) return
  generatingPdf.value = true
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_pdf', { deal: props.dealId })
    if (data?.file_url) {
      window.open(data.file_url, '_blank')
      toast.success(__('Wygenerowano PDF wniosku'))
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

<style scoped>
/* Income-group card + iOS-style TAK/NIE switch — copied from
   KalkulatorCPTab.vue's `.kalk-part`/`.kalk-switch` pattern (see that
   file's CSS comments for the full rationale). Colours are fixed by owner
   decision: green = on, BLACK = off, never grey/red. */
.kalk-part {
  border: 1px solid #e5e5e5;
  border-radius: 0.75rem;
  background: #fff;
  padding: 1.25rem 1.25rem 1.375rem;
}
.kalk-part-heading {
  letter-spacing: -0.01em;
}
.kalk-switch {
  position: relative;
  display: inline-block;
  flex-shrink: 0;
  width: 40px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  vertical-align: middle;
  transition: background-color 0.15s;
}
.kalk-switch-on {
  background: #16a34a;
}
.kalk-switch-off {
  background: #111827;
}
.kalk-switch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.kalk-switch:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
.kalk-switch-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 9999px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  transition: transform 0.15s;
}
.kalk-switch-on .kalk-switch-knob {
  transform: translateX(18px);
}
</style>
