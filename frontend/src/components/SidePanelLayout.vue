<template>
  <div
    :class="[
      'sections flex flex-col overflow-y-auto',
      karty && 'sections-karty gap-2 px-3 pb-3 pt-0',
    ]"
  >
    <div
      v-if="!preview && !karty && _sections.length"
      class="flex items-center justify-end gap-2 px-3 py-1.5"
    >
      <div class="text-sm text-ink-gray-5">{{ __('Ukryj puste pola') }}</div>
      <Switch size="sm" v-model="ukryjPuste" />
    </div>
    <template v-for="(section, i) in _sections" :key="section.name">
      <div v-if="section.visible" class="section flex flex-col">
        <div
          v-if="!karty && i !== firstVisibleIndex()"
          class="w-full section-border h-px border-t"
        />
        <div :class="karty ? '' : 'p-1 sm:p-3'">
          <component
            :is="karty ? KartaSekcji : Section"
            v-bind="opakowanieSekcji(section)"
          >
            <template v-if="!preview" #actions>
              <slot name="actions" v-bind="{ section }">
                <Button
                  v-if="section.showEditButton"
                  variant="ghost"
                  class="w-7 mr-2"
                  :icon="EditIcon"
                  @click="showSidePanelModal = true"
                />
              </slot>
            </template>
            <slot v-bind="{ section }">
              <component
                :is="karty ? 'div' : FadedScrollableDiv"
                v-if="section.columns?.[0].fields.length"
                :class="
                  karty
                    ? 'column grid grid-cols-2 gap-x-3 gap-y-2.5'
                    : 'column flex flex-col gap-1.5 overflow-y-auto'
                "
              >
                <template
                  v-for="field in section.columns[0].fields || []"
                  :key="field.fieldname"
                >
                  <div
                    v-if="field.visible && czyPoleTekstowe(field)"
                    :class="
                      karty
                        ? 'field col-span-2 flex min-w-0 flex-col gap-1 leading-5'
                        : 'field flex flex-col gap-1 px-3 py-1.5 leading-5 first:mt-3'
                    "
                    :ref="(el) => setTextareaRef(field.fieldname, el)"
                    @focusout="onUwagiFocusout(field)"
                    @focusin="onUwagiFocusin(field)"
                  >
                    <Tooltip :text="__(field.label)" :hoverDelay="1">
                      <div class="flex items-center gap-0.5" :class="karty && 'px-2'">
                        <div
                          :class="[
                            'text-sm text-ink-gray-5',
                            karty ? 'break-words' : 'truncate',
                          ]"
                        >
                          {{ __(field.label) }}
                        </div>
                        <div
                          v-if="
                            field.reqd ||
                            (field.mandatory_depends_on &&
                              field.mandatory_via_depends_on)
                          "
                          :class="karty ? 'text-ink-gray-5' : 'text-ink-red-5'"
                        >
                          *
                        </div>
                      </div>
                    </Tooltip>
                    <div
                      v-if="
                        karty &&
                        czyUwagiImport(field) &&
                        !edytujeUwagi &&
                        liniaUwag(field).length
                      "
                      data-testid="uwagi-odczyt"
                      class="grid cursor-text grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-3 gap-y-1 rounded px-2 py-1 text-sm hover:bg-surface-gray-1"
                      @click="rozpocznijEdycjeUwag"
                    >
                      <template v-for="(l, li) in liniaUwag(field)" :key="li">
                        <div
                          v-if="!l.calaSzerokosc"
                          class="min-w-0 break-words text-ink-gray-5"
                        >
                          {{ l.klucz ? l.klucz + ':' : '' }}
                        </div>
                        <div
                          :class="[
                            'min-w-0 whitespace-pre-wrap break-words text-ink-gray-8',
                            l.calaSzerokosc && 'col-span-2',
                          ]"
                        >
                          {{ l.wartosc }}
                        </div>
                      </template>
                    </div>
                    <div
                      v-else-if="field.read_only"
                      :class="[
                        'whitespace-pre-wrap break-words px-2 py-1 text-base',
                        karty ? 'text-ink-gray-7' : 'text-ink-gray-5',
                      ]"
                    >
                      {{ doc[field.fieldname] }}
                    </div>
                    <FormControl
                      v-else
                      class="form-control w-full"
                      type="textarea"
                      :value="doc[field.fieldname]"
                      :placeholder="field.placeholder"
                      :rows="liczWierszeTekstu(doc[field.fieldname])"
                      :debounce="500"
                      @input="onTekstoweInput"
                      @change.stop="fieldChange($event.target.value, field)"
                    />
                  </div>
                  <div
                    v-else-if="field.visible"
                    :class="
                      karty
                        ? [
                            'field flex min-w-0 flex-col gap-1 leading-5',
                            czySzerokiePole(field) && 'col-span-2',
                          ]
                        : [
                            'field flex gap-2 px-3 leading-5 first:mt-3',
                            podpowiedzDlaPola(field)
                              ? 'items-start'
                              : 'items-center',
                          ]
                    "
                  >
                    <Tooltip
                      v-if="!['Button', 'HTML'].includes(field.fieldtype)"
                      :text="__(field.label)"
                      :hoverDelay="1"
                    >
                      <div
                        :class="
                          karty
                            ? 'flex w-full items-center gap-0.5 px-2'
                            : [
                                'w-[35%] min-w-20 shrink-0 flex items-center gap-0.5',
                                podpowiedzDlaPola(field) && 'min-h-[28px]',
                              ]
                        "
                      >
                        <div
                          :class="[
                            'text-sm text-ink-gray-5',
                            karty ? 'break-words' : 'truncate',
                          ]"
                        >
                          {{ __(field.label) }}
                        </div>
                        <div
                          v-if="
                            field.reqd ||
                            (field.mandatory_depends_on &&
                              field.mandatory_via_depends_on)
                          "
                          :class="karty ? 'text-ink-gray-5' : 'text-ink-red-5'"
                        >
                          *
                        </div>
                      </div>
                    </Tooltip>
                    <div
                      :class="[
                        'flex items-center justify-between',
                        karty || ['Button', 'HTML'].includes(field.fieldtype)
                          ? 'w-full'
                          : 'w-[65%]',
                      ]"
                    >
                      <div
                        :class="[
                          'wartosc-pola grid min-h-[28px] flex-1 items-center overflow-hidden text-base',
                          karty &&
                            (field.read_only
                              ? 'wartosc-ro'
                              : ['Check', 'Button', 'HTML', 'Rating', 'Dropdown', 'Attach', 'Attach Image', 'Text Editor', 'Geolocation'].includes(field.fieldtype)
                                ? 'wartosc-bez-ramki'
                                : 'wartosc-edyt'),
                        ]"
                      >
                        <div
                          v-if="
                            field.read_only &&
                            !czyPoleTagow(field) &&
                            ![
                              'Int',
                              'Float',
                              'Currency',
                              'Percent',
                              'Check',
                              'Dropdown',
                              'Duration',
                              'Rating',
                              'Button',
                              'Attach',
                              'Attach Image',
                              'HTML',
                              'Geolocation',
                              'Text Editor',
                              'User',
                            ].includes(field.fieldtype)
                          "
                          :class="[
                            'flex h-7 items-center px-2 py-1',
                            karty ? 'cursor-default text-ink-gray-7' : 'cursor-pointer text-ink-gray-5',
                          ]"
                        >
                          <Tooltip :text="__(field.tooltip)">
                            <div :class="karty && 'break-words'">
                              {{ wartoscReadOnly(field) }}
                            </div>
                          </Tooltip>
                        </div>
                        <PrimaryDropdown
                          v-else-if="field.fieldtype === 'Dropdown'"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :options="field.options"
                          :create="field.create"
                          :label="field.label"
                        />
                        <FormControl
                          v-else-if="field.fieldtype == 'Check'"
                          v-model="doc[field.fieldname]"
                          class="form-control"
                          type="checkbox"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="
                            fieldChange($event.target.checked, field)
                          "
                        />
                        <FormControl
                          v-else-if="field.fieldtype === 'Code'"
                          class="form-control"
                          type="textarea"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          @change.stop="fieldChange($event.target.value, field)"
                        />
                        <FormControl
                          v-else-if="field.fieldname === 'custom_proby_kontaktu'"
                          :modelValue="
                            probyKontaktuDoWyswietlenia(doc[field.fieldname])
                          "
                          class="form-control cursor-pointer [&_select]:cursor-pointer truncate [&>*]:!ring-0"
                          type="select"
                          :options="field.options"
                          @update:modelValue="
                            (v) => {
                              doc[field.fieldname] = v
                              fieldChange(v, field)
                            }
                          "
                        />
                        <FormControl
                          v-else-if="field.fieldtype === 'Select'"
                          v-model="doc[field.fieldname]"
                          class="form-control cursor-pointer [&_select]:cursor-pointer truncate [&>*]:!ring-0"
                          type="select"
                          :options="field.options"
                          :placeholder="field.placeholder"
                          @update:modelValue="(v) => fieldChange(v, field)"
                        />
                        <Link
                          v-else-if="field.fieldtype === 'User'"
                          class="form-control"
                          :value="
                            doc[field.fieldname] &&
                            getUser(doc[field.fieldname]).full_name
                          "
                          doctype="User"
                          :filters="field.filters"
                          :placeholder="
                            karty
                              ? field.placeholder
                              : __('Select') + ' ' + field.label + '...'
                          "
                          :hideMe="true"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        >
                          <template v-if="doc[field.fieldname]" #prefix>
                            <UserAvatar
                              class="mr-1.5"
                              :user="doc[field.fieldname]"
                              size="sm"
                            />
                          </template>
                          <template #item-prefix="{ option }">
                            <UserAvatar
                              class="mr-1.5"
                              :user="option.value"
                              size="sm"
                            />
                          </template>
                          <template #item-label="{ option }">
                            <Tooltip :text="option.value">
                              <div class="cursor-pointer">
                                {{ getUser(option.value).full_name }}
                              </div>
                            </Tooltip>
                          </template>
                        </Link>
                        <Link
                          v-else-if="
                            ['Link', 'Dynamic Link'].includes(field.fieldtype)
                          "
                          class="form-control select-text"
                          :value="doc[field.fieldname]"
                          :doctype="
                            field.fieldtype == 'Link'
                              ? field.options
                              : doc[field.options]
                          "
                          :filters="field.filters"
                          :placeholder="field.placeholder"
                          :onCreate="field.create"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <div
                          v-else-if="field.fieldtype === 'Time'"
                          class="form-control"
                        >
                          <TimePicker
                            :value="doc[field.fieldname]"
                            :format="getFormat('', '', false, true, false)"
                            :placeholder="field.placeholder"
                            @change="(v) => fieldChange(v, field)"
                          />
                        </div>
                        <div
                          v-else-if="field.fieldtype === 'Datetime'"
                          class="form-control"
                        >
                          <DateTimePickerSiatka
                            :value="doc[field.fieldname]"
                            :format="karty ? 'DD.MM.YYYY HH:mm' : getFormat('', '', true, true, false)"
                            :placeholder="field.placeholder"
                            :placement="isMobileView ? 'bottom-start' : 'left-start'"
                            @change="(v) => fieldChange(v, field)"
                          />
                        </div>
                        <div
                          v-else-if="field.fieldtype === 'Date'"
                          class="form-control"
                        >
                          <DatePicker
                            :value="doc[field.fieldname]"
                            :format="karty ? 'DD.MM.YYYY' : getFormat('', '', true, false, false)"
                            :placeholder="field.placeholder"
                            :placement="isMobileView ? 'bottom-start' : 'left-start'"
                            @change="(v) => fieldChange(v, field)"
                          />
                        </div>
                        <FormattedInput
                          v-else-if="field.fieldtype === 'Percent'"
                          class="form-control"
                          type="text"
                          :value="getFormattedPercent(field.fieldname, doc)"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="
                            fieldChange(flt($event.target.value), field)
                          "
                        />
                        <Password
                          v-else-if="field.fieldtype === 'Password'"
                          class="form-control"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="fieldChange($event.target.value, field)"
                        />
                        <FormattedInput
                          v-else-if="field.fieldtype === 'Int'"
                          class="form-control"
                          type="text"
                          :value="doc[field.fieldname] || '0'"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="fieldChange($event.target.value, field)"
                        />
                        <FormattedInput
                          v-else-if="field.fieldtype === 'Float'"
                          class="form-control"
                          type="text"
                          :value="getFormattedFloat(field.fieldname, doc)"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="
                            fieldChange(flt($event.target.value), field)
                          "
                        />
                        <FormattedInput
                          v-else-if="field.fieldtype === 'Currency'"
                          class="form-control"
                          type="text"
                          :value="formatKwota(doc[field.fieldname], { jednostka: false })"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          :disabled="Boolean(field.read_only)"
                          @change.stop="
                            fieldChange(flt($event.target.value), field)
                          "
                        />
                        <div
                          v-else-if="field.fieldname === 'custom_czas_do_kontaktu'"
                          class="flex min-w-0 flex-col"
                        >
                          <CzasGgMmInput
                            class="form-control"
                            :value="doc[field.fieldname]"
                            :disabled="Boolean(field.read_only)"
                            @change="(v) => fieldChange(v, field)"
                          />
                          <!-- b83: wiek leada do przepisania przez CC, tylko
                               przy pustym i edytowalnym polu. Jedna linia o
                               stalej wysokosci: opis moze sie obciac (waska
                               kolumna siatki kart), gg:mm nigdy. Odswiezanie
                               co minute nie przesuwa ukladu. Nic nie wpisuje
                               do pola. -->
                          <div
                            v-if="podpowiedzDlaPola(field)"
                            class="flex h-4 min-w-0 gap-1 whitespace-nowrap px-2 text-xs leading-4 tabular-nums text-ink-gray-5"
                            :title="podpowiedzDlaPola(field).pelny"
                          >
                            <span class="truncate">
                              {{ podpowiedzDlaPola(field).opis }}
                            </span>
                            <span
                              v-if="podpowiedzDlaPola(field).ggmm"
                              class="shrink-0"
                            >
                              ({{ podpowiedzDlaPola(field).ggmm }})
                            </span>
                          </div>
                        </div>
                        <DurationInput
                          v-else-if="field.fieldtype === 'Duration'"
                          class="form-control"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <RatingInput
                          v-else-if="field.fieldtype === 'Rating'"
                          class="pl-[10px]"
                          :value="doc[field.fieldname]"
                          :max="field.options || 5"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <ButtonControl
                          v-else-if="field.fieldtype === 'Button'"
                          :label="field.label"
                          :icon="field.icon"
                          :theme="getButtonTheme(field.button_color)"
                          :variant="getButtonVariant(field.button_color)"
                          :disabled="Boolean(field.read_only)"
                          @click="handleButtonClick(field)"
                        />
                        <AttachControl
                          v-else-if="
                            ['Attach', 'Attach Image'].includes(field.fieldtype)
                          "
                          class="attach-control"
                          :value="doc[field.fieldname]"
                          :doctype="doctype"
                          :docname="doc.name"
                          :fieldname="field.fieldname"
                          :imageOnly="field.fieldtype === 'Attach Image'"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <HtmlControl
                          v-else-if="field.fieldtype === 'HTML'"
                          :html="
                            document.fieldHtmlMap?.[field.fieldname] !==
                            undefined
                              ? document.fieldHtmlMap[field.fieldname]
                              : interpolateTemplate(field.options || '', doc)
                          "
                        />
                        <GeolocationControl
                          v-else-if="field.fieldtype === 'Geolocation'"
                          class="geolocation-control"
                          :value="doc[field.fieldname]"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <TextEditorControl
                          v-else-if="field.fieldtype === 'Text Editor'"
                          variant="ghost"
                          :fixed-menu="false"
                          :bubble-menu="true"
                          editorClass="w-full !min-h-[38px] !h-[38px] ml-1"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :disabled="Boolean(field.read_only)"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <TagiProduktowInput
                          v-else-if="czyPoleTagow(field)"
                          :field="field"
                          :placeholder="karty ? __('Wybierz') : ''"
                          :value="doc[field.fieldname]"
                          :doctype="doctype"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <MiejscowoscInput
                          v-else-if="
                            doctype === 'CRM Lead' &&
                            field.fieldname === 'custom_install_city'
                          "
                          :value="doc[field.fieldname]"
                          :kod="doc.custom_install_postal_code"
                          :placeholder="field.placeholder"
                          @change="(v) => fieldChange(v, field)"
                        />
                        <FormControl
                          v-else
                          class="form-control"
                          type="text"
                          :value="doc[field.fieldname]"
                          :placeholder="field.placeholder"
                          :debounce="500"
                          @change.stop="fieldChange($event.target.value, field)"
                        />
                      </div>
                      <div class="ml-1">
                        <ArrowUpRightIcon
                          v-if="
                            field.fieldtype === 'Link' &&
                            field.link &&
                            doc[field.fieldname]
                          "
                          class="h-4 w-4 shrink-0 cursor-pointer text-ink-gray-5 hover:text-ink-gray-8"
                          @click.stop="field.link(doc[field.fieldname])"
                        />
                        <EditIcon
                          v-if="
                            field.fieldtype === 'Link' &&
                            field.edit &&
                            doc[field.fieldname]
                          "
                          class="size-3.5 shrink-0 cursor-pointer text-ink-gray-5 hover:text-ink-gray-8"
                          @click.stop="field.edit(doc[field.fieldname])"
                        />
                      </div>
                    </div>
                  </div>
                </template>
              </component>
            </slot>
          </component>
        </div>
      </div>
    </template>
  </div>
  <SidePanelModal
    v-if="showSidePanelModal"
    v-model="showSidePanelModal"
    :doctype="doctype"
    @reload="() => emit('reload')"
  />
