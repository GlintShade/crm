<!--
  VOLTEO (ops#94): pseudo-kolumna "Komentarze" na liście leadów otwiera ten
  modal zamiast nawigować do leada (klik ma `@click.stop.prevent` w
  LeadsListView.vue) — CC ma zobaczyć i dodać komentarz bez opuszczania
  listy. Celowo reużywalny (props `docname`/`doctype`, jedna zamontowana
  instancja na widok, patrz LeadsListView.vue): to samo okno ma posłużyć
  panelowi na mapie leadów (issue ops#94, "Kontekst wspólny").

  Historia komentarzy renderowana przez `CommentArea.vue` (ten sam komponent
  co w zakładce Aktywności — edycja/usuwanie własnego komentarza działają
  bez dodatkowego kodu), pole dodania przez `CommentBox.vue` (bogaty edytor:
  wzmianki @, załączniki, emoji — jak w Aktywności). Zapis idzie tą samą
  ścieżką co reszta aplikacji: `crm.api.comment.add_comment`
  (`reference_doctype`/`reference_name`/`content`/`attachments`), wzorowane
  1:1 na `CommunicationArea.vue::sendComment`.

  `Comment` nie ma pola `owner_name` (CommentArea.vue je wymaga) — ale
  `crm.api.comment.add_comment` zapisuje `comment_by` jako
  `get_fullname(frappe.session.user)` w momencie tworzenia, więc mapujemy
  `owner_name: c.comment_by || c.owner` zamiast dociągać osobne zapytanie.
  Załączniki komentarzy CELOWO nie są tu pobierane (uproszczenie zakresu
  ops#94 — `frappe.client.get_list` na `Comment` i tak nie umie zjoinować
  `File`, patrz analogiczny komentarz w `AudytTab.vue`); `CommentArea.vue`
  renderuje pustą listę załączników, co jest bezpieczne (warunek
  `v-if="activity.attachments?.length"`).
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

function filtryZapytania(docname) {
  return {
    doctype: 'Comment',
    filters: {
      reference_doctype: props.doctype,
      reference_name: docname,
      comment_type: 'Comment',
    },
    fields: ['name', 'owner', 'comment_by', 'comment_email', 'content', 'creation'],
    order_by: 'creation asc',
    limit_page_length: 200,
  }
}

const commentsResource = createResource({
  url: 'frappe.client.get_list',
  params: filtryZapytania(props.docname),
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
  commentsResource.update({ params: filtryZapytania(props.docname) })
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
