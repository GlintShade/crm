<template>
  <div class="section flex flex-col">
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
import { watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
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
  () => tasks.reload(),
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
