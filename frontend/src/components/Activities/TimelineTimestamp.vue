<template>
  <Tooltip :text="tooltipText">
    <div v-if="showExactTimestamp" :class="className">{{ exact }}</div>
    <div v-else :class="[className, 'text-right']">
      <span>{{ relative }}</span>
      <span
        v-if="dokladny"
        :class="stacked ? 'block whitespace-nowrap' : 'block whitespace-nowrap sm:ml-1 sm:inline'"
      >({{ dokladny }})</span>
    </div>
  </Tooltip>
</template>

<script setup>
import { Tooltip, dayjsLocal } from 'frappe-ui'
import { timeAgo, formatDate } from '@/utils'
import { dataGodzinaWarszawa } from '@/utils/dataPolska'
import { useTimelinePreferences } from '@/composables/useTimelinePreferences'
import { computed } from 'vue'

const props = defineProps({
  date: { type: [String, Object], default: '' },
  // Format used for the exact timestamp (falls back to the default in formatDate)
  format: { type: String, default: '' },
  className: { type: String, default: 'text-sm text-ink-gray-5' },
  // Dokładna data zawsze w osobnej linii (karty notatek)
  stacked: { type: Boolean, default: false },
})

const { showExactTimestamp } = useTimelinePreferences()

const relative = computed(() => __(timeAgo(props.date)))
const exact = computed(() => formatDate(props.date, props.format || undefined))

// ops#430: domyślnie "<względny> (DD.MM.RRRR HH:MM)" w czasie polskim
const dokladny = computed(() =>
  dataGodzinaWarszawa(props.date ? dayjsLocal(props.date).toDate() : null),
)

const tooltipText = computed(() =>
  showExactTimestamp.value ? relative.value : exact.value,
)
</script>
