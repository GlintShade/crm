<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Tasks" />
    </template>
    <template #right-header>
      <CustomActions
        v-if="tasksListView?.customListActions"
        :actions="tasksListView.customListActions"
      />
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="createTask"
      />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="tasks"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Task"
    :options="{
      allowedViews: ['list', 'kanban'],
    }"
  />
  <div
    v-if="$route.params.viewType !== 'kanban'"
    class="flex items-center px-3 pb-1 pt-2 sm:px-5"
    data-testid="zadania-zakladki"
  >
    <div
      class="inline-flex shrink-0 items-center overflow-hidden rounded border border-outline-gray-2"
    >
      <button
        v-for="(zakladka, index) in ZAKLADKI_ZADAN"
        :key="zakladka.klucz"
        type="button"
        class="flex h-7 items-center gap-1.5 whitespace-nowrap px-2 text-base transition-colors"
        :class="[
          zakladka.klucz === aktywnaZakladka
            ? 'bg-surface-gray-4 text-ink-gray-9'
            : 'text-ink-gray-6 hover:bg-surface-gray-2',
          index > 0 && 'border-l border-outline-gray-2',
        ]"
        :aria-pressed="zakladka.klucz === aktywnaZakladka"
        :data-testid="`zadania-zakladka-${zakladka.klucz}`"
        @click="wybierzZakladke(zakladka.klucz)"
      >
        {{ __(zakladka.etykieta) }}
      </button>
    </div>
  </div>
  <KanbanView
    v-if="$route.params.viewType == 'kanban' && rows.length"
    v-model="tasks"
    :options="{
      onClick: (row) => showTask(row.name),
      onNewClick: (column) => createTask(column),
    }"
    :etykietaKolumny="
      (nazwa) => etykietaPola(tasks.params?.column_field, nazwa)
    "
    @update="(data) => viewControls.updateKanbanSettings(data)"
    @loadMore="(columnName) => viewControls.loadMoreKanban(columnName)"
  >
    <template #title="{ titleField, itemName }">
      <div class="flex items-center gap-2">
        <div v-if="titleField === 'status'">
          <TaskStatusIcon :status="getRow(itemName, titleField).label" />
        </div>
        <div v-else-if="titleField === 'priority'">
          <TaskPriorityIcon :priority="getRow(itemName, titleField).label" />
        </div>
        <div v-else-if="titleField === 'assigned_to'">
          <Avatar
            v-if="getRow(itemName, titleField).full_name"
            class="flex items-center"
            :image="getRow(itemName, titleField).user_image"
            :label="getRow(itemName, titleField).full_name"
            size="sm"
          />
        </div>
        <div
          v-if="['modified', 'creation'].includes(titleField)"
          class="truncate text-base"
        >
          <Tooltip :text="getRow(itemName, titleField).label">
            <div>{{ getRow(itemName, titleField).timeAgo }}</div>
          </Tooltip>
        </div>
        <div
          v-else-if="getRow(itemName, titleField).label"
          class="truncate text-base"
        >
          {{ etykietaPola(titleField, getRow(itemName, titleField).label) }}
        </div>
        <div v-else class="text-ink-gray-4">{{ __('No Title') }}</div>
      </div>
    </template>
    <template #fields="{ fieldName, itemName }">
      <div
        v-if="getRow(itemName, fieldName).label"
        class="truncate flex items-center gap-2"
      >
        <div v-if="fieldName === 'status'">
          <TaskStatusIcon
            class="size-3"
            :status="getRow(itemName, fieldName).label"
          />
        </div>
        <div v-else-if="fieldName === 'priority'">
          <TaskPriorityIcon :priority="getRow(itemName, fieldName).label" />
        </div>
        <div v-else-if="fieldName === 'assigned_to'">
          <Avatar
            v-if="getRow(itemName, fieldName).full_name"
            class="flex items-center"
            :image="getRow(itemName, fieldName).user_image"
            :label="getRow(itemName, fieldName).full_name"
            size="sm"
          />
        </div>
        <div
          v-if="['modified', 'creation'].includes(fieldName)"
          class="truncate text-base"
        >
          <Tooltip :text="getRow(itemName, fieldName).label">
            <div>{{ getRow(itemName, fieldName).timeAgo }}</div>
          </Tooltip>
        </div>
        <div
          v-else-if="fieldName == 'description'"
          class="truncate text-base max-h-44"
        >
          <TextEditor
            v-if="getRow(itemName, fieldName).label"
            :content="getRow(itemName, fieldName).label"
            :editable="false"
            editor-class="!prose-sm max-w-none focus:outline-none"
            class="flex-1 overflow-hidden"
          />
        </div>
        <div v-else class="truncate text-base">
          {{ etykietaPola(fieldName, getRow(itemName, fieldName).label) }}
        </div>
      </div>
    </template>
    <template #actions="{ itemName }">
      <div class="flex gap-2 items-center justify-between">
        <div>
          <Button
            v-if="getRow(itemName, 'reference_docname').label"
            class="-ml-2"
            variant="ghost"
            size="sm"
            :label="
              getRow(itemName, 'reference_doctype').label == 'CRM Deal'
                ? __('Deal')
                : __('Lead')
            "
            :iconRight="ArrowUpRightIcon"
            @click.stop="
              redirect(
                getRow(itemName, 'reference_doctype').label,
                getRow(itemName, 'reference_docname').label,
              )
            "
          />
        </div>
        <div class="flex items-center gap-2" @click.stop.prevent>
          <Dropdown :options="actions(itemName)" variant="ghost">
            <Button icon="lucide-more-horizontal" variant="ghost" />
          </Dropdown>
        </div>
      </div>
    </template>
  </KanbanView>
  <TasksListView
    v-else-if="tasks.data && rows.length"
    ref="tasksListView"
    v-model="tasks.data.page_length_count"
    v-model:list="tasks"
    :rows="rows"
    :columns="columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: tasks.data.row_count,
      totalCount: tasks.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @showTask="showTask"
    @applyFilter="(data) => viewControls.applyFilter(data)"
    @applyLikeFilter="(data) => viewControls.applyLikeFilter(data)"
    @likeDoc="(data) => viewControls.likeDoc(data)"
    @selectionsChanged="
      (selections) => viewControls.updateSelections(selections)
    "
  />
  <EmptyState
    v-else-if="tasks.data && !rows.length"
    name="Tasks"
    :icon="Email2Icon"
  />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import CustomActions from '@/components/CustomActions.vue'
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import TasksListView from '@/components/ListViews/TasksListView.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import KanbanView from '@/components/Kanban/KanbanView.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { getMeta } from '@/stores/meta'
import { usersStore } from '@/stores/users'
import { formatDate } from '@/utils'
import { czyTlumaczycOpcje } from '@/utils/zadania'
import {
  ZAKLADKI_ZADAN,
  filtryDlaZakladki,
  zakladkaZFiltra,
} from '@/utils/zadaniaLista'
import { timestampCell } from '@/composables/useTimelinePreferences'
import { useOnboarding, useTelemetry } from 'frappe-ui/frappe'
import { Tooltip, Avatar, TextEditor, Dropdown, call, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const { getFormattedPercent, getFormattedFloat, getFormattedCurrency } =
  getMeta('CRM Task')
const { getUser } = usersStore()
const { updateOnboardingStep } = useOnboarding('frappecrm')
const { capture } = useTelemetry()

const router = useRouter()
const route = useRoute()

const tasksListView = ref(null)

// tasks data is loaded in the ViewControls component
const tasks = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

function getRow(name, field) {
  function getValue(value) {
    if (value && typeof value === 'object') {
      return value
    }
    return { label: value }
  }
  return getValue(rows.value?.find((row) => row.name == name)[field])
}

const rows = computed(() => {
  if (!tasks.value?.data?.data) return []

  if (tasks.value.data.view_type === 'kanban') {
    return getKanbanRows(tasks.value.data.data, tasks.value.data.fields)
  }

  openTaskFromURL()
  return parseRows(tasks.value?.data.data, tasks.value?.data.columns)
})

const columns = computed(() => {
  let _columns = tasks.value?.data?.columns || []

  // Set align right for last column
  if (_columns.length) {
    _columns = _columns.map((col, index) => {
      if (index === _columns.length - 1) {
        return { ...col, align: 'right' }
      }
      return col
    })
  }

  return _columns
})

function getKanbanRows(data, columns) {
  let _rows = []
  data.forEach((column) => {
    column.data?.forEach((row) => {
      _rows.push(row)
    })
  })
  return parseRows(_rows, columns)
}

function parseRows(rows, columns = []) {
  let view_type = tasks.value.data.view_type
  let key = view_type === 'kanban' ? 'fieldname' : 'key'
  let type = view_type === 'kanban' ? 'fieldtype' : 'type'

  return rows.map((task) => {
    let _rows = {}
    tasks.value?.data.rows.forEach((row) => {
      _rows[row] = task[row]

      let fieldType = columns?.find((col) => (col[key] || col.value) == row)?.[
        type
      ]

      if (
        fieldType &&
        ['Date', 'Datetime'].includes(fieldType) &&
        !['modified', 'creation', 'due_date'].includes(row)
      ) {
        _rows[row] = formatDate(task[row], '', true, fieldType == 'Datetime')
      }

      if (fieldType && fieldType == 'Currency') {
        _rows[row] = getFormattedCurrency(row, task)
      }

      if (fieldType && fieldType == 'Float') {
        _rows[row] = getFormattedFloat(row, task)
      }

      if (fieldType && fieldType == 'Percent') {
        _rows[row] = getFormattedPercent(row, task)
      }

      if (['modified', 'creation'].includes(row)) {
        _rows[row] = timestampCell(task[row])
      } else if (row == 'assigned_to') {
        _rows[row] = {
          label: task.assigned_to && getUser(task.assigned_to).full_name,
          ...(task.assigned_to && getUser(task.assigned_to)),
        }
      }
    })
    // Kolumna "Klient" (pseudo-pole `_klient`, ops#357): zawsze tekst.
    _rows._klient = task._klient || ''
    return _rows
  })
}

// Zakladki Aktywne / Wykonane / Anulowane (ops#357) to zwykly filtr statusu:
// podswietlona jest ta, ktorej odpowiada biezacy filtr; przy innym filtrze
// zadna.
const aktywnaZakladka = computed(() =>
  zakladkaZFiltra(tasks.value?.params?.filters?.status),
)

function wybierzZakladke(klucz) {
  if (!viewControls.value) return
  const filtry = tasks.value?.params?.filters || {}
  // `getParams` PRZED `updateFilter`: odswieza tozsamosc widoku (wzorzec
  // `wyczyscWidok()` z WidokiLeadowPasek.vue).
  viewControls.value.getParams()
  viewControls.value.updateFilter(filtryDlaZakladki(filtry, klucz))
}

// Kazde wejscie na strone zaczyna od zakladki Aktywne (decyzja wlasciciela),
// takze gdy poprzednio zapisano inny filtr statusu. Odpala sie RAZ na montaz,
// po pierwszym zakonczonym zaladowaniu listy (wczesniej ViewControls i tak
// przeladowalby parametry z zapisanego widoku). Zapisany widok (`?view=`) i
// Kanban nigdy nie sa nadpisywane; pozostale filtry uzytkownika zostaja.
let widzianoLadowanie = false
let wejscieObsluzone = false
watch(
  () => tasks.value?.loading,
  (laduje) => {
    if (wejscieObsluzone) return
    if (laduje) {
      widzianoLadowanie = true
      return
    }
    if (!widzianoLadowanie || !tasks.value?.data?.data) return
    if (route.params.viewType === 'kanban') return
    wejscieObsluzone = true
    if (route.query.view) return
    const filtry = tasks.value?.params?.filters || {}
    if (zakladkaZFiltra(filtry.status) !== 'aktywne') {
      wybierzZakladke('aktywne')
    }
  },
)

const { showModal } = useDoctypeModal()

const taskCallbacks = {
  afterInsert: () => {
    tasks.value.reload()
    updateOnboardingStep('create_first_task')
    capture('task_created')
  },
  afterUpdate: () => {
    tasks.value.reload()
    capture('task_updated')
  },
}

function showTask(name) {
  showModal({
    name,
    doctype: 'CRM Task',
    title: 'Task',
    callbacks: taskCallbacks,
  })
}

// Status i priorytet zadania sa angielskie w bazie; etykieta idzie przez __().
function etykietaPola(pole, wartosc) {
  return czyTlumaczycOpcje('CRM Task', pole) && wartosc ? __(wartosc) : wartosc
}

function createTask(column) {
  const defaults = { status: 'Todo', priority: 'Low' }

  if (column?.column?.name) {
    let column_field = tasks.value.params.column_field
    if (column_field) {
      defaults[column_field] = column.column.name
    }
  }

  showModal({
    doctype: 'CRM Task',
    title: 'Task',
    defaults: defaults,
    callbacks: taskCallbacks,
  })
}

function actions(name) {
  return [
    {
      label: __('Delete'),
      icon: 'trash-2',
      onClick: async () => {
        if (await deleteTask(name)) tasks.value.reload()
      },
    },
  ]
}

async function deleteTask(name) {
  try {
    await call('frappe.client.delete', {
      doctype: 'CRM Task',
      name,
    })
    return true
  } catch (err) {
    toast.error(err?.messages?.[0] || __('Nie udało się usunąć zadania.'))
    return false
  }
}

function redirect(doctype, docname) {
  if (!docname) return
  let name = doctype == 'CRM Deal' ? 'Deal' : 'Lead'
  let params = { leadId: docname }
  if (name == 'Deal') {
    params = { dealId: docname }
  }
  router.push({ name: name, params: params })
}

const openTaskFromURL = () => {
  const searchParams = new URLSearchParams(window.location.search)
  const taskName = searchParams.get('open')

  if (taskName && rows.value?.length) {
    showTask(parseInt(taskName))
    searchParams.delete('open')
    window.history.replaceState(null, '', window.location.pathname)
  }
}
</script>
