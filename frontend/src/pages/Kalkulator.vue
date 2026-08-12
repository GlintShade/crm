<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="Kalkulator" />
      </template>
    </LayoutHeader>

    <KalkulatorTab :contact="contactDoc">
      <template #client-picker>
        <Link
          ref="clientLinkRef"
          doctype="Contact"
          v-model="selectedContact"
          class="w-full"
          variant="outline"
          :placeholder="__('Wybierz klienta…')"
          :onCreate="onCreateContact"
          :createLabel="__('Stwórz klienta')"
        />
      </template>
    </KalkulatorTab>
    <ContactModal
      v-if="showContactModal"
      v-model="showContactModal"
      :contact="_contact"
      :options="{
        redirect: false,
        afterInsert: (doc) => {
          selectedContact = doc.name
          clientLinkRef?.reload('', true)
        },
      }"
    />
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import Link from '@/components/Controls/Link.vue'
import ContactModal from '@/components/Modals/ContactModal.vue'
import KalkulatorTab from '@/components/KalkulatorTab.vue'
import { createResource } from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const selectedContact = ref('')
const showContactModal = ref(false)
const _contact = ref({})
const clientLinkRef = ref(null)

function onCreateContact(value, close) {
  _contact.value = { first_name: value }
  showContactModal.value = true
  close()
}

const contactResource = createResource({
  url: 'frappe.client.get',
  makeParams: () => ({ doctype: 'Contact', name: selectedContact.value }),
})

watch(selectedContact, (name) => {
  if (name) contactResource.fetch()
  else contactResource.reset()
})

const contactDoc = computed(() => {
  const doc = contactResource.data
  return doc && doc.name === selectedContact.value ? doc : {}
})
</script>
