<template>
  <ListView
    :class="$attrs.class"
    :columns="columns"
    :rows="rows"
    :options="{
      getRowRoute: dealRoute,
      selectable: canSelectRows,
      showTooltip: options.showTooltip,
      resizeColumn: options.resizeColumn,
      rowHeight: options.rowHeight,
      selectionText: (n) =>
        n === 1 ? __('Zaznaczono 1 wiersz') : __('Zaznaczono {0} wierszy', [n]),
    }"
    row-key="name"
    @update:selections="(selections) => emit('selectionsChanged', selections)"
  >
    <ListHeader
      class="sm:mx-5 mx-3"
      @columnWidthUpdated="emit('columnWidthUpdated')"
    >
      <ListHeaderItem
        v-for="column in columns"
        :key="column.key"
        :item="column"
        @columnWidthUpdated="onColumnWidthUpdated"
      >
        <Button
          v-if="column.key == '_liked_by'"
          variant="ghosted"
          class="!h-4"
          :class="isLikeFilterApplied ? 'fill-red-500' : 'fill-white'"
          @click="() => emit('applyLikeFilter')"
        >
          <HeartIcon class="h-4 w-4" />
        </Button>
      </ListHeaderItem>
    </ListHeader>
    <ListRows
      v-slot="{ idx, column, item, row }"
      :rows="rows"
      doctype="CRM Deal"
    >
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden">
        <template #prefix>
          <div
            v-if="column.key === '_assign'"
            class="flex items-center truncate"
          >
            <MultipleAvatar
              :avatars="item"
              size="sm"
              @click="
                (event) =>
                  emit('applyFilter', {
                    event,
                    idx,
                    column,
                    item,
                    firstColumn: columns[0],
                  })
              "
            />
          </div>
          <div v-else-if="column.key === 'organization'">
            <Avatar
              v-if="item.label"
              class="flex items-center"
              :image="item.logo"
              :label="item.label"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'mobile_no' && item?.numer">
            <PhoneIcon class="h-4 w-4" />
          </div>
          <div v-else-if="column.key === '_liked_by'">
            <Button
              v-if="column.key == '_liked_by'"
              variant="ghosted"
              :class="isLiked(item) ? 'fill-red-500' : 'fill-white'"
              @click.stop.prevent="
                () => emit('likeDoc', { name: row.name, liked: isLiked(item) })
              "
            >
              <HeartIcon class="h-4 w-4" />
            </Button>
          </div>
        </template>
        <template #default="{ label }">
          <div
            v-if="column.key === 'lead_name'"
            class="flex flex-col overflow-hidden py-1 leading-tight"
          >
            <span
              v-if="item?.label"
              class="truncate font-medium text-ink-gray-9"
              data-fit="lead_name"
            >
              {{ item.label }}
            </span>
            <span v-else class="truncate italic text-ink-gray-4" data-fit="lead_name">
              {{ __('brak klienta') }}
            </span>
            <span class="truncate text-sm text-ink-gray-5" data-fit="lead_name">{{
              item?.dealName
            }}</span>
          </div>
          <div
            v-else-if="column.key === 'custom_rodzaj_umowy'"
            class="truncate text-base"
            :title="item?.pelnaNazwa"
            data-fit="custom_rodzaj_umowy"
          >
            {{ item?.kod }}
          </div>
          <div
            v-else-if="column.key === 'status'"
            class="flex w-full flex-col gap-1 overflow-hidden py-1 leading-tight"
          >
            <Badge
              variant="subtle"
              class="w-fit"
              :theme="item?.theme"
              size="md"
              :label="item?.label"
              @click="
                (event) =>
                  emit('applyFilter', {
                    event,
                    idx,
                    column,
                    item,
                    firstColumn: columns[0],
                  })
              "
            />
            <PasekEtapu
              v-if="segmentyDlaWiersza(row) > 0"
              :etap="wypelnioneDlaWiersza(row)"
              :etapow="segmentyDlaWiersza(row)"
              :theme="item?.theme"
            />
          </div>
          <div
            v-else-if="column.key === 'modified'"
            class="truncate text-base font-normal"
            :title="item?.pelnaData"
            data-fit="modified"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ item?.relatywnie }}
          </div>
          <div
            v-else-if="
              [
                'creation',
                'first_response_time',
                'first_responded_on',
                'response_by',
              ].includes(column.key)
            "
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            <Tooltip :text="item.label">
              <div>{{ item.timeAgo }}</div>
            </Tooltip>
          </div>
          <div
            v-else-if="column.key === 'sla_status'"
            class="truncate text-base"
          >
            <Badge
              v-if="item.value"
              :variant="'subtle'"
              :theme="item.color"
              size="md"
              :label="item.value"
              @click="
                (event) =>
                  emit('applyFilter', {
                    event,
                    idx,
                    column,
                    item,
                    firstColumn: columns[0],
                  })
              "
            />
          </div>
          <div v-else-if="column.type === 'Check'">
            <FormControl
              type="checkbox"
              :modelValue="item"
              :disabled="true"
              class="text-ink-gray-9"
            />
          </div>
          <RatingInput
            v-else-if="column.type === 'Rating'"
            :value="item"
            class="!opacity-100 flex-nowrap overflow-auto"
            :disabled="true"
            :max="column.options || 5"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          />
          <div
            v-else-if="column.key === 'deal_owner'"
            class="whitespace-nowrap text-base"
            data-fit="deal_owner"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ item?.label }}
          </div>
          <div v-else-if="column.key === 'mobile_no'" class="overflow-hidden py-1">
            <TelefonLink
              :numer="item?.numer || ''"
              class="truncate"
              data-fit="mobile_no"
            />
          </div>
          <div v-else-if="column.key === 'email'" class="overflow-hidden py-1">
            <a
              v-if="item?.email"
              :href="'mailto:' + item.email"
              class="truncate text-base hover:underline"
              data-fit="email"
              @click.stop
            >{{ item.email }}</a>
            <span
              v-else
              class="truncate text-base italic text-ink-gray-4"
              data-fit="email"
            >
              {{ __('brak maila') }}
            </span>
          </div>
          <div
            v-else-if="label"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ getLabel(label, column) }}
          </div>
        </template>
      </ListRowItem>
    </ListRows>
    <ListSelectBanner v-if="canSelectRows">
      <template #actions="{ selections, unselectAll }">
        <Dropdown
          :options="listBulkActionsRef.bulkActions(selections, unselectAll)"
        >
          <Button icon="lucide-more-horizontal" variant="ghost" />
        </Dropdown>
      </template>
    </ListSelectBanner>
  </ListView>
  <ListFooterVolteo
    v-if="pageLengthCount"
    v-model="pageLengthCount"
    class="border-t sm:px-5 px-3 py-2"
    :options="{
      rowCount: options.rowCount,
      totalCount: options.totalCount,
    }"
    @loadMore="emit('loadMore')"
  />
  <ListBulkActions
    ref="listBulkActionsRef"
    v-model="list"
    doctype="CRM Deal"
    :options="{ hideEdit: !isVolteoAdmin(), hideAssign: !isVolteoAdmin() }"
  />
