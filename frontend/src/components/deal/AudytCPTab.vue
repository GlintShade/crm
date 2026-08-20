<!--
  Audyt CP tab (Szansa view) — special audit form for Czyste Powietrze deals,
  1:1 with the deal (Volteo Audyt CP, name == dealId). Modeled directly on
  AudytTab.vue (loading/empty/form structure, per-element verification,
  optimistic immediate-save photos, comment thread) but simpler: no variant
  matrix — the document catalog is a fixed 7-slot list (see audytCP.js
  SLOTY), and there's a photo gallery (min 1, max 20, no captions) instead of
  per-variant photo slots.

  3-stage workflow, same shape as AudytTab.vue:
    Szkic (draft, editable by rep/admin) →
    Weryfikacja (submitted; back office/admin edits in place) →
    Zatwierdzony (approved, read-only; back office/admin may reopen via
      "Przywróć do edycji").
  Per-document verdicts (Akceptuj / Błąd+notatka / Cofnij) plus ONE grouped
  verdict for the whole photo gallery (KLUCZ_ZDJECIA). There are no text
  fields here — every save is a file swap, so saves are immediate, no
  debounce, optimistic with rollback on failure (same idiom as AudytTab's
  onPhotoChange).

  API (fixed interface, built by another agent in parallel). These are
  whitelisted methods in the fork (crm/api/audyt_cp.py), NOT Server Scripts,
  so every call() MUST use the full dotted path — see UmowaTab.vue's header
  comment for why a bare name silently breaks at runtime (417) despite
  looking like AudytTab.vue's pattern:
    crm.api.audyt_cp.volteo_audyt_cp_get(deal)                     -> {audyt|null, sloty, klucz_zdjecia, max_zdjec, max_notatka, can_review, is_admin, can_edit}
    crm.api.audyt_cp.volteo_audyt_cp_submit(deal)                  -> {ok, status}
    crm.api.audyt_cp.volteo_audyt_cp_set_status(deal, status)      -> {ok, status}
    crm.api.audyt_cp.volteo_audyt_cp_set_verdict(deal, key, status, note?) -> {ok, weryfikacja}

  `can_edit`/`can_review` are computed server-side and only combined with
  local status here — this component never derives permissions itself (see
  CLAUDE.md's "Preserve the cost/commission secrecy model" convention,
  same principle applied to review gating).
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <!-- Loading -->
      <div v-if="resource.loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <!-- Load failed — bail out, never render a misleading state -->
      <div
        v-else-if="loadError"
        class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
      >
        {{ loadError }}
      </div>

      <!-- No audit yet -->
      <div
        v-else-if="!exists"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <AudytIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak audytu') }}</div>
        <template v-if="canEditSrv">
          <div class="max-w-md text-sm text-ink-gray-5">
            {{ __('Audyt specjalny Czyste Powietrze — komplet dokumentów i zdjęć.') }}
          </div>
          <Button
            variant="solid"
            :label="__('Rozpocznij audyt')"
            :loading="creating"
            :disabled="creating"
            @click="createAudyt"
          />
        </template>
        <template v-else>
          <div class="max-w-md text-sm text-ink-gray-5">
            {{ __('Audyt nie został jeszcze rozpoczęty.') }}
          </div>
        </template>
      </div>

      <!-- Audit form (draft / verification / approved) -->
      <div v-else class="flex flex-col gap-6">
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="text-lg font-semibold text-ink-gray-8">{{ __('Audyt Czyste Powietrze') }}</div>
              <Badge :theme="badgeTheme" variant="subtle" size="lg" :label="status" />
            </div>
            <div class="flex items-center gap-3">
              <!-- Rep: submit draft to verification -->
              <Button
                v-if="canEditSrv && isDraft"
                variant="solid"
                :label="__('Prześlij do weryfikacji')"
                :disabled="!!submitBraki.length || submitting"
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
                  :disabled="!agg.allAccepted"
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

          <!-- Verification progress — only meaningful while under review -->
          <div v-if="isReview" class="text-xs text-ink-gray-5">
            {{ __('Zaakceptowano {0}/{1} elementów', [agg.accepted, agg.total]) }}<template v-if="agg.errors > 0"
              >&nbsp;· {{ __('Błędy: {0}', [agg.errors]) }}</template
            >
          </div>

          <!-- Submit helper — draft not yet complete -->
          <div v-if="isDraft && submitBraki.length" class="text-xs text-ink-amber-6">
            {{ __('Braki do uzupełnienia przed przesłaniem:') }} {{ submitBraki.join('; ') }}
          </div>

          <!-- Approve helper — review not yet fully accepted -->
          <div v-if="canReview && isReview && !agg.allAccepted" class="text-xs text-ink-amber-6">
            {{ __('Zatwierdzenie możliwe po zaakceptowaniu wszystkich elementów.') }}
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
              ? __('Audyt w weryfikacji — możesz edytować dokumenty bezpośrednio, a następnie zatwierdzić.')
              : __('Audyt oczekuje na weryfikację przez back office — dokumenty są zablokowane do czasu decyzji.')
          }}
        </div>

        <!-- Document slots -->
        <section>
          <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
            {{ __('Dokumenty') }}
          </div>
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div v-for="slot in SLOTY" :key="slot.key" class="flex flex-col gap-1">
              <AudytPhotoSlot
                :label="slot.label"
                :value="dokumenty[slot.key] || null"
                :optional="!slot.required"
                :allow-pdf="true"
                doctype="Volteo Audyt CP"
                :docname="dealId"
                :disabled="readOnly"
                :verdict-status="isReview && dokumenty[slot.key] ? verdictStatusFor(slot.key) : null"
                @change="(url) => onDocChange(slot.key, url)"
              />
              <AudytVerdictControls
                :verdict="verdictFor(weryfikacja, slot.key)"
                :can-review="canReview"
                :busy="!!verdictBusy[slot.key]"
                :show-controls="isReview && !!dokumenty[slot.key]"
                @set-verdict="(vStatus, note) => setVerdict(slot.key, vStatus, note)"
              />
            </div>
          </div>
        </section>

        <!-- Photo gallery -->
        <section>
          <div class="mb-3 flex items-center justify-between">
            <div class="text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
              {{ __('Zdjęcia') }}
            </div>
            <div class="text-xs text-ink-gray-5">{{ zdjeciaList.length }} / {{ MAX_ZDJEC }}</div>
          </div>
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <AudytPhotoSlot
              v-for="(url, idx) in zdjeciaList"
              :key="'zdjecie-' + idx + '-' + url"
              :label="__('Zdjęcie {0}', [idx + 1])"
              :value="url"
              doctype="Volteo Audyt CP"
              :docname="dealId"
              :disabled="readOnly"
              @change="(u) => onZdjecieChange(idx, u)"
            />
            <AudytPhotoSlot
              v-if="editable && zdjeciaList.length < MAX_ZDJEC"
              :key="'zdjecie-new-' + zdjeciaList.length"
              :label="__('Dodaj zdjęcie')"
              :value="null"
              doctype="Volteo Audyt CP"
              :docname="dealId"
              :disabled="false"
              @change="onZdjecieAdd"
            />
          </div>
          <AudytVerdictControls
            :verdict="verdictFor(weryfikacja, KLUCZ_ZDJECIA)"
            :can-review="canReview"
            :busy="!!verdictBusy[KLUCZ_ZDJECIA]"
            :show-controls="isReview"
            @set-verdict="(vStatus, note) => setVerdict(KLUCZ_ZDJECIA, vStatus, note)"
          />
        </section>

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
                  doctype: 'Volteo Audyt CP',
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
import AudytVerdictControls from '@/components/deal/AudytVerdictControls.vue'
import { useAttachments } from '@/composables/useAttachments'
import { KLUCZ_ZDJECIA, MAX_ZDJEC, SLOTY, brakiDoPrzeslania, cpAggregate, cpElements, parsujListe, parsujMape } from '@/utils/audytCP'
import { parseWeryfikacja, verdictFor } from '@/utils/audytWeryfikacja'
import { Badge, Button, FileUploader, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Audit record + server-computed permissions -------------------------
const resource = createResource({
  url: 'crm.api.audyt_cp.volteo_audyt_cp_get',
  params: { deal: props.dealId },
  auto: true,
})

const loadError = ref('')

watch(
  () => resource.error,
  (err) => {
    loadError.value = err ? extractErrorMessage(err) : ''
  },
)

const row = computed(() => resource.data?.audyt || null)
const exists = computed(() => !!row.value?.name)

const canEditSrv = computed(() => !!resource.data?.can_edit)
const canReview = computed(() => !!resource.data?.can_review)

// --- Status / permission state -------------------------------------------
const status = computed(() => row.value?.status || 'Szkic')
const isDraft = computed(() => status.value === 'Szkic')
const isReview = computed(() => status.value === 'Weryfikacja')
const isApproved = computed(() => status.value === 'Zatwierdzony')

// Fields/photos are editable in Szkic by rep/admin (canEditSrv), and in
// Weryfikacja by back office/admin (canReview) — a reviewer edits the audit
// directly instead of sending it back to the rep for corrections. Same
// formula as AudytTab.vue's `editable`.
const editable = computed(
  () => (canEditSrv.value && isDraft.value) || (canReview.value && isReview.value),
)
const readOnly = computed(() => !editable.value)

const badgeTheme = computed(() =>
  isApproved.value ? 'green' : isReview.value ? 'blue' : 'amber',
)

// --- Local editable state --------------------------------------------------
const dokumenty = reactive({})
const zdjeciaList = ref([])

// --- Per-element verification (Weryfikacja stage) ---------------------------
// Sparse map keyed by raw slot keys (dok:...) — no pole:/foto: prefix, CP has
// no mixed field/photo matrix to disambiguate. Always replaced wholesale, the
// same idiom audytWeryfikacja-based components use, so nothing here ever
// reads `hasOwnProperty` against this reactive object (see CLAUDE.md's Vue
// hasOwnProperty/reactive() trap).
const weryfikacja = reactive({})
const verdictBusy = reactive({})

function replaceWeryfikacja(map) {
  Object.keys(weryfikacja).forEach((k) => delete weryfikacja[k])
  Object.assign(weryfikacja, map || {})
}

const creating = ref(false)
const submitting = ref(false)
const statusUpdating = ref(false)

const { trackOldFile, processPendingDeletions } = useAttachments('Volteo Audyt CP', props.dealId)

watch(
  () => row.value,
  (r) => hydrate(r),
  { immediate: true },
)

function hydrate(r) {
  Object.keys(dokumenty).forEach((k) => delete dokumenty[k])
  Object.assign(dokumenty, parsujMape(r?.dokumenty_json))

  zdjeciaList.value = parsujListe(r?.zdjecia_json)

  // Server is authoritative — no local diffing on hydrate, just load
  // whatever the row currently carries (parseWeryfikacja drops malformed
  // entries, same as AudytTab.vue).
  replaceWeryfikacja(parseWeryfikacja(r?.weryfikacja_json))
}

// --- Progress / verification aggregation ------------------------------------
const elementy = computed(() => cpElements(dokumenty, zdjeciaList.value))
const agg = computed(() => cpAggregate(weryfikacja, elementy.value))
const submitBraki = computed(() => brakiDoPrzeslania(dokumenty, zdjeciaList.value))

function verdictStatusFor(key) {
  return verdictFor(weryfikacja, key).status
}

// --- Documents (immediate save) ----------------------------------------------
async function onDocChange(key, fileUrl) {
  if (readOnly.value) return
  const oldUrl = dokumenty[key] || null
  trackOldFile(oldUrl, fileUrl)
  if (fileUrl) dokumenty[key] = fileUrl
  else delete dokumenty[key]

  try {
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt CP',
      name: props.dealId,
      fieldname: { dokumenty_json: JSON.stringify(dokumenty) },
    })
    processPendingDeletions()
    // Mirrors the server's lock_guard rule 7: a saved change to this slot's
    // file resets its verdict back to waiting (same rationale as
    // AudytTab.vue's mirrorFieldResets()/dropWeryfikacjaKeys()).
    if (isReview.value) delete weryfikacja[key]
  } catch (err) {
    if (oldUrl) dokumenty[key] = oldUrl
    else delete dokumenty[key]
    toast.error(extractErrorMessage(err))
  }
}