</template>

<script setup>
import Password from '@/components/Controls/Password.vue'
import FormattedInput from '@/components/Controls/FormattedInput.vue'
import CzasGgMmInput from '@/components/Controls/CzasGgMmInput.vue'
import DurationInput from '@/components/Controls/DurationInput.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import AttachControl from '@/components/Controls/AttachControl.vue'
import HtmlControl from '@/components/Controls/HtmlControl.vue'
import GeolocationControl from '@/components/Controls/GeolocationControl.vue'
import TextEditorControl from '@/components/Controls/TextEditorControl.vue'
import ButtonControl, {
  getButtonTheme,
  getButtonVariant,
} from '@/components/Controls/ButtonControl.vue'
import Section from '@/components/CollapsibleSection.vue'
import KartaSekcji from '@/components/KartaSekcji.vue'
import PrimaryDropdown from '@/components/PrimaryDropdown.vue'
import FadedScrollableDiv from '@/components/FadedScrollableDiv.vue'
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import EditIcon from '@/components/Icons/EditIcon.vue'
import Link from '@/components/Controls/Link.vue'
import TagiProduktowInput from '@/components/Controls/TagiProduktowInput.vue'
import MiejscowoscInput from '@/components/Controls/MiejscowoscInput.vue'
import DateTimePickerSiatka from '@/components/Controls/DateTimePickerSiatka.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import SidePanelModal from '@/components/Modals/SidePanelModal.vue'
import { getMeta } from '@/stores/meta'
import { parseLinkFilters } from '@/utils/fieldTransforms'
import { czyPoleTagow } from '@/utils/tagiProduktow'
import { czyPoleTekstowe, liczWierszeTekstu } from '@/utils/panelTekst'
import { czyUkrycPole } from '@/utils/panelPuste'
import {
  podsumowanieSekcji,
  czyWygenerowanyPlaceholder,
  rozbijUwagi,
  formatTelefon,
  formatKwota,
  formatData,
  formatDataCzas,
} from '@/utils/panelBoczny'
import { useUkryjPustePola } from '@/composables/useUkryjPustePola'
import { useStanSekcjiPanelu } from '@/composables/useStanSekcjiPanelu'
import { domyslnieOtwartaKarta } from '@/utils/stanSekcjiPanelu'
import {
  miejscowosciKodu,
  uzupelnijAdresLeadaZKodu,
} from '@/data/kodPocztowy'
import { czyPokazacPustaMiejscowosc } from '@/utils/kodPocztowy'
import { usersStore } from '@/stores/users'
import { isMobileView } from '@/composables/settings'
import {
  getFormat,
  evaluateDependsOnValue,
  isNull,
  interpolateTemplate,
} from '@/utils'
import { flt } from '@/utils/numberFormat.js'
import { Tooltip, DatePicker, TimePicker, Switch, dayjsLocal } from 'frappe-ui'
import { useDocument } from '@/data/document'
import { probyKontaktuDoWyswietlenia } from '@/utils/leadyInline'
import {
  czesciPodpowiedzi,
  czyPokazacPodpowiedz,
} from '@/utils/podpowiedzKontaktu'
import {
  ref,
  computed,
  getCurrentInstance,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount,
} from 'vue'

