<!--
  Naglowek panelu bocznego szansy i leada (ops#326): imie klienta, telefon z
  przyciskiem Zadzwon, e-mail, numer rekordu jako chip z kopiowaniem,
  przelacznik "Ukryj puste" i zwijanie panelu. Zastepuje dawny 45 px pasek z
  samym numerem rekordu.
-->
<template>
  <div class="flex shrink-0 flex-col gap-2 border-b px-4 py-3" data-testid="panel-naglowek">
    <div class="flex min-w-0 items-center gap-1.5">
      <div
        class="min-w-0 flex-1 truncate text-[15px] font-semibold text-ink-gray-9"
        :title="imie"
      >
        {{ imie || __('Brak klienta') }}
      </div>
      <Button
        v-if="mozeOtworzyc"
        variant="ghost"
        size="sm"
        icon="lucide-arrow-up-right"
        :tooltip="__('Otwórz klienta')"
        @click="emit('otworz-klienta')"
      />
    </div>
    <div v-if="telefon" class="flex min-w-0 items-center gap-2 text-[12.5px] text-ink-gray-8">
      <span class="lucide-phone size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
      <span class="min-w-0 flex-1 truncate">{{ telefonWyswietlany }}</span>
      <Button
        v-if="href"
        size="sm"
        variant="subtle"
        :link="href"
        :label="__('Zadzwoń')"
      />
    </div>
    <div v-if="email" class="flex min-w-0 items-center gap-2 text-[12.5px] text-ink-gray-8">
      <span class="lucide-mail size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
      <span class="min-w-0 flex-1 truncate" :title="email">{{ email }}</span>
    </div>
    <div class="flex min-w-0 items-center gap-2 text-xs text-ink-gray-5">
      <button
        type="button"
        class="flex min-w-0 items-center gap-1.5 rounded-full bg-surface-gray-2 px-2 py-0.5 hover:bg-surface-gray-3"
        :title="__('Kopiuj numer rekordu')"
        @click="copyToClipboard(rekord)"
      >
        <span class="truncate">{{ __(rekord) }}</span>
        <span class="lucide-copy size-3 shrink-0" aria-hidden="true" />
      </button>
      <div class="ml-auto flex shrink-0 items-center gap-1.5">
        <span>{{ __('Ukryj puste') }}</span>
        <Switch size="sm" v-model="ukryjPuste" />
      </div>
      <Button
        variant="ghost"
        size="sm"
        icon="lucide-panel-right-close"
        :tooltip="__('Zwiń panel')"
        @click="emit('zwin')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button, Switch } from 'frappe-ui'
import { copyToClipboard } from '@/utils'
import { telHref } from '@/utils/telefon'
import { formatTelefon } from '@/utils/panelBoczny'
import { useUkryjPustePola } from '@/composables/useUkryjPustePola'

const props = defineProps({
  imie: { type: String, default: '' },
  telefon: { type: String, default: '' },
  email: { type: String, default: '' },
  rekord: { type: String, required: true },
  mozeOtworzyc: { type: Boolean, default: false },
})
const emit = defineEmits(['otworz-klienta', 'zwin'])

const { ukryjPuste } = useUkryjPustePola()
const href = computed(() => telHref(props.telefon))
const telefonWyswietlany = computed(() => formatTelefon(props.telefon))
</script>
