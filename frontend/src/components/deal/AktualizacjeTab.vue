<!--
  Wspólny komponent strumienia wpisów na szansie (Szansa view) — uogólnienie
  dawnego MontazTab.vue tak, by obsługiwał więcej niż jeden doctype: wpis +
  typ + oś czasu od najnowszego. Konkretny strumień (nazwa doctype, lista
  dostępnych typów, teksty UI, czy treść to zwykły tekst czy HTML) dostarcza
  props `konfig` — patrz `@/utils/aktualizacje.js` (MONTAZ, TRIFY). Kolejny
  strumień (np. przyszła zakładka kredytu CP) to tylko nowy obiekt
  konfiguracji, bez nowego komponentu.

  Tryb `konfig.html === true` (Trify) używa edytora frappe-ui `TextEditor`
  ze wzmiankami @użytkownik — dokładnie ten sam mechanizm co komentarze
  szansy (zob. CommentBox.vue). Lista podpowiedzi pochodzi z
  `usersStore().listaWzmianek()` — dedykowane API wg hierarchii (ops#75,
  decyzja właściciela), nie z pełnego `crmUsers`. Powiadomienie wspomnianej
  osoby robi serwer (hook after_insert na doctype), nie front — front tylko
  wysyła gotowy HTML. Tryb `konfig.html === false` (Montaż) zachowuje
  dokładny dotychczasowy wygląd i zachowanie: zwykła textarea, brak
  wzmianek.

  PUŁAPKA (ops#75): TextEditor bierze `mentions` jako snapshot przy
  montowaniu, a ta zakładka montuje się zanim usersStore się załaduje —
  dlatego edytorowi przekazujemy `mentionsKonfig` (getter), nie listę
  bezpośrednio; patrz komentarz przy `mentionsKonfig` niżej.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <!-- Dodaj wpis -->
      <div class="rounded-lg border border-outline-gray-2 p-4">
        <div class="mb-3 flex items-center gap-2">
          <FormControl
            type="select"
            :options="konfig.typy"
            v-model="draft.typ"
            class="w-48"
          />
        </div>
        <FormControl
          v-if="!konfig.html"
          type="textarea"
          :placeholder="__(konfig.placeholder)"
          v-model="draft.tekst"
          :rows="2"
        />
        <TextEditor
          v-else
          ref="textEditor"
          :content="draft.tekst"
          :editor-class="['prose-sm max-w-none min-h-[4rem]']"
          :placeholder="__(konfig.placeholder)"
          :editable="true"
          :mentions="mentionsKonfig"
          @change="draft.tekst = $event"
        />
        <div class="mt-3 flex justify-end">
          <Button
            variant="solid"
            :label="__(konfig.przycisk)"
            :loading="adding"
            :disabled="konfig.html ? tekstPusty(draft.tekst) : !draft.tekst.trim()"
            @click="addUpdate"
          />
        </div>
      </div>

      <!-- Oś czasu -->
      <div v-if="updates.loading" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div
        v-else-if="!rows.length"
        class="py-10 text-center text-sm text-ink-gray-5"
      >
        {{ __(konfig.pusty) }}
      </div>
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="u in rows"
          :key="u.name"
          :id="u.name"
          class="rounded-lg border border-outline-gray-1 p-4"
        >
          <div class="mb-1.5 flex items-center justify-between">
            <Badge variant="subtle" theme="gray" size="sm" :label="u.typ || __('Notatka')" />
            <span class="text-xs text-ink-gray-4">{{ fmtDate(u.data_zdarzenia) }}</span>
          </div>
          <div
            v-if="konfig.html"
            class="prose-f text-sm text-ink-gray-8"
            v-html="sanitizeHTML(u.tekst)"
          />
          <div v-else class="whitespace-pre-wrap text-sm text-ink-gray-8">{{ u.tekst }}</div>
          <div class="mt-1.5 text-xs text-ink-gray-5">{{ userName(u.owner) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, FormControl, TextEditor, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, computed } from 'vue'
import { usersStore } from '@/stores/users.js'
import { sanitizeHTML } from '@/utils'
import { tekstPusty } from '@/utils/aktualizacje'

const props = defineProps({
  dealId: { type: String, required: true },
  konfig: { type: Object, required: true },
})

const { getUser, listaWzmianek } = usersStore()
const draft = reactive({ typ: props.konfig.typy[0], tekst: '' })
const adding = ref(false)
const textEditor = ref(null)

// PUŁAPKA frappe-ui: TextEditor konfiguruje MentionExtension raz, przy
// tworzeniu edytora (snapshot tablicy). Ta zakładka montuje się przy wejściu
// na szansę, zanim usersStore się załaduje — więc tablica byłaby pusta na
// zawsze. Rozszerzenie czyta listę przez toValue(), a więc getter jest
// rozwiązywany leniwie przy każdym „@". Obiektowa forma propsa
// ({ mentions, component }) jest jedyną, która przepuszcza getter.
const mentionsKonfig = { mentions: () => listaWzmianek() }

const updates = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: props.konfig.doctype,
    filters: { deal: props.dealId },
    fields: ['name', 'typ', 'data_zdarzenia', 'tekst', 'owner'],
    order_by: 'data_zdarzenia desc',
    limit_page_length: 200,
  },
  auto: true,
})

const rows = computed(() => updates.data || [])

async function addUpdate() {
  if (props.konfig.html ? tekstPusty(draft.tekst) : !draft.tekst.trim()) return
  adding.value = true
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: props.konfig.doctype,
        deal: props.dealId,
        typ: draft.typ,
        tekst: props.konfig.html ? draft.tekst : draft.tekst.trim(),
      },
    })
    if (props.konfig.html) {
      // TipTap echem zwraca "<p></p>" po wyczyszczeniu treści — nie pusty
      // string. tekstPusty() (używana wyżej do bramkowania przycisku) to
      // rozpoznaje, więc to nie jest błąd, tylko oczekiwany stan "pusto".
      textEditor.value?.editor?.commands.clearContent()
    }
    draft.tekst = ''
    draft.typ = props.konfig.typy[0]
    await updates.reload()
  } catch (err) {
    toast.error((err && (err.messages?.[0] || err.message)) || __(props.konfig.blad))
  } finally {
    adding.value = false
  }
}

function userName(email) {
  return getUser(email)?.full_name || email || ''
}

function fmtDate(dt) {
  if (!dt) return ''
  return String(dt).slice(0, 16).replace('T', ' ')
}
</script>
