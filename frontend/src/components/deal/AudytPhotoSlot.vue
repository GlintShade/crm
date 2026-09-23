<!--
  Audyt photo slot — a single named photo tile inside the Audyt tab's photo
  grid (Dokumentacja zdjęciowa). Empty tiles open FilesUploader (camera or
  device); filled tiles show a thumbnail with hover/touch overlay actions to
  replace or remove. Purely presentational — the parent (AudytTab) owns the
  `zdjecia` map and persists it via `zdjecia_json`.
-->
<template>
  <div class="flex flex-col gap-1.5">
    <!-- Empty + enabled -->
    <button
      v-if="!value && !disabled"
      type="button"
      :class="[
        'flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed bg-surface-gray-1 text-ink-gray-5 transition-colors hover:border-outline-gray-4 hover:bg-surface-gray-2',
        verdictRing || 'border-outline-gray-3',
      ]"
      @click="showUploader = true"
    >
      <span class="lucide-camera size-6" aria-hidden="true" />
      <span class="px-2 text-center text-xs">{{ displayLabel }}</span>
    </button>

    <!-- Empty + disabled -->
    <div
      v-else-if="!value && disabled"
      :class="[
        'flex aspect-[4/3] w-full flex-col items-center justify-center gap-1 rounded-lg border bg-surface-gray-1 text-ink-gray-4',
        verdictRing || 'border-outline-gray-2',
      ]"
    >
      <span class="text-lg">—</span>
      <span class="px-2 text-center text-xs">{{ displayLabel }}</span>
    </div>

    <!-- Filled -->
    <div
      v-else
      :class="[
        'group relative aspect-[4/3] w-full overflow-hidden rounded-lg border bg-surface-gray-1',
        verdictRing || 'border-outline-gray-2',
      ]"
    >
      <span
        v-if="verdictStatus"
        class="absolute right-1.5 top-1.5 z-10 h-3.5 w-3.5 rounded-full ring-2 ring-white"
        :class="verdictDotBg"
        :aria-label="verdictStatus"
      />
      <img
        v-if="!isPdfValue"
        :src="value"
        :alt="label"
        class="h-full w-full cursor-pointer object-cover"
        @click="openFullImage"
      />
      <div
        v-else
        class="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 px-2"
        @click="openFullImage"
      >
        <FileTextIcon class="size-8 text-ink-gray-5" />
        <span class="w-full truncate text-center text-xs text-ink-gray-6">{{ fileNameFromUrl }}</span>
      </div>
      <!--
        Na myszy caly kafelek ciemnieje na hover (bg-black/55). Na dotyku
        (hover:none) nakladka jest widoczna cały czas (nie ma stanu hover do
        wywolania), wiec pelne przyciemnienie zostalo zastapione gradientem
        od dolu, zeby zdjecie nad paskiem przyciskow zostawalo czytelne.
      -->
      <div
        v-if="!disabled"
        class="pointer-events-none absolute inset-0 flex items-end justify-center gap-2 pb-2 opacity-0 transition-opacity [@media(hover:hover)]:bg-black/55 [@media(hover:none)]:bg-gradient-to-t [@media(hover:none)]:from-black/60 [@media(hover:none)]:to-transparent [@media(hover:none)]:opacity-100 group-focus-within:opacity-100 group-hover:opacity-100"
      >
        <!--
          Ponizej sm kafelek (2 kolumny, ok. 250px) jest za waski na dwa
          przyciski z etykietami: „Usuń" wystawal poza kafelek i byl ucinany
          przez overflow-hidden. Ponizej sm renderujemy same ikony z
          tooltipem, od sm w gore zostaja przyciski z etykietami jak dotad.
        -->
        <Button
          class="pointer-events-auto sm:hidden"
          size="sm"
          variant="subtle"
          icon="lucide-refresh-cw"
          :tooltip="__('Podmień')"
          @click.stop="showUploader = true"
        />
        <Button
          class="pointer-events-auto sm:hidden"
          size="sm"
          variant="subtle"
          theme="red"
          icon="lucide-trash-2"
          :tooltip="__('Usuń')"
          @click.stop="removePhoto"
        />
        <Button
          class="pointer-events-auto hidden sm:inline-flex"
          size="sm"
          variant="subtle"
          :label="__('Podmień')"
          iconLeft="lucide-refresh-cw"
          @click.stop="showUploader = true"
        />
        <Button
          class="pointer-events-auto hidden sm:inline-flex"
          size="sm"
          variant="subtle"
          theme="red"
          :label="__('Usuń')"
          iconLeft="lucide-trash-2"
          @click.stop="removePhoto"
        />
      </div>
    </div>

    <div v-if="value" class="truncate text-center text-xs text-ink-gray-5">
      {{ displayLabel }}
    </div>

    <FilesUploader
      v-if="showUploader"
      v-model="showUploader"
      :doctype="doctype"
      :docname="docname"
      :options="uploaderOptions"
      @after="onAfterUpload"
    />
  </div>
