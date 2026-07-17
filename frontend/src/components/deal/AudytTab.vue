<!--
  Audyt tab (Szansa view) — variant-driven technical audit form, 1:1 with the
  deal (Volteo Audyt, name == dealId). The whole form (sections/fields/photo
  slots) is server-driven via `volteo_audyt_requirements`, keyed by the chosen
  `rodzaj_instalacji`. Draft state autosaves (debounced for fields, immediate
  for photos); submit locks the record server-side.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <!-- Loading -->
      <div
        v-if="audyt.loading || reqLoading"
        class="py-16 text-center text-base text-ink-gray-5"
      >
        {{ __('Ładowanie…') }}
      </div>

      <!-- Requirements failed to load — bail out, never render a misleading state -->
      <div
        v-else-if="reqError"
        class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
      >
        {{ reqError }}
      </div>

      <!-- No audit yet -->
      <div
        v-else-if="!exists"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <AudytIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak audytu') }}</div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{ __('Wybierz rodzaj instalacji, aby rozpocząć audyt techniczny.') }}
        </div>
        <div class="w-64">
          <FormControl
            type="select"
            :options="['', ...requirements.variants]"
            :placeholder="__('Rodzaj instalacji')"
            :disabled="creating"
            v-model="newVariant"
          />
        </div>
      </div>

      <!-- Audit form (draft, legacy-variant, or locked) -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="text-lg font-semibold text-ink-gray-8">{{ __('Audyt techniczny') }}</div>
            <Badge
              :theme="locked ? 'green' : 'amber'"
              variant="subtle"
              size="sm"
              :label="locked ? __('Zatwierdzony') : __('Szkic')"
            />
          </div>
          <div class="flex items-center gap-3">
            <span v-if="!readOnly && saveState === 'saving'" class="text-xs text-ink-gray-4">
              {{ __('Zapisywanie…') }}
            </span>
            <span v-else-if="!readOnly && saveState === 'saved'" class="text-xs text-ink-green-6">
              {{ __('Zapisano') }} ✓
            </span>
            <span v-else-if="!readOnly && saveState === 'error'" class="text-xs text-ink-red-6">
              {{ __('Błąd zapisu') }}
            </span>
            <Button
              v-if="locked && requirements.can_reopen"
              :label="__('Przywróć do edycji')"
              :loading="reopening"
              @click="reopenAudyt"
            />
            <Button
              v-if="!locked && !legacyVariant"
              variant="solid"
              :label="__('Zatwierdź audyt')"
              :disabled="!complete || submitting"
              :loading="submitting"
              @click="submitAudyt"
            />
          </div>
        </div>

        <!-- Locked banner -->
        <div
          v-if="locked"
          class="rounded-lg border border-outline-green-3 bg-surface-green-2 px-4 py-3 text-sm text-ink-green-8"
        >
          {{
            __('Audyt zatwierdzony przez {0} · {1}', [
              row?.zatwierdzony_przez || '—',
              fmtDate(row?.zatwierdzony_dnia),
            ])
          }}
        </div>

        <!-- Legacy variant banner -->
        <div
          v-if="legacyVariant"
          class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-4 py-3 text-sm text-ink-amber-8"
        >
          {{
            __('Rodzaj instalacji „{0}” nie jest już obsługiwany — wybierz ponownie.', [
              form.rodzaj_instalacji,
            ])
          }}
        </div>

        <!-- Variant picker (always visible once the audit exists) -->
        <div class="w-full sm:max-w-xs">
          <FormControl
            type="select"
            :label="__('Rodzaj instalacji')"
            :options="['', ...requirements.variants]"
            :disabled="readOnly"
            v-model="form.rodzaj_instalacji"
          />
        </div>

        <template v-if="variantDef">
          <div class="text-sm text-ink-gray-5">
            {{ __('Pola') }}: {{ fieldsDone }}/{{ fieldsTotal }} · {{ __('Zdjęcia') }}: {{ photosDone }}/{{ photosTotal }}
          </div>

          <section v-for="sec in variantDef.sections" :key="sec.label">
            <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
              {{ sec.label }}
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div
                v-for="f in sec.fields"
                :key="f.fieldname"
                :class="[
                  'rounded',
                  f.required && !fieldOk(f) ? 'ring-1 ring-outline-red-3' : '',
                ]"
              >
                <FormControl
                  :type="f.type"
                  :label="f.label"
                  :options="f.options"
                  :step="f.step"
                  :required="!!f.required"
                  :disabled="readOnly"
                  v-model="form[f.fieldname]"
                />
              </div>
            </div>
          </section>

          <section>
            <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
              {{ __('Dokumentacja zdjęciowa') }} ({{ photosDone }}/{{ photosTotal }})
            </div>
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <AudytPhotoSlot
                v-for="slot in variantDef.photo_slots"
                :key="slot.key"
                :label="slot.label"
                :value="zdjecia[slot.key] || null"
                doctype="Volteo Audyt"
                :docname="dealId"
                :disabled="readOnly"
                @change="(url) => onPhotoChange(slot.key, url)"
              />
            </div>
          </section>
        </template>

        <div>
          <FormControl
            type="textarea"
            :label="__('Uwagi technika')"
            :disabled="readOnly"
            v-model="form.uwagi"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import AudytIcon from '@/components/Icons/AudytIcon.vue'