</template>

<script setup>
import HeartIcon from '@/components/Icons/HeartIcon.vue'
import MultipleAvatar from '@/components/MultipleAvatar.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import TelefonLink from '@/components/TelefonLink.vue'
import PasekEtapu from '@/components/PasekEtapu.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import ListBulkActions from '@/components/ListBulkActions.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import ListFooterVolteo from '@/components/ListFooterVolteo.vue'
import { isTranslatable, formatDuration } from '@/utils'
import { liczbaSegmentow, segmentyWypelnione } from '@/utils/pasekEtapu'
import {
  Avatar,
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  ListSelectBanner,
  Dropdown,
  Tooltip,
  createResource,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/users'
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
  options: {
    type: Object,
    default: () => ({
      selectable: true,
      showTooltip: true,
      resizeColumn: false,
      totalCount: 0,
      rowCount: 0,
    }),
  },
})

const emit = defineEmits([
  'loadMore',
  'updatePageCount',
  'columnWidthUpdated',
  'applyFilter',
  'applyLikeFilter',
  'likeDoc',
  'selectionsChanged',
])

const route = useRoute()

const pageLengthCount = defineModel({ type: Number })
const list = defineModel('list', { type: Object })

function getLabel(label, column) {
  if (column.type === 'Duration') return formatDuration(label)
  if (column.options && isTranslatable(column.options)) return __(label)
  return label
}

