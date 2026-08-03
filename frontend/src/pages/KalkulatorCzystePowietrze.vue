<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="KalkulatorCzystePowietrze" />
      </template>
    </LayoutHeader>

    <KalkulatorCPTab :contact="contactDoc">
      <template #client-picker>
        <Link
          doctype="Contact"
          v-model="selectedContact"
          class="w-full"
          variant="outline"
          :placeholder="__('Wybierz klienta…')"
        />
      </template>
    </KalkulatorCPTab>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import Link from '@/components/Controls/Link.vue'
import KalkulatorCPTab from '@/components/KalkulatorCPTab.vue'
import { createResource } from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const selectedContact = ref('')

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
