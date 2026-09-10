<template>
  <ListView
    :class="$attrs.class"
    :columns="columns"
    :rows="rows"
    :options="{
      selectable: canSelectRows,
      showTooltip: options.showTooltip,
      resizeColumn: options.resizeColumn,
    }"
    row-key="name"
    @update:selections="(selections) => emit('selectionsChanged', selections)"
  >
    <ListHeader
      class="sm:mx-5 mx-3"
      @columnWidthUpdated="emit('columnWidthUpdated')"
    >
      <ListHeaderItem
        v-for="column in columns"
        :key="column.key"
        :item="column"
        @columnWidthUpdated="emit('columnWidthUpdated', column)"
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
        <div
          v-else-if="column.label === 'Komentarze'"
          class="flex items-center text-ink-gray-5"
          :title="__('Komentarze')"
        >
          <CommentIcon class="h-4 w-4" />
        </div>
      </ListHeaderItem>
    </ListHeader>
    <ListRows
      v-slot="{ column, item, row }"
      :rows="rows"
      doctype="CRM Lead"
    >
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden">
        <template #prefix>
          <div
            v-if="column.key === '_assign'"
            class="flex items-center truncate"
          >
            <MultipleAvatar :avatars="item" size="sm" />
          </div>
          <!-- VOLTEO (issue #99): "status" jest teraz zawsze edytowana
               inline (patrz galaz KOLUMNY_INLINE w #default nizej), wiec ta
               galaz musi wygrac PRZED starym prefixem-indykatorem ponizej,
               ktory teraz obsluguje juz tylko kolumny spoza KOLUMNY_INLINE. -->
          <div v-else-if="KOLUMNY_INLINE.has(column.key)" />
          <div v-else-if="column.key === 'status'">
            <IndicatorIcon :class="item.color" />
          </div>
          <div v-else-if="column.key === 'lead_name'">
            <Avatar
              v-if="item.label"
              class="flex items-center"
              :image="item.image"
              :label="item.image_label"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'lead_owner'">
            <Avatar
              v-if="item.full_name"
              class="flex items-center"
              :image="item.user_image"
              :label="item.full_name"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'custom_cc'">
            <Avatar
              v-if="item.full_name"
              class="flex items-center"
              :image="item.user_image"
              :label="item.full_name"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'mobile_no' && item">
            <PhoneIcon class="h-4 w-4" />
          </div>
        </template>
        <template #default="{ label }">
          <div v-if="column.label === 'Szczegóły'" class="flex items-center">
            <Button
              variant="outline"
              size="sm"
              class="w-fit"
              @click.stop.prevent="() => goToLead(row)"
            >
              {{ __('Szczegóły') }}
            </Button>
          </div>
          <div
            v-else-if="column.label === 'Komentarze'"
            class="flex cursor-pointer items-center gap-1 text-ink-gray-6"
            @click.stop.prevent="() => openComments(row)"
          >
            <CommentIcon class="h-4 w-4" />
            <span v-if="item">{{ item }}</span>
          </div>
          <LeadInlineCell
            v-else-if="KOLUMNY_INLINE.has(column.key)"
            :row="row"
            :column="column"
            :item="item"
            @saved="(patch) => onInlineSaved(row, patch)"
          />
          <div
            v-else-if="
              [
                'modified',
                'creation',
                'first_response_time',
                'first_responded_on',
                'response_by',
              ].includes(column.key)
            "
            class="truncate text-base"
          >
            <Tooltip :text="item.label">
              <div>{{ item.timeAgo }}</div>
            </Tooltip>
          </div>
          <div v-else-if="column.key === '_liked_by'">
            <Button
              v-if="column.key == '_liked_by'"
              variant="ghosted"
              :class="isLiked(item) ? 'fill-red-500' : 'fill-white'"
              @click.stop.prevent="
                () =>
                  emit('likeDoc', {
                    name: row.name,
                    liked: isLiked(item),
                  })
              "
            >
              <HeartIcon class="h-4 w-4" />
            </Button>
          </div>
          <div
            v-else-if="column.key === 'sla_status'"
            class="truncate text-base"
          >
            <Badge
              v-if="item.value"
              :variant="'subtle'"
              :theme="item.color"
              size="md"
              :label="item.value"
            />
          </div>
          <div
            v-else-if="column.key === 'custom_zasady_dotacji'"
            class="truncate text-base"
          >
            <Badge
              v-if="item.label"
              variant="subtle"
              :theme="item.color"
              size="md"
              :label="item.label"
            />
          </div>
          <div v-else-if="column.type === 'Check'">
            <FormControl
              type="checkbox"
              :modelValue="item"
              :disabled="true"
              class="text-ink-gray-9"
            />
          </div>
          <RatingInput
            v-else-if="column.type === 'Rating'"
            :value="item"
            class="!opacity-100 flex-nowrap overflow-auto"
            :disabled="true"
            :max="column.options || 5"
          />
          <div v-else-if="label" class="truncate text-base">
            {{ getLabel(label, column) }}
          </div>
        </template>
      </ListRowItem>
    </ListRows>
    <ListSelectBanner v-if="canSelectRows">
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
    v-if="pageLengthCount"
    v-model="pageLengthCount"
    class="border-t sm:px-5 px-3 py-2"
    :options="{
      rowCount: options.rowCount,
      totalCount: options.totalCount,
    }"
    @loadMore="emit('loadMore')"
  />
  <ListBulkActions
    v-if="canSelectRows"
    ref="listBulkActionsRef"
    v-model="list"
    doctype="CRM Lead"
    :options="{
      hideAssign: true,
    }"
  />
  <KomentarzeLeadaModal
    v-model="showComments"
    :docname="commentsDocname"
    doctype="CRM Lead"
    @commentAdded="onCommentAdded"
  />
