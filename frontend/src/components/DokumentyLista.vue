<!--
  Biblioteka dokumentów (Dokumenty OZE / Dokumenty Czyste Powietrze) — jeden
  komponent obsługuje oba tryby (VOLTEO: kilka spójnych plików zamiast wielu
  drobnych, patrz CLAUDE.md).

  OZE: płaska lista uniwersalnych dokumentów.
  Czyste Powietrze: rep wybiera swoje województwa (zapisywane po stronie
  serwera), wybrane renderują się jako kafelki-foldery; kliknięcie kafelka
  otwiera listę plików tego województwa.

  Uprawnienia: serwer zwraca `czy_admin` w odpowiedzi listy — bramkujemy
  wyłącznie na tej wartości, czytanej wprost z jawnie zadeklarowanego stanu
  (nigdy przez hasOwnProperty na obiekcie reactive — pułapka udokumentowana
  w CLAUDE.md, przez którą panel administratora CP nie renderował się od
  początku istnienia funkcji).
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-4xl flex-col gap-4">
      <ErrorMessage class="mx-2" :message="listError" />

      <div v-if="initialLoading" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __('Wczytywanie…') }}
      </div>

      <template v-else>
        <!-- Czyste Powietrze: wybór województw + kafelki folderów -->
        <template v-if="linia === 'Czyste Powietrze' && !selectedFolder">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="text-lg-semibold text-ink-gray-8">
              {{ __('Dokumenty Czyste Powietrze') }}
            </div>
            <div class="flex flex-col items-end gap-1.5">
              <div class="text-sm text-ink-gray-6">{{ __('Wybierz swoje województwa') }}</div>
              <div ref="wojDropdownRoot" class="relative">
                <Button
                  id="dokumenty-woj-toggle-btn"
                  variant="outline"
                  :label="__('Wybrane województwa ({0})', [selectedWojewodztwa.length])"
                  icon-left="map-pin"
                  @click="showWojDropdown = !showWojDropdown"
                />
                <div
                  v-if="showWojDropdown"
                  class="absolute right-0 z-20 mt-1 w-64 rounded-lg border border-outline-gray-2 bg-surface-elevation-2 shadow-lg"
                >
                  <ul class="max-h-72 overflow-y-auto p-1.5">
                    <li
                      v-for="woj in stan.wojewodztwaOpcje"
                      :key="woj"
                      class="flex cursor-pointer items-center gap-2 rounded p-1.5 hover:bg-surface-gray-1"
                      @click="toggleWojewodztwo(woj)"
                    >
                      <CheckIcon
                        class="size-4 shrink-0"
                        :class="selectedWojewodztwa.includes(woj) ? 'opacity-100' : 'opacity-0'"
                      />
                      <span class="capitalize truncate text-sm text-ink-gray-8">{{ woj }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="!selectedWojewodztwa.length"
            class="py-10 text-center text-sm text-ink-gray-5"
          >
            {{ __('Wybierz województwa, aby zobaczyć katalogi dokumentów') }}
          </div>
          <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <button
              v-for="woj in wybraneWojewodztwaUporzadkowane"
              :key="woj"
              type="button"
              class="flex flex-col items-start gap-2 rounded-lg border border-outline-gray-2 p-4 text-left transition-colors hover:bg-surface-gray-1"
              @click="openFolder(woj)"
            >
              <FeatherIcon name="folder" class="h-6 w-6 text-ink-gray-6" />
              <div class="w-full capitalize truncate text-sm-medium text-ink-gray-8">{{ woj }}</div>
              <div class="text-p-sm text-ink-gray-5">
                {{
                  folderDocCount(woj)
                    ? __('{0} dok.', [folderDocCount(woj)])
                    : __('Brak dokumentów')
                }}
              </div>
              <Badge
                v-if="stan.foldery[woj]?.ostatnia_aktualizacja"
                :theme="folderIsNew(woj) ? 'blue' : 'gray'"
                variant="subtle"
                size="sm"
                :label="ostatniaAktualizacjaLabel(stan.foldery[woj].ostatnia_aktualizacja)"
              />
            </button>
          </div>
        </template>

        <!-- Lista plików: korzeń OZE, albo wnętrze folderu CP -->
        <template v-else>
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <Button
                v-if="linia === 'Czyste Powietrze'"
                variant="ghost"
                icon-left="arrow-left"
                :label="__('Wróć')"
                @click="backToFolders"
              />
              <div
                class="text-lg-semibold text-ink-gray-8"
                :class="{ capitalize: linia === 'Czyste Powietrze' }"
              >
                {{ linia === 'Czyste Powietrze' ? selectedFolder : __('Dokumenty OZE') }}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <Button
                :label="__('Pobierz komplet (ZIP)')"
                icon-left="download"
                :disabled="!visibleDocsWithFile.length"
                @click="handleDownloadZip"
              />
              <Button
                v-if="stan.czyAdmin"
                :label="__('Dodaj dokument')"
                variant="solid"
                icon-left="plus"
                @click="openAddDialog"
              />
            </div>
          </div>

          <div v-if="!visibleDocs.length" class="py-10 text-center text-sm text-ink-gray-5">
            {{ __('Brak dokumentów.') }}
          </div>
          <div v-else class="flex flex-col gap-2">
            <div
              v-for="doc in visibleDocs"
              :key="doc.name"
              class="flex items-center gap-3 rounded-lg border border-outline-gray-2 p-3 transition-colors"
              :class="doc.plik ? 'cursor-pointer hover:bg-surface-gray-1' : 'cursor-not-allowed opacity-70'"
              @click="doc.plik && openDocument(doc)"
            >
              <FeatherIcon name="file-text" class="h-5 w-5 shrink-0 text-ink-gray-6" />
              <div class="flex min-w-0 flex-1 flex-col gap-0.5">
                <div class="truncate text-sm-medium text-ink-gray-8">{{ doc.tytul }}</div>
                <div class="flex items-center gap-2">
                  <Badge
                    v-if="doc.zaktualizowano"
                    :theme="doc.nowosc ? 'blue' : 'gray'"
                    variant="subtle"
                    size="sm"
                    :label="ostatniaAktualizacjaLabel(doc.zaktualizowano)"
                  />
                  <span v-else class="text-p-sm text-ink-gray-4">—</span>
                  <Badge
                    v-if="!doc.plik"
                    theme="gray"
                    variant="subtle"
                    size="sm"
                    :label="__('Brak pliku')"
                  />
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-1" @click.stop>
                <Button
                  v-if="doc.plik"
                  variant="ghost"
                  :label="__('Pobierz')"
                  icon-left="download"
                  @click="downloadDocument(doc)"
                />
                <template v-if="stan.czyAdmin">
                  <FileUploader
                    :upload-args="{ private: true }"
                    :file-types="['.pdf']"
                    @success="(file) => onReplaceUploaded(doc, file)"
                  >
                    <template #default="{ openFileSelector, uploading }">
                      <Button
                        variant="ghost"
                        :label="__('Zamień')"
                        :loading="uploading || (replaceDocument.loading && replacingName === doc.name)"
                        @click="openFileSelector"
                      />
                    </template>
                  </FileUploader>
                  <Button
                    variant="ghost"
                    theme="red"
                    :label="__('Usuń')"
                    @click="openDeleteDialog(doc)"
                  />
                </template>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>

    <!-- Dodaj dokument -->
    <Dialog v-model:open="showAddDialog" :title="__('Dodaj dokument')" size="md" @close="closeAddDialog">
      <template #default>
        <div class="flex flex-col gap-4">
          <FormControl
            v-model="addForm.tytul"
            type="text"
            :label="__('Tytuł')"
            :disabled="addDocument.loading"
          />
          <FileUploader
            :upload-args="{ private: true }"
            :file-types="['.pdf']"
            @success="(file) => (addForm.plik_url = file.file_url)"
          >
            <template #default="{ openFileSelector, uploading }">
              <Button
                :label="addForm.plik_url ? __('Plik dodany') : __('Załącz plik PDF')"
                :icon-left="addForm.plik_url ? 'check' : 'paperclip'"
                :loading="uploading"
                @click="openFileSelector"
              />
            </template>
          </FileUploader>
          <ErrorMessage :message="addError" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="closeAddDialog" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            :loading="addDocument.loading"
            :disabled="!addForm.tytul.trim() || !addForm.plik_url"
            @click="submitAddDocument"
          />
        </div>
      </template>
    </Dialog>

    <!-- Usuń dokument -->
    <Dialog v-model:open="showDeleteDialog" :title="__('Usuń dokument')" size="md" @close="closeDeleteDialog">
      <template #default>
        <div class="flex flex-col gap-4">
          <p class="text-p-base text-ink-gray-7">
            {{
              __('Dokument {0} zostanie trwale usunięty z katalogu.', [
                deleteTarget?.tytul || '',
              ])
            }}
          </p>
          <ErrorMessage :message="deleteError" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="closeDeleteDialog" />
          <Button
            :label="__('Usuń')"
            variant="solid"
            theme="red"
            :loading="deleteDocument.loading"
            @click="confirmDelete"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import CheckIcon from '@/components/Icons/CheckIcon.vue'
import { onClickOutside } from '@vueuse/core'
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  FileUploader,
  FormControl,
  call,
  createResource,
  dayjs,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  linia: { type: String, required: true },
})

