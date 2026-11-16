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

  `konfig.zdjecia === true` (tylko MONTAZ, ops#191) montuje nad kartą
  "Dodaj wpis" galerię MontazZdjecia.vue, "Zdjęcia z realizacji" - jedna
  wspólna galeria dla całej szansy, niezależna od wpisów tego strumienia.

  `konfig.protokol === true` (tylko MONTAZ, ops#307) montuje pod galerią
  sekcję "Protokół montażu" (ten sam komponent, rodzaj="protokol").

  `konfig.prywatneNotatki === true` (tylko MONTAZ, issue #213) montuje nad
  kartą "Dodaj wpis" (nad galerią zdjęć, gdy obie są obecne) strumień
  notatek prywatnych administracji (NotatkiPrywatne.vue, doctype
  `Volteo Notatka Prywatna`, zupełnie osobny od `konfig.doctype` powyżej) -
  bramka widoczności żyje wewnątrz tamtego komponentu, nie tutaj.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <NotatkiPrywatne v-if="konfig.prywatneNotatki" :deal-id="dealId" />
      <MontazZdjecia v-if="konfig.zdjecia" :deal-id="dealId" />
      <MontazZdjecia v-if="konfig.protokol" :deal-id="dealId" rodzaj="protokol" />

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
            <div class="flex items-center gap-1">
              <span class="text-xs text-ink-gray-4">{{ fmtDate(u.data_zdarzenia) }}</span>
              <template v-if="konfig.edycja">
                <Button
                  v-if="liczbyZmian[u.name] > 0"
                  variant="ghost"
                  size="sm"
                  icon="lucide-history"
                  :tooltip="__('Historia zmian')"
                  data-testid="wpis-historia"
                  @click="otworzHistorie(u.name)"
                />
                <Button
                  v-if="u.owner === user && edytowany !== u.name"
                  variant="ghost"
                  size="sm"
                  icon="lucide-pencil"
                  :tooltip="__('Edit')"
                  data-testid="wpis-edytuj"
                  @click="zacznijEdycje(u)"
                />
                <Button
                  v-if="moznaUsuwac"
                  variant="ghost"
                  size="sm"
                  theme="red"
                  icon="lucide-trash-2"
                  :tooltip="__('Usuń')"
                  @click="usunWpis(u.name)"
                />
              </template>
            </div>
          </div>
          <div v-if="edytowany === u.name" class="flex flex-col gap-2">
            <FormControl
              v-if="!konfig.html"
              type="textarea"
              :rows="2"
              v-model="trescEdycji"
            />
            <TextEditor
              v-else
              :content="trescEdycji"
              :editor-class="['prose-sm max-w-none min-h-[3rem]']"
              :editable="true"
              :mentions="mentionsKonfig"
              @change="trescEdycji = $event"
            />
            <div class="flex justify-end gap-2">
              <Button :label="__('Cancel')" @click="edytowany = ''" />
              <Button
                variant="solid"
                :label="__('Save')"
                :loading="zapisuje"
                :disabled="konfig.html ? tekstPusty(trescEdycji) : !trescEdycji.trim()"
                data-testid="wpis-zapisz"
                @click="zapiszEdycje(u)"
              />
            </div>
          </div>
          <div
            v-else-if="konfig.html"
            class="prose-f text-sm text-ink-gray-8"
            v-html="sanitizeHTML(u.tekst)"
          />
          <div v-else class="whitespace-pre-wrap text-sm text-ink-gray-8">{{ u.tekst }}</div>
          <div class="mt-1.5 text-xs text-ink-gray-5">{{ userName(u.owner) }}</div>
        </div>
      </div>
    </div>
    <HistoriaWpisuDialog
      v-if="historiaOtwarta"
      v-model:open="historiaOtwarta"
      :komentarz="historiaWpis"
      :endpoint="`${konfig.api}.historia`"
      parametr="name"
    />
  </div>
</template>

<script setup>
import { Badge, Button, FormControl, TextEditor, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, computed } from 'vue'
import HistoriaWpisuDialog from '@/components/HistoriaWpisuDialog.vue'
import MontazZdjecia from '@/components/deal/MontazZdjecia.vue'
import NotatkiPrywatne from '@/components/deal/NotatkiPrywatne.vue'
import { sessionStore } from '@/stores/session'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users.js'
import { sanitizeHTML } from '@/utils'
import { tekstPusty } from '@/utils/aktualizacje'

const props = defineProps({
  dealId: { type: String, required: true },
  konfig: { type: Object, required: true },
})

const { getUser, listaWzmianek, isAdmin } = usersStore()
const { user } = sessionStore()
// `$dialog` jest w globalProperties (szablon), a w <script setup> dostepny
// wylacznie przez globalStore (jak w NotatkiPrywatne.vue).
const { $dialog } = globalStore()
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

// ops#364 (tylko strumienie z `konfig.edycja`, dzis Trify): liczba zmian tresci
// per wpis (ikona historii), edycja wlasnego wpisu, usuwanie tylko dla
// administratora (System Manager / Administrator, DocPerm decyduje serwerowo).
const liczbyZmianZasob = createResource({
  url: `${props.konfig.api}.liczby_zmian`,
  params: { deal: props.dealId },
  auto: Boolean(props.konfig.edycja),
})
const liczbyZmian = computed(() => liczbyZmianZasob.data || {})
const moznaUsuwac = computed(() => user === 'Administrator' || isAdmin(user))

const edytowany = ref('')
const trescEdycji = ref('')
const zapisuje = ref(false)
const historiaOtwarta = ref(false)
const historiaWpis = ref('')

function zacznijEdycje(u) {
  trescEdycji.value = u.tekst || ''
  edytowany.value = u.name
}

async function odswiez() {
  await Promise.all([updates.reload(), props.konfig.edycja ? liczbyZmianZasob.reload() : null])
}

async function zapiszEdycje(u) {
  if ((props.konfig.html ? tekstPusty(trescEdycji.value) : !trescEdycji.value.trim()) || zapisuje.value) return
  if (trescEdycji.value === u.tekst) {
    edytowany.value = ''
    return
  }
  zapisuje.value = true
  try {
    await call(`${props.konfig.api}.edytuj`, { name: u.name, tekst: trescEdycji.value })
    edytowany.value = ''
    await odswiez()
  } catch (err) {
    toast.error(err?.messages?.[0] || err?.message || __('Nie udało się zapisać zmiany'))
  } finally {
    zapisuje.value = false
  }
}

function otworzHistorie(name) {
  historiaWpis.value = name
  historiaOtwarta.value = true
}

function usunWpis(name) {
  $dialog({
    title: __('Usuń wpis'),
    message: __('Czy na pewno usunąć ten wpis? Tej operacji nie można cofnąć.'),
    actions: [
      {
        label: __('Usuń'),
        theme: 'red',
        variant: 'solid',
        onClick: async (close) => {
          try {
            await call('frappe.client.delete', { doctype: props.konfig.doctype, name })
            await odswiez()
            close()
          } catch (err) {
            toast.error(err?.messages?.[0] || err?.message || __('Nie udało się usunąć wpisu'))
          }
        },
      },
    ],
  })
}

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
    await odswiez()
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
