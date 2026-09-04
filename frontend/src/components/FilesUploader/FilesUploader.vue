<template>
  <Dialog v-model:open="show" :title="__('Attach')" :size="'xl'">
    <template #default>
      <FilesUploaderArea
        ref="filesUploaderArea"
        v-model="files"
        :doctype="doctype"
        :options="options"
      />
    </template>
    <template #actions>
      <div class="flex justify-between">
        <div class="flex gap-2">
          <Button
            v-if="files.length"
            variant="subtle"
            :label="__('Remove All')"
            :disabled="fileUploadStarted"
            @click="removeAllFiles"
          />
          <Button
            v-if="
              filesUploaderArea?.showWebLink || filesUploaderArea?.showCamera
            "
            :label="isMobileView ? __('Back') : __('Back to File Upload')"
            iconLeft="arrow-left"
            @click="
              () => {
                filesUploaderArea.showWebLink = false
                filesUploaderArea.showCamera = false
                filesUploaderArea.webLink = null
                filesUploaderArea.cameraImage = null
              }
            "
          />
          <Button
            v-if="
              filesUploaderArea?.showCamera && !filesUploaderArea?.cameraImage
            "
            :label="__('Switch Camera')"
            @click="() => filesUploaderArea.switchCamera()"
          />
          <Button
            v-if="filesUploaderArea?.cameraImage"
            :label="__('Retake')"
            @click="filesUploaderArea.cameraImage = null"
          />
        </div>
        <div class="flex gap-2">
          <Button
            v-if="!filesUploaderArea?.showCamera"
            variant="solid"
            :label="__('Attach')"
            :loading="fileUploadStarted"
            :disabled="disableAttachButton"
            @click="attachFiles"
          />
          <Button
            v-if="
              filesUploaderArea?.showCamera && filesUploaderArea?.cameraImage
            "
            variant="solid"
            :label="__('Upload')"
            @click="() => filesUploaderArea.uploadViaCamera()"
          />
          <Button
            v-if="
              filesUploaderArea?.showCamera && !filesUploaderArea?.cameraImage
            "
            variant="solid"
            :label="__('Capture')"
            @click="() => filesUploaderArea.captureImage()"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import FilesUploaderArea from '@/components/FilesUploader/FilesUploaderArea.vue'
import FilesUploadHandler from './filesUploaderHandler'
import { isMobileView } from '@/composables/settings'
import { sprawdzTrzon, zlozNazwe } from '@/utils/zalaczniki'
import { toast } from 'frappe-ui'
import { ref, computed } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  fieldname: { type: String, default: '' },
  options: {
    type: Object,
    default: () => ({
      folder: 'Home/Attachments',
    }),
  },
})

const emit = defineEmits(['after'])
// 'after' payload: array of uploaded file objects (each has file_url, file_name, name, ...)

const show = defineModel({ type: Boolean })

const filesUploaderArea = ref(null)
const files = ref([])

function removeAllFiles() {
  files.value = []
}

const disableAttachButton = computed(() => {
  if (filesUploaderArea.value?.showCamera) {
    return !filesUploaderArea.value.cameraImage
  }
  if (filesUploaderArea.value?.showWebLink) {
    return !filesUploaderArea.value.webLink
  }
  return !files.value.length
})

function attachFiles() {
  if (filesUploaderArea.value.showWebLink) {
    return uploadViaWebLink()
  }
  // Walidacja WSZYSTKICH edytowalnych nazw plików przed uploadem — jeśli
  // którykolwiek trzon jest niepoprawny, żaden plik nie wychodzi (issue
  // ops#74). Komunikaty lustrzane wobec serwerowych z
  // crm/volteo_zalaczniki.py.
  let maBlad = false
  files.value.forEach((file) => {
    const blad = sprawdzTrzon(file.trzon, file.rozszerzenie)
    file.errorMessage = blad
    if (blad) maBlad = true
  })
  if (maBlad) return

  // Świeża próba wysyłki — zdejmij ewentualny znacznik błędu z
  // poprzedniej, żeby wiersz znów pokazywał normalny pasek postępu
  // zamiast zostać zablokowany na koszu (ops#78).
  files.value.forEach((file) => {
    file.failed = false
  })

  files.value.forEach((file, i) => attachFile(file, i))
}

function uploadViaWebLink() {
  let fileUrl = filesUploaderArea.value.webLink
  if (!fileUrl) {
    toast.error(__('Please enter a valid URL'))
    return
  }
  fileUrl = decodeURI(fileUrl)
  show.value = false
  return attachFile({
    fileUrl,
  })
}

const uploader = ref(null)
const fileUploadStarted = ref(false)
const uploadedFiles = ref([])

// Serwer może odrzucić plik (np. ValidationError z hooka nazw systemowych)
// PO TYM, jak wszystkie bajty już dotarły — `file.uploaded` zdąży
// zrównać się z `file.total` zanim przyjdzie błąd. Bez tego resetu wiersz
// zostawał z zielonym znacznikiem ukończenia (pasek liczy się po
// uploaded==total, nie po sukcesie), a przycisk „Załącz” kręcił się w
// nieskończoność, bo `fileUploadStarted` nigdy nie wracał do false
// (ops#78).
function oznaczBlad(file, komunikat) {
  file.uploading = false
  file.failed = true
  // `undefined`, nie `0` — odtwarza stan początkowy wrappera z addFiles()
  // (bez klucza `uploaded`), żeby `uploaded == total` nie było prawdziwe
  // i pasek nie mignął na zielono, zanim przyjdzie pierwszy event 'progress'.
  file.uploaded = undefined
  file.total = 0
  file.errorMessage = komunikat
  fileUploadStarted.value = false
}

function attachFile(file, i) {
  const args = {
    fileObj: file.fileObj || {},
    type: file.type,
    private: file.private,
    fileUrl: file.fileUrl,
    folder: props.options.folder,
    doctype: props.doctype,
    docname: props.docname,
    fieldname: props.fieldname,
  }

  uploader.value = new FilesUploadHandler()

  uploader.value.on('start', () => {
    file.uploading = true
    fileUploadStarted.value = true
  })
  uploader.value.on('progress', (data) => {
    file.uploaded = data.uploaded
    file.total = data.total
  })
  uploader.value.on('error', (error) => {
    oznaczBlad(file, error || 'Error Uploading File')
  })
  uploader.value.on('finish', () => {
    file.uploading = false
  })

  // Wysyłamy kopię wrappera z nazwą złożoną z (ewentualnie zmienionego)
  // trzonu — callbacki wyżej nadal mutują oryginalny `file` z domknięcia,
  // to `filesUploaderHandler.ts` czyta tylko `.name` z pierwszego argumentu.
  uploader.value
    .upload({ ...file, name: zlozNazwe(file.trzon, file.rozszerzenie) }, args || {})
    .then((response) => {
      uploadedFiles.value.push(response)
      if (i === files.value.length - 1) {
        const uploaded = uploadedFiles.value.slice()
        uploadedFiles.value = []
        files.value = []
        show.value = false
        fileUploadStarted.value = false
        emit('after', uploaded)
      }
    })
    .catch((error) => {
      let errorMessage = 'Error Uploading File'
      if (error?._server_messages) {
        errorMessage = JSON.parse(JSON.parse(error._server_messages)[0]).message
      } else if (error?.exc) {
        errorMessage = JSON.parse(error.exc)[0].split('\n').slice(-2, -1)[0]
      } else if (typeof error === 'string') {
        errorMessage = error
      }
      oznaczBlad(file, errorMessage)
    })
}
</script>
