<!--
  Audyt tab (Szansa view) — variant-driven technical audit form, 1:1 with the
  deal (Volteo Audyt, name == dealId). The whole form (sections/fields/photo
  slots) is server-driven via `volteo_audyt_requirements`, keyed by the chosen
  `rodzaj_instalacji`.

  3-stage workflow:
    Szkic (draft, editable by rep/admin) →
    Weryfikacja (submitted; back office/admin can edit fields in place while
      the audit is under review) →
    Zatwierdzony (approved, read-only; back office/admin may reopen it via
      "Przywróć do edycji").
  Autosave (debounced for fields, immediate for photos) runs both for the
  rep's Szkic draft and for back office edits made during Weryfikacja. The
  rep submits Szkic→Weryfikacja; back office (can_review) edits in place and
  approves — there is no "send back for corrections" step anymore. A native
  Comment thread is available once the audit exists.
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

      <!-- Audit form (draft / verification / approved) -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="text-lg font-semibold text-ink-gray-8">{{ __('Audyt techniczny') }}</div>
              <Badge
                :theme="badgeTheme"
                variant="subtle"
                size="lg"
                :label="status"
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

              <!-- Rep: submit draft to verification -->
              <Button
                v-if="requirements.is_rep && isDraft"
                variant="solid"
                :label="__('Prześlij audyt do weryfikacji')"
                :disabled="!complete || submitting"
                :loading="submitting"
                @click="submitAudyt"
              />

              <!-- Back office: status control -->
              <template v-if="canReview">
                <Button
                  v-if="isReview"
                  variant="solid"
                  theme="green"
                  :label="__('Zatwierdź audyt')"
                  :loading="statusUpdating"
                  @click="setStatus('Zatwierdzony')"
                />
                <Button
                  v-else-if="isApproved"
                  :label="__('Przywróć do edycji')"
                  :loading="statusUpdating"
                  @click="setStatus('Szkic')"
                />
              </template>
            </div>
          </div>

          <!-- Submit helper — draft not yet complete -->
          <div v-if="isDraft && !complete" class="text-xs text-ink-amber-6">
            {{ __('Musisz wypełnić wszystkie wymagane pola i zdjęcia, aby przesłać audyt do weryfikacji.') }}
          </div>
        </div>

        <!-- Approved banner -->
        <div
          v-if="isApproved"
          class="rounded-lg border border-outline-green-3 bg-surface-green-2 px-4 py-3 text-sm text-ink-green-8"
        >
          {{
            __('Audyt zatwierdzony przez {0} · {1}', [
              row?.zatwierdzony_przez || '—',
              fmtDate(row?.zatwierdzony_dnia),
            ])
          }}
        </div>

        <!-- Verification (Weryfikacja) banner -->
        <div
          v-if="isReview"
          class="rounded-lg border border-outline-blue-2 bg-surface-blue-2 px-4 py-3 text-sm text-ink-blue-8"
        >
          {{
            canReview
              ? __('Audyt w weryfikacji — możesz edytować pola bezpośrednio, a następnie zatwierdzić.')
              : __('Audyt oczekuje na weryfikację przez back office — pola są zablokowane do czasu decyzji.')
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
                v-for="f in visibleFields(sec)"
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
                v-for="slot in visiblePhotoSlots"
                :key="slot.key"
                :label="slot.label"
                :value="zdjecia[slot.key] || null"
                :optional="!isPhotoRequired(slot)"
                :allow-pdf="!!slot.pdf"
                doctype="Volteo Audyt"
                :docname="dealId"
                :disabled="readOnly"
                @change="(url) => onPhotoChange(slot.key, url)"
              />
            </div>

            <!-- Additional (optional) photos -->
            <div v-if="editable || zdjeciaDodatkowe.length" class="mt-5">
              <div class="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                {{ __('Zdjęcia dodatkowe (opcjonalne, maks. 5)') }}
              </div>
              <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <AudytPhotoSlot
                  v-for="(url, idx) in zdjeciaDodatkowe"
                  :key="'extra-' + idx + '-' + url"
                  :label="__('Zdjęcie dodatkowe')"
                  :value="url"
                  doctype="Volteo Audyt"
                  :docname="dealId"
                  :disabled="readOnly"
                  @change="(u) => onExtraPhotoChange(idx, u)"
                />
                <AudytPhotoSlot
                  v-if="editable && zdjeciaDodatkowe.length < 5"
                  :key="'extra-new-' + zdjeciaDodatkowe.length"
                  :label="__('Zdjęcie dodatkowe')"
                  :value="null"
                  doctype="Volteo Audyt"
                  :docname="dealId"
                  :disabled="false"
                  @change="onExtraPhotoAdd"
                />
              </div>
            </div>
          </section>
        </template>

        <!-- Comment thread (available once the audit exists — all users) -->
        <section class="border-t border-outline-gray-2 pt-6">
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ __('Komentarze') }}
          </div>

          <div
            v-if="commentsResource.data && commentsResource.data.length"
            class="flex flex-col gap-3"
          >
            <div
              v-for="c in commentsResource.data"
              :key="c.name"
              class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2"
            >
              <div class="mb-1 flex items-center justify-between gap-2">
                <span class="text-xs font-medium text-ink-gray-7">
                  {{ c.comment_by || c.comment_email }}
                </span>
                <span class="text-xs text-ink-gray-4">{{ fmtDate(c.creation) }}</span>
              </div>
              <div class="whitespace-pre-wrap text-sm text-ink-gray-7">
                {{ commentText(c.content) }}
              </div>
              <div
                v-if="commentAttachments[c.name]?.length"
                class="mt-2 flex flex-wrap gap-2"
              >
                <AttachmentItem
                  v-for="a in commentAttachments[c.name]"
                  :key="a.name"
                  :label="a.file_name || __('Załącznik')"
                  :url="a.file_url"
                />
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-ink-gray-5">{{ __('Brak komentarzy.') }}</div>

          <div class="mt-3 flex flex-col gap-2">
            <FormControl
              type="textarea"
              :placeholder="__('Napisz komentarz…')"
              v-model="newComment"
            />
            <div
              v-if="newCommentAttachments.length"
              class="flex flex-wrap gap-2"
            >
              <AttachmentItem
                v-for="(a, idx) in newCommentAttachments"
                :key="a.name"
                :label="a.file_name || __('Załącznik')"
              >
                <template #suffix>
                  <span
                    class="lucide-x h-3.5"
                    aria-hidden="true"
                    @click.stop="removeNewCommentAttachment(idx)"
                  />
                </template>
              </AttachmentItem>
            </div>
            <div class="flex items-center justify-between gap-2">
              <FileUploader
                :upload-args="{
                  doctype: 'Volteo Audyt',
                  docname: dealId,
                  private: true,
                }"
                @success="(f) => newCommentAttachments.push(f)"
              >
                <template #default="{ openFileSelector }">
                  <Button
                    :label="__('Dołącz plik')"
                    variant="subtle"
                    :iconLeft="AttachmentIcon"
                    @click="openFileSelector()"
                  />
                </template>
              </FileUploader>
              <Button
                variant="solid"
                :label="__('Dodaj komentarz')"
                :disabled="!newComment.trim() || posting"
                :loading="posting"
                @click="postComment"
              />
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ __('Do komentarza możesz dołączyć zdjęcie lub plik.') }}
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import AttachmentItem from '@/components/AttachmentItem.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import AudytIcon from '@/components/Icons/AudytIcon.vue'
import AudytPhotoSlot from '@/components/deal/AudytPhotoSlot.vue'
import { useAttachments } from '@/composables/useAttachments'
import { Badge, Button, FileUploader, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Mutable timers/snapshots (plain vars — declared before any `immediate`
// watcher so they're initialised before first use, no TDZ surprises). -------
let saveTimer = null
let lastSavedFieldsPayload = ''

// --- Requirements (server-driven form definition + permissions) -------------
const requirements = reactive({
  variants: [],
  matrix: {},
  statuses: [],
  is_rep: false,
  is_backend: false,
  is_admin: false,
  can_review: false,
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
    requirements.statuses = data?.statuses || []
    requirements.is_rep = !!data?.is_rep
    requirements.is_backend = !!data?.is_backend
    requirements.is_admin = !!data?.is_admin
    requirements.can_review = !!data?.can_review
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

// --- Status / permission state ----------------------------------------------
const status = computed(() => row.value?.status || 'Szkic')
const isDraft = computed(() => status.value === 'Szkic')
const isReview = computed(() => status.value === 'Weryfikacja')
const isApproved = computed(() => status.value === 'Zatwierdzony')

// Back office/admin may approve, reopen an approved audit, and — now — edit
// the audit in place while it sits in Weryfikacja.
const canReview = computed(() => !!requirements.can_review)

// Fields/photos are editable in Szkic by rep/admin (can_edit), and in
// Weryfikacja by back office/admin (canReview) — a reviewer edits the audit
// directly instead of sending it back to the rep for corrections.
const editable = computed(
  () => (requirements.can_edit && isDraft.value) || (canReview.value && isReview.value),
)
const readOnly = computed(() => !editable.value)

const badgeTheme = computed(() =>
  isApproved.value ? 'green' : isReview.value ? 'blue' : 'amber',
)

// --- Local editable state ----------------------------------------------------
const form = reactive({ rodzaj_instalacji: '', uwagi: '' })
const zdjecia = reactive({})
const zdjeciaDodatkowe = ref([])
const hydrating = ref(true)
const saveState = ref('idle') // idle | saving | saved | error

const newVariant = ref('') // bound to the "create audit" picker only
const creating = ref(false)
const submitting = ref(false)
const statusUpdating = ref(false)

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

  zdjeciaDodatkowe.value = []
  if (r?.zdjecia_dodatkowe_json) {
    try {
      const parsed = JSON.parse(r.zdjecia_dodatkowe_json)
      if (Array.isArray(parsed)) {
        zdjeciaDodatkowe.value = parsed.filter((u) => typeof u === 'string' && u)
      }
    } catch (e) {
      // malformed JSON — start from an empty list rather than crash
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
  return (variantDef.value.sections || [])
    .flatMap((s) => s.fields || [])
    .filter((f) => f.required && depOk(f))
})
const fieldsTotal = computed(() => requiredFields.value.length)
const fieldsDone = computed(() => requiredFields.value.filter((f) => fieldOk(f)).length)

const photoSlots = computed(() => variantDef.value?.photo_slots || [])
// A slot with no `required` key at all (the currently deployed server matrix)
// is treated as required for backward compatibility — inverting this would
// silently turn every existing mandatory photo optional on the live site.
function isPhotoRequired(slot) {
  return slot.required === undefined || !!slot.required
}

// Brak `depends_on` (obecnie wdrożona macierz serwerowa) = element zawsze widoczny.
// Odwrócenie tego ukryłoby po cichu wszystkie dzisiejsze pola i zdjęcia.
function depOk(item) {
  const dep = item.depends_on
  if (!dep) return true
  return form[dep.fieldname] === dep.value
}

// Vue 3: `v-if` na tym samym węźle co `v-for` liczy się PRZED powstaniem
// zmiennej pętli (odwrotnie niż w Vue 2) — `depOk(f)` wywalałoby renderowanie
// z TypeError, bo `f` jeszcze by nie istniało. Filtrujemy więc w skrypcie i w
// szablonie robimy tylko `v-for="f in visibleFields(sec)"`, bez `v-if`.
function visibleFields(sec) {
  return (sec.fields || []).filter(depOk)
}

// Ukrytych wartości nie czyścimy: usunięcie zdjęcia oznaczałoby usunięcie pliku przez useAttachments/trackOldFile,
// a backend pomija ukryte elementy przy walidacji, więc wartości przetrwają przełączanie zależności.
const visiblePhotoSlots = computed(() => photoSlots.value.filter(depOk))
const requiredPhotoSlots = computed(() => visiblePhotoSlots.value.filter(isPhotoRequired))
const photosTotal = computed(() => requiredPhotoSlots.value.length)
const photosDone = computed(() => requiredPhotoSlots.value.filter((s) => !!zdjecia[s.key]).length)

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

// --- Additional photos (immediate save, immutable list updates) --------------
async function persistExtraPhotos(prevList) {
  try {
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt',
      name: props.dealId,
      fieldname: { zdjecia_dodatkowe_json: JSON.stringify(zdjeciaDodatkowe.value) },
    })
    processPendingDeletions()
  } catch (err) {
    zdjeciaDodatkowe.value = prevList
    toast.error(extractErrorMessage(err))
  }
}

async function onExtraPhotoChange(index, fileUrl) {
  if (readOnly.value) return
  const prevList = zdjeciaDodatkowe.value
  const oldUrl = prevList[index] || null
  trackOldFile(oldUrl, fileUrl)
  const nextList = fileUrl
    ? prevList.map((u, i) => (i === index ? fileUrl : u))
    : prevList.filter((_, i) => i !== index)
  zdjeciaDodatkowe.value = nextList
  await persistExtraPhotos(prevList)
}

async function onExtraPhotoAdd(fileUrl) {
  if (readOnly.value || !fileUrl) return
  if (zdjeciaDodatkowe.value.length >= 5) return
  const prevList = zdjeciaDodatkowe.value
  trackOldFile(null, fileUrl)
  zdjeciaDodatkowe.value = [...prevList, fileUrl]
  await persistExtraPhotos(prevList)
}

// --- Create / submit / status -------------------------------------------------
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
        status: 'Szkic',
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
    toast.success(__('Audyt przesłany do weryfikacji'))
    await audyt.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    submitting.value = false
  }
}

