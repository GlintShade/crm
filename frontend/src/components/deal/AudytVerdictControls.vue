<!--
  Per-element verdict controls for the Audyt tab's Weryfikacja stage —
  reused under every visible matrix field and every visible photo slot (see
  AudytTab.vue). Purely presentational: it renders the current verdict
  (waiting/accepted/error) and, for reviewers, the buttons to set one, but
  never calls the API or touches the audit store itself. The parent owns the
  `weryfikacja` map and is the only place `volteo_audyt_set_verdict` is
  called — this component only emits `set-verdict`.
-->
<template>
  <div v-if="showControls" class="mt-1.5 flex flex-col gap-1.5">
    <div class="flex flex-wrap items-center gap-1.5">
      <Badge :theme="meta.theme" variant="subtle" size="sm" :label="__(meta.label)" />

      <template v-if="canReview">
        <Button
          size="sm"
          variant="subtle"
          theme="green"
          iconLeft="lucide-check"
          :label="__('Akceptuj')"
          :disabled="busy"
          @click="$emit('set-verdict', 'accepted')"
        />
        <Button
          v-if="!noteMode"
          size="sm"
          variant="subtle"
          theme="red"
          iconLeft="lucide-x"
          :label="__('Błąd')"
          :disabled="busy"
          @click="openNote"
        />
        <Button
          v-if="verdict?.status !== 'waiting'"
          size="sm"
          variant="subtle"
          :label="__('Cofnij')"
          :disabled="busy"
          @click="$emit('set-verdict', 'waiting')"
        />
      </template>
    </div>

    <!-- Error note — visible to every role, including the rep, read-only here -->
    <div v-if="verdict?.status === 'error' && verdict?.note" class="text-xs text-ink-red-6">
      {{ verdict.note }}
    </div>

    <!-- Inline "report error" note editor — reviewers only -->
    <div
      v-if="canReview && noteMode"
      class="flex flex-col gap-1.5 rounded border border-outline-gray-2 bg-surface-gray-1 p-2"
    >
      <FormControl
        type="textarea"
        :label="__('Uwaga (opcjonalnie)')"
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
import { Badge, Button, FormControl } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  // `verdictFor()` result: { status: 'waiting'|'accepted'|'error', note?, by?, at? }
  verdict: { type: Object, default: () => ({ status: 'waiting' }) },
  canReview: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  // True only while the audit is in Weryfikacja — outside that stage this
  // component renders nothing at all.
  showControls: { type: Boolean, default: false },
})

const emit = defineEmits(['set-verdict'])

const meta = computed(() => VERDICT_META[props.verdict?.status] || VERDICT_META.waiting)

const noteMode = ref(false)
const noteText = ref('')

// The parent replaces `verdict` with the server's authoritative response
// after every call — once that lands, close any note editor left open
// rather than risk it showing a stale draft against a new status.
watch(
  () => props.verdict?.status,
  () => {
    noteMode.value = false
    noteText.value = ''
  },
)

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
