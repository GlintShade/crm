<!--
  Nagłówek szansy v2 (desktop): trzy wiersze nad paskiem zakładek.
  Wiersz 1: okruszki + kopiowanie numeru, po prawej akcje i Doradca.
  Wiersz 2: klient jako tytuł-link oraz linia meta (produkt, moc, magazyn, miejscowość).
  Wiersz 3: proces w jednej linii (albo forma zwarta, gdy się nie mieści) oraz
  JEDYNY przycisk główny strony: następny krok, który przełącza na zakładkę,
  na której ten krok się dzieje (etykieta i zakładka z jednego wpisu
  `nastepnyKrok` w utils/dealPipeline.js).

  Zmiana etapu idzie WYŁĄCZNIE starą ścieżką: opcje `opcjeStatusow` to dokładnie
  te z `statusOptions()` (Deal.vue), a ich `onClick` woła `triggerStatusChange`
  (formularz, okno przyczyny przegranej, automatyzacje, ślad w Aktywności).
-->
<template>
  <div class="w-full border-b bg-surface-base px-5 pb-3 pt-2.5" data-testid="deal-naglowek">
    <!-- Wiersz 1 -->
    <div class="flex items-center justify-between gap-3 text-xs text-ink-gray-5">
      <nav class="flex min-w-0 items-center gap-1" aria-label="breadcrumb">
        <template v-for="(item, i) in okruszki" :key="i">
          <span v-if="i > 0" class="lucide-chevron-right size-3 shrink-0" aria-hidden="true" />
          <RouterLink
            v-if="i < okruszki.length - 1"
            :to="item.route"
            class="truncate hover:text-ink-gray-8"
          >
            {{ item.label }}
          </RouterLink>
          <span v-else class="truncate text-ink-gray-7">{{ item.label }}</span>
        </template>
        <button
          type="button"
          class="ml-0.5 flex size-5 shrink-0 items-center justify-center rounded text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-8"
          :title="__('Kopiuj numer szansy')"
          data-testid="naglowek-kopiuj"
          @click="copyToClipboard(dealId)"
        >
          <span class="lucide-copy size-3" aria-hidden="true" />
        </button>
      </nav>
      <div class="flex shrink-0 items-center gap-2">
        <slot name="akcje" />
        <AssignTo
          :model-value="assignees"
          doctype="CRM Deal"
          :docname="dealId"
          @update:model-value="(v) => emit('update:assignees', v)"
        >
          <template #target="{ togglePopover }">
            <button
              type="button"
              class="flex items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-surface-gray-2"
              data-testid="naglowek-doradca"
              @click="togglePopover"
            >
              <span
                class="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-gray-3 text-[11px] font-medium uppercase text-ink-gray-8"
              >
                {{ inicjaly }}
              </span>
              <span class="text-xs text-ink-gray-5">{{ __('Doradca') }}</span>
              <span class="text-ink-gray-9">{{ doradca || __('Przypisz') }}</span>
              <span class="lucide-chevron-down size-3.5 text-ink-gray-5" aria-hidden="true" />
            </button>
          </template>
        </AssignTo>
      </div>
    </div>

    <!-- Wiersz 2 -->
    <div class="mt-1.5 flex min-w-0 items-baseline gap-3">
      <button
        v-if="maKlienta"
        type="button"
        class="group flex min-w-0 items-center gap-1.5 text-left"
        data-testid="naglowek-tytul"
        :title="__('Przejdź do klienta')"
        @click="emit('klient')"
      >
        <span class="truncate text-xl font-semibold text-ink-gray-9 group-hover:underline">
          {{ tytul }}
        </span>
        <span class="lucide-arrow-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
      </button>
      <h1 v-else class="truncate text-xl font-semibold text-ink-gray-9" data-testid="naglowek-tytul">
        {{ tytul }}
      </h1>
      <span v-if="meta" class="truncate text-sm text-ink-gray-5" data-testid="naglowek-meta">
        {{ meta }}
      </span>
    </div>

    <!-- Wiersz 3 -->
    <div v-if="payload && tryb !== 'hidden'" class="mt-2.5 flex items-center gap-4">
      <div ref="kontenerRef" class="relative min-w-0 flex-1 [overflow-x:clip]" data-testid="naglowek-proces">
        <!-- Pełna linia: zawsze w DOM (służy też do pomiaru szerokości). W formie
             zwartej jest niewidoczna i nieaktywna (inert). -->
        <div
          ref="liniaPelnaRef"
          class="flex w-max items-center gap-1.5 whitespace-nowrap text-sm"
          :class="zwarty ? 'invisible absolute left-0 top-0 h-0 overflow-hidden' : ''"
          :inert="zwarty ? '' : undefined"
          :aria-hidden="zwarty"
        >
          <template v-for="(el, i) in elementyPelne" :key="el.status">
            <span v-if="i > 0" class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
            <EtapElement :el="el" :czas="czas" :ma-podzadania="maPodzadania(el.status)" :panel-otwarty="panelOtwarty">
              <template #pigula="{ klasy }">
                <MenuEtapu :klasy="klasy" :el="el" :czas="czas" :menu="menu" @wybierz="wybierz" />
              </template>
              <template #panel>
                <button
                  v-if="maPodzadania(el.status)"
                  type="button"
                  class="flex size-6 items-center justify-center rounded-full text-ink-gray-5 hover:bg-surface-gray-2"
                  :title="__('Pokaż zadania etapu')"
                  :aria-expanded="panelOtwarty"
                  @click="panelOtwarty = !panelOtwarty"
                >
                  <span
                    class="lucide-chevron-down size-3.5 transition-transform"
                    :class="{ 'rotate-180': panelOtwarty }"
                    aria-hidden="true"
                  />
                </button>
              </template>
            </EtapElement>
          </template>
          <template v-if="odznaka">
            <span class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
            <MenuEtapu
              :klasy="odznakaKlasy"
              :el="{ stan: 'odznaka', nazwa: odznaka }"
              :czas="null"
              :menu="menu"
              @wybierz="wybierz"
            />
          </template>
        </div>

        <!-- Forma zwarta -->
        <div v-if="zwarty" class="flex items-center gap-1.5 whitespace-nowrap text-sm" data-testid="naglowek-zwarty">
          <template v-if="zwartyElementy.zrobione > 0">
            <span class="flex items-center gap-1 text-ink-gray-8">
              <span class="lucide-check size-4 text-ink-green-3" aria-hidden="true" />
              {{ etapyLiczba(zwartyElementy.zrobione) }}
            </span>
            <span class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
          </template>
          <template v-if="zwartyElementy.biezacy">
            <EtapElement
              :el="zwartyElementy.biezacy"
              :czas="czas"
              :ma-podzadania="maPodzadania(zwartyElementy.biezacy.status)"
              :panel-otwarty="panelOtwarty"
            >
              <template #pigula="{ klasy }">
                <MenuEtapu :klasy="klasy" :el="zwartyElementy.biezacy" :czas="czas" :menu="menu" @wybierz="wybierz" />
              </template>
              <template #panel>
                <button
                  v-if="maPodzadania(zwartyElementy.biezacy.status)"
                  type="button"
                  class="flex size-6 items-center justify-center rounded-full text-ink-gray-5 hover:bg-surface-gray-2"
                  :title="__('Pokaż zadania etapu')"
                  @click="panelOtwarty = !panelOtwarty"
                >
                  <span class="lucide-chevron-down size-3.5" aria-hidden="true" />
                </button>
              </template>
            </EtapElement>
          </template>
          <MenuEtapu
            v-else-if="odznaka"
            :klasy="odznakaKlasy"
            :el="{ stan: 'odznaka', nazwa: odznaka }"
            :czas="null"
            :menu="menu"
            @wybierz="wybierz"
          />
          <template v-if="zwartyElementy.nastepny">
            <span class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
            <EtapElement :el="zwartyElementy.nastepny" :czas="null" />
          </template>
          <Tooltip v-if="zwartyElementy.reszta.length" :text="zwartyElementy.reszta.join(', ')">
            <span
              class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6"
              data-testid="naglowek-reszta"
            >
              +{{ zwartyElementy.reszta.length }}
            </span>
          </Tooltip>
        </div>
      </div>

      <!-- Następny krok: JEDYNY przycisk główny -->
      <div class="shrink-0">
        <Button
          v-if="przyciskNastepnego"
          variant="solid"
          :label="przyciskNastepnego.etykieta"
          data-testid="naglowek-nastepny"
          @click="przejdzDoZakladki(przyciskNastepnego.indeks)"
        />
        <span
          v-else-if="nastepny?.tekst"
          class="flex items-center gap-1.5 text-sm text-ink-gray-5"
          data-testid="naglowek-nastepny-tekst"
        >
          <span v-if="nastepny.ikona" :class="'lucide-' + nastepny.ikona" class="size-4" aria-hidden="true" />
          {{ nastepny.tekst }}
        </span>
      </div>
    </div>

    <DealPipelineBar
      tylko-panel
      :deal-id="dealId"
      :status="doc.status"
      :rodzaj="doc.custom_rodzaj_umowy"
      :etap="panelOtwarty ? doc.status : ''"
    />

    <Dialog v-model:open="potwierdzenie.otwarte" :title="potwierdzenie.tytul">
      <template #default>
        <div class="text-sm text-ink-gray-7" data-testid="naglowek-potwierdzenie">
          <p v-if="potwierdzenie.pominiete.length" class="rounded-md bg-surface-amber-2 p-2 text-ink-amber-8">
            {{ __('Pominięte etapy') }}: {{ potwierdzenie.pominiete.join(', ') }}
          </p>
          <p v-else>{{ potwierdzenie.opis }}</p>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" @click="potwierdzenie.otwarte = false" />
          <Button variant="solid" :label="potwierdzenie.przycisk" @click="potwierdzUzgodnienie" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, Tooltip, createResource, toast } from 'frappe-ui'
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import AssignTo from '@/components/AssignTo.vue'
import DealPipelineBar from '@/components/deal/DealPipelineBar.vue'
import { statusesStore } from '@/stores/statuses'
import { usersStore } from '@/stores/users'
import { copyToClipboard } from '@/utils'
import {
  bandMode,
  currentIndexFor,
  nastepnyKrok,
  nodeStateForMode,
  offPipelineBadge,
  pominieteEtapy,
  podpowiedzEtapu,
  procesDlaRodzaju,
  rodzajZmianyEtapu,
  terminalneStatusy,
} from '@/utils/dealPipeline'
import { czasWEtapie, etapyLiczba, etykietaStatusu, metaSzansy } from '@/utils/dealNaglowek'