</template>

<script setup>
import FileTextIcon from '@/components/Icons/FileTextIcon.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { jestPdf, nazwaPlikuZUrl } from '@/utils/audytPodglad'
import { VERDICT_META } from '@/utils/audytWeryfikacja'
import { Button } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null },
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  disabled: { type: Boolean, default: false },
  optional: { type: Boolean, default: false },
  // Absent/false means images only (the safe default for every existing
  // slot); true only for the one slot the server flags with `pdf: 1`
  // (faktura_energia) — see AudytTab's `visiblePhotoSlots` pass-through.
  allowPdf: { type: Boolean, default: false },
  // Decoration only, set by AudytTab while the audit is in Weryfikacja —
  // one of 'waiting'/'accepted'/'error', or null outside that stage. The
  // verdict *controls* (accept/error/undo) live in the parent
  // (AudytVerdictControls), never here — this component stays presentational
  // and makes no API calls.
  verdictStatus: { type: String, default: null },
  // Identyfikator tego slotu w liście podglądu budowanej przez rodzica
  // (zbudujListePodgladu), przekazywany z powrotem w zdarzeniu `preview`,
  // żeby rodzic wiedział, który indeks otworzyć w AudytPodgladZdjec. Puste
  // sloty ("dodaj nowe") dostają go też, ale nigdy nie emitują `preview`.
  previewKey: { type: String, default: null },
})

const emit = defineEmits(['change', 'preview'])

const showUploader = ref(false)

// Solid fills for the status dot, restricted to the exact bg-surface-*-2
// tokens already proven to exist in this codebase (AudytTab.vue's Szkic/
// Weryfikacja/Zatwierdzony banners use the same three).
const STATUS_DOT_BG = {
  waiting: 'bg-surface-blue-2',
  accepted: 'bg-surface-green-2',
  error: 'bg-surface-red-2',
}

const verdictRing = computed(() => {
  const meta = props.verdictStatus ? VERDICT_META[props.verdictStatus] : null
  return meta ? `ring-2 ${meta.ring}` : ''
})

const verdictDotBg = computed(() => STATUS_DOT_BG[props.verdictStatus] || 'bg-surface-gray-3')

const displayLabel = computed(() =>
  props.optional ? `${props.label} ${__('(opcjonalne)')}` : props.label,
)

const uploaderOptions = computed(() => ({
  folder: 'Home/Attachments',
  allowMultiple: false,
  restrictions: {
    maxNumberOfFiles: 1,
    allowedFileTypes: props.allowPdf ? ['image/*', 'application/pdf'] : ['image/*'],
  },
}))

// Detected from the stored file URL, not the upload restriction — a slot's
// existing value may have been uploaded back when only images were allowed,
// or `allowPdf` may have changed since. Query/hash suffixes are stripped
// before checking the extension.
const isPdfValue = computed(() => jestPdf(props.value))

const fileNameFromUrl = computed(() => nazwaPlikuZUrl(props.value))

function onAfterUpload(uploadedFiles) {
  if (uploadedFiles && uploadedFiles.length) {
    emit('change', uploadedFiles[0].file_url)
  }
}

function removePhoto() {
  emit('change', null)
}

// PDF-y zostają otwierane w nowej karcie (natywna przeglądarka PDF jest
// lepsza niż iframe w modalu), decyzja właściciela. Obrazy otwierają się
// w podglądzie w oknie CRM zamiast wychodzić poza aplikację; rodzic (nie
// ten komponent) decyduje, który indeks pokazać, więc tylko emitujemy.
function openFullImage() {
  if (!props.value) return
  if (isPdfValue.value) {
    window.open(props.value, '_blank', 'noopener')
  } else {
    emit('preview', props.previewKey)
  }
}
</script>