// --- Photo gallery (immediate save, immutable list updates) ------------------
async function persistZdjecia(prevList) {
  try {
    await call('frappe.client.set_value', {
      doctype: 'Volteo Audyt CP',
      name: props.dealId,
      fieldname: { zdjecia_json: JSON.stringify(zdjeciaList.value) },
    })
    processPendingDeletions()
    // Mirrors the server's lock_guard rule 7 for the grouped photo element —
    // same rationale as onDocChange() above.
    if (isReview.value) delete weryfikacja[KLUCZ_ZDJECIA]
  } catch (err) {
    zdjeciaList.value = prevList
    toast.error(extractErrorMessage(err))
  }
}

async function onZdjecieChange(index, fileUrl) {
  if (readOnly.value) return
  const prevList = zdjeciaList.value
  const oldUrl = prevList[index] || null
  trackOldFile(oldUrl, fileUrl)
  const nextList = fileUrl
    ? prevList.map((u, i) => (i === index ? fileUrl : u))
    : prevList.filter((_, i) => i !== index)
  zdjeciaList.value = nextList
  await persistZdjecia(prevList)
}

async function onZdjecieAdd(fileUrl) {
  if (readOnly.value || !fileUrl) return
  if (zdjeciaList.value.length >= MAX_ZDJEC) return
  const prevList = zdjeciaList.value
  trackOldFile(null, fileUrl)
  zdjeciaList.value = [...prevList, fileUrl]
  await persistZdjecia(prevList)
}