// Przeciaganie krawedzi naglowka do zmiany szerokosci kolumny (runda 4
// klik-testu, 2026 09 29). frappe-ui's ListHeaderItem tylko EMITUJE
// {key, width, save} przy kazdym mousemove (save=false na biezaco,
// save=true raz, po 1 s debounce od ostatniego ruchu) - samo NIE zapisuje
// nowej szerokosci nigdzie. Upstream wzorzec skopiowany do kazdej listy w
// tej apce (`emit('columnWidthUpdated', column)`, od commitu ead04d4b,
// bump 1.77.3) odrzuca ten payload i podaje dalej STARY obiekt kolumny
// sprzed przeciagniecia, wiec szerokosc nigdy nie trafia do zadnego stanu
// - std. dlaczego przeciaganie nie robilo nic na ZADNEJ liscie w tej
// aplikacji, nie tylko na Umowach. Naprawa tylko tutaj (Umowy): kolumne
// szukamy PO KLUCZU wprost w `list.value.data.columns` (prawdziwa,
// reaktywna tablica zasobu `deals`, nie w lokalnym prop `columns` z
// Deals.vue, ktory dla OSTATNIEJ kolumny jest swiezo tworzona kopia przez
// spread w computed `columns` - mutacja klucza `width` na tej kopii
// zgineloby przy najblizszym przeliczeniu). Mutacja `.width` na
// prawdziwym obiekcie odswieza siatke na biezaco (frappe-ui czyta
// `column.width` wprost w swoim :style). Payload podajemy dalej
// niezmieniony (`emit('columnWidthUpdated', payload)`) - Deals.vue
// (onColumnWidthUpdated tam) odczytuje `payload.save` i dopiero na
// potwierdzonym, odebouncowanym zapisie wola trwaly zapis przez juz
// istniejacy mechanizm tego pliku (`watch(resizeColumn, ...)` ->
// `updateColumns()` w ViewControls.vue).
function onColumnWidthUpdated(payload) {
  const col = list.value?.data?.columns?.find((c) => c.key === payload?.key)
  if (col && payload?.width) {
    col.width = payload.width
  }
  emit('columnWidthUpdated', payload)
}