const props = defineProps({
  sections: { type: Object, default: () => ({}) },
  doctype: { type: String, default: 'CRM Lead' },
  docname: { type: String, required: true },
  preview: { type: Boolean, default: false },
  addContact: { type: Function, default: null },
  // Opt-in wariant wygladu: 'karty' (tylko Deal i Lead, ops#326). Domyslnie
  // panel renderuje sie dokladnie jak dotad (kontakty, organizacje, ...).
  wariant: { type: String, default: '' },
  liczbaKontaktow: { type: Number, default: null },
  // Wariant karty: sekcje bez zapamietanego stanu startuja zwiniete
  // (zapis uzytkownika wygrywa, ops#330).
  startZwiniete: { type: Boolean, default: false },
})

const emit = defineEmits(['beforeFieldChange', 'afterFieldChange', 'reload'])

const { getFormattedPercent, getFormattedFloat, getFormattedCurrency } =
  getMeta(props.doctype)

const { users, isManager, getUser } = usersStore()

const { ukryjPuste } = useUkryjPustePola()

const showSidePanelModal = ref(false)

const karty = computed(() => props.wariant === 'karty')

// Stan otwarcia sekcji zapamietany per uzytkownik i doctype (ops#330),
// wspolny dla wszystkich paneli tego doctype. Brak zapisu: karty otwieraja
// tylko pierwsza widoczna sekcje (ze startZwiniete zadnej), zwykly panel
// bierze `opened` z ukladu.
const stanSekcji = useStanSekcjiPanelu(() => props.doctype)

