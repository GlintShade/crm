<!--
  Zakonczone zadania (Done/Canceled) w karcie Zadania panelu bocznego:
  zwarty, wyciszony blok. Klik w wiersz otwiera zadanie, klik w ikone
  statusu przywraca je do Todo. Bez priorytetu, terminu i menu.
-->
<template>
  <div
    class="mt-1.5 flex flex-col gap-0.5 rounded bg-surface-gray-1 p-1"
    data-testid="zadania-zakonczone"
  >
    <div
      v-for="task in tasks"
      :key="task.name"
      class="flex cursor-pointer items-start gap-2 rounded px-1.5 py-1 hover:bg-surface-gray-2"
      data-testid="zadanie-zakonczone"
      @click="modalRef.showTask(task)"
    >
      <button
        type="button"
        class="mt-px shrink-0 rounded p-0.5 hover:bg-surface-gray-3"
        :title="__('Przywróć zadanie')"
        data-testid="zadanie-przywroc"
        @click.stop="modalRef.przywrocZadanie(task)"
      >
        <TaskStatusIcon :status="task.status" />
      </button>
      <div class="flex min-w-0 flex-1 flex-col">
        <div
          class="truncate text-[12.5px] font-normal leading-5 text-ink-gray-5 line-through"
          :title="task.title"
        >
          {{ task.title }}
        </div>
        <div class="truncate text-[11px] text-ink-gray-4">
          {{ opis(task) }}
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import { usersStore } from '@/stores/users'
import { formatujDzienMiesiac } from '@/utils/dataPolska'

defineProps({
  tasks: { type: Array, default: () => [] },
  modalRef: { type: Object, default: () => ({}) },
})

const { getUser } = usersStore()

function opis(task) {
  const czynnosc = task.status === 'Canceled' ? 'anulowane' : 'zrobione'
  const data = formatujDzienMiesiac(task.modified)
  const kiedy = data ? `${czynnosc} ${data}` : czynnosc
  const kto = task.assigned_to ? getUser(task.assigned_to).full_name : ''
  return kto ? `${kto} · ${kiedy}` : kiedy
}
</script>