import AudytPhotoSlot from '@/components/deal/AudytPhotoSlot.vue'
import { useAttachments } from '@/composables/useAttachments'
import { Badge, Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Mutable timers/snapshots (plain vars — declared before any `immediate`
// watcher so they're initialised before first use, no TDZ surprises). -------
let saveTimer = null
let lastSavedFieldsPayload = ''

// --- Requirements (server-driven form definition) ---------------------------
const requirements = reactive({
  variants: [],
  matrix: {},
  locked_status: 'Zatwierdzony',
  can_reopen: false,
  can_edit: true,
})
const reqLoading = ref(true)
const reqError = ref('')

onMounted(loadRequirements)

async function loadRequirements() {
  reqLoading.value = true
  reqError.value = ''
  try {
    const data = await call('volteo_audyt_requirements')
    requirements.variants = data?.variants || []
    requirements.matrix = data?.matrix || {}
    requirements.locked_status = data?.locked_status || 'Zatwierdzony'
    requirements.can_reopen = !!data?.can_reopen
    requirements.can_edit = data?.can_edit !== false
  } catch (err) {
    reqError.value = extractErrorMessage(err)
  } finally {
    reqLoading.value = false
  }
}

// All field names known across every variant — used to hydrate `form` from
// the raw row without pulling in Frappe meta fields. Hidden-variant values
// stay populated even while another variant is selected (they're simply not
// rendered), so switching back doesn't lose data.
const allFieldnames = computed(() => {
  const set = new Set()
  Object.values(requirements.matrix || {}).forEach((def) => {
    ;(def?.sections || []).forEach((sec) => {
      ;(sec?.fields || []).forEach((f) => {
        if (f?.fieldname) set.add(f.fieldname)
      })
    })
  })
  return set
})

// --- Audit record ------------------------------------------------------------
const audyt = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Volteo Audyt',
    filters: { deal: props.dealId },
    fields: ['*'],
    limit_page_length: 1,
  },
  auto: true,
})

const row = computed(() => audyt.data?.[0] || null)
const exists = computed(() => !!row.value?.name)
const locked = computed(() => exists.value && row.value?.status === requirements.locked_status)
const readOnly = computed(() => locked.value || !requirements.can_edit)

// --- Local editable state ----------------------------------------------------
const form = reactive({ rodzaj_instalacji: '', uwagi: '' })
const zdjecia = reactive({})
const hydrating = ref(true)
const saveState = ref('idle') // idle | saving | saved | error

const newVariant = ref('') // bound to the "create audit" picker only
const creating = ref(false)
const submitting = ref(false)
const reopening = ref(false)

const { trackOldFile, processPendingDeletions } = useAttachments('Volteo Audyt', props.dealId)

const variantDef = computed(() => requirements.matrix?.[form.rodzaj_instalacji] || null)
const legacyVariant = computed(
  () => exists.value && !!form.rodzaj_instalacji && !variantDef.value,
)

// Hydrate `form`/`zdjecia` whenever the row or the requirements (needed to
// know which field names are legit) change. Guarded so the deep autosave
// watcher below never fires from hydration itself.
watch(
  () => [row.value, reqLoading.value],
  () => {
    if (reqLoading.value) return
    hydrateForm(row.value)
  },
  { immediate: true },
)