// --- Create / submit / status -------------------------------------------------
async function createAudyt() {
  creating.value = true
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Volteo Audyt CP',
        deal: props.dealId,
        status: 'Szkic',
      },
    })
    await resource.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

async function submitAudyt() {
  if (submitBraki.value.length || submitting.value) return
  submitting.value = true
  try {
    await call('crm.api.audyt_cp.volteo_audyt_cp_submit', { deal: props.dealId })
    toast.success(__('Audyt przesłany do weryfikacji'))
    await resource.reload()
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
    await call('crm.api.audyt_cp.volteo_audyt_cp_set_status', { deal: props.dealId, status: s })
    toast.success(__('Status audytu zaktualizowany'))
    await resource.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    statusUpdating.value = false
  }
}

// --- Per-element verification (Weryfikacja stage) ----------------------------
// Deliberately never reloads the resource — the server response's
// `weryfikacja` map is authoritative on its own and is applied directly
// (same rationale as AudytTab.vue's setVerdict).
async function setVerdict(elementKey, vStatus, note) {
  if (!canReview.value || verdictBusy[elementKey]) return
  verdictBusy[elementKey] = true

  const before = { ...weryfikacja }
  const optimistic = { ...before }
  if (vStatus === 'waiting') delete optimistic[elementKey]
  else optimistic[elementKey] = { status: vStatus, note: note || undefined }
  replaceWeryfikacja(optimistic)

  try {
    const res = await call('crm.api.audyt_cp.volteo_audyt_cp_set_verdict', {
      deal: props.dealId,
      key: elementKey,
      status: vStatus,
      note: note || undefined,
    })
    replaceWeryfikacja(res?.weryfikacja || {})
  } catch (err) {
    replaceWeryfikacja(before)
    toast.error(extractErrorMessage(err))
  } finally {
    verdictBusy[elementKey] = false
  }
}