// --- Lista + stan lokalny ----------------------------------------------------
// Kształt deklarowany z góry i zawsze zastępowany nowym obiektem/tablicą przy
// aktualizacji — nigdy mutowany w miejscu (patrz coding-style.md), i nigdy
// bramkowany przez hasOwnProperty (patrz komentarz na górze pliku).
const stan = reactive({
  dokumenty: [],
  foldery: {},
  wojewodztwaUzytkownika: [],
  wojewodztwaOpcje: [],
  czyAdmin: false,
})
const listError = ref('')

const listResource = createResource({
  url: 'crm.api.dokumenty.dokumenty_lista',
  params: { linia: props.linia },
  auto: true,
  onSuccess: (data) => {
    stan.dokumenty = data.dokumenty || []
    stan.foldery = data.foldery || {}
    stan.wojewodztwaUzytkownika = data.wojewodztwa_uzytkownika || []
    stan.wojewodztwaOpcje = data.wojewodztwa_opcje || []
    stan.czyAdmin = Boolean(data.czy_admin)
    listError.value = ''
  },
  onError: (err) => {
    listError.value = extractErrorMessage(err) || __('Nie udało się wczytać dokumentów')
  },
})

const initialLoading = computed(() => listResource.loading && !listResource.data)

function formatDate(value) {
  if (!value) return ''
  return dayjs(value).format('DD.MM.YYYY')
}

