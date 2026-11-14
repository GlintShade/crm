<!--
  Audyt photo slot, a single named tile inside the Audyt tab's photo grid
  (Dokumentacja zdjęciowa). Holds a photo, a video (photo slots only, never
  document slots), or a PDF (document slots only). Empty tiles open
  FilesUploader (camera or device); filled tiles show a thumbnail (or an
  icon tile for video/PDF) shown as a card with always-visible corner tools
  (enlarge, replace, remove) and an optional footer slot (`stopka`). Purely presentational, the parent (AudytTab) owns the `zdjecia`
  map and persists it via `zdjecia_json`.
-->
<template>
  <div class="flex h-full flex-col gap-1.5">
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
      <span class="text-lg">-</span>
      <span class="px-2 text-center text-xs">{{ displayLabel }}</span>
    </div>

    <!-- Filled: card -->
    <div v-else :class="['flex flex-1 flex-col overflow-hidden rounded-lg border', cardClass]">
      <div class="relative aspect-[4/3] w-full overflow-hidden bg-surface-gray-1">
        <img
          v-if="!isPdfValue && !isVideoValue"
          :src="value"
          :alt="label"
          class="h-full w-full cursor-pointer object-cover"
          @click="openFullImage"
        />
        <div
          v-else-if="isVideoValue"
          class="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 px-2"
          @click="openFullImage"
        >
          <FileVideoIcon class="size-8 text-ink-gray-5" />
          <span v-if="kompakt" class="w-full truncate text-center text-xs text-ink-gray-6">{{ fileNameFromUrl }}</span>
        </div>
        <div v-else-if="pokazPodgladPdf" class="relative h-full w-full">
          <!-- ikona pod iframe: bez przegladarkowego czytnika PDF zostaje widoczna -->
          <div class="absolute inset-0 flex items-center justify-center">
            <FileTextIcon class="size-8 text-ink-gray-5" />
          </div>
          <iframe
            :src="pdfPodgladUrl"
            :title="label"
            loading="lazy"
            tabindex="-1"
            class="pointer-events-none absolute inset-0 h-full w-full border-0"
          />
          <!-- przezroczysta warstwa klikalna nad iframe -->
          <div class="absolute inset-0 cursor-pointer" @click="openFullImage" />
        </div>
        <div
          v-else
          class="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 px-2"
          @click="openFullImage"
        >
          <FileTextIcon class="size-8 text-ink-gray-5" />
          <span v-if="kompakt" class="w-full truncate text-center text-xs text-ink-gray-6">{{ fileNameFromUrl }}</span>
        </div>

        <span
          v-if="isPdfValue"
          class="pointer-events-none absolute left-1.5 top-1.5 rounded border border-outline-gray-2 bg-surface-base px-1.5 py-0.5 text-[10px] font-semibold leading-none text-ink-gray-8"
        >
          PDF
        </span>
        <span
          v-else-if="isVideoValue"
          class="pointer-events-none absolute left-1.5 top-1.5 rounded border border-outline-gray-2 bg-surface-base px-1.5 py-0.5 text-[10px] font-semibold leading-none text-ink-gray-8"
        >
          {{ __('film') }}
        </span>

        <!-- Narzedzia w rogu: zawsze widoczne male ikony -->
        <div class="pointer-events-none absolute right-1.5 top-1.5 flex gap-1">
          <Button
            v-if="!kompakt"
            class="pointer-events-auto"
            size="sm"
            variant="subtle"
            icon="lucide-maximize-2"
            :tooltip="__('Powiększ')"
            @click.stop="openFullImage"
          />
          <Button
            v-if="!disabled"
            class="pointer-events-auto"
            size="sm"
            variant="subtle"
            icon="lucide-refresh-cw"
            :tooltip="__('Podmień')"
            @click.stop="showUploader = true"
          />
          <Button
            v-if="!disabled && !(bezUsuwania && !kompakt)"
            class="pointer-events-auto"
            size="sm"
            variant="subtle"
            theme="red"
            icon="lucide-trash-2"
            :tooltip="__('Usuń')"
            @click.stop="removePhoto"
          />
        </div>
      </div>

      <div v-if="!kompakt" class="flex flex-1 flex-col gap-2 p-2.5">
        <div>
          <div class="line-clamp-2 text-left text-sm font-medium text-ink-gray-8">
            {{ displayLabel }}
          </div>
          <div v-if="isPdfValue || isVideoValue" class="truncate text-xs text-ink-gray-5">
            {{ fileNameFromUrl }}
          </div>
        </div>
        <div v-if="$slots.stopka" class="mt-auto"><slot name="stopka" /></div>
      </div>
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
import FileVideoIcon from '@/components/Icons/FileVideoIcon.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { TYPY_PLIKOW_WIDEO, jestPdf, jestWideo, nazwaPlikuZUrl } from '@/utils/audytPodglad'
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
  // Absent/false means no video, the safe default for every document slot
  // (allowPdf ones); true only for photo slots: OZE named slots without
  // `slot.pdf`, OZE extra photos, and the CP photo gallery. Never combined
  // with allowPdf.
  allowVideo: { type: Boolean, default: false },
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
  // Maly kafelek (zdjecia dodatkowe): tylko podglad, bez korpusu i podpisu.
  kompakt: { type: Boolean, default: false },
  // Ukrywa narzedzie Usun w zwyklej karcie (handlowiec w trybie poprawek).
  bezUsuwania: { type: Boolean, default: false },
})

