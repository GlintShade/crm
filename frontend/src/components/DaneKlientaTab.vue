<!--
  VOLTEO: "Dane klienta" — the client-view tab that turns the narrow
  right-side panel's Contact fields into a full-width, per-field auto-save
  form. `useDocument('Contact', contactId)` reads from the SAME
  `documentsCache` singleton (frontend/src/data/document.js) that
  Contact.vue and its SidePanelLayout already use, so this tab and the
  panel edit the exact same reactive `contact.doc` — a change here is
  visible in the panel (and vice versa) with no events, no reload.

  Auto-save is per field: a text field saves on blur, a select saves on
  change, and every save is a whole-document `contact.save.submit()` —
  this mirrors SidePanelLayout.vue's `fieldChange()`, which is *always* a
  full-document save, never a single-field PATCH. Validation (from
  `@/utils/contactValidators.js`) runs BEFORE the field is written back to
  `contact.doc` and blocks the request on failure — no wasted round-trip
  for a value the backend would reject anyway.

  Validated fields (first_name, last_name, custom_pesel — plus email/phone
  below) bind `v-model` to a LOCAL ref, never straight to `contact.doc`.
  `contact.doc` is the shared singleton: writing a rejected value into it
  even though no request was sent would (a) leak instantly into the right
  panel, and (b) get silently persisted by the very next whole-document
  save from ANY field, in either surface. So the local ref absorbs
  mid-typing/invalid input, and only a value that already passed
  validation is copied onto `contact.doc` immediately before submit.

  PESEL is `reqd=1` on Contact (see ops/crm-contact-address-inline.py). If
  it is blank, `contact.save.submit()` — via useDocument's checkMandatory
  wrapper — refuses silently (a toast, no onSuccess/onError), which would
  otherwise leave the save-status pill stuck forever. `peselPusty` heads
  that off: while PESEL is empty, every field OTHER than PESEL itself
  short-circuits straight to the "Zapis wstrzymany" state instead of firing
  a submit that can never resolve.

  Field-spec labels below are plain, UNTRANSLATED strings — `__()` is only
  ever called at render time in the template. Precedent: Contact.vue's own
  `tabs` computed stores `label: 'Deals'` and calls `__(tab.label)` only
  inside the tab-item template. Calling `__()` at module/array-definition
  time is the eager-chunk trap that once broke KalkulatorCPTab's admin
  panel — see CLAUDE.md "Eager chunk a __()".

  Gating is by explicit `null`/falsy checks throughout (`v-if="!contact.doc"`,
  `computed(() => Boolean(...))`), never `hasOwnProperty` on the reactive
  `contact` object — see CLAUDE.md's hasOwnProperty/reactive() trap.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div v-if="!contact.doc && !bladLadowania" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie danych klienta…') }}
      </div>

      <div
        v-else-if="bladLadowania"
        class="rounded border border-outline-red-3 bg-surface-red-2 px-3 py-2 text-sm text-ink-red-8"
      >
        {{ bladLadowania }}
      </div>

      <template v-else>
        <div class="mb-4 flex items-center justify-between">
          <div class="text-lg font-bold text-ink-gray-9">{{ __('Dane klienta') }}</div>
          <div v-if="pigulka.text" class="text-sm font-medium" :class="pigulka.klasa">
            {{ pigulka.text }}
          </div>
        </div>

        <ErrorMessage
          v-if="stanZapisu === 'blad' && komunikat"
          class="mb-4"
          :message="komunikat"
        />

        <div
          v-if="peselPusty"
          class="mb-4 rounded border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
        >
          {{
            __(
              'Ten kontakt nie ma numeru PESEL. Pole jest wymagane — uzupełnij je, aby zapisywanie zmian zadziałało.',
            )
          }}
        </div>

        <!-- Dane osobowe -->
        <div class="mb-6">
          <div class="mb-3 border-b border-outline-gray-1 pb-2 text-base font-semibold text-ink-gray-9">
            {{ __('Dane osobowe') }}
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <div v-for="pole in POLA_DANE_OSOBOWE" :key="pole.fieldname">
              <FormControl
                type="text"
                :label="__(pole.label)"
                v-model="refyDaneOsobowe[pole.fieldname].value"
                :disabled="!mozeZapisywac"
                :error="bladPola(pole.fieldname)"
                @blur="onBlurDaneOsobowe(pole.fieldname)"
              />
            </div>
          </div>
        </div>

        <!-- Dane kontaktowe -->
        <div class="mb-6">
          <div class="mb-3 border-b border-outline-gray-1 pb-2 text-base font-semibold text-ink-gray-9">
            {{ __('Dane kontaktowe') }}
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <div>
              <FormControl
                type="email"
                :label="__('Główny e-mail')"
                v-model="emailGlowny"
                :disabled="!mozeZapisywac"
                :error="bledy.email_id"
                @blur="onBlurEmailGlowny"
              />
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Główny telefon')"
                v-model="telefonGlowny"
                :disabled="!mozeZapisywac"
                :error="bledy.mobile_no"
                @blur="onBlurTelefonGlowny"
              />
            </div>
          </div>
        </div>

        <!-- Adres zamieszkania -->
        <div class="mb-6">
          <div class="mb-3 border-b border-outline-gray-1 pb-2 text-base font-semibold text-ink-gray-9">
            {{ __('Adres zamieszkania') }}
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <div>
              <FormControl
                type="text"
                :label="__('Kod pocztowy')"
                v-model="contact.doc.custom_kod_pocztowy"
                :disabled="!mozeZapisywac"
                @blur="onBlurKodPocztowy"
              />
            </div>
            <div>
              <FormControl
                :type="opcjeMiast.length > 1 ? 'select' : 'text'"
                :options="opcjeMiast.length > 1 ? opcjeMiastSelect : undefined"
                :label="__('Miasto')"
                v-model="contact.doc.custom_miasto"
                :disabled="!mozeZapisywac"
                @blur="opcjeMiast.length <= 1 && zapiszPole('custom_miasto', contact.doc.custom_miasto)"
                @change="opcjeMiast.length > 1 && zapiszPole('custom_miasto', contact.doc.custom_miasto)"
              />
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Ulica')"
                v-model="contact.doc.custom_ulica"
                :disabled="!mozeZapisywac"
                @blur="zapiszPole('custom_ulica', contact.doc.custom_ulica)"
              />
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Nr domu')"
                v-model="contact.doc.custom_nr_domu"
                :disabled="!mozeZapisywac"
                @blur="zapiszPole('custom_nr_domu', contact.doc.custom_nr_domu)"
              />
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Nr mieszkania')"
                v-model="contact.doc.custom_nr_mieszkania"
                :disabled="!mozeZapisywac"
                @blur="zapiszPole('custom_nr_mieszkania', contact.doc.custom_nr_mieszkania)"
              />
            </div>
            <div>
              <FormControl
                type="text"
                :label="__('Województwo')"
                v-model="contact.doc.custom_wojewodztwo"
                :disabled="!mozeZapisywac"
                @blur="zapiszPole('custom_wojewodztwo', contact.doc.custom_wojewodztwo)"
              />
            </div>
            <!-- custom_powiat / custom_gmina are derived from the postal-code
                 lookup, never typed directly — always read-only regardless
                 of write permission (see module docblock). -->
            <div>
              <FormControl type="text" :label="__('Powiat')" :model-value="contact.doc.custom_powiat" disabled />
            </div>
            <div>
              <FormControl type="text" :label="__('Gmina')" :model-value="contact.doc.custom_gmina" disabled />
            </div>
          </div>
        </div>

        <!-- Zgody RODO (podgląd) -->
        <div class="mb-6">
          <div class="mb-1 border-b border-outline-gray-1 pb-2 text-base font-semibold text-ink-gray-9">
            {{ __('Zgody RODO') }}
          </div>
          <div class="mb-3 text-xs text-ink-gray-5">
            {{ __('Zgody edytuje się w formularzu umowy.') }}
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <FormControl
              type="checkbox"
              :label="__('Zgoda na kontakt telefoniczny')"
              :model-value="Boolean(contact.doc.custom_zgoda_telefon)"
              disabled
            />
            <FormControl
              type="checkbox"
              :label="__('Zgoda na działania promocyjne')"
              :model-value="Boolean(contact.doc.custom_zgoda_marketing)"
              disabled
            />
            <FormControl
              type="date"
              :label="__('Data wyrażenia zgody')"
              :model-value="contact.doc.custom_zgoda_data"
              disabled
            />
            <FormControl
              type="text"
              :label="__('Źródło zgody')"
              :model-value="contact.doc.custom_zgoda_zrodlo"
              disabled
            />
          </div>
        </div>

        <!-- Przypisanie — custom_opiekun controls contact visibility
             (crm/permissions/contact_visibility.py); ALWAYS read-only here,
             regardless of the viewer's permlevel-1 write access, so
             reassignment stays a deliberate act elsewhere, not a side
             effect of editing this form. -->
        <div class="mb-2">
          <div class="mb-3 border-b border-outline-gray-1 pb-2 text-base font-semibold text-ink-gray-9">
            {{ __('Przypisanie') }}
          </div>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <FormControl type="text" :label="__('Opiekun')" :model-value="opiekunEtykieta" disabled />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { useDocument } from '@/data/document'
