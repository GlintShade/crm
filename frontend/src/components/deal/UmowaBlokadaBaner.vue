<!--
  Baner blokady formularza umowy (ops#371), wspolny dla UmowaTab.vue i
  UmowaCPTab.vue. Stan liczy czysta funkcja `stanBlokady`; brak `blokada`
  (stary backend) nie renderuje nic.
-->
<template>
  <div
    v-if="stan.tekstBanera"
    data-testid="umowa-blokada-baner"
    :class="[
      'flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm',
      stan.zablokowany
        ? 'border-outline-gray-2 bg-surface-gray-2 text-ink-gray-8'
        : 'border-outline-amber-3 bg-surface-amber-2 text-ink-amber-8',
    ]"
  >
    <span class="min-w-0 flex-1">{{ __(stan.tekstBanera) }}</span>
    <Button
      v-if="stan.pokazOdblokuj"
      data-testid="umowa-odblokuj"
      variant="outline"
      :label="__('Odblokuj formularz')"
      :disabled="zajety"
      :loading="zajety"
      @click="emit('odblokuj')"
    />
    <Button
      v-if="stan.pokazZablokuj"
      data-testid="umowa-zablokuj"
      variant="outline"
      :label="__('Zablokuj ponownie')"
      :disabled="zajety"
      :loading="zajety"
      @click="emit('zablokuj')"
    />
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { computed } from 'vue'
import { stanBlokady } from '@/utils/umowaBlokada'

const props = defineProps({
  blokada: { type: Object, default: null },
  zajety: { type: Boolean, default: false },
})
const emit = defineEmits(['odblokuj', 'zablokuj'])

const stan = computed(() => stanBlokady(props.blokada))
</script>