function ostatniaAktualizacjaLabel(value) {
  return __('Ostatnia aktualizacja: {0}', [formatDate(value)])
}

function markSeen(rodzaj, klucze) {
  if (!klucze.length) return
  call('crm.api.dokumenty.oznacz_odczyty', {
    rodzaj,
    klucze: JSON.stringify(klucze),
  }).catch(() => {
    // Best-effort: the UI already grayed the note locally. A failed write
    // here only means the note may reappear as "new" after a reload — not
    // worth surfacing as an error to the rep.
  })
}

// --- Tryb Czyste Powietrze: wybór województw + kafelki -----------------------

const selectedFolder = ref(null)
const selectedWojewodztwa = ref([])
const showWojDropdown = ref(false)
const wojDropdownRoot = ref(null)

onClickOutside(
  wojDropdownRoot,
  () => {
    showWojDropdown.value = false
  },
  { ignore: ['#dokumenty-woj-toggle-btn'] },
)

// Seed local selection from the server value whenever it (re)loads. Toggling
// updates selectedWojewodztwa directly without touching stan.wojewodztwaUzytkownika,
// so this watcher never fights the optimistic local update.
watch(
  () => stan.wojewodztwaUzytkownika,
  (val) => {
    selectedWojewodztwa.value = [...val]
  },
  { immediate: true },
)

function toggleWojewodztwo(woj) {
  const has = selectedWojewodztwa.value.includes(woj)
  selectedWojewodztwa.value = has
    ? selectedWojewodztwa.value.filter((w) => w !== woj)
    : [...selectedWojewodztwa.value, woj]

  call('crm.api.dokumenty.zapisz_wojewodztwa', {
    wojewodztwa: JSON.stringify(selectedWojewodztwa.value),
  }).catch(() => {
    toast.error(__('Nie udało się zapisać wyboru województw'))
  })
}

const wybraneWojewodztwaUporzadkowane = computed(() =>
  stan.wojewodztwaOpcje.filter((woj) => selectedWojewodztwa.value.includes(woj)),
)

function folderDocCount(woj) {
  return stan.dokumenty.filter((d) => d.wojewodztwo === woj).length
}

function folderIsNew(woj) {
  return Boolean(stan.foldery[woj]?.folder_nowosc)
}

function openFolder(woj) {
  markSeen('folder', [woj])
  if (stan.foldery[woj]) {
    stan.foldery = { ...stan.foldery, [woj]: { ...stan.foldery[woj], folder_nowosc: false } }
  }
  selectedFolder.value = woj
}

function backToFolders() {
  selectedFolder.value = null
}

// --- Lista plików (OZE root, albo wnętrze folderu CP) -------------------------

const visibleDocs = computed(() => {
  if (props.linia === 'Czyste Powietrze') {
    if (!selectedFolder.value) return []
    return stan.dokumenty.filter((d) => d.wojewodztwo === selectedFolder.value)
  }
  return stan.dokumenty
})

const visibleDocsWithFile = computed(() => visibleDocs.value.filter((d) => d.plik))

const currentWojewodztwo = computed(() =>
  props.linia === 'Czyste Powietrze' ? selectedFolder.value || '' : '',
)

