<!-- eslint-disable vue/no-v-html -->
<template>
  <ListView
    :columns="columns"
    :rows="rows"
    :options="{
      onRowClick: (row) => emit('showTask', row.name),
      selectable: options.selectable,
      showTooltip: options.showTooltip,
      resizeColumn: options.resizeColumn,
      selectionText: (n) =>
        n === 1 ? __('Zaznaczono 1 wiersz') : __('Zaznaczono {0} wierszy', [n]),
    }"
    row-key="name"
    @update:selections="(selections) => emit('selectionsChanged', selections)"
  >
    <ListHeader
      class="mx-3 sm:mx-5"
      @columnWidthUpdated="emit('columnWidthUpdated')"
    >
      <ListHeaderItem
        v-for="column in columns"
        :key="column.key"
        :item="column"
        @columnWidthUpdated="onColumnWidthUpdated"
      >
        <Button
          v-if="column.key == '_liked_by'"
          variant="ghosted"
          class="!h-4"
          :class="isLikeFilterApplied ? 'fill-red-500' : 'fill-white'"
          @click="() => emit('applyLikeFilter')"
        >
          <HeartIcon class="h-4 w-4" />
        </Button>
      </ListHeaderItem>
    </ListHeader>
    <ListRows
      v-slot="{ idx, column, item, row }"
      class="mx-3 sm:mx-5"
      :rows="rows"
      doctype="CRM Task"
      :rowClass="klasaWiersza"
    >
      <div
        v-if="column.key === 'due_date' && item"
        :title="formatujTermin(item)"
      >
        <div class="flex items-center gap-2 truncate text-base">
          <div
            :class="
              czyPrzeterminowane(row.due_date, row.status)
                ? 'text-ink-red-8'
                : ''
            "
          >
            <component
              :is="
                czyPrzeterminowane(row.due_date, row.status)
                  ? AlertIcon
                  : CalendarIcon
              "
              class="size-4"
            />
          </div>
          <div class="flex min-w-0 flex-col">
            <div
              class="truncate"
              :class="
                czyPrzeterminowane(row.due_date, row.status)
                  ? 'font-semibold text-ink-red-8'
                  : ''
              "
            >
              {{ formatujTerminKrotko(item) }}
            </div>
            <div
              v-if="czyPrzeterminowane(row.due_date, row.status)"
              class="truncate text-xs text-ink-red-8"
              data-testid="zadanie-po-terminie-tekst"
            >
              {{ tekstPoTerminie(row.due_date) }}
            </div>
          </div>
        </div>
      </div>
      <ListRowItem
        v-else
        :item="item"
        :align="column.align"
        class="overflow-hidden"
      >
        <template #prefix>
          <div v-if="column.key === 'status'">
            <TaskStatusIcon :status="item" />
          </div>
          <div v-else-if="column.key === 'priority'">
            <TaskPriorityIcon :priority="item" />
          </div>
          <div v-else-if="column.key === 'assigned_to'">
            <Avatar
              v-if="item.full_name"
              class="flex items-center"
              :image="item.user_image"
              :label="item.full_name"
              size="sm"
            />
          </div>
        </template>
        <template #default="{ label }">
          <div
            v-if="column.key === '_klient'"
            class="overflow-hidden"
            data-testid="zadanie-klient"
          >
            <span v-if="item" class="truncate text-base font-[520]">
              {{ item }}
            </span>
            <span v-else class="truncate italic text-ink-gray-4">
              {{ __('brak klienta') }}
            </span>
          </div>
          <div
            v-else-if="column.key === '_dw'"
            class="overflow-hidden"
            data-testid="zadanie-do-wiadomosci"
            :title="item"
          >
            <span class="truncate text-base">{{ item }}</span>
          </div>
          <div
            v-else-if="['modified', 'creation'].includes(column.key)"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            <Tooltip :text="item.label">
              <div>{{ item.timeAgo }}</div>
            </Tooltip>
          </div>
          <div
            v-else-if="column.type === 'Text Editor'"
            class="truncate text-base h-4 [&>p]:truncate"
            v-html="sanitizeHTML(item)"
          />
          <div v-else-if="column.type === 'Check'">
            <FormControl
              type="checkbox"
              :modelValue="item"
              :disabled="true"
              class="text-ink-gray-9"
            />
          </div>
          <div v-else-if="column.key === '_liked_by'">
            <Button
              v-if="column.key == '_liked_by'"
              variant="ghosted"
              :class="isLiked(item) ? 'fill-red-500' : 'fill-white'"
              @click.stop.prevent="
                () => emit('likeDoc', { name: row.name, liked: isLiked(item) })
              "
            >
              <HeartIcon class="h-4 w-4" />
            </Button>
          </div>
          <RatingInput
            v-else-if="column.type === 'Rating'"
            :value="item"
            class="!opacity-100 flex-nowrap overflow-auto"
            :disabled="true"
            :max="column.options || 5"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          />
          <div
            v-else-if="label"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ getLabel(label, column) }}
          </div>
        </template>
      </ListRowItem>
    </ListRows>
    <ListSelectBanner>
      <template #actions="{ selections, unselectAll }">
        <Dropdown
          :options="listBulkActionsRef.bulkActions(selections, unselectAll)"
        >
          <Button icon="lucide-more-horizontal" variant="ghost" />
        </Dropdown>
      </template>
    </ListSelectBanner>
  </ListView>
  <ListFooterVolteo
    v-model="pageLengthCount"
    class="border-t px-3 py-2 sm:px-5"
    :options="{
      rowCount: options.rowCount,
      totalCount: options.totalCount,
    }"
    @loadMore="emit('loadMore')"
  />
  <ListBulkActions
    ref="listBulkActionsRef"
    v-model="list"
    doctype="CRM Task"
    :options="{
      hideAssign: true,
    }"
  />
