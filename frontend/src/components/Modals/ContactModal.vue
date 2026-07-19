<!--
  VOLTEO: explicit "Klient" (Contact) create form — replaces the generic
  FieldLayout/Quick-Entry-driven layout with a hard-coded, inline-validated
  form for the fields the business cares about at creation time: Imię,
  Nazwisko, PESEL, E-mail, Telefon, plus an inline address section (Kod
  pocztowy / Miasto / Ulica / Nr domu / Nr mieszkania) — all required except
  the apartment number. `custom_opiekun` is intentionally never rendered here
  (reps are auto-assigned server-side). See contactValidators.js for the pure
  format validators; duplicate checks for PESEL/E-mail/Telefon go through the
  `volteo_contact_duplicate_check` Server Script API, mirroring the
  `call(name, params)` convention used by KalkulatorTab.vue / AudytTab.vue.
  Kod pocztowy autofills Miasto/gmina/powiat/województwo on blur via the
  `volteo_postal_lookup` API (silent on failure); the derived gmina/powiat/
  województwo fields are not rendered — the After-Save sync hook persists
  everything into a linked Address record from these Contact fields.
-->
<template>
  <Dialog v-model:open="show" :size="'xl'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              {{ __('New Contact') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button
              variant="ghost"
              class="w-7"
              icon="lucide-x"
              @click="show = false"
            />
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <div>
            <FormControl
              type="text"
              :label="__('Imię')"
              required
              v-model="_contact.doc.first_name"
              :error="fieldError('first_name')"
              @blur="onBlur('first_name')"
            />
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('Nazwisko')"
              required
              v-model="_contact.doc.last_name"
              :error="fieldError('last_name')"
              @blur="onBlur('last_name')"
            />
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('PESEL')"
              required
              v-model="_contact.doc.custom_pesel"
              :error="fieldError('custom_pesel')"
              @blur="onBlur('custom_pesel')"
            />
            <div
              v-if="fieldChecking('custom_pesel')"
              class="mt-1 text-xs text-ink-gray-4"
            >
              {{ __('sprawdzanie…') }}
            </div>
          </div>

          <div>
            <FormControl
              type="email"
              :label="__('E-mail')"
              required
              v-model="_contact.doc.email_id"
              :error="fieldError('email_id')"
              @blur="onBlur('email_id')"
            />
            <div
              v-if="fieldChecking('email_id')"
              class="mt-1 text-xs text-ink-gray-4"
            >
              {{ __('sprawdzanie…') }}
            </div>
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('Telefon')"
              required
              v-model="_contact.doc.mobile_no"
              :error="fieldError('mobile_no')"
              @blur="onBlur('mobile_no')"
            />
            <div
              v-if="fieldChecking('mobile_no')"
              class="mt-1 text-xs text-ink-gray-4"
            >
              {{ __('sprawdzanie…') }}
            </div>
          </div>

          <div class="pt-2">
            <div class="mb-3 h-px border-t border-outline-gray-2"></div>
            <div class="text-sm-medium text-ink-gray-5">{{ __('Adres') }}</div>
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('Kod pocztowy')"
              required
              v-model="_contact.doc.custom_kod_pocztowy"
              :error="fieldError('custom_kod_pocztowy')"
              @blur="onBlur('custom_kod_pocztowy')"
            />
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('Miasto')"
              required
              v-model="_contact.doc.custom_miasto"
              :error="fieldError('custom_miasto')"
              @blur="onBlur('custom_miasto')"
            />
          </div>

          <div>
            <FormControl
              type="text"
              :label="__('Ulica')"
              required
              v-model="_contact.doc.custom_ulica"
              :error="fieldError('custom_ulica')"
              @blur="onBlur('custom_ulica')"
            />
          </div>

          <div class="flex gap-4">
            <div class="flex-1">
              <FormControl
                type="text"
                :label="__('Nr domu')"
                required
                v-model="_contact.doc.custom_nr_domu"
                :error="fieldError('custom_nr_domu')"
                @blur="onBlur('custom_nr_domu')"
              />
            </div>
            <div class="flex-1">
              <FormControl
                type="text"
                :label="__('Nr mieszkania')"
                v-model="_contact.doc.custom_nr_mieszkania"
                :error="fieldError('custom_nr_mieszkania')"
                @blur="onBlur('custom_nr_mieszkania')"
              />
            </div>
          </div>
        </div>

        <ErrorMessage v-if="error" class="mt-6" :message="__(error)" />
      </div>
      <div class="px-4 pb-7 pt-4 sm:px-6">
        <div class="space-y-2">
          <Button
            class="w-full"
            variant="solid"
            :label="__('Create')"
            :disabled="!canSubmit"
            :loading="insertContact.loading"
            @click="createContact"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { useDocument } from '@/data/document'
