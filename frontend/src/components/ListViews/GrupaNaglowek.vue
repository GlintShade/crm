<template>
  <div class="flex items-center">
    <button
      class="ms-[3px] me-[11px] rounded p-1 hover:bg-surface-gray-2"
      :aria-label="group.collapsed ? __('Rozwiń grupę') : __('Zwiń grupę')"
      @click="group.onToggle()"
    >
      <ChevronDownIcon
        class="h-4 w-4 text-ink-gray-6 transition-transform duration-200"
        :class="group.collapsed ? '-rotate-90' : ''"
      />
    </button>
    <div
      class="flex w-full cursor-pointer items-center gap-2 py-1.5 pe-2 text-base-medium text-ink-gray-8"
      @click="group.onToggle()"
    >
      <TaskStatusIcon
        v-if="group.kind === 'status' && doctype === 'CRM Task' && !group.empty"
        :status="group.klucz"
      />
      <IndicatorIcon
        v-else-if="group.kind === 'status' && kolorStatusu"
        :class="kolorStatusu"
      />
      <template v-else-if="group.kind === 'user'">
        <Avatar
          v-if="!group.empty"
          :image="uzytkownik?.user_image"
          :label="group.label"
          size="sm"
        />
        <div
          v-else
          class="flex h-5 w-5 items-center justify-center rounded-full bg-surface-gray-3 text-xs text-ink-gray-6"
        >
          ?
        </div>
      </template>
      <span :class="group.empty ? 'text-ink-gray-5' : ''">
        {{ nazwa }}
      </span>
      <span
        class="rounded-full border border-outline-gray-2 px-2 text-xs font-medium text-ink-gray-6"
      >
        {{ group.count }}
      </span>
    </div>
  </div>
  <div class="mx-2 h-px border-t border-outline-elevation-2"></div>
</template>

<script setup>
import ChevronDownIcon from '~icons/lucide/chevron-down'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import { statusesStore } from '@/stores/statuses'
import { usersStore } from '@/stores/users'
import { Avatar } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  group: { type: Object, required: true },
  doctype: { type: String, default: '' },
})

const { getDealStatus, getLeadStatus } = statusesStore()
const { getUser } = usersStore()

const kolorStatusu = computed(() => {
  if (props.group.empty || !props.group.klucz) return ''
  if (props.doctype === 'CRM Deal') return getDealStatus(props.group.klucz)?.color
  if (props.doctype === 'CRM Lead') return getLeadStatus(props.group.klucz)?.color
  return ''
})

const uzytkownik = computed(() =>
  props.group.kind === 'user' && props.group.klucz ? getUser(props.group.klucz) : null,
)

const nazwa = computed(() => __(props.group.label))
</script>
