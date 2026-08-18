<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="DokumentyOze" />
      </template>
    </LayoutHeader>

    <DokumentyLista linia="OZE" />
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import DokumentyLista from '@/components/DokumentyLista.vue'
import { usePageMeta } from 'frappe-ui'

usePageMeta(() => {
  return { title: __('Dokumenty OZE') }
})
</script>
