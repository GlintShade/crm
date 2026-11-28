<template>
  <div
    class="activity group flex h-48 cursor-pointer flex-col justify-between gap-2 rounded-md bg-surface-gray-1 px-4 py-3 hover:bg-surface-gray-2"
  >
    <div class="flex items-center justify-between">
      <div class="truncate text-lg-medium text-ink-gray-8">
        {{ note.title }}
      </div>
      <Dropdown
        :options="[
          {
            label: __('Delete'),
            icon: 'trash-2',
            onClick: () => deleteNote(note.name),
          },
        ]"
        class="h-6 w-6"
        @click.stop
      >
        <Button
          icon="lucide-more-horizontal"
          variant="ghosted"
          class="!h-6 !w-6 hover:bg-surface-gray-2"
          @click.stop.prevent
        />
      </Dropdown>
    </div>
    <TextEditor
      v-if="note.content"
      :content="note.content"
      :editable="false"
      editor-class="prose-sm text-p-sm max-w-none text-ink-gray-5 focus:outline-none"
      class="flex-1 overflow-hidden"
    />
    <div class="mt-1 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 truncate">
        <UserAvatar :user="note.owner" size="xs" />
        <div
          class="truncate text-sm text-ink-gray-8"
          :title="getUser(note.owner).full_name"
        >
          {{ getUser(note.owner).full_name }}
        </div>
      </div>
      <div class="shrink-0 text-right">
        <TimelineTimestamp
          :date="note.creation"
          stacked
          class-name="text-sm text-ink-gray-7"
        />
        <div
          v-if="edytowano"
          class="whitespace-nowrap text-xs text-ink-gray-5"
        >
          {{ __('edytowano') }} {{ czasEdycji }}
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import TimelineTimestamp from '@/components/Activities/TimelineTimestamp.vue'
import { Dropdown, TextEditor, call, toast, dayjsLocal } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { dataGodzinaWarszawa, czyEdytowano } from '@/utils/dataPolska'
import { computed } from 'vue'

const props = defineProps({
  note: { type: Object, default: () => ({}) },
})

const notes = defineModel({ type: Object })

const { getUser } = usersStore()

// ops#430: ta sama konwersja co w TimelineTimestamp.vue (surowy tekst -> chwila)
const instant = (x) => (x ? dayjsLocal(x).toDate() : null)
const edytowano = computed(() =>
  czyEdytowano(instant(props.note.creation), instant(props.note.modified)),
)
const czasEdycji = computed(() => dataGodzinaWarszawa(instant(props.note.modified)))

async function deleteNote(name) {
  await toast.promise(
    call('frappe.client.delete', {
      doctype: 'FCRM Note',
      name,
    }),
    {
      loading: __('Deleting note...'),
      success: __('Note deleted'),
      error: __('Failed to delete note'),
    },
  )
  notes.value?.reload()
}
</script>