// Standardowe dopasowanie szerokości kolumn do treści (runda 4 klik-testu,
// 2026 09 29, decyzja właściciela: układ hybrydowy). `default_list_data()`
// w crm_deal.py celowo nie niesie już żadnej szerokości - po każdym
// świeżym zestawie wierszy mierzymy najszerszą komórkę KAŻDEJ kolumny,
// która jeszcze NIE MA szerokości (`col.width` fałszywe: świeży widok
// domyślny z serwera, albo pierwszy przebieg tej funkcji w tej sesji) i
// wpisujemy wynik w pikselach do `list.value.data.columns[i].width`,
// dokładnie tym samym mechanizmem co ręczne przeciągnięcie
// (onColumnWidthUpdated wyżej) - więc gdy użytkownik cokolwiek przeciągnie
// i to się zapisze, CAŁY zestaw szerokości (auto-dopasowane + przeciągnięta)
// zamraża się w zapisanym widoku (CRM View Settings), każda kolumna ma już
// `.width`, i ta funkcja przestaje je ruszać - dokładnie takie samo
// zachowanie jak reszta tej apki (bez zapisanego widoku = świeże domyślne,
// z zapisanym widokiem = to, co w nim jest), żaden nowy, osobny mechanizm.
//
// Mierzymy po kluczu przez atrybut `data-fit="klucz-kolumny"` na
// elementach treści komórek (patrz szablon wyżej). Nagłówek kolumny NIE
// jest mierzony w DOM (zależałoby to od wewnętrznej struktury frappe-ui's
// ListHeaderItem.vue, której ta lista nie kontroluje) - zamiast tego każda
// kolumna ma bezpieczny, ręcznie dobrany próg minimalny w MIN_SZEROKOSC_PX,
// wystarczający na jej własną etykietę nagłówka (a dla "Etap procesu"
// dodatkowo na pasek segmentów i najdłuższy realny status, "Weryfikacja
// Backoffice" - stały próg, żeby kolumna nie skakała w zależności od tego,
// co akurat jest na stronie).
//
// PUŁAPKA znaleziona w QA tej rundy (2026 09 29): `element.scrollWidth`
// zwraca szerokość WŁASNEGO BOX-u elementu, nie treści, gdy treść jest
// WĘŻSZA niż box - `scrollWidth` "widzi" nadmiar tylko wtedy, gdy treść
// PRZEPEŁNIA box, w przeciwnym razie zwraca po prostu `clientWidth`. Każdy
// znaczony `[data-fit]` element w tym pliku jest w praktyce rozciągnięty:
// świeża kolumna bez `.width` startuje z równym udziałem `1fr` (patrz
// `getGridTemplateColumns` we frappe-ui), więc w momencie pomiaru krótki
// numer telefonu siedzi w komórce już rozciągniętej do tego 1fr-owego
// udziału - `scrollWidth` mierzył więc box, nie tekst, i Telefon/Mail
// wychodziły identyczne (obie kolumny zaczynają z tym samym udziałem).
// Naprawa: mierzyć faktyczny layout TREŚCI przez `Range` zamiast rozmiaru
// elementu - `Range.getBoundingClientRect()` zwraca geometrię
// wyrenderowanego tekstu, niezależną od tego, jak szeroki jest
// zawierający go box.
//
// `document.querySelectorAll` (nie zawężone do korzenia tego komponentu)
// zakłada jedną listę Umowy na raz na stronie - trasa montuje dokładnie
// jeden DealsListView.vue naraz, tak jak dziś.
const MIN_SZEROKOSC_PX = {
  lead_name: 110, // "Klient / szansa"
  custom_rodzaj_umowy: 56, // "Rodzaj" - ma zostać kompaktowa (dawniej sztywne 3.5rem = 56px)
  status: 280, // "Weryfikacja Backoffice" + pełny pasek etapu procesu
  deal_owner: 70, // "Doradca"
  mobile_no: 70, // "Telefon"
  email: 50, // "Mail"
  modified: 70, // "Zmiana"
}
const KOLUMNY_Z_IKONA_PREFIKSU = new Set(['mobile_no']) // ikona telefonu w #prefix (h-4 w-4 + gap-2)
// 12px, nie 24 (QA rundy 5, 2026 09 29): z poprawnym pomiarem tresci (Range,
// nie scrollWidth) siedem kolumn z 24px oddechu kazda sumowalo sie do 1340px
// tresci - wiecej niz miejsce dostepne na 1680px (zmierzone
// scrollWidth>clientWidth na korzeniu ListView.vue, realny poziomy scroll,
// „Zmiana" wypychana poza widok). Zadna z kolumn nie ma wlasnego paddingu
// (ListRowItem to "flex items-center gap-2" bez px, gap dziala tylko MIEDZY
// wieloma dziecmi, a wiekszosc kolumn ma tu tylko jedno) - 24px bylo czystym
// zapasem bez konkretnego uzasadnienia. 12px dalej daje realny oddech
// (zweryfikowane: 0/350 obcietych komorek na 1680 i 1280px) i miesci
// wszystkie siedem kolumn w 1680px bez przewijania w poziomie.
const ODDECH_PX = 12
const IKONA_PREFIKSU_PX = 24 // 16px ikona + 8px gap (rzeczywisty, mierzony rozmiar - nie ruszane)

// Szerokość faktycznie wyrenderowanej treści elementu (tekst i inline
// dzieci), nie szerokość jego (być może rozciągniętego) boxu - patrz
// pułapka opisana wyżej. `Range.selectNodeContents` + `getBoundingClientRect`
// jest odporne na to, czy element jest blokowy/rozciągnięty flexem/gridem:
// mierzy geometrię samej treści, tak jak by ją zaznaczyć myszką.
function szerokoscTresci(el) {
  if (!el || el.offsetParent === null) return 0 // display:none / niewidoczny (szybki filtr)
  const zakres = document.createRange()
  zakres.selectNodeContents(el)
  const prostokat = zakres.getBoundingClientRect()
  zakres.detach?.()
  if (!prostokat || (prostokat.width === 0 && prostokat.height === 0)) return 0
  return prostokat.width
}