function czyOtwarta(section) {
  const idx = _sections.value.findIndex((s) => s.name === section.name)
  return stanSekcji.czyOtwarta(
    section.name,
    domyslnieOtwartaKarta({
      startZwiniete: props.startZwiniete,
      pierwszaWidoczna: idx === firstVisibleIndex(),
    }),
  )
}

function przelaczSekcje(section) {
  stanSekcji.ustaw(section.name, !czyOtwarta(section))
}

function czyOtwartaZwykla(section) {
  const zUkladu = section.opened ?? true
  // Podglad ukladu i sekcja bez naglowka (nie da sie jej zwinac): sam uklad.
  if (props.preview || !section.label) return zUkladu
  return stanSekcji.czyOtwarta(section.name, zUkladu)
}

function rozwiazWartosc(pole, wartosc) {
  if (pole?.fieldtype === 'User') return getUser(wartosc)?.full_name
  return null
}

function opakowanieSekcji(section) {
  if (!karty.value) {
    return {
      labelClass: 'px-2 font-semibold',
      headerClass: 'h-8',
      label: section.label,
      hideLabel: !section.label,
      opened: czyOtwartaZwykla(section),
      'onUpdate:opened': (v) => !props.preview && stanSekcji.ustaw(section.name, v),
    }
  }
  return {
    label: section.label,
    nazwa: section.name,
    opened: czyOtwarta(section),
    summary: podsumowanieSekcji(section, doc.value, {
      rozwiaz: rozwiazWartosc,
      liczbaKontaktow: props.liczbaKontaktow,
      t: (tekst) => __(tekst),
    }),
    onToggle: () => przelaczSekcje(section),
  }
}

