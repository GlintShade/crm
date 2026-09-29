<template>
  <div v-if="tasks.length">
    <div v-for="(task, i) in tasks" :key="task.name">
      <div
        class="activity flex cursor-pointer gap-3 rounded p-2.5 duration-300 ease-in-out hover:bg-surface-gray-1"
        @click="modalRef.showTask(task)"
      >
        <div class="flex min-w-0 flex-1 flex-col gap-1 text-base">
          <div class="truncate font-medium text-ink-gray-9" :title="task.title">
            {{ task.title }}
          </div>
          <div
            v-if="task.assigned_to"
            class="flex min-w-0 items-center gap-1.5 text-ink-gray-8"
          >
            <UserAvatar :user="task.assigned_to" size="xs" />
            <span class="truncate">{{ getUser(task.assigned_to).full_name }}</span>
          </div>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-gray-5">
            <div
              v-if="task.due_date"
              class="flex items-center gap-1.5"
              :class="terminPrzeterminowany(task) ? 'text-ink-red-4' : ''"
              :title="formatujTermin(task.due_date)"
            >
              <CalendarIcon class="h-3.5 w-3.5 shrink-0" />
              {{ formatujTerminKrotko(task.due_date) }}
            </div>
            <div class="flex items-center gap-1.5">
              <TaskPriorityIcon class="!h-2 !w-2" :priority="task.priority" />
              {{ __(task.priority) }}
            </div>
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1 self-start">
          <Dropdown
            :options="taskStatusOptions(modalRef.updateTaskStatus, task)"
          >
            <Button
              :tooltip="__('Change Status')"
              variant="ghosted"
              class="hover:bg-surface-gray-4"
              @click.stop.prevent
            >
              <TaskStatusIcon :status="task.status" />
            </Button>
          </Dropdown>
          <Dropdown
            :options="[
              {
                label: __('Delete'),
                icon: 'trash-2',
                onClick: () => {
                  $dialog({
                    title: __('Delete Task'),
                    message: __('Are you sure you want to delete this task?'),
                    actions: [
                      {
                        label: __('Delete'),
                        theme: 'red',
                        variant: 'solid',
                        onClick(close) {
                          modalRef.deleteTask(task.name)
                          close()
                        },
                      },
                    ],
                  })
                },
              },
            ]"
          >
            <Button
              icon="lucide-more-horizontal"
              variant="ghosted"
              class="hover:bg-surface-gray-4 text-ink-gray-9"
              @click.stop.prevent
            />
          </Dropdown>
        </div>
      </div>
      <div
        v-if="i < tasks.length - 1"
        class="mx-2 h-px border-t border-outline-elevation-2"
      />
    </div>
  </div>
</template>
<script setup>
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { taskStatusOptions } from '@/utils'
import { formatujTermin, formatujTerminKrotko, terminWzgledny } from '@/utils/dataPolska'
import { usersStore } from '@/stores/users'
import { globalStore } from '@/stores/global'
import { Dropdown } from 'frappe-ui'

defineProps({
  tasks: { type: Array, default: () => [] },
  modalRef: { type: Object, default: () => ({}) },
})

const { getUser } = usersStore()
const { $dialog } = globalStore()

// Wiersz zadania w waskim panelu bocznym (TasksSection.vue, ok. 360 px) -
// termin na czerwono tylko gdy faktycznie minal I zadanie nie jest juz
// zamkniete (Done/Canceled), zeby stare zakonczone zadania nie straszyly
// czerwienia bez powodu.
function terminPrzeterminowany(task) {
  if (task.status === 'Done' || task.status === 'Canceled') return false
  return terminWzgledny(task.due_date).startsWith('Termin minął')
}
</script>