const props = defineProps({
  dealId: { type: String, required: true },
  doc: { type: Object, required: true },
  okruszki: { type: Array, default: () => [] },
  tytul: { type: String, default: '' },
  maKlienta: { type: Boolean, default: false },
  tabs: { type: Array, default: () => [] },
  opcjeStatusow: { type: Array, default: () => [] },
  assignees: { type: Array, default: () => [] },
})
const emit = defineEmits(['klient', 'update:assignees'])
const tabIndex = defineModel('tabIndex', { type: Number, default: 0 })

const { getDealStatus } = statusesStore()
const { getUser } = usersStore()

// Ten sam zasób (URL, parametry, klucz cache) co w DealPipelineBar.vue, więc
// współdzielony; odświeżany tylko przy zmianie rodzaju (patrz tamten komentarz).
const resource = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_get',
  params: { deal: props.dealId },
  auto: true,
  cache: ['volteo-pipeline', props.dealId],
})
watch(() => props.doc.custom_rodzaj_umowy, () => resource.reload())
const payload = computed(() => resource.data || null)

const status = computed(() => props.doc.status)
const statusType = computed(() => getDealStatus?.(status.value)?.type)
const tryb = computed(() => bandMode(payload.value, status.value, statusType.value))
const biezacy = computed(() => currentIndexFor(payload.value?.steps, status.value))
const proces = computed(() => procesDlaRodzaju(props.doc.custom_rodzaj_umowy))
const odznaka = computed(() => offPipelineBadge(payload.value, status.value, statusType.value))

