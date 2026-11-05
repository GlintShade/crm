<!--
  VOLTEO (b84): notatki leada (dawne "Komentarze") jako zwijana sekcja
  zakladki "Szczegoly" (Lead.vue, MobileLead.vue), zamiast osobnej zakladki
  "Komentarze". Nazwa sekcji to "Notatki" (spojnie z karta w prawym
  panelu, NotatkiLeadaPanel.vue) -- to tylko etykieta w tym widoku, dane
  pod spodem to nadal ten sam `Comment` co dotad (patrz docstring
  NotatkiLeadaPanel.vue), wiec reszta kodu (zmienne, API, testy) zostaje
  przy nazwie "komentarze". Dane i zapis te same co w
  KomentarzeLeadaModal.vue: odczyt przez crm.api.volteo_leady.komentarze
  (has_permission na leadzie + maskowanie CC), zapis przez
  crm.api.comment.add_comment, lista przez CommentArea, edytor z
  @wzmiankami i zalacznikami przez CommentBox (`card` -- jedno spojne pole
  z tlem panelu, patrz CommentBox.vue).

  Stan otwarcia jest domyslnie WSPOLNY z karta "Notatki" w prawym panelu: ten
  sam klucz (SEKCJA_NOTATKI), wiec przelaczenie jednego przelacza drugie i
  stan przezywa odswiezenie strony. Przelacznik "Synchronizuj sekcje" (b84,
  zadanie F) moze to rozdzielic -- ta sekcja zawsze bierze zakres widoku
  "Szczegoly" (WIDOK_SZCZEGOLY), wiec przy wylaczonej synchronizacji ma
  wlasny zapis, niezalezny od karty w prawym panelu (ta zostaje bez zakresu,
  patrz NotatkiLeadaPanel.vue). Lista przeladowuje sie na wspolny sygnal z
  utils/notatkiLeada.js (dodanie komentarza w prawym panelu, w popupie albo
  w zakladce Aktywnosc).
-->
<template>
  <div ref="korzen" class="section flex flex-col" data-testid="komentarze-leada-sekcja">
    <div class="w-full section-border h-px border-t" />
    <div class="p-1 sm:p-3">
      <CollapsibleSection
        :label="__('Notatki')"
        labelClass="px-2 font-semibold"
        headerClass="h-8"
        :count="comments.length || ''"
        :opened="otwarte"
        @update:opened="(v) => stanSekcji.ustaw(SEKCJA_NOTATKI, v)"
      >
        <div class="px-2 pb-2 pt-2">
          <div class="mb-3 flex max-h-[26rem] flex-col gap-3 overflow-y-auto pr-1">
            <div v-if="zasob.loading && !zasob.data" class="text-sm text-ink-gray-5">
              {{ __('Ładowanie…') }}
            </div>
            <div v-else-if="!comments.length" class="text-sm text-ink-gray-5">
              {{ __('Brak notatek.') }}
            </div>
            <template v-else>
              <div v-for="activity in comments" :key="activity.name">
                <CommentArea
                  :activity="activity"
                  :rzeczownikWpisu="__('notatkę')"
                  @reload="przeladuj"
                />
              </div>
            </template>
          </div>
          <CommentBox
            v-model="commentDoc"
            v-model:content="nowaTresc"
            v-model:attachments="noweZalaczniki"
            :editable="true"
            :doctype="doctype"
            card
            :placeholder="__('Napisz notatkę, @ oznacza osobę')"
            :submitLabel="__('Dodaj notatkę')"
            :discardLabel="__('Anuluj')"
            :submitButtonProps="{
              variant: 'solid',
              onClick: dodaj,
              disabled: pusty || wysylanie,
              loading: wysylanie,
            }"
            :discardButtonProps="{ onClick: odrzuc }"
          />
        </div>
      </CollapsibleSection>
    </div>
  </div>
</template>

<script setup>
import CommentArea from '@/components/Activities/CommentArea.vue'
import CommentBox from '@/components/CommentBox.vue'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import { useStanSekcjiPanelu } from '@/composables/useStanSekcjiPanelu'
import { SEKCJA_NOTATKI, WIDOK_SZCZEGOLY } from '@/utils/stanSekcjiPanelu'
import { wersjaKomentarzy, zglosZmianeKomentarzy } from '@/utils/notatkiLeada'
import { call, createResource, toast } from 'frappe-ui'
import { przewinDoKomentarzy } from '@/utils/komentarzeSekcja'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  docname: { type: String, required: true },
  doctype: { type: String, default: 'CRM Lead' },
})

const stanSekcji = useStanSekcjiPanelu(() => props.doctype, WIDOK_SZCZEGOLY)
const otwarte = computed(() => stanSekcji.czyOtwarta(SEKCJA_NOTATKI, true))

const korzen = ref(null)
const commentDoc = ref({ name: props.docname })
const nowaTresc = ref('')
const noweZalaczniki = ref([])
const wysylanie = ref(false)

const pusty = computed(() => !nowaTresc.value || nowaTresc.value === '<p></p>')

const zasob = createResource({
  url: 'crm.api.volteo_leady.komentarze',
  params: { doctype: props.doctype, name: props.docname },
  auto: true,
})

const comments = computed(() =>
  (zasob.data || []).map((c) => ({
    name: c.name,
    owner: c.owner,
    owner_name: c.comment_by || c.owner,
    creation: c.creation,
    content: c.content,
    attachments: [],
  })),
)

function przeladuj() {
  zasob.update({ params: { doctype: props.doctype, name: props.docname } })
  return zasob.reload()
}

watch(
  () => props.docname,
  (nazwa) => {
    commentDoc.value = { name: nazwa }
    przeladuj()
  },
)

// Komentarz dodany gdzie indziej (prawy panel, popup, zakladka Aktywnosc).
watch(
  () => wersjaKomentarzy(props.doctype, props.docname),
  () => {
    if (!wysylanie.value) przeladuj()
  },
)

// Adres wskazujacy komentarze (dawne #comments, #<komentarz> z powiadomienia):
// sekcja jest juz otwarta przez Lead.vue, tu tylko przewijamy do niej.
watch(
  [przewinDoKomentarzy, korzen],
  ([chce, el]) => {
    if (!chce || !el) return
    przewinDoKomentarzy.value = false
    nextTick(() =>
      setTimeout(() => {
        const hash = decodeURIComponent(location.hash.replace('#', ''))
        const cel = (hash && document.getElementById(hash)) || el
        cel.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 350),
    )
  },
  { immediate: true },
)

async function dodaj() {
  if (pusty.value || wysylanie.value) return
  wysylanie.value = true
  try {
    await call('crm.api.comment.add_comment', {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      content: nowaTresc.value,
      attachments: noweZalaczniki.value.map((f) => f.name),
    })
    nowaTresc.value = ''
    noweZalaczniki.value = []
    await przeladuj()
    zglosZmianeKomentarzy(props.doctype, props.docname)
  } catch (err) {
    toast.error(err?.messages?.[0] || __('Nie udało się dodać komentarza'))
  } finally {
    wysylanie.value = false
  }
}

function odrzuc() {
  nowaTresc.value = ''
  noweZalaczniki.value = []
}
</script>
