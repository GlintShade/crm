<!--
  Dedykowane okno zadania (CRM Task), wariant C planu wizualnego
  plan-def235a312fe485c: dwie kolumny, treść po lewej, panel właściwości po
  prawej (issue GlintShade/proenergy-crm-ops#208). Zastępuje generyczny
  DoctypeModal.vue WYŁĄCZNIE dla `doctype === 'CRM Task'` -
  DoctypeModals.vue rozgałęzia na ten komponent, każdy inny doctype
  dostaje DoctypeModal.vue bez zmian.

  Interfejs identyczny jak DoctypeModal.vue (props docname/defaults/
  doctypeTitle, emity afterInsert/afterUpdate, v-model show) - żaden
  wołający (TasksSection.vue, pages/Tasks.vue, Deals.vue, Leads.vue,
  Activities/AllModals.vue, Modals/CallLogDetailModal.vue) nie wymaga
  zmian, wszystkie idą przez `showModal()`/`useDoctypeModal()`.

  Zapis/tworzenie: dokładnie ten sam mechanizm co DoctypeModal.vue -
  `useDocument('CRM Task', docname)`, `document.save.submit` przy edycji,
  `frappe.client.insert` przy tworzeniu, `MandatoryError` -> ErrorMessage,
  `defaults` scalane w onMounted, `await triggerOnRender()` PO scaleniu
  defaults - to jest load-bearing dla akcji "Otwórz szansę/lead" poniżej:
  przy tworzeniu z defaults (TasksSection.vue przekazuje
  reference_doctype/reference_docname dopiero jako `defaults`, doc jest
  pusty w momencie konstrukcji `useDocument`), `CRMTask.onRender()`
  (doctypes/crm_task/form.js) musi zobaczyć te pola PO ich scaleniu, inaczej
  `document.actions` zostaje puste na całe życie modala.

  Link kontekstowy w nagłówku ("Szansa · PRO/PVME/26/1105" / "Lead · ...")
  czyta reference_doctype/reference_docname bezpośrednio z `doc` (etykieta
  budowana tutaj, nie z `document.actions[0].label`, bo ten niesie tekst
  przycisku "Otwórz Szansa", nie treść pigułki) - klik deleguje nawigację
  do `document.actions[0].onClick(close)`, dokładnie ten sam callback co
  CustomActions.vue przekazuje wszędzie indziej w apce.

  Panel właściwości (status/priorytet/przypisanie/termin) NIE przechodzi
  przez FieldLayout/Field.vue - układ jest stały w kodzie (bez ołówka
  "Edytuj układ pól"), ale kontrolki są te same co Field.vue używa dla
  Link->User (komponent Controls/Link.vue z link_filters name-in-crmUsers)
  i Datetime (DateTimePickerSiatka.vue), żeby zachowanie (dropdown
  użytkowników, siatka godzin pod kalendarzem) było identyczne.

  Kolory statusu/priorytetu z @/utils/zadania.js (frappe-free, literalne
  klasy Tailwind - rose/emerald/sky/lime NIE istnieją w presecie).
  "In Progress" jest zawsze niebieski (decyzja właściciela 2026-09-28,
  MEMORY.md "statusy-w-trakcie-niebieskie").

  Historia (tylko w trybie edycji) czyta WYŁĄCZNIE metadane dokumentu
  (creation/owner/modified/modified_by) - celowo bez sięgania po Version,
  to zostaje poza zakresem tego issue (patrz "Poza zakresem").
-->
<template>
  <Dialog v-model:open="show" size="3xl">
    <template #body>
      <div class="bg-surface-elevation-1 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between gap-2 px-4 sm:px-6">
          <div class="flex min-w-0 items-center gap-2">
            <h3 class="truncate text-3xl-semibold leading-6 text-ink-gray-9">
              {{ editMode ? __('Edit Task') : __('Create Task') }}
            </h3>
            <Button
              v-if="referenceLabel"
              variant="subtle"
              size="sm"
              class="shrink-0"
              :label="referenceLabel"
              :iconRight="ArrowUpRightIcon"
              @click="otworzReferencje"
            />
          </div>
          <Button
            variant="ghost"
            class="w-7 shrink-0"
            icon="lucide-x"
            @click="show = false"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-[1fr_250px]">
          <!-- Lewa kolumna: treść -->
          <div class="flex min-w-0 flex-col gap-4 px-4 pb-2 sm:px-6">
            <FormControl
              type="text"
              :label="__('Title')"
              v-model="doc.title"
              :placeholder="__('Enter {0}', [__('Title')])"
            />

            <div>
              <div class="mb-2 text-sm text-ink-gray-5">{{ __('Description') }}</div>
              <TextEditor
                ref="opisEditor"
                :content="doc.description"
                :editor-class="[
                  'prose-sm max-w-none min-h-[7rem] rounded-b-lg border border-t-0 border-outline-gray-2 bg-surface-white px-3 py-2',
                ]"
                :fixed-menu="opisPrzyciski"
                :mentions="mentionsKonfig"
                :placeholder="__('Description')"
                @change="doc.description = $event"
              />
            </div>

            <div
              v-if="editMode"
              class="flex flex-col gap-1 border-t border-outline-gray-2 pt-3 text-sm text-ink-gray-5"
            >
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-4">
                {{ __('Historia') }}
              </div>
              <div>{{ __('Utworzone {0}', [utworzoneTekst]) }}</div>
              <div>{{ __('Ostatnia zmiana {0}', [ostatniaZmianaTekst]) }}</div>
            </div>

            <ErrorMessage v-if="error" :message="__(error)" />
          </div>

          <!-- Prawa kolumna: panel właściwości -->
          <div
            class="mt-4 flex flex-col gap-5 border-t border-outline-gray-2 bg-surface-gray-1 p-4 sm:mt-0 sm:border-l sm:border-t-0"
          >
            <div>
              <div class="mb-2 text-sm text-ink-gray-5">{{ __('Status') }}</div>
              <div class="flex flex-col gap-0.5">
                <button
                  v-for="s in STATUSY_ZADANIA"
                  :key="s"
                  type="button"
                  class="flex items-center gap-2 rounded px-2 py-1.5 text-left text-sm"
                  :class="
                    doc.status === s
                      ? tloWybranegoStatusu(s)
                      : 'text-ink-gray-7 hover:bg-surface-gray-2'
                  "
                  @click="doc.status = s"
                >
                  <IndicatorIcon :class="kropkaStatusu(s)" />
                  {{ __(s) }}
                </button>
              </div>
            </div>

            <div>
              <div class="mb-2 text-sm text-ink-gray-5">{{ __('Priority') }}</div>
              <div class="flex gap-1">
                <button
                  v-for="p in PRIORYTETY_ZADANIA"
                  :key="p"
                  type="button"
                  class="flex-1 rounded px-2 py-1.5 text-center text-sm"
                  :class="
                    doc.priority === p
                      ? tloWybranegoPriorytetu(p)
                      : 'text-ink-gray-7 hover:bg-surface-gray-2'
                  "
                  @click="doc.priority = p"
                >
                  {{ __(p) }}
                </button>
              </div>
            </div>

            <div>
              <div class="mb-2 text-sm text-ink-gray-5">{{ __('Assigned To') }}</div>
              <Link
                class="form-control"
                :value="doc.assigned_to && getUser(doc.assigned_to).full_name"
                doctype="User"
                :filters="przypisanyFiltry"
                :placeholder="__('Select {0}', [__('Assigned To')])"
                :hideMe="true"
                @change="(v) => (doc.assigned_to = v)"
              >
                <template #prefix>
                  <UserAvatar
                    v-if="doc.assigned_to"
                    class="mr-2"
                    :user="doc.assigned_to"
                    size="sm"
                  />
                </template>
                <template #item-prefix="{ option }">
                  <UserAvatar class="mr-2" :user="option.value" size="sm" />
                </template>
                <template #item-label="{ option }">
                  <Tooltip :text="option.value">
                    <div class="cursor-pointer">
                      {{ getUser(option.value).full_name }}
                    </div>
                  </Tooltip>
                </template>
              </Link>
            </div>

            <div>
              <div class="mb-2 text-sm text-ink-gray-5">{{ __('Due Date') }}</div>
              <DateTimePickerSiatka
                :value="doc.due_date"
                :format="terminFormat"
                :placeholder="__('Enter {0}', [__('Due Date')])"
                input-class="border-none"
                @change="(v) => (doc.due_date = v)"
              />
              <div
                v-if="terminTekst"
                class="mt-1 text-xs"
                :class="terminPrzeterminowany ? 'text-ink-red-4' : 'text-ink-gray-5'"
              >
                {{ terminTekst }}
              </div>
              <div class="mt-2 flex flex-wrap gap-1">
                <Button variant="outline" size="sm" :label="__('Dziś')" @click="ustawTerminZaDni(0)" />
                <Button variant="outline" size="sm" :label="__('Jutro')" @click="ustawTerminZaDni(1)" />
                <Button
                  variant="outline"
                  size="sm"
                  :label="__('Za tydzień')"
                  @click="ustawTerminZaDni(7)"
                />
                <Button variant="ghost" size="sm" :label="__('Clear')" @click="wyczyscTermin" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-4 pb-2 pt-4 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button
            variant="solid"
            :label="editMode ? __('Save') : __('Create')"
            :loading="editMode ? document.save.loading : _create.loading"
            @click="editMode ? update() : create()"
          />
          <Button variant="subtle" :label="__('Cancel')" @click="show = false" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import Link from '@/components/Controls/Link.vue'