import { usersStore } from '@/stores/users.js'
import { call } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import {
  validateFirstName,
  validateLastName,
  validatePesel,
  validateEmail,
  validatePhone,
  normalizePesel,
  formatPhone,
} from '@/utils/contactValidators'

const props = defineProps({
  contactId: { type: String, required: true },
})

const { document: contact, permissions, error } = useDocument('Contact', props.contactId)
const { getUser } = usersStore()

const bladLadowania = computed(() => {
  if (!error.value) return ''
  return error.value.messages?.[0] || __('Nie udało się wczytać danych klienta.')
})

// Doc-level write permission (same shape/precedent as `canDelete` in
// Contact.vue: `permissions.data?.permissions?.delete`). Fails closed
// while permissions are still loading, same as the existing Delete button.
const mozeZapisywac = computed(() => permissions.data?.permissions?.write || false)

function jestPuste(v) {
  return v === null || v === undefined || String(v).trim() === ''
}

// PESEL is `reqd=1` on Contact — see module docblock for why this has to
// gate every OTHER field's save, not just PESEL's own.
const peselPusty = computed(() => jestPuste(contact.doc?.custom_pesel))

// --- Field specs (plain, untranslated labels — see module docblock) -------
const POLA_DANE_OSOBOWE = [
  { fieldname: 'first_name', label: 'Imię' },
  { fieldname: 'last_name', label: 'Nazwisko' },
  { fieldname: 'custom_pesel', label: 'PESEL' },
]