import { useTelemetry } from 'frappe-ui/frappe'
import { call, createResource } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { computed, reactive, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  validateFirstName,
  validateLastName,
  validatePesel,
  validateEmail,
  validatePhone,
  normalizePesel,
  normalizePhone,
  formatPhone,
} from '@/utils/contactValidators'

const props = defineProps({
  contact: { type: Object, default: () => {} },
  options: {
    type: Object,
    default: () => ({ redirect: true, afterInsert: () => {} }),
  },
})

const { capture } = useTelemetry()

const router = useRouter()
const show = defineModel({ type: Boolean })

const error = ref(null)

const { document: _contact, triggerOnBeforeCreate } = useDocument('Contact')

// --- Field / duplicate-check state -----------------------------------------
// Fields that participate in inline validation, in display order. PESEL /
// E-mail / Telefon additionally run a server-side duplicate check.
const FIELDS = ['first_name', 'last_name', 'custom_pesel', 'email_id', 'mobile_no']

// Inline address section — required except the apartment number. No format
// validators (required-only); the linked Address record itself is created
// server-side by the After-Save sync hook from these fields.
const ADDRESS_REQUIRED = [
  'custom_kod_pocztowy',
  'custom_miasto',
  'custom_ulica',
  'custom_nr_domu',
]
const ADDRESS_FIELDS = [...ADDRESS_REQUIRED, 'custom_nr_mieszkania']

const DUP_BACKEND_FIELD = {
  custom_pesel: 'pesel',
  email_id: 'email',
  mobile_no: 'phone',
}

const DUP_MESSAGES = {
  custom_pesel: __('Ten numer PESEL już istnieje w systemie.'),
  email_id: __('Ten adres e-mail już istnieje w systemie.'),
  mobile_no: __('Ten numer telefonu już istnieje w systemie.'),
}

const touched = reactive({
  first_name: false,
  last_name: false,
  custom_pesel: false,
  email_id: false,
  mobile_no: false,
  custom_kod_pocztowy: false,
  custom_miasto: false,
  custom_ulica: false,
  custom_nr_domu: false,
  custom_nr_mieszkania: false,
})

// Server-side error surfaced by the Before-Save guard (backstop), mapped
// back onto a specific field when the message concept matches one.
const serverFieldError = reactive({
  first_name: null,
  last_name: null,
  custom_pesel: null,
  email_id: null,
  mobile_no: null,
})

// 'idle' | 'checking' | 'ok' | 'duplicate' | 'error'
const dupStatus = reactive({
  custom_pesel: 'idle',
  email_id: 'idle',
  mobile_no: 'idle',
})
// The normalized value the current dupStatus[field] actually applies to —
// lets us skip a redundant re-check when nothing changed since last time.
const dupCheckedValue = reactive({
  custom_pesel: null,
  email_id: null,
  mobile_no: null,
})

function isEmpty(v) {
  return v === null || v === undefined || String(v).trim() === ''
}

const formatErrors = computed(() => ({
  first_name: validateFirstName(_contact.doc.first_name),
  last_name: validateLastName(_contact.doc.last_name),
  custom_pesel: validatePesel(_contact.doc.custom_pesel),
  email_id: validateEmail(_contact.doc.email_id),
  mobile_no: validatePhone(_contact.doc.mobile_no),
}))

