<template>
  <DateTimePicker v-bind="$attrs" :value="value" @change="(v) => emit('change', v)">
    <template #time="{ time, selected, setTime, setDate, close }">
      <TimePicker
        :modelValue="time"
        :open-on-click="false"
        :open-on-focus="false"
        :placeholder="__('Godzina, np. 16:15')"
        @change="setTime"
      />
      <div class="grid grid-cols-4 gap-1 text-xs tabular-nums">
        <button
          v-for="p in pola"
          :key="p.wartosc"
          type="button"
          class="h-6 rounded hover:bg-surface-gray-2"
          :class="czyWybrane(p, time) ? 'bg-surface-gray-7 text-ink-white' : 'text-ink-gray-8'"
          @click="wybierz(p, { selected, setTime, setDate, close })"
        >{{ p.etykieta }}</button>
      </div>
    </template>
  </DateTimePicker>
</template>

<script setup>
import { DateTimePicker, TimePicker } from 'frappe-ui'
import { generujSiatke, czyWybrane } from '@/utils/siatkaGodzin'

defineOptions({ inheritAttrs: false })
defineProps({ value: { type: String, default: '' } })
const emit = defineEmits(['change'])
const pola = generujSiatke()

function wybierz(pole, { selected, setTime, setDate, close }) {
  if (!selected) setDate(new Date())
  setTime(pole.wartosc)
  close()
}
</script>