const meta = computed(() => metaSzansy(props.doc))
const czas = computed(() => czasWEtapie(props.doc.status_change_log, status.value))

const doradca = computed(() => {
  const owner = props.doc.deal_owner
  if (!owner) return ''
  const u = getUser(owner)
  const nazwa = u?.full_name || owner
  const wiecej = Math.max(0, (props.assignees?.length || 0) - 1)
  return wiecej ? `${nazwa} +${wiecej}` : nazwa
})
const inicjaly = computed(() => {
  const owner = props.doc.deal_owner
  if (!owner) return '?'
  const nazwa = getUser(owner)?.full_name || owner
  return nazwa
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((c) => c[0])
    .join('')
})

// --- Elementy linii ---------------------------------------------------------
const elementyPelne = computed(() =>
  (payload.value?.steps || []).map((s) => {
    const stan = nodeStateForMode(tryb.value, s.index, biezacy.value)
    return {
      status: s.status,
      nazwa: __(s.status),
      numer: s.index + 1,
      stan,
      // pigułka bieżącego etapu: tylko gdy status jest w procesie
      pigula: s.index === biezacy.value,
      wygrana: s.index === biezacy.value && tryb.value === 'won',
    }
  }),
)

const odznakaKlasy = computed(() =>
  tryb.value === 'lost'
    ? 'border-outline-red-3 bg-surface-red-2 text-ink-red-8'
    : tryb.value === 'won'
      ? 'border-outline-green-3 bg-surface-green-2 text-ink-green-8'
      : 'border-outline-gray-2 bg-surface-gray-2 text-ink-gray-6',
)