function fieldError(field) {
  if (!touched[field] && !serverFieldError[field]) return ''
  if (formatErrors.value[field]) return formatErrors.value[field]
  if (serverFieldError[field]) return serverFieldError[field]
  if (DUP_MESSAGES[field] && dupStatus[field] === 'duplicate') {
    return DUP_MESSAGES[field]
  }
  return ''
}

function fieldChecking(field) {
  return DUP_MESSAGES[field] ? dupStatus[field] === 'checking' : false
}

function dupNormalizedValue(field) {
  const raw = _contact.doc[field]
  if (field === 'email_id') return String(raw ?? '').trim().toLowerCase()
  if (field === 'custom_pesel') return normalizePesel(raw)
  if (field === 'mobile_no') return normalizePhone(raw)
  return raw
}

function resetDupStatus(field) {
  dupStatus[field] = 'idle'
  dupCheckedValue[field] = null
}

async function performDuplicateCheck(field) {
  if (formatErrors.value[field]) {
    resetDupStatus(field)
    return
  }
  const value = dupNormalizedValue(field)
  if (!value) {
    resetDupStatus(field)
    return
  }
  if (
    dupCheckedValue[field] === value &&
    (dupStatus[field] === 'ok' || dupStatus[field] === 'duplicate')
  ) {
    return
  }

  dupStatus[field] = 'checking'
  try {
    const res = await call('volteo_contact_duplicate_check', {
      field: DUP_BACKEND_FIELD[field],
      value,
    })
    // The value may have changed again while the request was in flight —
    // don't apply a stale result to whatever is in the box now.
    if (dupNormalizedValue(field) !== value) return
    dupCheckedValue[field] = value
    dupStatus[field] = res?.duplicate ? 'duplicate' : 'ok'
  } catch (err) {
    if (dupNormalizedValue(field) !== value) return
    // Failed check = not-yet-valid. Submit stays blocked; no scary inline
    // error is shown (network hiccups shouldn't look like a data problem).
    dupStatus[field] = 'error'
  }
}

// One debounced wrapper per field (not shared) so blurring two different
// fields in quick succession doesn't cancel each other's pending check.
const debouncedDupCheck = {
  custom_pesel: useDebounceFn(() => performDuplicateCheck('custom_pesel'), 400),
  email_id: useDebounceFn(() => performDuplicateCheck('email_id'), 400),
  mobile_no: useDebounceFn(() => performDuplicateCheck('mobile_no'), 400),
}

async function onBlur(field) {
  touched[field] = true
  serverFieldError[field] = null

  // Auto-format a valid phone number on blur only — never mid-typing, and
  // never when invalid (so the inline error shows against what was typed).
  if (
    field === 'mobile_no' &&
    !isEmpty(_contact.doc.mobile_no) &&
    !validatePhone(_contact.doc.mobile_no)
  ) {
    _contact.doc.mobile_no = formatPhone(_contact.doc.mobile_no)
  }

  // Postal-code autofill — mirrors the existing CRM Form Script. A failed or
  // no-match lookup must never block the user, so all errors are silent.
  if (
    field === 'custom_kod_pocztowy' &&
    /^\d{2}-\d{3}$/.test(String(_contact.doc.custom_kod_pocztowy ?? '').trim())
  ) {
    try {
      const r = await call('volteo_postal_lookup', {
        pincode: _contact.doc.custom_kod_pocztowy.trim(),
      })
      if (r && r.found) {
        const cities = r.cities && r.cities.length
          ? r.cities
          : r.miejscowosc
            ? [r.miejscowosc]
            : []
        if (cities.length === 1 && isEmpty(_contact.doc.custom_miasto)) {
          _contact.doc.custom_miasto = cities[0]
        }
        if (r.wojewodztwo) _contact.doc.custom_wojewodztwo = r.wojewodztwo
        if (r.powiat) _contact.doc.custom_powiat = r.powiat
        if (r.gmina) _contact.doc.custom_gmina = r.gmina
      }
    } catch (e) {
      /* silent — lookup failure must not block the user */
    }
  }

  if (!DUP_BACKEND_FIELD[field]) return
  if (formatErrors.value[field] || isEmpty(_contact.doc[field])) {
    resetDupStatus(field)
    return
  }
  debouncedDupCheck[field]()
}