import DateTimePickerSiatka from '@/components/Controls/DateTimePickerSiatka.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { useDocument } from '@/data/document'
import { usersStore } from '@/stores/users'
import { getFormat } from '@/utils'
import { przyciskiWedlugListy } from '@/utils/edytorPrzyciski'
import { formatujTermin, terminWzgledny } from '@/utils/dataPolska'
import {
  STATUSY_ZADANIA,
  PRIORYTETY_ZADANIA,
  kropkaStatusu,
  tloWybranegoStatusu,
  tloWybranegoPriorytetu,
} from '@/utils/zadania'
import { TextEditor, Tooltip, createEditorButton, createResource } from 'frappe-ui'
import { computed, ref, onMounted } from 'vue'

const props = defineProps({
  doctypeTitle: { type: String, default: '' },
  doctype: { type: String, default: '' },
  docname: { type: String, default: '' },
  defaults: { type: Object, default: () => ({}) },
})

const show = defineModel({ type: Boolean })

const emit = defineEmits(['afterInsert', 'afterUpdate'])

const { getUser, crmUsers, listaWzmianek } = usersStore()

const { document, triggerOnRender, triggerOnBeforeCreate } = useDocument(
  props.doctype,
  props.docname || null,
)

const doc = computed(() => document.doc || {})
const editMode = computed(() => Boolean(document.doc?.name))
const error = ref(null)

