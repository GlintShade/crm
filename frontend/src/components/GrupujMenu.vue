<template>
  <Popover placement="bottom-end">
    <template #target="{ togglePopover, isOpen }">
      <Tooltip :text="grupowanie.komunikatOdmowy.value" :disabled="!grupowanie.odmowa.value">
        <Button
          :label="etykieta"
          :iconLeft="GroupByIcon"
          :iconRight="isOpen ? 'chevron-up' : 'chevron-down'"
          :variant="grupowanie.aktywne.value ? 'subtle' : 'outline'"
          :theme="grupowanie.odmowa.value ? 'red' : 'gray'"
          @click="togglePopover()"
        />
      </Tooltip>
    </template>
    <template #body="{ close }">
      <div
        class="my-2 min-w-56 rounded-lg bg-surface-elevation-2 p-2 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        <div
          v-if="grupowanie.odmowa.value"
          class="mb-2 rounded bg-surface-red-2 px-2 py-1.5 text-sm text-ink-red-8"
        >
          {{ grupowanie.komunikatOdmowy.value }}
        </div>
        <button
          class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
          @click="wybierz(null, close)"
        >
          <span class="w-4">
            <CheckIcon v-if="!grupowanie.stan.value.pole" class="h-4 w-4" />
          </span>
          {{ __('Bez grupowania') }}
        </button>
        <div class="px-2 pb-1 pt-2 text-xs font-medium uppercase text-ink-gray-5">
          {{ __('Grupuj według') }}
        </div>
        <button
          v-for="pole in grupowanie.pola.value"
          :key="pole.fieldname"
          class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
          :class="pole.fieldname === grupowanie.stan.value.pole ? 'bg-surface-gray-2' : ''"
          @click="wybierz(pole.fieldname, close)"
        >
          <span class="w-4">
            <CheckIcon
              v-if="pole.fieldname === grupowanie.stan.value.pole"
              class="h-4 w-4"
            />
          </span>
          {{ __(pole.label) }}
        </button>
        <template v-if="grupowanie.stan.value.pole">
          <hr class="my-2" />
          <div class="px-2 py-1">
            <FormControl
              type="checkbox"
              :label="__('Pokaż puste grupy')"
              :modelValue="grupowanie.stan.value.pokazPuste"
              @update:modelValue="grupowanie.przelaczPustych()"
            />
          </div>
          <button
            class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
            @click="grupowanie.zwinWsz(); close()"
          >
            <span class="w-4" />
            {{ __('Zwiń wszystkie grupy') }}
          </button>
          <button
            v-if="grupowanie.stan.value.zwiniete.length"
            class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
            @click="grupowanie.rozwinWsz(); close()"
          >
            <span class="w-4" />
            {{ __('Rozwiń wszystkie grupy') }}
          </button>
        </template>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import CheckIcon from '@/components/Icons/CheckIcon.vue'
import GroupByIcon from '@/components/Icons/GroupByIcon.vue'
import { Button, FormControl, Popover, Tooltip } from 'frappe-ui'
import { computed } from 'vue'

// `grupowanie` to wynik useGrupowanieListy (refy zostaja refami, bo obiekt nie jest reaktywny)
const props = defineProps({
  grupowanie: { type: Object, required: true },
  hideLabel: { type: Boolean, default: false },
})

const etykieta = computed(() => {
  if (props.hideLabel) return ''
  const g = props.grupowanie
  return g.stan.value.pole && g.etykietaPola.value
    ? __('Grupuj: {0}', [__(g.etykietaPola.value)])
    : __('Grupuj')
})

function wybierz(pole, close) {
  props.grupowanie.ustawPolem(pole)
  close()
}
</script>