const zwartyElementy = computed(() => {
  const els = elementyPelne.value
  const i = biezacy.value
  if (i < 0) {
    return { zrobione: tryb.value === 'won' ? els.length : 0, biezacy: null, nastepny: null, reszta: [] }
  }
  const nast = els[i + 1] || null
  return {
    zrobione: els.slice(0, i).length,
    biezacy: els[i],
    nastepny: nast ? { ...nast, stan: 'future' } : null,
    reszta: els.slice(i + 2).map((e) => e.nazwa),
  }
})

// --- Pomiar: forma zwarta, gdy pełna linia się nie mieści --------------------
const kontenerRef = ref(null)
const liniaPelnaRef = ref(null)
const zwarty = ref(false)
let obserwator = null

function zmierz() {
  const kontener = kontenerRef.value
  const linia = liniaPelnaRef.value
  if (!kontener || !linia) return
  zwarty.value = linia.scrollWidth > kontener.clientWidth + 1
}

onMounted(() => {
  obserwator = new ResizeObserver(zmierz)
  watch(
    [kontenerRef, liniaPelnaRef],
    ([k, l]) => {
      obserwator.disconnect()
      if (k) obserwator.observe(k)
      if (l) obserwator.observe(l)
      nextTick(zmierz)
    },
    { immediate: true },
  )
})
onBeforeUnmount(() => obserwator?.disconnect())
// treść linii zmienia się (status, czas, payload): zmierz po aktualizacji DOM
watch([elementyPelne, czas, odznaka], () => nextTick(zmierz))

// --- Podzadania (CP) ---------------------------------------------------------
const panelOtwarty = ref(false)
watch(status, () => (panelOtwarty.value = false))
function maPodzadania(nazwa) {
  return nazwa === status.value && Boolean(payload.value?.subtasks?.[nazwa]?.length)
}

// --- Następny krok -----------------------------------------------------------
const nastepny = computed(() => {
  if (tryb.value !== 'progress') return null
  return nastepnyKrok(proces.value, status.value, payload.value?.notes)
})

// Nazwa logiczna zakładki -> realna zakładka tej szansy (Umowa/UmowaCP itd.).
function indeksZakladki(logiczna) {
  let i = props.tabs.findIndex((t) => t.name === logiczna)
  if (i < 0) i = props.tabs.findIndex((t) => t.name === logiczna + 'CP')
  return i
}
const przyciskNastepnego = computed(() => {
  const n = nastepny.value
  if (!n?.zakladka) return null
  const indeks = indeksZakladki(n.zakladka)
  return indeks >= 0 ? { etykieta: n.etykieta, indeks } : null
})
function przejdzDoZakladki(indeks) {
  tabIndex.value = indeks
}

// --- Menu etapu --------------------------------------------------------------
const terminalne = computed(() =>
  terminalneStatusy(payload.value).map((nazwa) => ({
    nazwa,
    etykieta: etykietaStatusu(nazwa),
    typ: getDealStatus?.(nazwa)?.type,
  })),
)