// Any edit invalidates a previously-resolved duplicate-check result for that
// field — it needs to be re-checked against the new value on the next blur.
watch(() => _contact.doc.custom_pesel, () => resetDupStatus('custom_pesel'))
watch(() => _contact.doc.email_id, () => resetDupStatus('email_id'))
watch(() => _contact.doc.mobile_no, () => resetDupStatus('mobile_no'))

const hasMissingRequired = computed(() =>
  [...FIELDS, ...ADDRESS_REQUIRED].some((f) => isEmpty(_contact.doc[f])),
)
const hasFormatError = computed(() =>
  FIELDS.some((f) => !!formatErrors.value[f]),
)
const hasDuplicateError = computed(() =>
  Object.keys(DUP_MESSAGES).some((f) => dupStatus[f] === 'duplicate'),
)
const dupChecksPending = computed(() =>
  Object.keys(DUP_MESSAGES).some((f) => {
    if (isEmpty(_contact.doc[f]) || formatErrors.value[f]) return false
    return dupStatus[f] !== 'ok'
  }),
)
// A still-showing Before-Save-guard rejection blocks resubmission until the
// user actually edits (and blurs) the flagged field — otherwise Create would
// re-enable immediately and let them replay the exact same failing payload.
const hasServerFieldError = computed(() => FIELDS.some((f) => !!serverFieldError[f]))

const canSubmit = computed(
  () =>
    !hasMissingRequired.value &&
    !hasFormatError.value &&
    !hasDuplicateError.value &&
    !dupChecksPending.value &&
    !hasServerFieldError.value,
)

// --- Server-side error → field mapping (Before-Save guard is a backstop) ---
const SERVER_ERROR_FIELD_MATCHERS = [
  ['custom_pesel', /pesel/i],
  ['email_id', /e-?mail/i],
  ['mobile_no', /telefon|numer telefonu|phone/i],
]

function mapServerErrorToField(message) {
  if (!message) return null
  const hit = SERVER_ERROR_FIELD_MATCHERS.find(([, re]) => re.test(message))
  return hit ? hit[0] : null
}

const insertContact = createResource({
  url: 'frappe.client.insert',
  onSuccess: (doc) => {
    capture('contact_created')
    handleContactUpdate(doc)
    _contact.doc = {}
  },
  onError: (err) => {
    const message =
      err.error?.messages?.[0] ||
      err.messages?.[0] ||
      err.message ||
      __('Wystąpił błąd - spróbuj ponownie')
    const mappedField = mapServerErrorToField(message)
    if (mappedField) {
      serverFieldError[mappedField] = message
      touched[mappedField] = true
      error.value = null
    } else {
      error.value = message
    }
  },
})

async function createContact() {
  error.value = null
  ;[...FIELDS, ...ADDRESS_FIELDS].forEach((f) => (touched[f] = true))

  if (!canSubmit.value) return

  if (_contact.doc.email_id) {
    _contact.doc.email_ids = [
      { email_id: _contact.doc.email_id, is_primary: 1 },
    ]
    delete _contact.doc.email_id
  }

  if (_contact.doc.mobile_no) {
    _contact.doc.phone_nos = [
      { phone: _contact.doc.mobile_no, is_primary_mobile_no: 1 },
    ]
    delete _contact.doc.mobile_no
  }

  await triggerOnBeforeCreate?.()

  insertContact.submit({
    doc: {
      doctype: 'Contact',
      ..._contact.doc,
    },
  })
}

function handleContactUpdate(doc) {
  props.contact?.reload?.()
  if (doc.name && props.options.redirect) {
    router.push({
      name: 'Contact',
      params: { contactId: doc.name },
    })
  }
  show.value = false
  props.options.afterInsert?.(doc)
}

onMounted(() => {
  _contact.doc = {}
  Object.assign(_contact.doc, props.contact.data || props.contact)
})
</script>