const WALIDATORY = {
  first_name: validateFirstName,
  last_name: validateLastName,
  custom_pesel: validatePesel,
}

const bledy = reactive({
  first_name: '',
  last_name: '',
  custom_pesel: '',
  email_id: '',
  mobile_no: '',
})

// 'idle' | 'zapisywanie' | 'zapisano' | 'blad' | 'wstrzymany'
const stanZapisu = ref('idle')
const komunikat = ref('')

const pigulka = computed(() => {
  switch (stanZapisu.value) {
    case 'zapisywanie':
      return { text: __('Zapisywanie…'), klasa: 'text-ink-gray-5' }
    case 'zapisano':
      return { text: __('Zapisano'), klasa: 'text-ink-green-6' }
    case 'blad':
      return { text: __('Błąd zapisu'), klasa: 'text-ink-red-6' }
    case 'wstrzymany':
      return { text: __('Zapis wstrzymany'), klasa: 'text-ink-amber-6' }
    default:
      return { text: '', klasa: '' }
  }
})

// PESEL gets an extra visual nudge (via FormControl's own `:error` styling)
// on top of the page-level banner, without inventing bespoke CSS for it —
// same red-outline treatment every other validation error already uses.
function bladPola(fieldname) {
  if (bledy[fieldname]) return bledy[fieldname]
  if (fieldname === 'custom_pesel' && peselPusty.value) {
    return __('Numer PESEL jest wymagany do zapisywania zmian.')
  }
  return ''
}

