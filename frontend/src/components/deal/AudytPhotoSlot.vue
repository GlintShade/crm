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
      class="flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-outline-gray-3 bg-surface-gray-1 text-ink-gray-5 transition-colors hover:border-outline-gray-4 hover:bg-surface-gray-2"
      @click="showUploader = true"
    >
      <span class="lucide-camera size-6" aria-hidden="true" />
      <span class="px-2 text-center text-xs">{{ label }}</span>
    </button>

    <!-- Empty + disabled -->
    <div
      v-else-if="!value && disabled"
      class="flex aspect-[4/3] w-full flex-col items-center justify-center gap-1 rounded-lg border border-outline-gray-2 bg-surface-gray-1 text-ink-gray-4"
    >
      <span class="text-lg">—</span>
      <span class="px-2 text-center text-xs">{{ label }}</span>
    </div>

    <!-- Filled -->
    <div
      v-else
      class="group relative aspect-[4/3] w-full overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-1"
    >
      <img
        :src="value"
        :alt="label"
        class="h-full w-full cursor-pointer object-cover"
        @click="openFullImage"
      />
      <div
        v-if="!disabled"
        class="absolute inset-0 flex items-center justify-center gap-2 bg-black/55 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
      >
        <Button
          size="sm"
          variant="subtle"
          :label="__('Podmień')"
          iconLeft="lucide-refresh-cw"
          @click.stop="showUploader = true"
        />
        <Button
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
      {{ label }}
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
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { Button } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null },
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['change'])

const showUploader = ref(false)

const uploaderOptions = computed(() => ({
  folder: 'Home/Attachments',
  allowMultiple: false,
  restrictions: {
    maxNumberOfFiles: 1,
    allowedFileTypes: ['image/*'],
  },
}))

function onAfterUpload(uploadedFiles) {
  if (uploadedFiles && uploadedFiles.length) {
    emit('change', uploadedFiles[0].file_url)
  }
}

function removePhoto() {
  emit('change', null)
}

function openFullImage() {
  if (props.value) window.open(props.value, '_blank', 'noopener')
}
</script>