const TYPY_SZEROKIE = [
  'Datetime',
  'Link',
  'User',
  'Dynamic Link',
  'Select',
  'Text Editor',
  'Code',
  'HTML',
  'Attach',
  'Attach Image',
  'Geolocation',
  'Button',
  'Table',
]

function czySzerokiePole(field) {
  return TYPY_SZEROKIE.includes(field.fieldtype) || czyPoleTagow(field)
}

function placeholderKarty(field) {
  // Wybor i daty: jednolite napisy zamiast "Dodaj <etykieta>" z ukladu.
  if (['Select', 'Link', 'User', 'Dynamic Link'].includes(field.fieldtype)) {
    return __('Wybierz')
  }
  if (['Date', 'Datetime'].includes(field.fieldtype)) return 'DD.MM.RRRR'
  if (field.placeholder && !czyWygenerowanyPlaceholder(field.placeholder)) {
    return field.placeholder
  }
  return __('Wpisz')
}

function wartoscReadOnly(field) {
  const v = doc.value[field.fieldname]
  if (!karty.value) return v
  if (field.fieldtype === 'Date') return formatData(v) || v
  if (field.fieldtype === 'Datetime') return formatDataCzas(v) || v
  if (field.fieldname === 'mobile_no' || field.fieldname === 'phone') {
    return formatTelefon(v) || v
  }
  return v
}

// Uwagi (import): w trybie odczytu linie "Klucz: wartosc", klik przelacza na
// dotychczasowy textarea. Zapisany tekst nigdy nie jest przepisywany.
const edytujeUwagi = ref(false)
let uwagiTimer = null

function czyUwagiImport(field) {
  return field.fieldname === 'custom_uwagi_import'
}

// Dlugi "klucz" (zdanie z dwukropkiem w srodku) to nie etykieta: caly
// segment jest wartoscia na pelna szerokosc, czarna i zawijana.
const MAKS_DLUGOSC_KLUCZA_UWAG = 30
function liniaUwag(field) {
  return rozbijUwagi(doc.value[field.fieldname]).map((l) =>
    l.klucz.length > MAKS_DLUGOSC_KLUCZA_UWAG
      ? { klucz: '', wartosc: l.klucz + ': ' + l.wartosc, calaSzerokosc: true }
      : l,
  )
}

