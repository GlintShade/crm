<!--
  Dolny pasek decyzji na etapie Weryfikacja (tylko dla back office): postep
  akceptacji, lista elementow, ktore zostaly lub maja blad, oraz przycisk
  "Zatwierdz audyt". Przyklejony do dolu przewijanego obszaru zakladki.
  Prezentacyjny: emituje `zatwierdz` i `idz` (klucz elementu), nie wola API.
-->
<template>
  <div
    class="sticky bottom-0 z-20 -mx-5 mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-outline-gray-2 bg-surface-white px-5 py-3"
  >
    <div class="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-surface-gray-3">
      <div class="h-full rounded-full bg-surface-green-3" :style="{ width: procent + '%' }" />
    </div>

    <div class="min-w-0 flex-1 text-sm text-ink-gray-6">
      <template v-if="agg.allAccepted">
        <strong class="font-semibold text-ink-gray-8">
          {{ __('Wszystkie {0} zaakceptowane.', [agg.total]) }}
        </strong>
        {{ __('Możesz zatwierdzić audyt.') }}
      </template>
      <template v-else>
        <strong class="font-semibold text-ink-gray-8">
          {{ __('{0} z {1} zaakceptowane.', [agg.accepted, agg.total]) }}
        </strong>
        <span v-if="pozostale.bledy.length">
          {{ ' ' + __('Błędy:') + ' ' }}
          <template v-for="(el, i) in pozostale.bledy" :key="el.key">
            <button type="button" class="text-ink-red-7 underline-offset-2 hover:underline" @click="$emit('idz', el.key)">
              {{ el.label }}
            </button
            ><template v-if="i < pozostale.bledy.length - 1">, </template>
          </template>
          .
        </span>
        <span v-if="pozostale.oczekujace.length && pozostale.oczekujace.length <= 4">
          {{ ' ' + __('Zostały:') + ' ' }}
          <template v-for="(el, i) in pozostale.oczekujace" :key="el.key">
            <button type="button" class="text-ink-blue-7 underline-offset-2 hover:underline" @click="$emit('idz', el.key)">
              {{ el.label }}
            </button
            ><template v-if="i < pozostale.oczekujace.length - 1">, </template>
          </template>
          .
        </span>
        <span v-else-if="pozostale.oczekujace.length">
          {{ ' ' + __('Do sprawdzenia: {0}', [pozostale.oczekujace.length]) }}
        </span>
      </template>
    </div>

    <Button
      variant="solid"
      :theme="agg.allAccepted ? 'green' : 'gray'"
      :label="__('Zatwierdź audyt')"
      :disabled="!agg.allAccepted"
      :loading="loading"
      @click="$emit('zatwierdz')"
    />
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  // wynik aggregate(): { accepted, errors, waiting, total, allAccepted }
  agg: { type: Object, required: true },
  // wynik pozostale(): { oczekujace: [...], bledy: [...] }
  pozostale: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

defineEmits(['zatwierdz', 'idz'])

const procent = computed(() =>
  props.agg.total ? Math.round((props.agg.accepted / props.agg.total) * 100) : 0,
)
</script>