function autoDopasujKolumny() {
  const kolumny = list.value?.data?.columns
  if (!kolumny?.length) return
  for (const col of kolumny) {
    if (col.width) continue
    if (col.key === 'status') {
      col.width = `${MIN_SZEROKOSC_PX.status}px`
      continue
    }
    const elementy = document.querySelectorAll(`[data-fit="${col.key}"]`)
    let najszersza = 0
    elementy.forEach((el) => {
      const w = szerokoscTresci(el)
      if (w > najszersza) najszersza = w
    })
    if (najszersza === 0) continue
    let szerokosc = najszersza + ODDECH_PX
    if (KOLUMNY_Z_IKONA_PREFIKSU.has(col.key)) szerokosc += IKONA_PREFIKSU_PX
    const prog = MIN_SZEROKOSC_PX[col.key] || 0
    col.width = `${Math.round(Math.max(szerokosc, prog))}px`
  }
}

onMounted(() => nextTick(autoDopasujKolumny))
watch(
  () => props.rows,
  () => nextTick(autoDopasujKolumny),
  { flush: 'post' },
)

// Destination for the whole row link (ListView options.getRowRoute below).
// The Szczegoly icon column that used to call this through a separate
// goToDeal helper was removed by owner decision (round 3 click test,
// 2026 09 29), so this function is now used only here.
function dealRoute(row) {
  return {
    name: 'Deal',
    params: { dealId: row.name },
    query: { view: route.query.view, viewType: route.params.viewType },
  }
}

// Pasek postępu procesu pod odznaką statusu (kolumna "Etap procesu",
// wariant B, b65) - ten sam zasób co Filter.vue/QuickFilterField.vue
// (cache 'volteo-pipeline-grupy', patrz utils/etapFiltr.js), więc zwykle
// jest już ciepły w cache przy wejściu na listę szans. Liczby segmentów
// liczone są z tych danych (utils/pasekEtapu.js), nigdy hardkodowane.
const grupyStatusow = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_grupy',
  cache: ['volteo-pipeline-grupy'],
  auto: true,
})

function segmentyDlaWiersza(row) {
  return liczbaSegmentow(grupyStatusow.data, row?.custom_rodzaj_umowy?.raw)
}

function wypelnioneDlaWiersza(row) {
  return segmentyWypelnione(
    grupyStatusow.data,
    row?.custom_rodzaj_umowy?.raw,
    row?.status?.label,
    row?.status?.type,
  )
}

// Bulk actions (selection checkboxes + the select banner) are restricted to
// administrative roles: System Manager (via isAdmin) and Volteo Core Admin
// (the Volteo-specific admin role, folded into isVolteoAdmin), plus, since
// ops#183, Volteo Backend, who may only delete (see the ListBulkActions
// options below: hideEdit/hideAssign hide everything else in that menu for
// backoffice, can_delete on the server is the real gate). Volteo D2D Sales
// still deliberately does not get bulk actions: this only hides the UI,
// the underlying bulk-action calls remain subject to normal DocPerm checks.
const { isVolteoAdmin, isBackend } = usersStore()
const canSelectRows = computed(() => isVolteoAdmin() || isBackend())

const isLikeFilterApplied = computed(() => {
  return list.value.params?.filters?._liked_by ? true : false
})

const { user } = sessionStore()

function isLiked(item) {
  if (item) {
    let likedByMe = JSON.parse(item)
    return likedByMe.includes(user)
  }
}

watch(pageLengthCount, (val, old_value) => {
  if (val === old_value) return
  emit('updatePageCount', val)
})

const listBulkActionsRef = ref(null)

defineExpose({
  customListActions: computed(
    () => listBulkActionsRef.value?.customListActions,
  ),
})
</script>
