<!--
  Per-element verdict controls for the Audyt tab's Weryfikacja stage,
  reused in every list row and every photo card footer (see
  AudytTab.vue). Purely presentational: it renders the current verdict
  (waiting/accepted/error) and, for reviewers, the buttons to set one, but
  never calls the API or touches the audit store itself. The parent owns the
  `weryfikacja` map and is the only place `volteo_audyt_set_verdict` is
  called, this component only emits `set-verdict`.
-->
<template>
  <div
    v-if="showControls"
    :class="karta ? 'flex flex-col gap-2' : 'flex flex-col items-end gap-1 text-right'"
  >
    <!-- Reviewer: waiting -> two equal actions -->
    <template v-if="canReview && status === 'waiting' && !noteMode">
      <div :class="karta ? 'flex flex-wrap gap-2' : 'flex items-center gap-1.5'">
        <Button
          size="sm"
          variant="subtle"
          theme="green"
          :iconLeft="karta ? undefined : 'lucide-check'"
          :class="karta ? 'flex-1 basis-[4.75rem]' : ''"
          :label="__('Akceptuj')"
          :disabled="busy"
          @click="$emit('set-verdict', 'accepted')"
        />
        <Button
          size="sm"
          variant="subtle"
          theme="red"
          :iconLeft="karta ? undefined : 'lucide-x'"
          :class="karta ? 'flex-1 basis-[4.75rem]' : ''"
          :label="__('Odrzuć')"
          :disabled="busy"
          @click="openNote"
        />
      </div>
    </template>

    <!-- Status row (waiting for non-reviewers, accepted, error) -->
    <div
      v-if="status !== 'waiting' || !canReview"
      :class="
        karta
          ? 'flex items-center justify-between gap-2'
          : 'flex items-center justify-end gap-2'
      "
    >
      <span
        v-if="status === 'waiting'"
        class="rounded bg-surface-blue-2 px-1.5 py-0.5 text-xs font-medium text-ink-blue-8"
      >
        {{ __(meta.label) }}
      </span>
      <span
        v-else-if="status === 'accepted'"
        class="inline-flex items-center gap-1 text-xs font-medium text-ink-green-8"
      >
        <span class="lucide-check size-3.5" aria-hidden="true" />
        {{ __(meta.label) }}
      </span>
      <span v-else class="inline-flex items-center gap-1 text-xs font-medium text-ink-red-8">
        <span class="lucide-x size-3.5" aria-hidden="true" />
        {{ __(meta.label) }}
      </span>

      <span v-if="canReview && status !== 'waiting' && !noteMode" class="flex items-center gap-3">
        <button
          v-if="status === 'error'"
          type="button"
          class="text-xs text-ink-gray-5 underline-offset-2 hover:text-ink-gray-8 hover:underline disabled:opacity-50"
          :disabled="busy"
          @click="openNote"
        >
          {{ __('Edytuj powód') }}
        </button>
        <button
          type="button"
          class="text-xs text-ink-gray-5 underline-offset-2 hover:text-ink-gray-8 hover:underline disabled:opacity-50"
          :disabled="busy"
          @click="$emit('set-verdict', 'waiting')"
        >
          {{ __('Cofnij') }}
        </button>
      </span>
    </div>

    <!-- Error note, visible to every role including the rep -->
    <div v-if="status === 'error' && verdict?.note" class="text-xs text-ink-red-6">
      {{ verdict.note }}
    </div>

    <!-- Inline note editor, reviewers only -->
    <div
      v-if="canReview && noteMode"
      class="flex w-full flex-col gap-1.5 rounded border border-outline-gray-2 bg-surface-gray-1 p-2 text-left"
    >
      <FormControl
        type="textarea"
        :label="__('Co jest nie tak?')"
        :disabled="busy"
        :maxlength="500"
        v-model="noteText"
      />
      <div class="flex items-center gap-2">
        <Button
          size="sm"
          variant="solid"
          theme="red"
          :label="__('Zgłoś błąd')"
          :disabled="busy"
          @click="confirmError"
        />
        <Button
          size="sm"
          variant="subtle"
          :label="__('Anuluj')"
          :disabled="busy"
          @click="cancelNote"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { VERDICT_META } from '@/utils/audytWeryfikacja'
import { Button, FormControl } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  // `verdictFor()` result: { status: 'waiting'|'accepted'|'error', note?, by?, at? }
  verdict: { type: Object, default: () => ({ status: 'waiting' }) },
  canReview: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  // True only while the audit is in Weryfikacja, outside that stage this
  // component renders nothing at all.
  showControls: { type: Boolean, default: false },
  // 'wiersz' (kompaktowo, do prawej, dla wierszy listy) albo 'karta' (stopka karty zdjecia).
  uklad: { type: String, default: 'wiersz' },
})

const emit = defineEmits(['set-verdict', 'edytor'])

const karta = computed(() => props.uklad === 'karta')
const status = computed(() => props.verdict?.status || 'waiting')
const meta = computed(() => VERDICT_META[props.verdict?.status] || VERDICT_META.waiting)

const noteMode = ref(false)
const noteText = ref('')

// The parent replaces `verdict` with the server's authoritative response
// after every call, once that lands, close any note editor left open
// rather than risk it showing a stale draft against a new status.
watch(
  [() => props.verdict?.status, () => props.verdict?.note, () => props.verdict?.at],
  () => {
    noteMode.value = false
    noteText.value = ''
  },
)

// Rodzic (wiersz listy) moze dzieki temu dac edytorowi cala szerokosc.
watch(noteMode, (v) => emit('edytor', v))

function openNote() {
  noteText.value = props.verdict?.status === 'error' ? props.verdict?.note || '' : ''
  noteMode.value = true
}

function cancelNote() {
  noteMode.value = false
  noteText.value = ''
}

function confirmError() {
  const trimmed = noteText.value.trim()
  emit('set-verdict', 'error', trimmed || undefined)
}
</script>
