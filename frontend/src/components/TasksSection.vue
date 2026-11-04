<template>
  <!-- Wariant kart (panel szansy i leada, ops#326): brak zadan to jeden wiersz
       karty, z zadaniami karta z podsumowaniem i lista. -->
  <div v-if="karty" class="shrink-0 px-3 pb-2 pt-3">
    <div
      v-if="!tasks.data?.length"
      class="flex min-w-0 items-center gap-2 rounded-lg border border-outline-gray-1 bg-surface-white py-2 pl-3 pr-2"
      data-testid="karta-zadania"
    >
      <div class="flex min-w-0 flex-1 flex-col gap-px">
        <div class="text-[13px] font-semibold text-ink-gray-9">{{ __('Zadania') }}</div>
        <div class="truncate text-[11.5px] text-ink-gray-5">{{ __('Brak zadań') }}</div>
      </div>
      <Button variant="ghost" class="w-7" icon="lucide-plus" @click="showTask()" />
    </div>
    <KartaSekcji
      v-else
      :label="__('Zadania')"
      nazwa="zadania"
      :summary="podsumowanie"
      :opened="otwarte"
      @toggle="otwarte = !otwarte"
    >
      <template #actions>
        <Button variant="ghost" class="w-7" icon="lucide-plus" @click="showTask()" />
      </template>
      <div
        v-if="!podzial.otwarte.length"
        class="flex items-center gap-1.5 py-1 text-[12.5px] text-ink-gray-5"
        data-testid="zadania-wszystkie-zakonczone"
      >
        <span class="lucide-check size-4 shrink-0 text-ink-green-3" aria-hidden="true" />
        {{ __('Wszystkie zadania zakończone.') }}
      </div>
      <div v-else class="max-h-72 overflow-y-auto">
        <TaskArea
          :tasks="podzial.otwarte"
          :modalRef="taskHandlers"
          :przejsciowe="przejsciowe"
          :dataZalozenia="true"
        />
      </div>
      <template v-if="podzial.zakonczone.length">
        <button
          type="button"
          class="mt-1 flex w-full items-center gap-1 border-t border-dashed border-outline-gray-2 pt-1.5 text-left text-[12px] text-ink-gray-5 hover:text-ink-gray-8"
          data-testid="pokaz-zakonczone"
          @click="pokazZakonczone = !pokazZakonczone"
        >
          <span
            :class="[
              pokazZakonczone ? 'lucide-chevron-down' : 'lucide-chevron-right',
              'size-3.5 shrink-0',
            ]"
            aria-hidden="true"
          />
          {{
            pokazZakonczone
              ? __('Ukryj zakończone') + ` (${podzial.zakonczone.length})`
              : __('Pokaż zakończone') + ` (${podzial.zakonczone.length})`
          }}
        </button>
        <ZakonczoneZadania
          v-if="pokazZakonczone"
          :tasks="podzial.zakonczone"
          :modalRef="taskHandlers"
        />
      </template>
    </KartaSekcji>
  </div>
  <div v-else class="section flex flex-col">
    <div class="w-full section-border h-px border-t" />
    <div class="p-1 sm:p-3">
      <CollapsibleSection
        labelClass="px-2 font-semibold"
        headerClass="h-8"
        :label="__('Tasks')"
        :count="tasks.data?.length || undefined"
        :opened="true"
      >
        <template #actions>
          <Button
            variant="ghost"
            class="w-7 mr-2"
            icon="lucide-plus"
            @click="showTask()"
          />
        </template>
        <div v-if="tasks.data?.length" class="max-h-72 overflow-y-auto px-1">
          <TaskArea :tasks="tasks.data" :modalRef="taskHandlers" />
        </div>
        <div
          v-else
          class="flex h-16 items-center justify-center text-base text-ink-gray-5"
        >
          {{ __('No Tasks') }}
        </div>
      </CollapsibleSection>
    </div>
  </div>