function hydrateForm(r) {
  hydrating.value = true
  saveState.value = 'idle'

  Object.keys(form).forEach((k) => delete form[k])
  form.rodzaj_instalacji = r?.rodzaj_instalacji || ''
  form.uwagi = r?.uwagi || ''
  allFieldnames.value.forEach((fn) => {
    if (r && r[fn] !== undefined && r[fn] !== null) form[fn] = r[fn]
  })

  Object.keys(zdjecia).forEach((k) => delete zdjecia[k])
  if (r?.zdjecia_json) {
    try {
      const parsed = JSON.parse(r.zdjecia_json)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        Object.assign(zdjecia, parsed)
      }
    } catch (e) {
      // malformed JSON on the row — start from an empty map rather than crash
    }
  }

  lastSavedFieldsPayload = JSON.stringify(currentFieldsPayload())
  nextTick(() => {
    hydrating.value = false
  })
}

// --- Field rules / progress ---------------------------------------------------
function fieldOk(f) {
  const v = form[f.fieldname]
  if (f.rule === 'positive') return Number(v) > 0
  return String(v ?? '').trim() !== ''
}

const requiredFields = computed(() => {
  if (!variantDef.value) return []
  return (variantDef.value.sections || []).flatMap((s) => s.fields || []).filter((f) => f.required)
})
const fieldsTotal = computed(() => requiredFields.value.length)
const fieldsDone = computed(() => requiredFields.value.filter((f) => fieldOk(f)).length)

const photoSlots = computed(() => variantDef.value?.photo_slots || [])
const photosTotal = computed(() => photoSlots.value.length)
const photosDone = computed(() => photoSlots.value.filter((s) => !!zdjecia[s.key]).length)

const complete = computed(
  () =>
    !!variantDef.value &&
    fieldsDone.value === fieldsTotal.value &&
    photosDone.value === photosTotal.value,
)

// --- Autosave (fields) --------------------------------------------------------
function currentFieldsPayload() {
  const payload = { rodzaj_instalacji: form.rodzaj_instalacji || '', uwagi: form.uwagi || '' }
  if (variantDef.value) {
    ;(variantDef.value.sections || []).forEach((sec) => {
      ;(sec.fields || []).forEach((f) => {
        payload[f.fieldname] = form[f.fieldname] ?? ''
      })
    })
  }
  return payload
}

watch(
  form,
  () => {
    if (hydrating.value || readOnly.value || !exists.value) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(saveFields, 500)
  },
  { deep: true },
)

async function saveFields() {
  const payload = currentFieldsPayload()
  const payloadStr = JSON.stringify(payload)
  if (payloadStr === lastSavedFieldsPayload) return
  saveState.value = 'saving'
  try {
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt',
      name: props.dealId,
      fieldname: payload,
    })
    lastSavedFieldsPayload = payloadStr
    saveState.value = 'saved'
  } catch (err) {
    saveState.value = 'error'
    toast.error(extractErrorMessage(err))
  }
}

// --- Photos (immediate save) --------------------------------------------------
async function onPhotoChange(key, fileUrl) {
  if (readOnly.value) return
  const oldUrl = zdjecia[key] || null
  trackOldFile(oldUrl, fileUrl)
  if (fileUrl) zdjecia[key] = fileUrl
  else delete zdjecia[key]

  try {
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt',
      name: props.dealId,
      fieldname: { zdjecia_json: JSON.stringify(zdjecia) },
    })
    processPendingDeletions()
  } catch (err) {
    if (oldUrl) zdjecia[key] = oldUrl
    else delete zdjecia[key]
    toast.error(extractErrorMessage(err))
  }
}

// --- Create / submit / reopen -------------------------------------------------
watch(newVariant, (v) => {
  if (v) createAudyt(v)
})

async function createAudyt(variant) {
  creating.value = true
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Volteo Audyt',
        deal: props.dealId,
        status: 'Niekompletny',
        rodzaj_instalacji: variant,
      },
    })
    await audyt.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
    newVariant.value = ''
  } finally {
    creating.value = false
  }
}

async function submitAudyt() {
  if (!complete.value || submitting.value) return
  submitting.value = true
  try {
    await call('volteo_audyt_submit', { deal: props.dealId })
    toast.success(__('Audyt zatwierdzony'))
    await audyt.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    submitting.value = false
  }
}

async function reopenAudyt() {
  reopening.value = true
  try {
    await call('volteo_audyt_reopen', { deal: props.dealId })
    toast.success(__('Audyt przywrócony do edycji'))
    await audyt.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    reopening.value = false
  }
}

// --- Helpers -------------------------------------------------------------------
function fmtDate(dt) {
  if (!dt) return '—'
  return String(dt).slice(0, 16).replace('T', ' ')
}

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