const menu = computed(() => ({
  etapy: elementyPelne.value.map((e) => ({
    ...e,
    podpowiedz: podpowiedzEtapu(proces.value, e.status),
    biezacy: e.status === status.value,
  })),
  terminalne: terminalne.value,
}))

function zmienStatus(nazwa) {
  const opcja = props.opcjeStatusow.find((o) => o.value === nazwa)
  if (!opcja) {
    toast.error(__('Ten etap nie jest dostępny dla tej szansy'))
    return false
  }
  opcja.onClick?.()
  return true
}

const potwierdzenie = reactive({
  otwarte: false,
  tytul: '',
  opis: '',
  przycisk: '',
  pominiete: [],
  cel: '',
})
function potwierdzUzgodnienie() {
  const cel = potwierdzenie.cel
  potwierdzenie.otwarte = false
  zmienStatus(cel)
}

function wybierz(wybor) {
  // wybor: { nazwa, indeks|null }
  const rodzaj = rodzajZmianyEtapu(biezacy.value, wybor.indeks)
  const etykieta = etykietaStatusu(wybor.nazwa)
  if (rodzaj === 'ten-sam') return
  if (rodzaj === 'dalej') {
    const poprzedni = status.value
    if (!zmienStatus(wybor.nazwa)) return
    toast(__('Etap zmieniony na {0}', [etykieta]), {
      duration: 8000,
      action: { label: __('Cofnij'), onClick: () => zmienStatus(poprzedni) },
    })
    return
  }
  Object.assign(potwierdzenie, {
    cel: wybor.nazwa,
    pominiete: [],
    opis: '',
  })
  if (rodzaj === 'przeskok') {
    Object.assign(potwierdzenie, {
      tytul: __('Przeskoczyć do etapu {0}?', [etykieta]),
      przycisk: __('Przeskocz etap'),
      pominiete: pominieteEtapy(payload.value.steps, biezacy.value, wybor.indeks).map((s) => __(s)),
      opis: __('Etap zostanie zmieniony.'),
    })
  } else if (rodzaj === 'wstecz') {
    Object.assign(potwierdzenie, {
      tytul: __('Cofnąć do etapu {0}?', [etykieta]),
      przycisk: __('Cofnij etap'),
      opis: __('Szansa wróci do wcześniejszego etapu.'),
    })
  } else {
    Object.assign(potwierdzenie, {
      tytul: __('Oznaczyć jako {0}?', [etykieta]),
      przycisk: __('Oznacz'),
      opis: __('Szansa przejdzie do statusu {0}.', [etykieta]),
    })
  }
  potwierdzenie.otwarte = true
}

// --- Małe komponenty renderujące ---------------------------------------------
// Element linii: ukończony (ptaszek + nazwa), bieżący (pigułka z menu) albo
// przyszły (kółko z numerem + nazwa).
const EtapElement = defineComponent({
  props: {
    el: { type: Object, required: true },
    czas: { type: String, default: null },
    maPodzadania: { type: Boolean, default: false },
    panelOtwarty: { type: Boolean, default: false },
  },
  setup(p, { slots }) {
    return () => {
      const el = p.el
      if (el.pigula && slots.pigula) {
        const klasy = el.wygrana
          ? 'border-outline-green-3 bg-surface-green-2 text-ink-green-8'
          : 'border-outline-blue-3 bg-surface-blue-2 text-ink-blue-8'
        return h('span', { class: 'flex items-center gap-1' }, [
          slots.pigula({ klasy }),
          slots.panel?.(),
        ])
      }
      if (el.stan === 'done') {
        return h('span', { class: 'flex items-center gap-1 text-ink-gray-8' }, [
          h('span', { class: 'lucide-check size-4 text-ink-green-3', 'aria-hidden': 'true' }),
          el.nazwa,
        ])
      }
      return h('span', { class: 'flex items-center gap-1.5 text-ink-gray-5' }, [
        h(
          'span',
          {
            class:
              'flex size-5 shrink-0 items-center justify-center rounded-full border border-outline-gray-3 text-[11px]',
          },
          String(el.numer),
        ),
        el.nazwa,
      ])
    }
  },
})