</template>
<script setup>
import TaskArea from '@/components/Activities/TaskArea.vue'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { createResource, call, Button } from 'frappe-ui'
import KartaSekcji from '@/components/KartaSekcji.vue'
import ZakonczoneZadania from '@/components/ZakonczoneZadania.vue'
import { podsumowanieZadan, podzielZadania } from '@/utils/panelBoczny'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  karty: { type: Boolean, default: false },
  // Karta zadan startuje zwinieta przy kazdym wejsciu na rekord.
  startZwiniete: { type: Boolean, default: false },
})

const otwarte = ref(!props.startZwiniete)
const pokazZakonczone = ref(false)

// Stan przejsciowy (5 s) po oznaczeniu zadania jako zakonczone: wiersz zostaje
// na liscie otwartych z linkiem "Cofnij". nazwa -> { poprzedni }.
const CZAS_COFNIECIA_MS = 5000
const przejsciowe = reactive({})
const timery = {}

function wyczyscPrzejsciowe(name) {
  clearTimeout(timery[name])
  delete timery[name]
  delete przejsciowe[name]
}
function wyczyscWszystkiePrzejsciowe() {
  Object.keys(timery).forEach(wyczyscPrzejsciowe)
}

const podzial = computed(() =>
  podzielZadania(tasks.data || [], new Set(Object.keys(przejsciowe))),
)
const podsumowanie = computed(() =>
  podsumowanieZadan(podzial.value.otwarte.length, podzial.value.zakonczone.length),
)

const { showModal } = useDoctypeModal()

const tasks = createResource({
  url: 'frappe.client.get_list',
  makeParams: () => ({
    doctype: 'CRM Task',
    filters: {
      reference_doctype: props.doctype,
      reference_docname: props.docname,
    },
    fields: [
      'name',
      'title',
      'description',
      'assigned_to',
      'due_date',
      'priority',
      'status',
      'modified',
      'creation',
    ],
    order_by: 'modified desc',
    limit_page_length: 0,
  }),
  auto: true,
})

watch(
  () => props.docname,
  () => {
    if (props.startZwiniete) otwarte.value = false
    pokazZakonczone.value = false
    wyczyscWszystkiePrzejsciowe()
    tasks.reload()
  },
)

function showTask(task) {
  showModal({
    name: task?.name,
    doctype: 'CRM Task',
    title: 'Task',
    defaults: {
      reference_doctype: props.doctype,
      reference_docname: props.docname,
    },
    callbacks: {
      afterInsert: () => tasks.reload(),
      afterUpdate: () => tasks.reload(),
    },
  })
}

async function deleteTask(name) {
  await call('frappe.client.delete', {
    doctype: 'CRM Task',
    name,
  })
  tasks.reload()
}

function zapiszStatus(task, status) {
  return call('frappe.client.set_value', {
    doctype: 'CRM Task',
    name: task.name,
    fieldname: 'status',
    value: status,
  })
}

function updateTaskStatus(status, task) {
  const koniec = ['Done', 'Canceled'].includes(status)
  const bylOtwarty = !['Done', 'Canceled'].includes(task.status)
  const poprzedni = task.status
  zapiszStatus(task, status).then(() => {
    if (koniec && bylOtwarty) {
      wyczyscPrzejsciowe(task.name)
      przejsciowe[task.name] = { poprzedni }
      timery[task.name] = setTimeout(
        () => wyczyscPrzejsciowe(task.name),
        CZAS_COFNIECIA_MS,
      )
    } else {
      wyczyscPrzejsciowe(task.name)
    }
    tasks.reload()
  })
}

function cofnijStatus(task) {
  const poprzedni = przejsciowe[task.name]?.poprzedni || 'Todo'
  wyczyscPrzejsciowe(task.name)
  zapiszStatus(task, poprzedni).then(() => tasks.reload())
}

function przywrocZadanie(task) {
  zapiszStatus(task, 'Todo').then(() => tasks.reload())
}

onBeforeUnmount(wyczyscWszystkiePrzejsciowe)

const taskHandlers = {
  showTask,
  deleteTask,
  updateTaskStatus,
  cofnijStatus,
  przywrocZadanie,
}
</script>
