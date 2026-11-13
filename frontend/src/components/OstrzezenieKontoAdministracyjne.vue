<template>
  <div
    v-if="widoczne"
    data-testid="ostrzezenie-konto-administracyjne"
    class="flex w-full min-w-0 items-start gap-2 rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
    role="note"
  >
    <FeatherIcon name="alert-triangle" class="mt-0.5 h-4 w-4 shrink-0" />
    <span class="min-w-0 break-words">{{ tekstOstrzezenia(rodzaj) }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import {
  czyKontoAdministracyjne,
  tekstOstrzezenia,
} from '@/utils/kontoAdministracyjne'

defineProps({
  rodzaj: { type: String, default: 'szansa' },
})

const { isVolteoAdmin, isBackend } = usersStore()
const widoczne = computed(() =>
  czyKontoAdministracyjne(isVolteoAdmin(), isBackend()),
)
</script>
