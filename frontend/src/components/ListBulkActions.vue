<template>
  <EditValueModal
    v-if="showEditModal"
    v-model="showEditModal"
    :doctype="doctype"
    :selectedValues="selectedValues"
    @reload="reload"
  />
  <AssignmentModal
    v-if="showAssignmentModal"
    v-model="showAssignmentModal"
    v-model:assignees="bulkAssignees"
    :docs="selectedValues"
    :doctype="doctype"
    @reload="reload"
  />
  <DeleteLinkedDocModal
    v-if="showDeleteDocModal.showLinkedDocsModal"
    v-model="showDeleteDocModal.showLinkedDocsModal"
    :doctype="props.doctype"
    :docname="showDeleteDocModal.docname"
    :reload="reload"
  />
  <BulkDeleteLinkedDocModal
    v-if="showDeleteDocModal.showDeleteModal"
    v-model="showDeleteDocModal.showDeleteModal"
    :doctype="props.doctype"
    :items="showDeleteDocModal.items"
    :reload="reload"
  />
  <PrzydzielCCModal
    v-if="showPrzydzielCCModal"
    v-model="showPrzydzielCCModal"
    :selections="selectedValues"
    :list="list"
    @reload="reload"
  />
</template>

<script setup>
import EditValueModal from '@/components/Modals/EditValueModal.vue'
import AssignmentModal from '@/components/Modals/AssignmentModal.vue'
import PrzydzielCCModal from '@/components/Modals/PrzydzielCCModal.vue'
import { setupListCustomizations } from '@/utils'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { useTelemetry } from 'frappe-ui/frappe'
import { call, toast } from 'frappe-ui'
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  doctype: { type: String, default: '' },
  options: {
    type: Object,
    default: () => ({
      hideEdit: false,
      hideDelete: false,
      hideAssign: false,
    }),
  },
})

const canDeleteDoctype = ref(false)

function fetchCanDeleteDoctype() {
  if (!props.doctype) {
    canDeleteDoctype.value = false
    return
  }
  call('crm.api.doc.can_delete', { doctype: props.doctype }).then((value) => {
    canDeleteDoctype.value = Boolean(value)
  })
}

fetchCanDeleteDoctype()
watch(() => props.doctype, fetchCanDeleteDoctype)

const list = defineModel({ type: Object })

const router = useRouter()

const { $dialog, $socket } = globalStore()
const { isVolteoAdmin } = usersStore()
const { capture } = useTelemetry()

const showEditModal = ref(false)
const selectedValues = ref([])
const unselectAllAction = ref(() => {})
const showDeleteDocModal = ref({
  showLinkedDocsModal: false,
  showDeleteModal: false,
  docname: null,
})
function editValues(selections, unselectAll) {
  selectedValues.value = selections
  showEditModal.value = true
  unselectAllAction.value = unselectAll
}

function convertToDeal(selections, unselectAll) {
  $dialog({
    title: __('Convert to Deal'),
    message: __('Are you sure you want to convert {0} lead(s) to deal(s)?', [
      selections.size,
    ]),
    variant: 'solid',
    theme: 'blue',
    actions: [
      {
        label: __('Convert'),
        variant: 'solid',
        onClick: (close) => {
          capture('bulk_convert_to_deal')
          Array.from(selections).forEach((name) => {
            call('crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal', {
              lead: name,
            }).then(() => {
              toast.success(__('Converted Successfully'))
              list.value.reload()
              unselectAll()
              close()
            })
          })
        },
      },
    ],
  })
}

function deleteValues(selections, unselectAll) {
  unselectAllAction.value = unselectAll

  const selectedDocs = Array.from(selections)
  if (selectedDocs.length == 1) {
    showDeleteDocModal.value = {
      showLinkedDocsModal: true,
      docname: selectedDocs[0],
    }
  } else {
    showDeleteDocModal.value = {
      showDeleteModal: true,
      items: selectedDocs,
    }
  }
}

const showAssignmentModal = ref(false)
const bulkAssignees = ref([])

