<template>
  <div :id="activity.name">
    <div class="mb-1 flex items-center justify-stretch gap-2 py-1 text-base">
      <div class="inline-flex items-center flex-wrap gap-1 text-ink-gray-5">
        <UserAvatar class="mr-1" :user="activity.owner" size="md" />
        <span class="font-medium text-ink-gray-8">
          {{ activity.owner_name }}
        </span>
        <span>{{ __('added a') }}</span>
        <span class="max-w-xs truncate font-medium text-ink-gray-8">
          {{ rzeczownikWpisu || __('comment') }}
        </span>
      </div>
      <div class="ml-auto flex items-center gap-1 whitespace-nowrap">
        <TimelineTimestamp :date="activity.creation" />
        <!-- VOLTEO (rozmowa zadania): historia zmian wpisu, widoczna dla
          kazdego, kto widzi wpis (nie tylko autora). Tylko gdy API podalo
          `liczba_zmian` > 0 (inne miejsca uzywajace tego komponentu nie
          przekazuja tego pola, wiec przycisku tam nie ma). -->
        <Button
          v-if="activity.liczba_zmian > 0"
          icon="lucide-history"
          variant="ghost"
          class="!h-6 !w-6"
          :tooltip="__('Historia zmian')"
          data-testid="wpis-historia"
          @click="otworzHistorie"
        />
        <!-- VOLTEO (ops#364): wlasciciel wpisu edytuje go jednym kliknieciem
          (olowek). Pozycje "Usun" widza tylko administratorzy (System Manager,
          Administrator): tylko oni maja prawo `delete` na Comment, dla pozostalych
          kontrolka usuwania nie jest renderowana wcale. Administrator widzacy
          cudzy wpis ma menu z samym "Usun". -->
        <Button
          v-if="isOwner && !editing && !usuwanieWidoczne"
          icon="lucide-pencil"
          variant="ghost"
          class="!h-6 !w-6"
          :tooltip="__('Edit')"
          data-testid="wpis-edytuj"
          @click="startEdit"
        />
        <Dropdown
          v-else-if="(isOwner || usuwanieWidoczne) && !editing"
          :options="menuOptions"
          placement="right"
          @click="confirmingDelete = false"
        >
          <Button
            icon="lucide-more-horizontal"
            variant="ghost"
            class="!h-6 !w-6"
          />
        </Dropdown>
      </div>
    </div>
    <div
      class="rounded bg-surface-gray-1 px-3 py-[7.5px] text-base leading-6 transition-all duration-300 ease-in-out"
    >
      <template v-if="editing">
        <TextEditor
          :content="editContent"
          :editable="true"
          :editor-class="['prose-sm max-w-none min-h-[3rem]']"
          @change="editContent = $event"
        />
        <div class="mt-2 flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="cancelEdit" />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saving"
            @click="saveEdit"
          />
        </div>
      </template>
      <template v-else>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="prose-f" v-html="sanitizeHTML(activity.content)" />
        <div
          v-if="activity.attachments?.length"
          class="mt-2 flex flex-wrap gap-2"
        >
          <AttachmentItem
            v-for="a in activity.attachments"
            :key="a.file_url"
            :label="a.file_name"
            :url="a.file_url"
          />
        </div>
      </template>
    </div>
    <HistoriaWpisuDialog
      v-if="!historiaZewnetrzna && historiaOtwarta"
      v-model:open="historiaOtwarta"
      :komentarz="activity.name"
    />
  </div>
</template>
<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import AttachmentItem from '@/components/AttachmentItem.vue'
import HistoriaWpisuDialog from '@/components/HistoriaWpisuDialog.vue'
import { Dropdown, Button, TextEditor, call, toast } from 'frappe-ui'
import TimelineTimestamp from '@/components/Activities/TimelineTimestamp.vue'
import { sanitizeHTML, ConfirmDelete } from '@/utils'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/users'
import { computed, ref } from 'vue'

const props = defineProps({
  activity: { type: Object, default: () => ({}) },
  // VOLTEO (b84): sekcja Notatki leada (KomentarzeLeadaSekcja.vue) pokazuje
  // "dodał(a) notatkę" zamiast domyslnego "dodał(a) komentarz" -- te same
  // dane (Comment), inna etykieta w naglowku wpisu. Puste = bez zmian.
  rzeczownikWpisu: { type: String, default: '' },
  // VOLTEO (rozmowa zadania): menu wpisu bez gałęzi usuwania (zostaje samo
  // "Edit"). Domyślnie false - pozostałe miejsca bez zmian.
  bezUsuwania: { type: Boolean, default: false },
  // VOLTEO: własny zapis edycji, `async (nazwaWpisu, tresc)`. Domyślnie (null)
  // edycja idzie przez `crm.api.komentarze.edytuj` (lead i szansa, ops#364: tylko
  // autor, wersja w historii); `frappe.client.set_value` odmawiał rolom bez prawa
  // `write` na Comment (D2D, Backend). Rozmowa zadania przekazuje tu wywołanie
  // `crm.api.zadania_rozmowa.edytuj`.
  zapiszEdycje: { type: Function, default: null },
  // VOLTEO (ops#364): rozmowa zadania otwiera okno historii sama (zdarzenie
  // `historia`, własny endpoint); lead i szansa zostawiają je temu komponentowi.
  historiaZewnetrzna: { type: Boolean, default: false },
})

// `historia` niesie nazwę wpisu (`activity.name`); emitowane tylko z przycisku
// widocznego przy `activity.liczba_zmian > 0`.
const emit = defineEmits(['reload', 'historia'])

const { user } = sessionStore()

const { isAdmin } = usersStore()

const isOwner = computed(() => props.activity.owner === user)
// Tylko administrator (rola System Manager albo konto Administrator) ma prawo
// `delete` na Comment; nie `isVolteoAdmin()`, bo Volteo Core Admin go nie ma.
const usuwanieWidoczne = computed(
  () => !props.bezUsuwania && (user === 'Administrator' || isAdmin(user)),
)

const historiaOtwarta = ref(false)
function otworzHistorie() {
  if (props.historiaZewnetrzna) emit('historia', props.activity.name)
  else historiaOtwarta.value = true
}

const editing = ref(false)
const saving = ref(false)
const editContent = ref('')
const confirmingDelete = ref(false)

const menuOptions = computed(() => [
  ...(isOwner.value
    ? [
        {
          label: __('Edit'),
          icon: 'edit-2',
          onClick: startEdit,
        },
      ]
    : []),
  ...(!usuwanieWidoczne.value
    ? []
    : ConfirmDelete({
        onConfirmDelete: deleteComment,
        isConfirmingDelete: confirmingDelete,
      })),
])

function startEdit() {
  editContent.value = props.activity.content || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editContent.value = ''
}

async function saveEdit() {
  if (editContent.value === props.activity.content) {
    editing.value = false
    return
  }
  saving.value = true
  try {
    if (props.zapiszEdycje) {
      await props.zapiszEdycje(props.activity.name, editContent.value)
    } else {
      await call('crm.api.komentarze.edytuj', {
        komentarz: props.activity.name,
        tresc: editContent.value,
      })
    }
    editing.value = false
    emit('reload')
  } catch (e) {
    // Endpointy edycji zwracają czytelne powody ("Wpis może edytować tylko jego
    // autor."); stały komunikat tylko, gdy serwer nic nie podał.
    toast.error(e?.messages?.[0] || __('Failed to update comment'))
  } finally {
    saving.value = false
  }
}

async function deleteComment() {
  try {
    await call('frappe.client.delete', {
      doctype: 'Comment',
      name: props.activity.name,
    })
    emit('reload')
  } catch (e) {
    toast.error(__('Failed to delete comment'))
  }
}
</script>
