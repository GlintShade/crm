<template>
  <Dialog v-model:open="show" :size="'xl'">
    <template #body>
      <div
        v-if="!resultInfo"
        class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6"
      >
        <div class="mb-6 flex items-center justify-between">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              {{ __('Delete') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="ghost" icon="lucide-x" @click="show = false" />
          </div>
        </div>
        <div>
          <div class="text-ink-gray-5 text-base">
            {{
              __('Are you sure you want to delete {0} items?', [
                props.items?.length,
              ])
            }}
          </div>
        </div>
      </div>
      <div v-if="!resultInfo" class="px-4 pb-7 pt-0 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button
            :label="__('Delete {0} items', [props.items.length])"
            icon-left="lucide-trash-2"
            variant="solid"
            theme="red"
            @click="confirmDelete()"
          />
          <Button
            :label="__('Unlink & Delete {0} items', [props.items.length])"
            icon-left="lucide-unlock"
            variant="solid"
            @click="confirmUnlink()"
          />
        </div>
      </div>
      <div
        v-if="confirmDeleteInfo.show && !resultInfo"
        class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6"
      >
        <div class="mb-6 flex items-center justify-between">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              {{ __('Delete') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="ghost" icon="lucide-x" @click="show = false" />
          </div>
        </div>
        <div>
          <div class="text-ink-gray-5 text-base">
            {{
              confirmDeleteInfo.delete
                ? __(
                    'This will delete selected items and items linked to it, are you sure?',
                  )
                : __(
                    'This will delete selected items and unlink linked items to it, are you sure?',
                  )
            }}
          </div>
        </div>
      </div>
      <div
        v-if="confirmDeleteInfo.show && !resultInfo"
        class="px-4 pb-7 pt-0 sm:px-6"
      >
        <div class="flex flex-row-reverse gap-2">
          <Button
            :label="
              confirmDeleteInfo.delete ? __('Delete') : __('Unlink & Delete')
            "
            :icon-left="confirmDeleteInfo.delete ? 'trash-2' : 'unlock'"
            variant="solid"
            theme="red"
            @click="deleteDocs()"
          />
          <Button
            :label="__('Cancel')"
            variant="subtle"
            @click="confirmDeleteInfo.show = false"
          />
        </div>
      </div>
      <div
        v-if="resultInfo"
        class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6"
      >
        <div class="mb-6 flex items-center justify-between">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              Usunięto {{ resultInfo.deletedCount }} z {{ resultInfo.total }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="ghost" icon="lucide-x" @click="closeResult()" />
          </div>
        </div>
        <div>
          <div class="text-ink-gray-5 text-base mb-2">Nie usunięto:</div>
          <div class="flex flex-col gap-2 max-h-64 overflow-y-auto">
            <div
              v-for="item in resultInfo.failed"
              :key="item.name"
              class="border-b border-outline-gray-2 pb-2 text-sm"
            >
              <div class="font-medium text-ink-gray-8">{{ item.name }}</div>
              <div class="text-ink-gray-6">{{ item.reason }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="resultInfo" class="px-4 pb-7 pt-0 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button label="Zamknij" variant="solid" @click="closeResult()" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { call, toast } from 'frappe-ui'
import { ref } from 'vue'

const show = defineModel({ type: Boolean })
const props = defineProps({
  doctype: { type: String, required: true },
  items: { type: Array, required: true },
  reload: { type: Function, required: true },
})

const confirmDeleteInfo = ref({
  show: false,
  title: '',
  message: '',
  delete: false,
})

const resultInfo = ref(null)

const odmianaRekordu = (n) => {
  if (n === 1) return 'rekord'
  const r10 = n % 10
  const r100 = n % 100
  if (r10 >= 2 && r10 <= 4 && (r100 < 12 || r100 > 14)) return 'rekordy'
  return 'rekordów'
}

const confirmDelete = () => {
  confirmDeleteInfo.value = {
    show: true,
    title: __('Delete'),
    message: __('Are you sure you want to delete {0} linked doc(s)?', [
      props.items.length,
    ]),
    delete: true,
  }
}

const confirmUnlink = () => {
  confirmDeleteInfo.value = {
    show: true,
    title: __('Unlink'),
    message: __('Are you sure you want to unlink {0} linked doc(s)?', [
      props.items.length,
    ]),
    delete: false,
  }
}

const deleteDocs = async () => {
  try {
    const report = await call('crm.api.doc.delete_bulk_docs', {
      items: props.items,
      doctype: props.doctype,
      delete_linked: confirmDeleteInfo.value.delete,
    })
    confirmDeleteInfo.value = {
      show: false,
      title: '',
    }

    const deleted = report?.deleted ?? []
    const failed = report?.failed ?? []
    const total = report?.total ?? props.items.length

    if (failed.length === 0) {
      toast.success(
        `Usunięto ${deleted.length} ${odmianaRekordu(deleted.length)}`,
      )
      show.value = false
      props.reload()
    } else {
      props.reload()
      resultInfo.value = {
        deletedCount: deleted.length,
        total,
        failed,
      }
    }
  } catch (err) {
    toast.error(
      (err && (err.messages?.[0] || err.message)) ||
        'Nie udało się usunąć rekordów',
    )
  }
}

const closeResult = () => {
  show.value = false
  resultInfo.value = null
}
</script>
