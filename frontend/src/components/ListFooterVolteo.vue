<template>
  <ListFooter v-model="pageLengthCount" :options="options">
    <template #right>
      <div class="flex items-center">
        <Button v-if="showLoadMore" :label="__('Load More')" @click="emit('loadMore')" />
        <div v-if="showLoadMore" class="mx-3 h-[80%] border-l" />
        <div class="flex items-center gap-1 text-base text-ink-gray-5">
          <div>{{ options.rowCount || '0' }}</div>
          <div>z</div>
          <div>{{ options.totalCount || '0' }}</div>
        </div>
      </div>
    </template>
  </ListFooter>
</template>
<script setup>
// Cienki wrapper na frappe-ui ListFooter, tłumaczący slot "right" na polski.
// ListFooter (frontend/node_modules/frappe-ui/src/components/ListView/ListFooter.vue)
// osadza gołe literały "Load More" / "of" bez __(), więc katalog pl.po nie może
// ich przechwycić. Slot "left" (TabButtons z page-length) zostaje domyślny z
// frappe-ui - nie jest tu nadpisywany.
import { Button, ListFooter } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    default: 20,
  },
  options: {
    type: Object,
    default: () => ({
      rowCount: 0,
      totalCount: 0,
      pageLengthOptions: [20, 50, 100],
    }),
  },
})

const emit = defineEmits(['update:modelValue', 'loadMore'])

const pageLengthCount = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// Odtworzone 1:1 z oryginału ListFooter.vue (showLoadMore computed).
const showLoadMore = computed(() => {
  return (
    props.options.rowCount &&
    props.options.totalCount &&
    props.options.rowCount < props.options.totalCount
  )
})
</script>
