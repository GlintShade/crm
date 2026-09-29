<template>
  <TaskModal
    v-if="doctypeModal.show.value && doctypeModal.doctype.value === 'CRM Task'"
    v-model="doctypeModal.show.value"
    :doctypeTitle="doctypeModal.title.value"
    :doctype="doctypeModal.doctype.value"
    :docname="doctypeModal.name.value"
    :defaults="doctypeModal.defaults.value"
    @afterInsert="(d) => doctypeModal.triggerCallback('afterInsert', d)"
    @afterUpdate="(d) => doctypeModal.triggerCallback('afterUpdate', d)"
  />
  <DoctypeModal
    v-else-if="doctypeModal.show.value"
    v-model="doctypeModal.show.value"
    :doctypeTitle="doctypeModal.title.value"
    :doctype="doctypeModal.doctype.value"
    :docname="doctypeModal.name.value"
    :defaults="doctypeModal.defaults.value"
    @afterInsert="(d) => doctypeModal.triggerCallback('afterInsert', d)"
    @afterUpdate="(d) => doctypeModal.triggerCallback('afterUpdate', d)"
  />
</template>
<script setup>
// Issue GlintShade/proenergy-crm-ops#208: CRM Task dostaje dedykowane okno
// (wariant C, panel właściwości) zamiast generycznego DoctypeModal.vue.
// Każdy inny doctype (przez ten sam useDoctypeModal()/showModal()) zostaje
// bez zmian na DoctypeModal.vue.
import DoctypeModal from '@/components/Modals/DoctypeModal.vue'
import TaskModal from '@/components/Modals/TaskModal.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'

const doctypeModal = useDoctypeModal()
</script>