// Pigułka bieżącego etapu z menu (Popover frappe-ui nie jest potrzebny: menu to
// zwykły panel pod przyciskiem, zamykany klikiem poza nim).
const MenuEtapu = defineComponent({
  props: {
    klasy: { type: String, default: '' },
    el: { type: Object, required: true },
    czas: { type: String, default: null },
    menu: { type: Object, required: true },
  },
  emits: ['wybierz'],
  setup(p, { emit: emitMenu }) {
    const otwarte = ref(false)
    const korzen = ref(null)
    function poza(e) {
      if (korzen.value && !korzen.value.contains(e.target)) otwarte.value = false
    }
    onMounted(() => document.addEventListener('mousedown', poza))
    onBeforeUnmount(() => document.removeEventListener('mousedown', poza))

    const wybierzEtap = (e) => {
      otwarte.value = false
      emitMenu('wybierz', e)
    }

    function wiersz(e) {
      const stan = e.biezacy ? 'biezacy' : e.stan
      return h(
        'button',
        {
          type: 'button',
          'data-testid': 'menu-etap',
          class:
            'flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-gray-2 ' +
            (e.biezacy ? 'bg-surface-blue-2 text-ink-blue-8 font-medium' : 'text-ink-gray-8'),
          onClick: () => wybierzEtap({ nazwa: e.status, indeks: e.numer - 1 }),
        },
        [
          stan === 'done'
            ? h('span', { class: 'lucide-check mt-0.5 size-4 shrink-0 text-ink-green-3' })
            : h(
                'span',
                {
                  class:
                    'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border border-outline-gray-3 text-[10px]',
                },
                String(e.numer),
              ),
          h('span', { class: 'flex flex-col' }, [
            h('span', null, [e.nazwa, e.biezacy && p.czas ? ` · ${p.czas}` : '']),
            e.podpowiedz ? h('span', { class: 'text-xs font-normal text-ink-gray-5' }, e.podpowiedz) : null,
          ]),
        ],
      )
    }

    return () => {
      const el = p.el
      const etykieta = el.stan === 'odznaka' ? etykietaStatusu(el.nazwa) : el.nazwa
      const tekst = el.stan === 'odznaka' || !p.czas ? etykieta : `${etykieta} · ${p.czas}`
      return h('span', { class: 'relative inline-flex', ref: korzen }, [
        h(
          'button',
          {
            type: 'button',
            'data-testid': 'naglowek-pigula',
            class: `flex items-center gap-1 rounded-full border px-3 py-1 text-sm font-semibold ${p.klasy}`,
            'aria-haspopup': 'menu',
            'aria-expanded': otwarte.value,
            onClick: () => (otwarte.value = !otwarte.value),
          },
          [tekst, h('span', { class: 'lucide-chevron-down size-3.5', 'aria-hidden': 'true' })],
        ),
        otwarte.value
          ? h(
              'div',
              {
                role: 'menu',
                'data-testid': 'menu-etapu',
                class:
                  'absolute left-0 top-full z-50 mt-1.5 w-72 rounded-lg bg-surface-elevation-2 p-1.5 shadow-2xl ring-1 ring-black ring-opacity-5',
              },
              [
                h('div', { class: 'px-2 pb-1 pt-1 text-xs font-medium text-ink-gray-5' }, __('Etap szansy')),
                ...p.menu.etapy.map(wiersz),
                p.menu.terminalne.length ? h('div', { class: 'my-1 h-px bg-outline-gray-2' }) : null,
                ...p.menu.terminalne.map((t) =>
                  h(
                    'button',
                    {
                      type: 'button',
                      'data-testid': 'menu-terminal',
                      class:
                        'flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-gray-2 ' +
                        (t.typ === 'Won' ? 'text-ink-green-8' : t.typ === 'Lost' ? 'text-ink-red-8' : 'text-ink-gray-8'),
                      onClick: () => wybierzEtap({ nazwa: t.nazwa, indeks: null }),
                    },
                    __('Oznacz jako {0}', [t.etykieta]),
                  ),
                ),
              ],
            )
          : null,
      ])
    }
  },
})
</script>
