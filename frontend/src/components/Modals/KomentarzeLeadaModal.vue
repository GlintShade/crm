<!--
  VOLTEO (ops#94): pseudo-kolumna "Komentarze" na liście leadów otwiera ten
  modal zamiast nawigować do leada, żeby CC mógł dodać komentarz bez
  opuszczania listy. Reużywalny (props docname/doctype, jedna instancja na
  widok), bo ma posłużyć też panelowi na mapie leadów (issue ops#94).
  Historia idzie przez CommentArea.vue, dodawanie przez CommentBox.vue i
  crm.api.comment.add_comment, tak samo jak w zakładce Aktywności.
-->
<template>
  <Dialog v-model:open="show" :options="{ size: '3xl' }">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
            {{ __('Komentarze') }}
          </h3>
          <Button
            icon="lucide-x"
            variant="ghost"
            class="w-7"
            @click="show = false"
          />
        </div>

        <div
          class="flex max-h-[22rem] flex-col gap-3 overflow-y-auto pr-1"
        >
          <div v-if="commentsResource.loading" class="text-sm text-ink-gray-5">
            {{ __('Ładowanie…') }}
          </div>
          <div v-else-if="!comments.length" class="text-sm text-ink-gray-5">
            {{ __('Brak komentarzy.') }}
          </div>
          <template v-else>
            <div v-for="activity in comments" :key="activity.name">
              <CommentArea :activity="activity" @reload="reloadComments" />
            </div>
          </template>
        </div>

        <div class="mt-4 border-t pt-4">
          <CommentBox
            v-model="commentDoc"
            v-model:content="newCommentContent"
            v-model:attachments="newCommentAttachments"
            :editable="true"
            :doctype="doctype"
            :placeholder="__('@Jan, czy możesz to sprawdzić?')"
            :submitButtonProps="{
              variant: 'solid',
              onClick: postComment,
              disabled: commentEmpty || posting,
              loading: posting,
            }"
            :discardButtonProps="{
              onClick: discardComment,
            }"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import CommentArea from '@/components/Activities/CommentArea.vue'
import CommentBox from '@/components/CommentBox.vue'
import { Button, Dialog, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  docname: { type: String, required: true },
  doctype: { type: String, default: 'CRM Lead' },
})

// Niesie swiezy licznik komentarzy (odczytany po zapisie) -- wywolujacy
// (LeadsListView.vue) subskrybuje to zdarzenie, zeby odswiezyc licznik w
// wierszu.
const emit = defineEmits(['commentAdded'])

const show = defineModel({ type: Boolean, default: false })

const commentDoc = ref({ name: props.docname })
const newCommentContent = ref('')
const newCommentAttachments = ref([])
const posting = ref(false)

const commentEmpty = computed(() => {
  return !newCommentContent.value || newCommentContent.value === '<p></p>'
})

// VOLTEO: nie wolamy tu frappe.client.get_list z filtrem po
// reference_doctype/reference_name -- crm.api.volteo_filtry_guard bramkuje
// filtry po polach, ktorych Comment nie udostepnia do odczytu roli Volteo
// Call Center ani Volteo D2D Sales (get_permitted_fields zwraca dla obu
// tylko siedem default_fields), wiec taki filtr byl odrzucany z toastem
// "Brak uprawnień do filtrowania po polu reference_doctype" mimo poprawnego
// zapisu. crm.api.volteo_leady.komentarze sprawdza has_permission na
// dokumencie nadrzednym i czyta Comment przez get_all (patrz docstring tej
// funkcji w crm/api/volteo_leady.py).
function parametryZapytania(docname) {
  return {
    doctype: props.doctype,
    name: docname,
  }
}

const commentsResource = createResource({
  url: 'crm.api.volteo_leady.komentarze',
  params: parametryZapytania(props.docname),
  auto: false,
})

const comments = computed(() => {
  return (commentsResource.data || []).map((c) => ({
    name: c.name,
    owner: c.owner,
    owner_name: c.comment_by || c.owner,
    creation: c.creation,
    content: c.content,
    attachments: [],
  }))
})

function reloadComments() {
  commentsResource.update({ params: parametryZapytania(props.docname) })
  return commentsResource.reload()
}

// Modal jest reuzywalny (jedna instancja na widok) -- `docname` zmienia sie
// przy kolejnym kliknieciu w inny wiersz, wiec odswiezamy przy kazdym
// otwarciu i przy zmianie docname w trakcie otwarcia (na wypadek gdyby
// wywolujacy podmienil props bez zamykania okna).
watch(
  [() => show.value, () => props.docname],
  ([open, docname]) => {
    commentDoc.value = { name: docname }
    if (open && docname) {
      reloadComments()
    }
  },
  { immediate: true },
)

async function postComment() {
  if (commentEmpty.value || posting.value) return
  posting.value = true
  try {
    await call('crm.api.comment.add_comment', {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      content: newCommentContent.value,
      attachments: newCommentAttachments.value.map((f) => f.name),
    })
    newCommentContent.value = ''
    newCommentAttachments.value = []
    await reloadComments()
    emit('commentAdded', { docname: props.docname, count: comments.value.length })
  } catch (err) {
    toast.error(err?.messages?.[0] || __('Nie udało się dodać komentarza'))
  } finally {
    posting.value = false
  }
}

async function discardComment() {
  newCommentContent.value = ''
  newCommentAttachments.value = []
}
</script>