const showPrzydzielCCModal = ref(false)

// VOLTEO (issue #95): "Przypisz do CC" -- lustro assignValues powyzej,
// ale bez pola-modelu dedykowanego pod dane modalu (selectedValues jest
// juz dzielone z EditValueModal/AssignmentModal, PrzydzielCCModal czyta z
// niego wprost). unselectAllAction.value ustawiony tak samo jak w innych
// akcjach, zeby wspolny reload() nizej odznaczyl wiersze po sukcesie.
function assignToCC(selections, unselectAll) {
  showPrzydzielCCModal.value = true
  selectedValues.value = selections
  unselectAllAction.value = unselectAll
}

function assignValues(selections, unselectAll) {
  showAssignmentModal.value = true
  selectedValues.value = selections
  unselectAllAction.value = unselectAll
}

function clearAssignments(selections, unselectAll) {
  $dialog({
    title: __('Clear Assignment'),
    message: __('Are you sure you want to clear assignment for {0} item(s)?', [
      selections.size,
    ]),
    variant: 'solid',
    theme: 'red',
    actions: [
      {
        label: __('Clear Assignment'),
        variant: 'solid',
        theme: 'red',
        onClick: (close) => {
          capture('bulk_clear_assignment')
          call('frappe.desk.form.assign_to.remove_multiple', {
            doctype: props.doctype,
            names: JSON.stringify(Array.from(selections)),
            ignore_permissions: true,
          }).then(() => {
            toast.success(__('Assignment Cleared Successfully'))
            reload(unselectAll)
            close()
          })
        },
      },
    ],
  })
}

const customBulkActions = ref([])
const customListActions = ref([])

function bulkActions(selections, unselectAll) {
  let actions = []

  if (!props.options.hideEdit) {
    actions.push({
      label: __('Edit'),
      onClick: () => editValues(selections, unselectAll),
    })
  }

  if (!props.options.hideDelete && canDeleteDoctype.value) {
    actions.push({
      label: __('Delete'),
      onClick: () => deleteValues(selections, unselectAll),
    })
  }

  if (!props.options.hideAssign) {
    actions.push({
      label: __('Assign To'),
      onClick: () => assignValues(selections, unselectAll),
    })
    actions.push({
      label: __('Clear Assignment'),
      onClick: () => clearAssignments(selections, unselectAll),
    })
  }

  if (props.doctype === 'CRM Lead') {
    actions.push({
      label: __('Convert to Deal'),
      onClick: () => convertToDeal(selections, unselectAll),
    })
    // VOLTEO (issue #95): masowy przydzial do CC, tylko dla adminow -- CC i
    // D2D nie widza tej pozycji w menu, serwer (crm.api.volteo_leady.
    // przydziel_cc) egzekwuje to samo niezaleznie (frappe.only_for).
    if (isVolteoAdmin()) {
      actions.push({
        label: __('Przypisz do CC'),
        onClick: () => assignToCC(selections, unselectAll),
      })
    }
  }

  customBulkActions.value.forEach((action) => {
    actions.push({
      label: __(action.label),
      onClick: () =>
        action.onClick({
          list: list.value,
          selections,
          unselectAll,
          call,
          createToast: toast.create,
          toast,
          $dialog,
          router,
        }),
    })
  })
  return actions
}

function reload(unselectAll) {
  showDeleteDocModal.value = {
    showLinkedDocsModal: false,
    showDeleteModal: false,
    docname: null,
  }

  unselectAllAction.value?.()
  unselectAll?.()
  list.value?.reload()
}

onMounted(async () => {
  if (!list.value?.data) return
  let customization = await setupListCustomizations(list.value.data, {
    list: list.value,
    call,
    createToast: toast.create,
    toast,
    $dialog,
    $socket,
    router,
  })
  customBulkActions.value =
    customization?.bulkActions || list.value?.data?.bulkActions || []
  customListActions.value =
    customization?.actions || list.value?.data?.listActions || []
})

defineExpose({
  bulkActions,
  customListActions,
})
</script>
