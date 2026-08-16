<template>
  <div class="flex h-full flex-col gap-6 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4 px-2 pt-2">
      <div class="flex flex-col gap-1">
        <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
          {{ __('Karty paneli') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Katalog kart producenckich paneli PV. Dostępność rotuje się przełącznikiem Aktywna / Nieaktywna. Karta, której nie użyła żadna szansa, może zostać trwale usunięta; karta już użyta — nie.',
            )
          }}
        </p>
      </div>
      <Button
        :label="__('Dodaj kartę')"
        variant="solid"
        icon-left="plus"
        @click="openCreateDialog"
      />
    </div>

    <ErrorMessage class="mx-2" :message="listError" />

    <!-- Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 px-2">
      <div
        v-for="karta in state.karty"
        :key="karta.name"
        class="flex flex-col gap-3 rounded-lg border p-4"
        :class="
          karta.aktywny
            ? 'bg-surface-white border-outline-green-3'
            : 'bg-surface-gray-1 opacity-70'
        "
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col">
            <div
              class="text-base-semibold"
              :class="karta.aktywny ? 'text-ink-gray-9' : 'text-ink-gray-8'"
            >
              {{ karta.nazwa }}
            </div>
            <div class="text-p-sm text-ink-gray-6">{{ karta.model }}</div>
          </div>
          <div
            class="text-xs-medium px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap"
            :class="
              karta.aktywny
                ? 'bg-surface-green-2 text-ink-green-3'
                : 'bg-surface-gray-3 text-ink-gray-5'
            "
          >
            {{ karta.aktywny ? __('Aktywna') : __('Nieaktywna') }}
          </div>
        </div>

        <div class="flex flex-col gap-1 text-p-sm text-ink-gray-7">
          <div>{{ __('Moc: {0} Wp', [karta.moc_wp]) }}</div>
          <div>{{ __('Cena: {0}', [formatPln(karta.cena_jednostkowa_netto)]) }}</div>
          <div v-if="karta.gwarancja_tekst">
            {{ __('Gwarancja: {0} lat', [karta.gwarancja_tekst]) }}
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-1">
          <Button
            :label="__('Edytuj')"
            variant="subtle"
            icon-left="edit-2"
            @click="openEditDialog(karta)"
          />
          <Button
            :label="karta.aktywny ? __('Dezaktywuj') : __('Aktywuj')"
            :variant="karta.aktywny ? 'subtle' : 'solid'"
            :theme="karta.aktywny ? 'gray' : undefined"
            :loading="toggleAktywnosc.loading && togglingName === karta.name"
            @click="toggleCard(karta)"
          />
          <Button
            :label="__('Usuń')"
            variant="subtle"
            theme="red"
            icon-left="trash-2"
            :loading="deleteCard.loading && deletingName === karta.name"
            @click="openDeleteDialog(karta)"
          />
        </div>
      </div>

      <div
        v-if="listResource.loading && !state.karty.length"
        class="text-p-sm text-ink-gray-5 px-2"
      >
        {{ __('Wczytywanie…') }}
      </div>
      <div
        v-else-if="!listResource.loading && !state.karty.length"
        class="text-p-sm text-ink-gray-5 px-2"
      >
        {{ __('Brak kart paneli PV. Dodaj pierwszą kartę.') }}
      </div>
    </div>

    <!-- Create/edit dialog -->
    <Dialog v-model:open="showFormDialog" :title="formDialogTitle" :size="'md'" @close="closeFormDialog">
      <template #default>
        <div class="flex flex-col gap-4">
          <FormControl
            v-model="form.nazwa"
            type="text"
            :label="__('Producent (nazwa)')"
            placeholder="AIKO"
            :disabled="saveCard.loading"
          />
          <FormControl
            v-model="form.model"
            type="text"
            :label="__('Model')"
            placeholder="A600-MAH54Mb"
            :disabled="saveCard.loading"
          />
          <div class="grid grid-cols-2 gap-4">
            <FormControl
              v-model="form.moc_wp"
              type="number"
              :label="__('Moc (Wp)')"
              placeholder="500"
              :disabled="saveCard.loading"
            />
            <FormControl
              v-model="form.cena_jednostkowa_netto"
              type="number"
              :label="__('Cena jednostkowa netto (zł)')"
              placeholder="360.00"
              :disabled="saveCard.loading"
            />
          </div>
          <FormControl
            v-model="form.gwarancja_tekst"
            type="text"
            :label="__('Gwarancja')"
            placeholder="25/30"
            :disabled="saveCard.loading"
          />
          <FormControl
            v-model="form.sort"
            type="number"
            :label="__('Kolejność sortowania')"
            placeholder="0"
            :disabled="saveCard.loading"
          />
          <ErrorMessage :message="formError" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="closeFormDialog" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            :loading="saveCard.loading"
            @click="submitForm"
          />
        </div>
      </template>
    </Dialog>

    <!-- Delete confirmation dialog -->
    <Dialog
      v-model:open="showDeleteDialog"
      :title="__('Usuń kartę panelu')"
      :size="'md'"
      @close="closeDeleteDialog"
    >
      <template #default>
        <div class="flex flex-col gap-4">
          <p class="text-p-base text-ink-gray-7">
            {{
              __(
                'Ta operacja jest nieodwracalna. Karta {0} zostanie trwale usunięta z katalogu. Karty użytej już w jakiejkolwiek szansie nie da się usunąć — w takim wypadku użyj akcji Dezaktywuj.',
                [deleteTarget?.nazwa || ''],
              )
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
            :loading="deleteCard.loading"
            @click="confirmDelete"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { createResource, toast, Dialog, ErrorMessage } from 'frappe-ui'
import { formatPln } from '@/utils/money'

// Reactive state declares every key up front and is always replaced with a
// fresh array on update — never gated on key presence (see CLAUDE.md:
// hasOwnProperty on a reactive() object breaks Vue's dependency tracking
// and froze the CP admin panel for its entire lifetime).
const state = reactive({ karty: [] })
const listError = ref('')

const listResource = createResource({
  url: 'crm.api.volteo_panele.volteo_panele_lista',
  auto: true,
  onSuccess: (data) => {
    state.karty = data.karty || []
    listError.value = ''
  },
  onError: (err) => {
    listError.value = err?.messages?.[0] || __('Nie udało się wczytać kart paneli')
  },
})

// --- Create/edit dialog --------------------------------------------------

function emptyForm() {
  return {
    docname: '',
    nazwa: '',
    model: '',
    moc_wp: '',
    cena_jednostkowa_netto: '',
    gwarancja_tekst: '',
    sort: '',
  }
}

const form = reactive(emptyForm())
const formError = ref('')
const showFormDialog = ref(false)
const isEditing = computed(() => Boolean(form.docname))
const formDialogTitle = computed(() =>
  isEditing.value ? __('Edytuj kartę panelu') : __('Nowa karta panelu'),
)

function openCreateDialog() {
  Object.assign(form, emptyForm())
  formError.value = ''
  showFormDialog.value = true
}

function openEditDialog(karta) {
  Object.assign(form, {
    docname: karta.name,
    nazwa: karta.nazwa || '',
    model: karta.model || '',
    moc_wp: karta.moc_wp ?? '',
    cena_jednostkowa_netto: karta.cena_jednostkowa_netto ?? '',
    gwarancja_tekst: karta.gwarancja_tekst || '',
    sort: karta.sort ?? '',
  })
  formError.value = ''
  showFormDialog.value = true
}

function closeFormDialog() {
  showFormDialog.value = false
  Object.assign(form, emptyForm())
  formError.value = ''
}

// Merge a saved/toggled card back into state.karty, replacing the array so
// the change is always seen (add on create, replace in place on update).
function upsertCard(karta) {
  const idx = state.karty.findIndex((k) => k.name === karta.name)
  if (idx === -1) {
    state.karty = [...state.karty, karta]
  } else {
    state.karty = state.karty.map((k) => (k.name === karta.name ? karta : k))
  }
}

const saveCard = createResource({
  url: 'crm.api.volteo_panele.volteo_panel_zapisz',
  makeParams: () => ({
    docname: form.docname || undefined,
    nazwa: form.nazwa.trim(),
    model: form.model.trim(),
    moc_wp: form.moc_wp,
    cena_jednostkowa_netto: form.cena_jednostkowa_netto,
    gwarancja_tekst: form.gwarancja_tekst.trim(),
    sort: form.sort,
  }),
  onSuccess: (data) => {
    upsertCard(data.karta)
    toast.success(
      isEditing.value
        ? __('Karta {0} została zaktualizowana', [data.karta.nazwa])
        : __('Karta {0} została utworzona', [data.karta.nazwa]),
    )
    closeFormDialog()
  },
  onError: (err) => {
    formError.value = err?.messages?.[0] || __('Nie udało się zapisać karty')
  },
})

function submitForm() {
  formError.value = ''

  if (!form.nazwa.trim()) {
    formError.value = __('Podaj nazwę producenta')
    return
  }
  const moc = Number(form.moc_wp)
  if (!Number.isFinite(moc) || moc <= 0) {
    formError.value = __('Moc (Wp) musi być liczbą większą od zera')
    return
  }
  const cena = Number(form.cena_jednostkowa_netto)
  if (!Number.isFinite(cena) || cena < 0) {
    formError.value = __('Cena jednostkowa netto nie może być ujemna')
    return
  }

  saveCard.submit()
}

// --- Toggle aktywny --------------------------------------------------------

const togglingName = ref('')

const toggleAktywnosc = createResource({
  url: 'crm.api.volteo_panele.volteo_panel_aktywnosc',
  onSuccess: (data) => {
    upsertCard(data.karta)
    togglingName.value = ''
  },
  onError: (err) => {
    togglingName.value = ''
    toast.error(err?.messages?.[0] || __('Nie udało się zmienić dostępności karty'))
  },
})

function toggleCard(karta) {
  togglingName.value = karta.name
  toggleAktywnosc.submit({
    name: karta.name,
    aktywny: karta.aktywny ? 0 : 1,
  })
}

// --- Delete card -------------------------------------------------------

const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleteError = ref('')
const deletingName = ref('')

const deleteCard = createResource({
  url: 'crm.api.volteo_panele.volteo_panel_usun',
  onSuccess: (data) => {
    state.karty = state.karty.filter((k) => k.name !== data.usunieto)
    toast.success(__('Karta {0} została usunięta', [deleteTarget.value?.nazwa || '']))
    deletingName.value = ''
    closeDeleteDialog()
  },
  onError: (err) => {
    deletingName.value = ''
    deleteError.value = err?.messages?.[0] || __('Nie udało się usunąć karty')
  },
})

function openDeleteDialog(karta) {
  deleteTarget.value = karta
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
  deletingName.value = deleteTarget.value.name
  deleteCard.submit({ name: deleteTarget.value.name })
}
</script>