async function setStatus(s) {
  if (statusUpdating.value) return
  statusUpdating.value = true
  try {
    await call('volteo_audyt_set_status', { deal: props.dealId, status: s })
    toast.success(__('Status audytu zaktualizowany'))
    await audyt.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    statusUpdating.value = false
  }
}

// --- Comments ----------------------------------------------------------------
const commentsResource = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Comment',
    filters: {
      reference_doctype: 'Volteo Audyt',
      reference_name: props.dealId,
      comment_type: 'Comment',
    },
    fields: ['name', 'comment_by', 'comment_email', 'content', 'creation'],
    order_by: 'creation asc',
    limit_page_length: 200,
  },
  auto: true,
})

const newComment = ref('')
const newCommentAttachments = ref([])
const posting = ref(false)

// reference_doctype='Volteo Audyt' works unchanged against the generic
// crm.api.comment.add_comment — it's already generic over reference_doctype.
// Trade-off vs. the old `volteo_audyt_comment` Server Script: that script
// checked the comment author's role (admin/backoffice/deal owner) explicitly;
// this path relies on `Comment` DocPerm instead, which Volteo D2D Sales and
// Volteo Backend already hold read+create on — a real but slightly broader
// gate (any role with Comment create rights, not just this deal's context).
async function postComment() {
  const text = newComment.value.trim()
  if (!text || posting.value) return
  posting.value = true
  try {
    await call('crm.api.comment.add_comment', {
      reference_doctype: 'Volteo Audyt',
      reference_name: props.dealId,
      content: text,
      attachments: newCommentAttachments.value.map((f) => f.name),
    })
    newComment.value = ''
    newCommentAttachments.value = []
    await commentsResource.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    posting.value = false
  }
}

