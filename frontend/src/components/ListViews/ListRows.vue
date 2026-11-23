<template>
  <div v-if="showGroupedRows" class="mx-3 mt-2 h-full overflow-y-auto sm:mx-5">
    <div v-for="group in reactivieRows" :key="group.group">
      <GrupaNaglowek :group="group" :doctype="doctype" />
      <ListGroupRows :group="group">
        <ListRow
          v-for="row in group.rows"
          :key="row.name"
          v-slot="{ idx, column, item }"
          :row="row"
          :class="rowClass(row)"
        >
          <slot v-bind="{ idx, column, item, row }" />
        </ListRow>
        <div
          v-if="group.loading && !group.rows.length"
          class="px-2 py-3 text-base text-ink-gray-5"
        >
          {{ __('Ładowanie...') }}
        </div>
        <div
          v-if="group.hasMore"
          class="flex items-center gap-2 border-t px-2 pt-2 text-base"
        >
          <Button
            variant="ghost"
            :label="__('Pokaż kolejne')"
            :loading="group.loading"
            @click="group.onMore()"
          />
          <span class="text-ink-gray-5">
            {{ __('pokazano {0} z {1}', [group.loaded, group.count]) }}
          </span>
        </div>
      </ListGroupRows>
    </div>
  </div>
  <ListRows
    v-else
    ref="scrollContainer"
    class="mx-3 sm:mx-5"
    @scroll="handleScroll"
  >
    <ListRow
      v-for="row in reactivieRows"
      :key="row.name"
      v-slot="{ idx, column, item }"
      :row="row"
      :class="rowClass(row)"
    >
      <slot v-bind="{ idx, column, item, row }" />
    </ListRow>
  </ListRows>
</template>

<script setup>
import { useStorage } from '@vueuse/core'
import { Button, ListRows, ListRow, ListGroupRows } from 'frappe-ui'
import GrupaNaglowek from '@/components/ListViews/GrupaNaglowek.vue'
import { ref, computed, watch, onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true },
  doctype: { type: String, default: 'CRM Lead' },
  // Opcjonalna klasa CSS wiersza (np. podswietlenie zadan po terminie na
  // liscie Zadan, ops#357). Domyslnie brak: pozostale listy sie nie zmieniaja.
  rowClass: { type: Function, default: () => '' },
})

const reactivieRows = ref(props.rows)

watch(
  () => props.rows,
  (val) => (reactivieRows.value = val),
)

let showGroupedRows = computed(() => {
  return props.rows.every(
    (row) => row.group && row.rows && Array.isArray(row.rows),
  )
})

const scrollPosition = useStorage(`scrollPosition${props.doctype}`, 0)
const scrollContainer = ref(null)

const handleScroll = () => {
  if (scrollContainer.value) {
    scrollPosition.value = scrollContainer.value.$el.scrollTop
  }
}

onBeforeUnmount(() => {
  if (scrollContainer.value) {
    scrollContainer.value.$el.removeEventListener('scroll', handleScroll)
  }
})

onMounted(() => {
  if (scrollContainer.value) {
    scrollContainer.value.$el.addEventListener('scroll', handleScroll)
    scrollContainer.value.$el.scrollTop = scrollPosition.value
  }
})
</script>