function openDocument(doc) {
  if (!doc.plik) return
  markSeen('dokument', [doc.name])
  setDocSeenLocally(doc.name)
  // Private file served by Frappe under the caller's existing session
  // cookie — a plain relative-URL open is enough, same-origin (precedent:
  // deal/UmowaTab.vue's generatePdf()).
  window.open(doc.plik, '_blank')
}

function downloadDocument(doc) {
  if (!doc.plik) return
  markSeen('dokument', [doc.name])
  setDocSeenLocally(doc.name)
  const a = document.createElement('a')
  a.href = doc.plik
  // Name the saved file after the actual filename (with extension), not
  // the human title — `doc.tytul` alone would save an extension-less file
  // on most browsers.
  a.download = decodeURIComponent(doc.plik.split('/').pop() || '')
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function setDocSeenLocally(name) {
  stan.dokumenty = stan.dokumenty.map((d) => (d.name === name ? { ...d, nowosc: false } : d))
}

function handleDownloadZip() {
  const params = new URLSearchParams({ linia: props.linia })
  if (currentWojewodztwo.value) params.set('wojewodztwo', currentWojewodztwo.value)
  window.open(`/api/method/crm.api.dokumenty.pobierz_zip?${params.toString()}`)

  const keys = visibleDocs.value.filter((d) => d.plik).map((d) => d.name)
  if (!keys.length) return
  markSeen('dokument', keys)
  stan.dokumenty = stan.dokumenty.map((d) => (keys.includes(d.name) ? { ...d, nowosc: false } : d))
}

// --- Admin: Dodaj dokument -----------------------------------------------

const showAddDialog = ref(false)
const addForm = reactive({ tytul: '', plik_url: '' })
const addError = ref('')

function openAddDialog() {
  addForm.tytul = ''
  addForm.plik_url = ''
  addError.value = ''
  showAddDialog.value = true
}

function closeAddDialog() {
  showAddDialog.value = false
  addForm.tytul = ''
  addForm.plik_url = ''
  addError.value = ''
}

const addDocument = createResource({
  url: 'crm.api.dokumenty.dodaj_dokument',
  onSuccess: () => {
    toast.success(__('Dokument dodany'))
    closeAddDialog()
    listResource.reload()
  },
  onError: (err) => {
    addError.value = extractErrorMessage(err) || __('Nie udało się dodać dokumentu')
  },
})

function submitAddDocument() {
  addError.value = ''
  if (!addForm.tytul.trim()) {
    addError.value = __('Podaj tytuł dokumentu')
    return
  }
  if (!addForm.plik_url) {
    addError.value = __('Załącz plik PDF')
    return
  }
  addDocument.submit({
    tytul: addForm.tytul.trim(),
    linia: props.linia,
    plik_url: addForm.plik_url,
    wojewodztwo: currentWojewodztwo.value,
  })
}

// --- Admin: Zamień plik -----------------------------------------------

const replacingName = ref('')

const replaceDocument = createResource({
  url: 'crm.api.dokumenty.zamien_plik',
  onSuccess: () => {
    toast.success(__('Plik podmieniony'))
    replacingName.value = ''
    listResource.reload()
  },
  onError: (err) => {
    replacingName.value = ''
    toast.error(extractErrorMessage(err) || __('Nie udało się podmienić pliku'))
  },
})

function onReplaceUploaded(doc, file) {
  replacingName.value = doc.name
  replaceDocument.submit({ dokument: doc.name, plik_url: file.file_url })
}

// --- Admin: Usuń dokument -----------------------------------------------

const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleteError = ref('')

const deleteDocument = createResource({
  url: 'crm.api.dokumenty.usun_dokument',
  onSuccess: () => {
    toast.success(__('Dokument usunięty'))
    closeDeleteDialog()
    listResource.reload()
  },
  onError: (err) => {
    deleteError.value = extractErrorMessage(err) || __('Nie udało się usunąć dokumentu')
  },
})

function openDeleteDialog(doc) {
  deleteTarget.value = doc
  deleteError.value = ''
  showDeleteDialog.value = true
}

function closeDeleteDialog() {
  showDeleteDialog.value = false
  deleteTarget.value = null
  deleteError.value = ''
}

function confirmDelete() {
  if (!deleteTarget.value) return
  deleteError.value = ''
  deleteDocument.submit({ dokument: deleteTarget.value.name })
}

// --- Helpers -----------------------------------------------------------------------
// Precedent: deal/UmowaTab.vue's extractErrorMessage().
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
        return first.message || ''
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || ''
    }
    if (err && err.messages && err.messages.length) return err.messages[0]
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return ''
}
</script>