function rozpocznijEdycjeUwag() {
  edytujeUwagi.value = true
  nextTick(() =>
    nextTick(() => textareaEls['custom_uwagi_import']?.focus?.()),
  )
}

function onUwagiFocusin(field) {
  if (!czyUwagiImport(field)) return
  clearTimeout(uwagiTimer)
}

// Opoznienie > debounce FormControl (500 ms), zeby nie odmontowac pola przed
// wyslaniem zmiany.
function onUwagiFocusout(field) {
  if (!czyUwagiImport(field) || !karty.value) return
  clearTimeout(uwagiTimer)
  uwagiTimer = setTimeout(() => (edytujeUwagi.value = false), 800)
}

let document = { doc: {} }
let triggerOnChange
let triggerButton = () => {}

if (props.docname) {
  let d = useDocument(props.doctype, props.docname)
  document = d.document
  triggerOnChange = d.triggerOnChange
  triggerButton = d.triggerButton
}

const doc = computed(() => document.doc || {})

// b83: wiek leada przy "Czas do pierwszego kontaktu". Tylko CRM Lead, poza
// podgladem ukladu, tylko przy pustym i edytowalnym polu. Podpowiedz siedzi
// w galezi pola, wiec kto nie widzi pola (permlevel 3), nie widzi tez
// podpowiedzi. `creation` przychodzi w strefie systemu; dayjsLocal przelicza
// na strefe przegladarki, tak samo jak lista leadow (Leads.vue).
const teraz = ref(Date.now())
let zegarPodpowiedzi = null

onMounted(() => {
  if (props.doctype !== 'CRM Lead' || props.preview) return
  zegarPodpowiedzi = setInterval(() => (teraz.value = Date.now()), 60000)
})

onBeforeUnmount(() => clearInterval(zegarPodpowiedzi))

const podpowiedzKontaktu = computed(() => {
  if (props.doctype !== 'CRM Lead' || props.preview) return null
  const creation = doc.value?.creation
  if (!creation) return null
  return czesciPodpowiedzi(dayjsLocal(creation).valueOf(), teraz.value)
})

function podpowiedzDlaPola(field) {
  if (field.fieldname !== 'custom_czas_do_kontaktu') return null
  if (!czyPokazacPodpowiedz(doc.value?.[field.fieldname], field.read_only)) {
    return null
  }
  return podpowiedzKontaktu.value
}

const _sections = computed(() => {
  if (!props.sections?.length) return []
  let editButtonAdded = false
  return props.sections.map((section) => {
    // Klonujemy sekcje/kolumny zamiast mutowac obiekty z props.sections
    // (sections.data, dzielone miedzy panelem bocznym a zakladka
    // Szczegoly na tej samej stronie leada -- oba uzywaja TEGO SAMEGO
    // createResource). Mutacja w miejscu wywolywala niekonczaca sie
    // petle reaktywnosci Vue: kazde przeliczenie tego computed nadpisywalo
    // wspoldzielone dane, co oznaczalo dla DRUGIEJ instancji SidePanelLayout,
    // ze jej wlasny _sections jest "brudny", wiec ona rowniez przeliczala
    // i nadpisywala te same dane, wzajemnie odswiezajac sie w nieskonczonosc
    // (potwierdzone CDP Debugger.pause: stos zawieszony w tej funkcji).
    let _section = { ...section }
    if (_section.columns?.length) {
      _section.columns = [
        {
          ..._section.columns[0],
          fields: _section.columns[0].fields.map((field) => parsedField(field)),
        },
        ..._section.columns.slice(1),
      ]
    }
    _section = parsedSection(_section, editButtonAdded)
    if (_section.showEditButton) {
      editButtonAdded = true
    }
    return _section
  })
})

function parsedField(field) {
  // Clone to avoid mutating the cached layout data
  field = { ...field }

  // Merge script property overrides
  const overrides = document.fieldPropertyOverrides?.[field.fieldname]
  if (overrides) {
    Object.assign(field, overrides)
  }

  if (field.fieldtype == 'Select' && typeof field.options === 'string') {
    field.options = field.options.split('\n').map((option) => {
      return { label: option, value: option }
    })

    if (
      field.options[0].value !== '' &&
      !field.reqd &&
      field.fieldname !== 'custom_proby_kontaktu'
    ) {
      field.options.unshift({ label: '', value: '' })
    }
  }

  if (field.fieldtype === 'Link' && field.options === 'User') {
    field.fieldtype = 'User'
    field.link_filters = JSON.stringify({
      name: ['in', users.data?.crmUsers?.map((user) => user.name)],
      ignore_user_type: 1,
      ...(parseLinkFilters(field.link_filters) || {}),
    })
  }

  const read_only_via_depends_on = evaluateDependsOnValue(
    field.read_only_depends_on,
    doc.value,
  )

  // Script overrides for read_only take priority over depends_on
  const scriptReadOnly = overrides?.read_only
  const effectiveReadOnly =
    scriptReadOnly !== undefined
      ? scriptReadOnly
      : field.read_only ||
        (field.read_only_depends_on && read_only_via_depends_on)

  let _field = {
    ...field,
    filters: parseLinkFilters(field.link_filters),
    placeholder: karty.value
      ? placeholderKarty(field)
      : field.placeholder || field.label,
    display_via_depends_on: evaluateDependsOnValue(field.depends_on, doc.value),
    mandatory_via_depends_on: evaluateDependsOnValue(
      field.mandatory_depends_on,
      doc.value,
    ),
    read_only: effectiveReadOnly,
  }

  _field.visible = isFieldVisible(_field, overrides?.hidden)
  _field.visible =
    _field.visible &&
    (!czyUkrycPole(_field, doc.value?.[_field.fieldname], ukryjPuste.value && !props.preview) ||
      czyPokazacPustaMiejscowosc(props.doctype, _field, () =>
        miejscowosciKodu(doc.value?.custom_install_postal_code),
      ))
  return _field
}