// PUŁAPKA frappe-ui (patrz komentarz w NotatkiStrumien.vue/AktualizacjeTab.vue
// przy `mentionsKonfig`): TextEditor bierze `mentions` jako snapshot przy
// montowaniu edytora, więc getter, nigdy sama wartość.
const mentionsKonfig = { mentions: () => listaWzmianek() }

// Polskie etykiety paska narzędzi (@/utils/edytorPrzyciski.js), własny
// wąski podzbiór (pogrubienie, kursywa, lista punktowana, link) - ten sam
// wzorzec co CommentBox.vue/EmailEditor.vue.
const opisPrzyciski = przyciskiWedlugListy(['Bold', 'Italic', 'Bullet List', 'Link'], createEditorButton)

// Ten sam filtr co Field.vue buduje dla Link->User (field.fieldtype ===
// 'Link' && field.options === 'User'): tylko użytkownicy CRM.
const przypisanyFiltry = computed(() => ({
  name: ['in', (crmUsers.value || []).map((u) => u.name)],
  ignore_user_type: 1,
}))

// Link kontekstowy w nagłówku - etykieta budowana z reference_doctype/
// reference_docname wprost (NIE z document.actions[0].label, który niesie
// tekst przycisku "Otwórz Szansa"/"Otwórz Lead", nie treść pigułki).
const referenceLabel = computed(() => {
  const rt = doc.value.reference_doctype
  const rn = doc.value.reference_docname
  if (!rt || !rn) return ''
  const etykieta = rt === 'CRM Deal' ? __('Deal') : __('Lead')
  return `${etykieta} · ${rn}`
})