</template>
<script setup>
import HeartIcon from '@/components/Icons/HeartIcon.vue'
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import ListBulkActions from '@/components/ListBulkActions.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import ListFooterVolteo from '@/components/ListFooterVolteo.vue'
import AlertIcon from '~icons/lucide/circle-alert'
import { formatujTermin, formatujTerminKrotko } from '@/utils/dataPolska'
import { czyPrzeterminowane, tekstPoTerminie } from '@/utils/zadaniaLista'
import { isTranslatable, formatDuration, sanitizeHTML } from '@/utils'
import {
  Avatar,
  ListView,
  ListHeader,
  ListHeaderItem,
  ListSelectBanner,
  ListRowItem,
  Dropdown,
  Tooltip,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { ref, computed, watch } from 'vue'

defineProps({
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
  options: {
    type: Object,
    default: () => ({
      selectable: true,
      showTooltip: true,
      resizeColumn: false,
      totalCount: 0,
      rowCount: 0,
    }),
  },
})

const emit = defineEmits([
  'loadMore',
  'updatePageCount',
  'showTask',
  'columnWidthUpdated',
  'applyFilter',
  'applyLikeFilter',
  'likeDoc',
  'selectionsChanged',
])

const pageLengthCount = defineModel({ type: Number })
const list = defineModel('list', { type: Object })

// Reczna zmiana szerokosci kolumny (przeciagniecie krawedzi naglowka). Ta sama
// naprawa co na liscie Umow, patrz `onColumnWidthUpdated` i jego komentarz w
// DealsListView.vue: frappe-ui's ListHeaderItem tylko emituje `{key, width,
// save}` i niczego nie zapamietuje, wiec kolumne szukamy PO KLUCZU w prawdziwej,
// reaktywnej `list.value.data.columns` (nie w lokalnym prop `columns`, w ktorym
// ostatnia kolumna jest kopia ze spreada w computed Tasks.vue) i ustawiamy jej
// `width`. Payload idzie dalej do Tasks.vue, ktory na `save` wola trwaly zapis.
function onColumnWidthUpdated(payload) {
  const col = list.value?.data?.columns?.find((c) => c.key === payload?.key)
  if (col && payload?.width) {
    col.width = payload.width
  }
  emit('columnWidthUpdated', payload)
}

function getLabel(label, column) {
  if (column.type === 'Duration') return formatDuration(label)
  if (['status', 'priority'].includes(column.key)) return __(label)
  if (column.options && isTranslatable(column.options)) return __(label)
  return label
}

// Wiersz zadania po terminie: tlo z tokenu frappe-ui `bg-surface-red-2` (w
// ciemnym motywie token sam zmienia wartosc). Klasa `zadanie-po-terminie` sluzy
// stylom ponizej, ktore przywracaja stany zaznaczenia i najechania.
function klasaWiersza(row) {
  return czyPrzeterminowane(row.due_date, row.status)
    ? 'bg-surface-red-2 zadanie-po-terminie'
    : ''
}

const isLikeFilterApplied = computed(() => {
  return list.value.params?.filters?._liked_by ? true : false
})

const { user } = sessionStore()

function isLiked(item) {
  if (item) {
    let likedByMe = JSON.parse(item)
    return likedByMe.includes(user)
  }
}

watch(pageLengthCount, (val, old_value) => {
  if (val === old_value) return
  emit('updatePageCount', val)
})

const listBulkActionsRef = ref(null)

defineExpose({
  customListActions: computed(
    () => listBulkActionsRef.value?.customListActions,
  ),
})
</script>

<style scoped>
/*
  Korzen wiersza (ListRow.vue z frappe-ui) sam niesie tlo zaznaczenia
  (`bg-surface-gray-2`) i najechania (`hover:bg-surface-sidebar`). Czerwone tlo
  z `bg-surface-red-2` ma byc widoczne w stanie spoczynku, ale nie moze
  zakrywac zaznaczenia ani najechania, wiec te stany dostaja wlasne, mocniejsze
  reguly (tokeny, bez palety i bez hex). Tokeny `--surface-*` to pelne
  wartosci koloru (oklch), nie trojki kanalow, wiec uzywamy ich wprost, bez rgb().
*/
:deep(.zadanie-po-terminie:hover) {
  background-color: var(--surface-red-3);
}
:deep(.zadanie-po-terminie.bg-surface-gray-2) {
  background-color: var(--surface-gray-2);
}
:deep(.zadanie-po-terminie.bg-surface-gray-2:hover) {
  background-color: var(--surface-gray-3);
}
</style>