const instance = getCurrentInstance()
const attrs = instance?.vnode?.props ?? {}

async function fieldChange(value, df) {
  if (props.preview) return

  await triggerOnChange(df.fieldname, value)
  // ops#329: nowy kod leada uzupelnia wojewodztwo/powiat/gmine (i jedyna
  // miejscowosc) przed zapisem; blad lookupu jest cichy.
  if (
    props.doctype === 'CRM Lead' &&
    df.fieldname === 'custom_install_postal_code'
  ) {
    await uzupelnijAdresLeadaZKodu(document.doc)
  }

  const hasListener = attrs['onBeforeFieldChange'] !== undefined

  if (hasListener) {
    emit('beforeFieldChange', { [df.fieldname]: value })
  } else {
    document.save.submit(null, {
      onSuccess: () => emit('afterFieldChange', { [df.fieldname]: value }),
    })
  }
}

function parsedSection(section, editButtonAdded) {
  // Merge script property overrides for section
  const overrides = document.fieldPropertyOverrides?.[section.name]
  if (overrides) {
    section = { ...section, ...overrides }
  }

  let isContactSection = section.name == 'contacts_section'
  section.showEditButton = !(
    isMobileView.value ||
    !isManager() ||
    isContactSection ||
    editButtonAdded
  )

  // Script hidden override for sections
  if (overrides?.hidden !== undefined) {
    section.visible = !overrides.hidden
  } else {
    section.visible =
      isContactSection ||
      section.columns?.[0].fields.filter((f) => f.visible).length
  }

  return section
}

function isFieldVisible(field, scriptHidden) {
  if (props.preview) return true

  // Script override for hidden wins over everything
  if (scriptHidden !== undefined) return !scriptHidden

  let readOnlyField =
    field.read_only || field.fieldtype === 'Read Only' ? true : false

  let hideEmptyReadOnlyField =
    isNull(doc.value[field.fieldname]) &&
    Number(window.sysdefaults?.hide_empty_read_only_fields ?? 1)

  let showReadOnlyField = readOnlyField && !hideEmptyReadOnlyField

  return (
    (field.fieldtype == 'Check' ||
      field.fieldtype == 'Button' ||
      showReadOnlyField ||
      !readOnlyField) &&
    (!field.depends_on || field.display_via_depends_on) &&
    !field.hidden
  )
}

async function handleButtonClick(field) {
  if (props.preview) return

  if (typeof field.click === 'function') {
    await field.click(doc.value)
  } else {
    await triggerButton(field.fieldname)
  }
}

// Auto-grow pol tekstowych (Small Text/Text/Long Text, issue #177): rows z
// liczWierszeTekstu() daje sensowna wysokosc od razu (fallback, gdy DOM
// jeszcze nie zmierzony), a ponizsze dopina textarea do faktycznej tresci po
// zamontowaniu, na kazdym wpisywaniu i po kazdej zmianie wartosci pola spoza
// samego pisania (np. odswiezenie dokumentu).
//
// Pulapka znaleziona headless (Chromium+WebKit) po scaleniu #177: ref
// bezposrednio na <FormControl> nie daje natywnego <textarea>. FormControl
// to <script setup> bez defineExpose, a `$el` szablonowego refa na takim
// komponencie nie jest gwarantowanym, jednowezlowym elementem -- w praktyce
// wskazywal na cos bez `.style`, wiec `autoGrow` rzucal
// "Cannot set properties of undefined (setting 'height')" przy kazdym
// montowaniu i kazdej zmianie wartosci. Ref idzie teraz na OPAKOWUJACY
// <div> pionowej galezi (zwykly element DOM, bez niejednoznacznosci), a
// faktyczny <textarea> jest w nim wyszukiwany przez querySelector -- dziala
// tez dla galezi read_only (bez textarea w ogole), ktora po prostu nic nie
// znajduje i wychodzi bez efektu.
const textareaWatchStops = {}
const textareaEls = {}