</template>

<script setup>
import HeartIcon from '@/components/Icons/HeartIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import KomentarzeLeadaModal from '@/components/Modals/KomentarzeLeadaModal.vue'
import LeadInlineCell from '@/components/ListViews/LeadInlineCell.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import MultipleAvatar from '@/components/MultipleAvatar.vue'
import ListBulkActions from '@/components/ListBulkActions.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import ListFooterVolteo from '@/components/ListFooterVolteo.vue'
import { KOLUMNY_INLINE, nowaListaZPodmienionymPolem } from '@/utils/leadyInline'
import { isTranslatable, formatDuration } from '@/utils'
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
import { usersStore } from '@/stores/users'
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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
  'columnWidthUpdated',
  'applyFilter',
  'applyLikeFilter',
  'likeDoc',
  'selectionsChanged',
])

const route = useRoute()
const router = useRouter()

const pageLengthCount = defineModel({ type: Number })
const list = defineModel('list', { type: Object })

function getLabel(label, column) {
  if (column.type === 'Duration') return formatDuration(label)
  if (column.options && isTranslatable(column.options)) return __(label)
  return label
}

// VOLTEO (zgloszenie wlasciciela 2026-09-10): lista leadow nie ma juz
// nawigacji ani filtrowania po kliknieciu w wiersz/komorke. ListView nie
// dostaje juz "getRowRoute" w opcjach (patrz szablon), wiec caly wiersz
// przestal byc linkiem, a klikniecie w dowolna komorke poza dozwolonymi
// wyjatkami (checkbox, "Szczegoly", "Komentarze", cztery pola edytowane
// inline) nic juz nie robi. Jedyne miejsce, ktore nadal otwiera leada, to
// przycisk "Szczegoly" (patrz goToLead nizej), wiec ta funkcja zostaje
// jedynym zrodlem trasy leada.
function leadRoute(row) {
  return {
    name: 'Lead',
    params: { leadId: row.name },
    query: { view: route.query.view, viewType: route.params.viewType },
  }
}

function goToLead(row) {
  router.push(leadRoute(row))
}

// VOLTEO (ops#94): pseudo-kolumna "Komentarze" -- jedna zamontowana
// instancja modala na cala liste (nie jedna na wiersz), docname przelaczany
// przy kolejnym kliknieciu. Klik ma `@click.stop.prevent` (patrz szablon),
// wiec nie nawiguje do leada, w przeciwienstwie do reszty wiersza.
const showComments = ref(false)
const commentsDocname = ref('')

function openComments(row) {
  commentsDocname.value = row.name
  showComments.value = true
}

// Po dodaniu komentarza przeladowuje cala liste (ten sam mechanizm co
// `ListBulkActions` uzywa po akcjach masowych) -- `_comment_count` jest
// liczony po stronie backendu (patrz `crm/api/doc.py`, komentarz
// "VOLTEO (ops#94)" przy `get_data`), wiec przeladowanie jest jedynym
// pewnym sposobem, zeby licznik w wierszu odzwierciedlal realny stan.
function onCommentAdded() {
  list.value?.reload?.()
}

// VOLTEO (issue #99): LeadInlineCell.vue zapisuje przez set_value samo i
// emituje tylko surowa pare {fieldname, value} po udanym zapisie. Podmiana
// idzie na SUROWYCH danych listy (list.data.data), nie na juz sparsowanych
// `rows` -- Leads.vue::rows to computed zalezny od list.data.data, wiec po
// tej podmianie parseRows sam przeliczy kolor statusu / etykiete daty, bez
// duplikowania tej logiki tutaj. Podmiana jest niemutowalna: nowa tablica z
// jednym nowym obiektem wiersza (patrz nowaListaZPodmienionymPolem).
function onInlineSaved(row, { fieldname, value }) {
  if (!list.value?.data?.data) return
  list.value.data.data = nowaListaZPodmienionymPolem(
    list.value.data.data,
    row.name,
    fieldname,
    value,
  )
}

// Bulk actions (selection checkboxes + the select banner) są ukryte zarówno
// dla handlowca (rola Volteo D2D Sales), jak i dla backoffice'u (rola
// Volteo Backend) -- decyzja właściciela 2026-09-10 (opcja B): Volteo
// Backend na liście leadów ma być traktowany jak handlowiec, bez checkboxów
// i bez paska akcji masowych. Akcje masowe zostają tylko dla adminów
// (isVolteoAdmin()) i CC (isCallCenter()) -- odwrotnie niż DealsListView.vue
// (samo isVolteoAdmin()), tu dochodzi isCallCenter(). Administrator, Volteo
// Core Admin i Volteo Call Center pozostają bez zmian.
const { isVolteoAdmin, isCallCenter } = usersStore()
const canSelectRows = computed(() => isVolteoAdmin() || isCallCenter())

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