function zapiszPole(fieldname, wartosc) {
  const waliduj = WALIDATORY[fieldname]
  const blad = waliduj ? waliduj(wartosc) : null
  if (blad) {
    bledy[fieldname] = blad
    return
  }
  bledy[fieldname] = ''

  // Would checkMandatory (inside contact.save.submit) block this anyway
  // because PESEL is still blank? If so, don't even attempt the submit —
  // it would return without calling onSuccess/onError and leave the pill
  // stuck on "Zapisywanie" forever. PESEL's own save is exempt: writing a
  // valid PESEL is exactly what clears the block.
  const peselPoZapisie = fieldname === 'custom_pesel' ? wartosc : contact.doc.custom_pesel
  if (fieldname !== 'custom_pesel' && jestPuste(peselPoZapisie)) {
    stanZapisu.value = 'wstrzymany'
    return
  }

  contact.doc[fieldname] = wartosc
  stanZapisu.value = 'zapisywanie'
  komunikat.value = ''
  contact.save.submit(null, {
    onSuccess: () => {
      stanZapisu.value = 'zapisano'
    },
    onError: (err) => {
      stanZapisu.value = 'blad'
      komunikat.value = err.messages?.[0] || __('Wystąpił błąd zapisu.')
    },
  })
}

// --- Dane osobowe — local refs, never bound straight to contact.doc ------
// See module docblock: a rejected value must never sit in the shared
// `contact.doc`, or the next whole-document save (from any field, in
// either surface) would persist it. Each local ref stays in sync with
// contact.doc via watch (same pattern as emailGlowny/telefonGlowny below)
// and only a value that already passed its validator is copied onto
// contact.doc, immediately before zapiszPole's submit.
const imieLokalne = ref(contact.doc?.first_name || '')
const nazwiskoLokalne = ref(contact.doc?.last_name || '')
const peselLokalny = ref(contact.doc?.custom_pesel || '')

const refyDaneOsobowe = {
  first_name: imieLokalne,
  last_name: nazwiskoLokalne,
  custom_pesel: peselLokalny,
}

watch(
  () => contact.doc?.first_name,
  (v) => {
    imieLokalne.value = v || ''
  },
)
watch(
  () => contact.doc?.last_name,
  (v) => {
    nazwiskoLokalne.value = v || ''
  },
)
watch(
  () => contact.doc?.custom_pesel,
  (v) => {
    peselLokalny.value = v || ''
  },
)

function onBlurDaneOsobowe(fieldname) {
  const wartosc = refyDaneOsobowe[fieldname].value

  if (wartosc === (contact.doc[fieldname] || '')) return

  const waliduj = WALIDATORY[fieldname]
  const blad = waliduj ? waliduj(wartosc) : null
  if (blad) {
    bledy[fieldname] = blad
    return
  }
  bledy[fieldname] = ''

  // PESEL is persisted digits-only — must match what ContactModal.vue
  // sends when creating a contact (normalizePesel), so a contact's PESEL
  // is stored the same way regardless of which form last touched it.
  const wartoscDoZapisu = fieldname === 'custom_pesel' ? normalizePesel(wartosc) : wartosc
  zapiszPole(fieldname, wartoscDoZapisu)
}

// --- Główny e-mail / telefon — derived from email_ids / phone_nos --------
// email_id / mobile_no are read-only rollups of the primary child-table
// row; editing them directly does nothing. Same two API calls the right
// panel already uses (Contact.vue: editOption / createNew), so both
// surfaces stay consistent — then reload so contact.doc (and therefore
// this same singleton doc in the panel) reflects the new primary value.
const emailGlowny = ref(contact.doc?.email_id || '')
const telefonGlowny = ref(contact.doc?.mobile_no || '')

watch(
  () => contact.doc?.email_id,
  (v) => {
    emailGlowny.value = v || ''
  },
)
watch(
  () => contact.doc?.mobile_no,
  (v) => {
    telefonGlowny.value = v || ''
  },
)

function znajdzGlownyEmail() {
  const lista = contact.doc?.email_ids || []
  return (
    lista.find((e) => e.is_primary) ||
    lista.find((e) => e.email_id === contact.doc?.email_id)
  )
}

function znajdzGlownyTelefon() {
  const lista = contact.doc?.phone_nos || []
  return (
    lista.find((p) => p.is_primary_mobile_no) ||
    lista.find((p) => p.phone === contact.doc?.mobile_no)
  )
}