function removeNewCommentAttachment(idx) {
  newCommentAttachments.value = newCommentAttachments.value.filter((_, i) => i !== idx)
}

// Attachments for the listed comments — a second, client-side query rather
// than a backend change, since `frappe.client.get_list` on Comment cannot
// join File. Keyed by comment name, mirroring how
// crm/api/activities.py::get_attachments enriches comment rows server-side
// for the main Activities timeline (not reused here — that helper isn't
// whitelisted on its own and this stays a plain File query).
const commentAttachments = reactive({})

watch(
  () => commentsResource.data,
  (data) => loadCommentAttachments((data || []).map((c) => c.name)),
)

async function loadCommentAttachments(names) {
  // Same clear-then-repopulate shape as hydrateForm()'s reactive maps above:
  // build the new grouping as a plain object first, then sync it onto the
  // reactive map in one go, rather than mutating grouped arrays in place.
  let grouped = {}
  if (names.length) {
    try {
      const files = await call('frappe.client.get_list', {
        doctype: 'File',
        filters: { attached_to_doctype: 'Comment', attached_to_name: ['in', names] },
        fields: ['name', 'file_name', 'file_url', 'attached_to_name'],
        limit_page_length: 0,
      })
      ;(files || []).forEach((f) => {
        grouped[f.attached_to_name] = [...(grouped[f.attached_to_name] || []), f]
      })
    } catch (err) {
      // Non-fatal — comments still render without their attachments rather
      // than blocking the thread on a secondary query failing.
      grouped = {}
    }
  }
  Object.keys(commentAttachments).forEach((k) => delete commentAttachments[k])
  Object.assign(commentAttachments, grouped)
}

// Comment content may contain HTML — render it as plain text. DOMParser with
// text/html neither executes scripts nor loads resources, so extracting
// textContent is a safe way to strip markup.
function commentText(html) {
  if (!html) return ''
  try {
    const doc = new DOMParser().parseFromString(String(html), 'text/html')
    return (doc.body.textContent || '').trim()
  } catch (e) {
    return String(html).replace(/<[^>]*>/g, '').trim()
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
