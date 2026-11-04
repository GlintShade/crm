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
      <div class="max-h-72 overflow-y-auto">
        <TaskArea :tasks="tasks.data" :modalRef="taskHandlers" />
      </div>
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
import { podsumowanieZadan } from '@/utils/panelBoczny'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  karty: { type: Boolean, default: false },
  // Karta zadan startuje zwinieta przy kazdym wejsciu na rekord.
  startZwiniete: { type: Boolean, default: false },
})

const otwarte = ref(!props.startZwiniete)
const podsumowanie = computed(() => {
  const lista = tasks.data || []
  const otwartych = lista.filter(
    (t) => !['Done', 'Canceled'].includes(t.status),
  ).length
  return podsumowanieZadan(lista.length, otwartych)
})

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

function updateTaskStatus(status, task) {
  call('frappe.client.set_value', {
    doctype: 'CRM Task',
    name: task.name,
    fieldname: 'status',
    value: status,
  }).then(() => {
    tasks.reload()
  })
}

const taskHandlers = { showTask, deleteTask, updateTaskStatus }
</script>
