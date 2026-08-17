<template>
  <div
    class="grid h-full place-items-center px-4 py-20 text-center text-lg text-ink-gray-5"
  >
    <div class="space-y-2">
      <div>{{ __('Invalid page or not permitted to access') }}</div>
      <Button
        :route="{ name: 'Leads' }"
        :label="__('Leads')"
        :iconLeft="LeadsIcon"
      />
    </div>
  </div>
</template>

<script setup>
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import { usePageMeta } from 'frappe-ui'

usePageMeta(() => {
  return { title: __('Nieprawidłowa strona') }
})
</script>