function autoGrow(el) {
  if (!el || !el.style) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

function onTekstoweInput(event) {
  autoGrow(event.target)
}

function setTextareaRef(fieldname, wrapper) {
  const ta = wrapper?.querySelector?.('textarea')

  if (ta instanceof HTMLTextAreaElement) textareaEls[fieldname] = ta
  else delete textareaEls[fieldname]

  if (!(ta instanceof HTMLTextAreaElement)) {
    // Galaz read_only (bez textarea) albo pole odmontowane -- zatrzymaj
    // watcher, zeby nie trzymac referencji do odlaczonego/nieistniejacego DOM.
    textareaWatchStops[fieldname]?.()
    delete textareaWatchStops[fieldname]
    return
  }

  // nextTick, zeby mierzyc juz zamontowany/zaktualizowany DOM, nie wezel
  // sprzed patcha.
  nextTick(() => autoGrow(ta))

  if (!textareaWatchStops[fieldname]) {
    textareaWatchStops[fieldname] = watch(
      () => doc.value[fieldname],
      () => nextTick(() => autoGrow(ta)),
    )
  }
}

onBeforeUnmount(() => {
  Object.values(textareaWatchStops).forEach((stop) => stop())
  clearTimeout(uwagiTimer)
})

function firstVisibleIndex() {
  return _sections.value.findIndex((section) => section.visible)
}
</script>

<style scoped>
.form-control {
  margin: 2px;
}

:deep(.form-control input:not([type='checkbox'])),
:deep(.form-control select),
:deep(.form-control textarea),
:deep(.form-control button),
:deep(.attach-control),
:deep(.geolocation-control),
.dropdown-button {
  border-color: transparent;
  background: transparent;
}

:deep(.form-control button) {
  gap: 0;
}
:deep(.form-control [type='checkbox']) {
  margin-left: 9px;
  cursor: pointer;
}

:deep(.form-control button > div) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.form-control button svg) {
  color: white;
  width: 0;
}

.sections .section .column {
  /* Domyslnie 300px (Lead.vue, Deal.vue, Contact.vue itp. -- bez zmian).
     Wywolujacy moze podniesc/zdjac ten limit przez zmienna CSS
     --sidepanel-column-max-height na dowolnym przodku (np. LeadSzybkiPodglad.vue),
     bez dotykania tego pliku ani zmiany wygladu istniejacych stron. */
  max-height: var(--sidepanel-column-max-height, 300px);
}
.sections-karty .form-control {
  margin: 0;
}
/* Wariant karty: wartosci pol zawsze czarne (ink-gray-8, jak dotad pola
   edytowalne), takze dla pol tylko do odczytu (disabled) i dla Select/Link.
   Etykiety zostaja szare (text-ink-gray-5), a placeholdery pustych pol
   (Wpisz/Wybierz, text-ink-gray-4) pozostaja szare. */
.sections-karty :deep(.wartosc-pola),
.sections-karty :deep(.wartosc-pola input),
.sections-karty :deep(.wartosc-pola textarea),
.sections-karty :deep(.wartosc-pola select),
.sections-karty :deep(.wartosc-pola button),
.sections-karty
  :deep(
    .wartosc-pola
      [class*='text-ink-gray-']:not(.text-ink-gray-4):not([class*='lucide-']):not(svg)
  ) {
  @apply text-ink-gray-8;
  -webkit-text-fill-color: currentColor;
  opacity: 1;
}
.sections-karty :deep(.wartosc-pola input::placeholder),
.sections-karty :deep(.wartosc-pola textarea::placeholder) {
  @apply text-ink-gray-4;
  -webkit-text-fill-color: currentColor;
}
/* Wariant karty: edytowalne pole = jasnoszare pudelko (bg-surface-gray-2,
   ciemniejsze na hover, kursor wskazujacy), tylko do odczytu = bez pudelka,
   zwykly tekst text-ink-gray-7. Pudelko jest na kontenerze .wartosc-pola, a
   kontrolki w srodku (input/select/przycisk/picker) sa przezroczyste, zeby
   kazdy typ pola (Link, Date, Datetime, Duration, tagi, Miejscowosc) wygladal
   tak samo jak Select. Tylko style, zero zmiany zachowania. */
.sections-karty .wartosc-edyt {
  @apply cursor-pointer rounded bg-surface-gray-2 transition-colors;
}
.sections-karty .wartosc-edyt:hover,
.sections-karty .wartosc-edyt:focus-within {
  @apply bg-surface-gray-3;
}
.sections-karty .wartosc-edyt :deep(input),
.sections-karty .wartosc-edyt :deep(textarea),
.sections-karty .wartosc-edyt :deep(select),
.sections-karty .wartosc-edyt :deep(button),
.sections-karty .wartosc-edyt :deep([class*='bg-surface-gray-']),
.sections-karty .wartosc-edyt :deep([class*='bg-surface-white']) {
  background: transparent !important;
  box-shadow: none !important;
  cursor: pointer;
}
.sections-karty .wartosc-edyt :deep(input:not([type='checkbox'])),
.sections-karty .wartosc-edyt :deep(textarea) {
  cursor: text;
}
.sections-karty .wartosc-ro,
.sections-karty .wartosc-ro :deep(*) {
  cursor: default;
}
.sections-karty .wartosc-ro.wartosc-pola,
.sections-karty .wartosc-ro :deep([class*='text-ink-gray-']:not(.text-ink-gray-4):not([class*='lucide-']):not(svg)),
.sections-karty .wartosc-ro :deep(input),
.sections-karty .wartosc-ro :deep(textarea),
.sections-karty .wartosc-ro :deep(select),
.sections-karty .wartosc-ro :deep(button),
.sections-karty .wartosc-ro :deep([class*='bg-surface-gray-']) {
  background: transparent !important;
  box-shadow: none !important;
  @apply text-ink-gray-7;
  -webkit-text-fill-color: currentColor;
}
.sections-karty .section .column {
  max-height: none;
}
.sections .section:last-of-type .column {
  max-height: none;
}
</style>
