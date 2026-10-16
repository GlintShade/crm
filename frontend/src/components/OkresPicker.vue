<!--
  Wybor okresu rozliczen (ops#283): "Okres wg" (select), "Okres" (menu z presetami
  i wlasnym zakresem) oraz pigulka aktywnego zakresu z "x" (reset do domyslnego).
  v-model: { wg, preset, od, do } (od/do tylko dla preset === 'wlasny').
-->
<template>
  <div class="flex flex-wrap items-end gap-3">
    <div class="w-52">
      <label class="mb-1 block text-xs text-ink-gray-5">{{ __('Okres wg') }}</label>
      <select
        class="h-7 w-full rounded border border-outline-gray-2 bg-surface-base px-2 text-sm text-ink-gray-8"
        :value="modelValue.wg"
        @change="zmienWg($event.target.value)"
      >
        <option v-for="o in OPCJE_WG" :key="o.klucz" :value="o.klucz">{{ __(o.etykieta) }}</option>
      </select>
    </div>

    <div ref="korzen" class="relative">
      <label class="mb-1 block text-xs text-ink-gray-5">{{ __('Okres') }}</label>
      <button
        type="button"
        class="flex h-7 min-w-44 items-center justify-between gap-2 rounded border border-outline-gray-2 bg-surface-base px-2 text-sm text-ink-gray-8 hover:bg-surface-gray-1"
        @click="otwarte = !otwarte"
      >
        <span>{{ etykietaPresetu }}</span>
        <FeatherIcon name="chevron-down" class="h-3.5 w-3.5 text-ink-gray-5" />
      </button>
      <div
        v-if="otwarte"
        class="absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-outline-gray-2 bg-surface-base p-1 shadow-xl"
      >
        <div class="px-2 py-1 text-xs font-medium uppercase text-ink-gray-5">{{ __('Szybki wybór') }}</div>
        <button
          v-for="p in presetyGotowe"
          :key="p.klucz"
          type="button"
          class="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
          :class="{ 'bg-surface-gray-2': modelValue.preset === p.klucz }"
          @click="wybierzPreset(p.klucz)"
        >
          {{ __(p.etykieta) }}
          <FeatherIcon v-if="modelValue.preset === p.klucz" name="check" class="h-3.5 w-3.5" />
        </button>
        <div class="my-1 border-t border-outline-gray-2" />
        <div class="px-2 py-1 text-xs font-medium uppercase text-ink-gray-5">{{ __('Własny zakres') }}</div>
        <div class="flex flex-col gap-2 px-2 pb-2">
          <div class="flex items-center gap-2">
            <input
              v-model="wlasnyOd"
              type="date"
              class="h-7 w-full rounded border border-outline-gray-2 bg-surface-base px-1 text-sm text-ink-gray-8"
            />
            <input
              v-model="wlasnyDo"
              type="date"
              class="h-7 w-full rounded border border-outline-gray-2 bg-surface-base px-1 text-sm text-ink-gray-8"
            />
          </div>
          <div v-if="bladWlasnego" class="text-xs text-ink-red-4">{{ bladWlasnego }}</div>
          <Button size="sm" variant="solid" :label="__('Zastosuj')" @click="zastosujWlasny" />
        </div>
      </div>
    </div>

    <span
      class="inline-flex h-7 items-center gap-1.5 rounded-full bg-surface-blue-2 px-3 text-sm text-ink-blue-3"
      data-testid="okres-pigulka"
    >
      {{ etykietaAktywnego }}
      <button
        v-if="!jestDomyslny"
        type="button"
        class="text-ink-blue-3 hover:text-ink-blue-4"
        :title="__('Przywróć domyślny okres')"
        @click="reset"
      >
        <FeatherIcon name="x" class="h-3.5 w-3.5" />
      </button>
    </span>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { Button, FeatherIcon } from 'frappe-ui'
import {
  DOMYSLNY_WYBOR,
  OPCJE_WG,
  PRESETY,
  etykietaZakresu,
  zakresOkresu,
} from '@/utils/okres'

const props = defineProps({
  modelValue: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue'])

const otwarte = ref(false)
const korzen = ref(null)
onClickOutside(korzen, () => (otwarte.value = false))

const presetyGotowe = PRESETY.filter((p) => p.klucz !== 'wlasny')
const wlasnyOd = ref(props.modelValue.od || '')
const wlasnyDo = ref(props.modelValue.do || '')
const bladWlasnego = ref('')

watch(
  () => props.modelValue,
  (w) => {
    wlasnyOd.value = w.od || ''
    wlasnyDo.value = w.do || ''
  },
)

const zakres = computed(() =>
  zakresOkresu(props.modelValue.preset, new Date(), props.modelValue.od, props.modelValue.do),
)
const etykietaPresetu = computed(() => {
  const p = PRESETY.find((x) => x.klucz === props.modelValue.preset)
  return p ? __(p.etykieta) : __('Okres')
})
const etykietaAktywnego = computed(() =>
  zakres.value ? etykietaZakresu(zakres.value.od, zakres.value.do) : __('Niepoprawny zakres'),
)
const jestDomyslny = computed(
  () =>
    props.modelValue.preset === DOMYSLNY_WYBOR.preset && props.modelValue.wg === DOMYSLNY_WYBOR.wg,
)

function zmienWg(wg) {
  emit('update:modelValue', { ...props.modelValue, wg })
}

function wybierzPreset(preset) {
  bladWlasnego.value = ''
  otwarte.value = false
  emit('update:modelValue', { wg: props.modelValue.wg, preset })
}

function zastosujWlasny() {
  if (!zakresOkresu('wlasny', new Date(), wlasnyOd.value, wlasnyDo.value)) {
    bladWlasnego.value = __('Podaj obie daty, początkowa nie może być późniejsza niż końcowa.')
    return
  }
  bladWlasnego.value = ''
  otwarte.value = false
  emit('update:modelValue', {
    wg: props.modelValue.wg,
    preset: 'wlasny',
    od: wlasnyOd.value,
    do: wlasnyDo.value,
  })
}

function reset() {
  emit('update:modelValue', { ...DOMYSLNY_WYBOR })
}
</script>
