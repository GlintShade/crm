<template>
  <Tooltip :text="tooltipText">
    <div :class="className">{{ displayText }}</div>
  </Tooltip>
</template>

<script setup>
import { Tooltip, dayjsLocal } from 'frappe-ui'
import { timeAgo, formatDate } from '@/utils'
import { czasWzgledny } from '@/utils/dataPolska'
import { useTimelinePreferences } from '@/composables/useTimelinePreferences'
import { computed } from 'vue'

const props = defineProps({
  date: { type: [String, Object], default: '' },
  // Format used for the exact timestamp (falls back to the default in formatDate)
  format: { type: String, default: '' },
  className: { type: String, default: 'text-sm text-ink-gray-5' },
})

const { showExactTimestamp } = useTimelinePreferences()

const relative = computed(() => __(timeAgo(props.date)))
const exact = computed(() => formatDate(props.date, props.format || undefined))

// ops#430: domyślnie "<względny> (DD.MM.RRRR HH:MM)" w czasie polskim
const relativeZDokladnym = computed(() =>
  czasWzgledny(
    relative.value,
    props.date ? dayjsLocal(props.date).toDate() : null,
  ),
)

const displayText = computed(() =>
  showExactTimestamp.value ? exact.value : relativeZDokladnym.value,
)
const tooltipText = computed(() =>
  showExactTimestamp.value ? relative.value : exact.value,
)
</script>