async function onBlurEmailGlowny() {
  const wartosc = emailGlowny.value
  if (wartosc === (contact.doc?.email_id || '')) return

  const blad = validateEmail(wartosc)
  if (blad) {
    bledy.email_id = blad
    return
  }
  bledy.email_id = ''

  if (peselPusty.value) {
    stanZapisu.value = 'wstrzymany'
    return
  }

  stanZapisu.value = 'zapisywanie'
  komunikat.value = ''
  try {
    const istniejacy = znajdzGlownyEmail()
    if (istniejacy) {
      await call('frappe.client.set_value', {
        doctype: 'Contact Email',
        name: istniejacy.name,
        fieldname: 'email_id',
        value: wartosc,
      })
    } else {
      await call('crm.api.contact.create_new', {
        contact: contact.doc.name,
        field: 'email',
        value: wartosc,
      })
    }
    await contact.reload()
    stanZapisu.value = 'zapisano'
  } catch (err) {
    stanZapisu.value = 'blad'
    komunikat.value = err.messages?.[0] || __('Wystąpił błąd zapisu.')
  }
}

async function onBlurTelefonGlowny() {
  const wartosc = telefonGlowny.value
  if (wartosc === (contact.doc?.mobile_no || '')) return

  const blad = validatePhone(wartosc)
  if (blad) {
    bledy.mobile_no = blad
    return
  }
  bledy.mobile_no = ''

  if (peselPusty.value) {
    stanZapisu.value = 'wstrzymany'
    return
  }

  const sformatowany = formatPhone(wartosc)
  stanZapisu.value = 'zapisywanie'
  komunikat.value = ''
  try {
    const istniejacy = znajdzGlownyTelefon()
    if (istniejacy) {
      await call('frappe.client.set_value', {
        doctype: 'Contact Phone',
        name: istniejacy.name,
        fieldname: 'phone',
        value: sformatowany,
      })
    } else {
      await call('crm.api.contact.create_new', {
        contact: contact.doc.name,
        field: 'phone',
        value: sformatowany,
      })
    }
    await contact.reload()
    stanZapisu.value = 'zapisano'
  } catch (err) {
    stanZapisu.value = 'blad'
    komunikat.value = err.messages?.[0] || __('Wystąpił błąd zapisu.')
  }
}

// --- Kod pocztowy → autofill Miasto/Województwo/Powiat/Gmina --------------
// Mirrors ContactModal.vue's onBlur handler exactly (same API, same guard,
// same silent-failure contract) — the only difference is that here the
// autofilled fields are written straight onto the shared `contact.doc`,
// so the immediately-following zapiszPole() call persists them together
// with the postal code in one whole-document save.
const opcjeMiast = ref([])
const opcjeMiastSelect = computed(() => {
  const current = contact.doc?.custom_miasto
  if (!jestPuste(current) && !opcjeMiast.value.includes(current)) {
    return [...opcjeMiast.value, current]
  }
  return opcjeMiast.value
})

watch(
  () => contact.doc?.custom_kod_pocztowy,
  () => {
    opcjeMiast.value = []
  },
)

async function onBlurKodPocztowy() {
  const kod = String(contact.doc?.custom_kod_pocztowy ?? '').trim()
  if (/^\d{2}-\d{3}$/.test(kod)) {
    try {
      const r = await call('volteo_postal_lookup', { pincode: kod })
      if (r && r.found) {
        const cities = r.cities && r.cities.length ? r.cities : r.miejscowosc ? [r.miejscowosc] : []
        if (cities.length > 1) {
          opcjeMiast.value = cities
          if (jestPuste(contact.doc.custom_miasto)) contact.doc.custom_miasto = cities[0]
        } else if (cities.length === 1 && jestPuste(contact.doc.custom_miasto)) {
          contact.doc.custom_miasto = cities[0]
        }
        if (r.wojewodztwo) contact.doc.custom_wojewodztwo = r.wojewodztwo
        if (r.powiat) contact.doc.custom_powiat = r.powiat
        if (r.gmina) contact.doc.custom_gmina = r.gmina
      }
    } catch (e) {
      /* cichy błąd — nieudany lookup nie może blokować użytkownika */
    }
  }
  zapiszPole('custom_kod_pocztowy', contact.doc.custom_kod_pocztowy)
}

// --- Opiekun (read-only display) ------------------------------------------
const opiekunEtykieta = computed(() => {
  const opiekun = contact.doc?.custom_opiekun
  if (!opiekun) return ''
  return getUser(opiekun)?.full_name || opiekun
})
</script>
