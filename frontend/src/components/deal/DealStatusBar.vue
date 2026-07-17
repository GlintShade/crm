<!--
  Szansa pipeline status bar — a compact, clickable visualisation of where the
  deal sits in the (admin-configurable) Open/Ongoing → Won pipeline. Sits above
  the existing header status dropdown, which remains the source of truth for
  changing status; this bar is a second, always-visible entry point into the
  same `triggerStatusChange` flow (so the Lost-reason gate still applies).
-->
<template>
  <div class="min-h-[52px] border-b px-5 py-3">
    <template v-if="statusesLoaded && currentStatus">
      <div v-if="pipelineStages.length" class="flex gap-1">
        <div
          v-for="(stage, index) in pipelineStages"
          :key="stage.name"
          role="button"
          tabindex="0"
          :title="statusLabel(stage.name)"
          class="h-1.5 flex-1 cursor-pointer rounded-full transition-colors duration-150"
          :class="segmentClass(index)"
          @click="onSegmentClick(stage)"
          @keyup.enter="onSegmentClick(stage)"
          @keyup.space="onSegmentClick(stage)"
        />
      </div>
      <div class="mt-2 flex items-center justify-between gap-2">
        <Dropdown :options="dropdownOptions">
          <template #default="{ open }">
            <button
              type="button"
              class="-mx-1 flex min-w-0 items-center gap-1.5 rounded px-1 py-0.5 text-base text-ink-gray-8 transition-colors duration-150"
              :class="open ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-3'"
            >
              <IndicatorIcon :class="isLost ? '!text-red-600' : currentStatus.color" />
              <span class="truncate">{{ statusLabel(currentStatus.name) }}</span>
              <span
                class="size-3.5 shrink-0 text-ink-gray-5"
                :class="open ? 'lucide-chevron-up' : 'lucide-chevron-down'"
                aria-hidden="true"
              />
            </button>
          </template>
        </Dropdown>
        <Badge
          v-if="isLost"
          :label="__('Przegrana')"
          theme="red"
          variant="subtle"
        />
        <div
          v-else-if="pipelineStages.length"
          class="shrink-0 text-sm text-ink-gray-5"
        >
          {{ __('Etap {0}/{1}', [currentIndex + 1, pipelineStages.length]) }}
        </div>
      </div>
    </template>
  </div>
</template>
<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import { isTranslatable } from '@/utils'
import { statusesStore } from '@/stores/statuses'
import { Badge, Dropdown } from 'frappe-ui'
import { ref, computed } from 'vue'

// Full, literal Tailwind class strings — required so the JIT scanner (which
// reads this file's source text) generates them; a template-built string like
// `bg-${name}-500` would be invisible to the scanner and get purged.
const BG_CLASS_MAP = {
  gray: 'bg-gray-500',
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  red: 'bg-red-500',
  pink: 'bg-pink-500',
  orange: 'bg-orange-500',
  amber: 'bg-amber-500',
  yellow: 'bg-yellow-500',
  cyan: 'bg-cyan-500',
  teal: 'bg-teal-500',
  violet: 'bg-violet-500',
  purple: 'bg-purple-500',
  black: 'bg-gray-900',
}

const props = defineProps({
  // Current deal status name (doc.status). Empty is valid — falls back to the
  // first pipeline stage, same as statusesStore().getDealStatus().
  status: { type: String, default: '' },
  // The page's existing status-change handler (Deal.vue ~L745 / MobileDeal.vue
  // ~L607) — routes through the Lost-reason gate. Awaited here so a busy flag
  // can guard against double-fires while a change is in flight.
  triggerStatusChange: { type: Function, required: true },
})

const { dealStatuses, getDealStatus, statusOptions } = statusesStore()

const busy = ref(false)

// dealStatuses.data starts as [] (initialData) and populates once the
// auto-fetch resolves. getDealStatus() falls back to dealStatuses.data[0]
// when name is falsy, which would throw on an empty list — only resolve the
// current status once there's at least one status loaded.
const statusesLoaded = computed(() => (dealStatuses.data?.length ?? 0) > 0)

const currentStatus = computed(() =>
  statusesLoaded.value ? getDealStatus(props.status) : null,
)

const isLost = computed(() => currentStatus.value?.type === 'Lost')

// Ordered pipeline = Open/Ongoing statuses + Won, in admin-configured position
// order (dealStatuses is already orderBy position asc). Never hardcoded.
const pipelineStages = computed(() =>
  (dealStatuses.data || []).filter((s) => s.type !== 'Lost'),
)

const currentIndex = computed(() =>
  pipelineStages.value.findIndex((s) => s.name === currentStatus.value?.name),
)

function colorNameFromParsed(parsedColorClass) {
  // dealStatuses' transform already ran status.color through parseColor(),
  // turning e.g. "orange" into "!text-orange-600" — recover the raw name.
  const match = parsedColorClass?.match(/^!text-([a-z]+)-\d+$/)
  return match ? match[1] : 'gray'
}

const activeFillClass = computed(() => {
  const name = colorNameFromParsed(currentStatus.value?.color)
  return BG_CLASS_MAP[name] || BG_CLASS_MAP.gray
})

function segmentClass(index) {
  if (isLost.value) {
    return 'bg-red-200 hover:bg-red-300'
  }
  if (index <= currentIndex.value) {
    return `${activeFillClass.value} hover:opacity-80`
  }
  return 'bg-surface-gray-3 hover:bg-surface-gray-4'
}

function statusLabel(name) {
  if (isTranslatable('CRM Deal Status')) return __(name)
  return name
}

// Guards both the segmented-track click and the dropdown-selection click
// below against firing a second status change while one is in flight.
async function changeStatus(name) {
  if (busy.value) return

  busy.value = true
  try {
    await props.triggerStatusChange(name)
  } finally {
    busy.value = false
  }
}

async function onSegmentClick(stage) {
  if (!isLost.value && stage.name === currentStatus.value?.name) return
  await changeStatus(stage.name)
}

// All deal statuses (including Lost/"Przegrana"), each with its own
// color-coded IndicatorIcon dot — deliberately NOT scoped to the doc's
// customStatuses restriction the header dropdown (Deal.vue ~L29-45,
// MobileDeal.vue ~L29-45) applies, since this row is meant to offer every
// status, Przegrana included. statusOptions('deal', [], ...) with an empty
// statuses list falls through to every CRM Deal Status.
const dropdownOptions = computed(() =>
  statusesLoaded.value ? statusOptions('deal', [], changeStatus) : [],
)
</script>