// --- Comments ----------------------------------------------------------------
const commentsResource = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Comment',
    filters: {
      reference_doctype: 'Volteo Audyt CP',
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

async function postComment() {
  const text = newComment.value.trim()
  if (!text || posting.value) return
  posting.value = true
  try {
    await call('crm.api.comment.add_comment', {
      reference_doctype: 'Volteo Audyt CP',
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
// join File. Keyed by comment name (same idiom as AudytTab.vue).
const commentAttachments = reactive({})

watch(
  () => commentsResource.data,
  (data) => loadCommentAttachments((data || []).map((c) => c.name)),
)

async function loadCommentAttachments(names) {
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

// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) — but that
// pattern was blind to the actual shape of errors thrown by frappe-ui's
// call() (see frontend/node_modules/frappe-ui/src/utils/frappeRequest.js
// ~L82-124): call() consumes _server_messages itself and re-throws an
// error whose `message` is just "{url} {exc_type}" and whose `messages` is
// the already-parsed array of server message strings (the Polish text
// lives there, not under `_server_messages`/`exception`). Without the
// `err.messages` branch below, the name-mismatch ValidationError always
// fell through to the raw "{url} {exc_type}" fallback instead of the
// server's Polish message. The old `_server_messages`/`exception` branches
// are kept as a fallback for any caller that isn't call().
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
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