function otworzReferencje() {
  const akcja = document.actions?.[0]
  if (!akcja?.onClick) return
  akcja.onClick(() => (show.value = false))
}

// Historia (tylko w trybie edycji) - metadane dokumentu, bez Version.
const utworzoneTekst = computed(() => {
  const data = formatujTermin(doc.value.creation)
  const autor = doc.value.owner ? getUser(doc.value.owner).full_name : ''
  return [data, autor].filter(Boolean).join(' · ')
})
const ostatniaZmianaTekst = computed(() => {
  const data = formatujTermin(doc.value.modified)
  const autor = doc.value.modified_by ? getUser(doc.value.modified_by).full_name : ''
  return [data, autor].filter(Boolean).join(' · ')
})

// Ten sam format co Field.vue dla Datetime (onlyDate+onlyTime, withDate
// false, bo `getFormat` z pustym `date` i `withDate=true` zwróciłby '').
const terminFormat = getFormat('', '', true, true, false)

const terminTekst = computed(() => terminWzgledny(doc.value.due_date))
const terminPrzeterminowany = computed(() => terminTekst.value.startsWith('Termin minął'))

function formatujDataDoZapisu(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// Chipy "Dziś"/"Jutro"/"Za tydzień": ustawiają dany dzień na 09:00
// lokalnie (założenie do klik-testu, brief #208).
function ustawTerminZaDni(przesuniecieDni) {
  const d = new Date()
  d.setDate(d.getDate() + przesuniecieDni)
  d.setHours(9, 0, 0, 0)
  doc.value.due_date = formatujDataDoZapisu(d)
}

function wyczyscTermin() {
  doc.value.due_date = null
}

const _create = createResource({
  url: 'frappe.client.insert',
  onSuccess: (d) => {
    document.doc = {}
    emit('afterInsert', d)
    show.value = false
  },
  onError: (err) => {
    if (err.exc_type == 'MandatoryError') {
      const fieldName = err.messages
        .map((msg) => {
          let arr = msg.split(': ')
          return arr[arr.length - 1].trim()
        })
        .join(', ')
      error.value = __('Mandatory field error: {0}', [fieldName])
      return
    }
    error.value = err.messages?.[0] || 'Could not create document'
  },
})

async function create() {
  await triggerOnBeforeCreate?.()

  _create.submit({
    doc: {
      doctype: props.doctype,
      ...document.doc,
    },
  })
}

function update() {
  document.save.submit(null, {
    onSuccess: (d) => {
      emit('afterUpdate', d)
      show.value = false
    },
    onError: (err) => {
      error.value = err.messages?.[0] || 'Could not update document'
    },
  })
}

onMounted(async () => {
  document.doc = {
    ...document.doc,
    ...props.defaults,
  }
  // Load-bearing dla CRMTask.onRender() (doctypes/crm_task/form.js): przy
  // tworzeniu z defaults, reference_doctype/reference_docname arrive tutaj,
  // PO konstrukcji useDocument() - bez tego drugiego triggerOnRender()
  // document.actions zostaje puste, patrz komentarz w nagłówku pliku.
  await triggerOnRender()
})
</script>