const emit = defineEmits(['change', 'preview'])

const showUploader = ref(false)

const verdictRing = computed(() => {
  const meta = props.verdictStatus ? VERDICT_META[props.verdictStatus] : null
  return meta ? `ring-2 ${meta.ring}` : ''
})

// Obramowanie i tlo karty wg decyzji: oczekuje = niebieskie, blad = czerwone,
// zaakceptowane lub brak decyzji = zwykle szare.
const cardClass = computed(() => {
  if (props.verdictStatus === 'waiting') return 'border-outline-blue-2 bg-surface-blue-2'
  if (props.verdictStatus === 'error') return 'border-outline-red-3 bg-surface-red-2'
  return 'border-outline-gray-2 bg-surface-base'
})

// Podglad pierwszej strony PDF w iframe. Jedna flaga: ustaw na false, aby
// wrocic do kafelka z ikona i nazwa pliku.
const PODGLAD_PDF_W_IFRAME = true
const pokazPodgladPdf = computed(() => PODGLAD_PDF_W_IFRAME && isPdfValue.value)
const pdfPodgladUrl = computed(
  () => `${(props.value || '').split('#')[0]}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`,
)

const displayLabel = computed(() =>
  props.optional ? `${props.label} ${__('(opcjonalne)')}` : props.label,
)

const uploaderOptions = computed(() => {
  const allowedFileTypes = ['image/*']
  if (props.allowPdf) allowedFileTypes.push('application/pdf')
  if (props.allowVideo) allowedFileTypes.push(...TYPY_PLIKOW_WIDEO)
  return {
    folder: 'Home/Attachments',
    allowMultiple: false,
    restrictions: {
      maxNumberOfFiles: 1,
      allowedFileTypes,
    },
  }
})

// Detected from the stored file URL, not the upload restriction — a slot's
// existing value may have been uploaded back when only images were allowed,
// or `allowPdf`/`allowVideo` may have changed since. Query/hash suffixes are
// stripped before checking the extension.
const isPdfValue = computed(() => jestPdf(props.value))
const isVideoValue = computed(() => jestWideo(props.value))

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
// lepsza niż iframe w modalu), decyzja właściciela. Obrazy i wideo otwierają
// się w podglądzie w oknie CRM zamiast wychodzić poza aplikację; rodzic (nie
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
