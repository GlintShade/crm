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
              <span class="text-xs text-ink-gray-5">{{ __('Doradca') }}</span>
              <span class="text-ink-gray-9">{{ doradca || __('Przypisz') }}</span>
              <span class="lucide-chevron-down size-3.5 text-ink-gray-5" aria-hidden="true" />
            </button>
          </template>
        </AssignTo>
      </div>
    </div>

    <!-- Pasek etapów + następny krok -->
    <div v-if="payload && tryb !== 'hidden'" class="mt-3 flex items-start gap-4">
      <div class="min-w-0 flex-1">
        <template v-if="wariant === 'kroki'">
        <ol ref="kontenerRef" class="flex w-full items-start" data-testid="naglowek-proces">
          <li
            v-for="(el, i) in elementy"
            :key="el.status"
            class="relative flex min-w-0 flex-1 flex-col items-center"
            :title="!el.etykieta ? el.nazwa : undefined"
            :data-stan="el.stan"
          >
            <span
              v-if="i > 0"
              class="absolute left-0 top-[14.5px] h-[3px] w-[calc(50%-20px)] rounded-full"
              :class="liniaKlasa(i - 1)"
              aria-hidden="true"
            />
            <span
              v-if="i < elementy.length - 1"
              class="absolute left-[calc(50%+20px)] right-0 top-[14.5px] h-[3px] rounded-full"
              :class="liniaKlasa(i)"
              aria-hidden="true"
            />

            <!-- Bieżący etap: kółko + etykieta to jedyna klikalna kontrolka (menu etapu) -->
            <MenuEtapu v-if="el.stan === 'current'" :menu="menu" :wariant="wariant" :wyrownanie="wyrownanie" @wybierz="wybierz" @przelacz="ustawWariant">
              <template #trigger="{ toggle, otwarte }">
                <button
                  type="button"
                  class="relative flex max-w-full cursor-pointer flex-col items-center gap-1.5 rounded-md px-1 outline-none"
                  :class="zwarty && el.etykieta ? 'mb-9' : ''"
                  data-testid="naglowek-pigula"
                  aria-haspopup="menu"
                  :aria-expanded="otwarte"
                  @click="toggle"
                >
                  <span :class="[kolkoBaza, kolkoKlasa(el.stan)]">{{ el.numer }}</span>
                  <!-- W formie zwartej etykieta jest poza przepływem (nie rozpycha
                       wąskiej kolumny), wyśrodkowana pod kółkiem i dociśnięta do
                       krawędzi paska przy pierwszym i ostatnim etapie. -->
                  <span
                    v-if="el.etykieta"
                    class="flex items-center gap-0.5 text-center text-[13px] font-semibold leading-tight text-ink-blue-8"
                    :class="
                      zwarty
                        ? [
                            'absolute top-[calc(100%+6px)] w-max max-w-[9rem]',
                            i === 0
                              ? 'left-0'
                              : i === elementy.length - 1
                                ? 'right-0'
                                : 'left-1/2 -translate-x-1/2',
                          ]
                        : ''
                    "
                  >
                    <span class="line-clamp-2">{{ el.nazwa }}</span>
                    <span class="lucide-chevron-down size-3.5 shrink-0" aria-hidden="true" />
                  </span>
                  <span v-if="!zwarty" class="text-xs text-ink-blue-8" data-testid="naglowek-teraz">
                    {{ czas ? `Teraz \u00b7 ${czas}` : 'Teraz' }}
                  </span>
                </button>
              </template>
            </MenuEtapu>

            <div v-else class="flex max-w-full flex-col items-center gap-1.5 px-1">
              <span :class="[kolkoBaza, kolkoKlasa(el.stan)]">
                <span v-if="el.stan === 'done'" class="lucide-check size-4.5" aria-hidden="true" />
                <template v-else>{{ el.numer }}</template>
              </span>
              <span
                v-if="el.etykieta"
                class="line-clamp-2 text-center text-[13px] leading-tight"
                :class="etykietaKlasa(el.stan)"
              >
                {{ el.nazwa }}
              </span>
            </div>

            <button
              v-if="!zwarty && el.stan === 'current' && maPodzadania(el.status)"
              type="button"
              class="mt-1 flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-ink-gray-6 hover:bg-surface-gray-2"
              :aria-expanded="panelOtwarty"
              @click="panelOtwarty = !panelOtwarty"
            >
              {{ __('Zadania etapu') }}
              <span class="lucide-chevron-down size-3.5 transition-transform" :class="{ 'rotate-180': panelOtwarty }" aria-hidden="true" />
            </button>
          </li>
        </ol>

        <!-- Forma zwarta: pełny tekst stanu pod paskiem -->
        <div
          v-if="zwarty && biezacy >= 0"
          class="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
          data-testid="naglowek-etap-tekst"
        >
          <span class="font-medium text-ink-gray-9">{{ tekstStanu }}</span>
          <span v-if="tekstNastepnego" class="text-ink-gray-5">{{ tekstNastepnego }}</span>
          <button
            v-if="maPodzadania(status)"
            type="button"
            class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-ink-gray-6 hover:bg-surface-gray-2"
            :aria-expanded="panelOtwarty"
            :title="__('Pokaż zadania etapu')"
            @click="panelOtwarty = !panelOtwarty"
          >
            {{ __('Zadania etapu') }}
            <span class="lucide-chevron-down size-3.5 transition-transform" :class="{ 'rotate-180': panelOtwarty }" aria-hidden="true" />
          </button>
        </div>
        </template>

        <!-- Wariant "pasek": blok z numerem i nazwą etapu + segmenty -->
        <div v-else class="flex items-start gap-6" data-testid="naglowek-pasek">
          <div class="w-52 shrink-0 xl:w-64">
            <div class="text-[13px] text-ink-gray-5">
              {{ biezacy >= 0 ? tekstNumeruEtapu(biezacy, liczbaEtapow) : __('Status') }}
            </div>
            <MenuEtapu
              v-if="tryb === 'progress'"
              :menu="menu"
              :wariant="wariant"
              :wyrownanie="'lewo'"
              @wybierz="wybierz"
              @przelacz="ustawWariant"
            >
              <template #trigger="{ toggle, otwarte }">
                <button
                  type="button"
                  class="flex max-w-full cursor-pointer items-center gap-1 rounded-md text-left outline-none"
                  data-testid="naglowek-pigula"
                  aria-haspopup="menu"
                  :aria-expanded="otwarte"
                  @click="toggle"
                >
                  <span class="truncate text-[22px] font-semibold leading-tight text-ink-blue-8">
                    {{ __(status) }}
                  </span>
                  <span class="lucide-chevron-down size-4 shrink-0 text-ink-blue-8" aria-hidden="true" />
                </button>
              </template>
            </MenuEtapu>
            <div
              v-else
              class="truncate text-[22px] font-semibold leading-tight"
              :class="tryb === 'won' ? 'text-ink-green-8' : tryb === 'lost' ? 'text-ink-red-8' : 'text-ink-gray-7'"
            >
              {{ etykietaStatusu(__(status)) }}
            </div>
            <div class="mt-0.5 min-h-[18px] text-[13px] text-ink-gray-7">
              {{ tryb === 'progress' && czas ? czasOd(czas) : '' }}
            </div>
          </div>
          <div
            ref="segmentyRef"
            class="flex min-w-0 flex-1"
            :class="zwarty ? 'mt-[28px]' : 'self-center'"
            data-testid="naglowek-segmenty"
          >
           <div
            class="flex min-w-0 flex-col"
            :class="zwarty ? 'w-full gap-2.5' : 'w-full gap-1.5'"
            data-testid="pasek-grupa"
           >
            <!-- Każda etykieta stoi bezpośrednio pod własnym paskiem (ta sama
                 szerokość, wyrównana do lewej). W formie zwartej (12 etapów) jeden
                 rząd, a gdy nieaktywny pasek miałby poniżej ok. 80 px, dwa rzędy
                 po 6 pasków; aktywny pasek jest 1,5 raza szerszy w swoim rzędzie. -->
            <div
              v-for="(rzad, r) in rzedyPaska"
              :key="r"
              class="flex min-w-0 items-start"
              :class="'gap-1.5'"
              data-testid="pasek-rzad"
            >
              <div
                v-for="el in rzad"
                :key="el.status"
                class="flex min-w-0 flex-col gap-1.5"
                :class="zwarty && el.stan === 'current' ? 'flex-[1.5]' : 'flex-1'"
                :title="el.nazwa"
                :data-stan="el.stan"
                data-testid="pasek-segment"
              >
                <span class="h-2 w-full rounded-full" :class="segmentKlasa(el.stan)" />
                <span
                  data-testid="pasek-etykieta"
                  class="break-words text-left leading-tight"
                  :class="[
                    el.stan === 'current'
                      ? 'font-semibold text-ink-gray-9'
                      : el.stan === 'done'
                        ? 'text-ink-gray-6'
                        : 'text-ink-gray-4',
                    zwarty
                      ? [el.stan === 'current' ? 'text-xs' : 'text-[11px]', 'line-clamp-3']
                      : 'line-clamp-2 text-[12px]',
                  ]"
                >
                  {{ el.nazwa }}
                </span>
              </div>
            </div>
           </div>
          </div>
        </div>
        <div
          v-if="wariant === 'pasek' && biezacy >= 0 && (liczbaEtapow > 6 || maPodzadania(status))"
          class="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
          data-testid="naglowek-etap-tekst"
        >
          <span v-if="nastepny?.tekst && zwarty" class="text-ink-gray-5" data-testid="naglowek-nastepny-tekst-dol">
            {{ nastepny.tekst }}
          </span>
          <span v-if="tekstNastepnego" class="text-ink-gray-5">{{ tekstNastepnego }}</span>
          <button
            v-if="maPodzadania(status)"
            type="button"
            class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-ink-gray-6 hover:bg-surface-gray-2"
            :aria-expanded="panelOtwarty"
            :title="__('Pokaż zadania etapu')"
            @click="panelOtwarty = !panelOtwarty"
          >
            {{ __('Zadania etapu') }}
            <span class="lucide-chevron-down size-3.5 transition-transform" :class="{ 'rotate-180': panelOtwarty }" aria-hidden="true" />
          </button>
        </div>
      </div>

      <!-- Następny krok albo wynik terminalny: JEDYNY przycisk główny -->
      <div class="shrink-0" :class="wariant === 'pasek' ? 'pt-[18px]' : 'pt-0.5'">
        <MenuEtapu v-if="odznaka" :menu="menu" :wariant="wariant" wyrownanie="prawo" @wybierz="wybierz" @przelacz="ustawWariant">
          <template #trigger="{ toggle, otwarte }">
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-sm font-semibold"
              :class="odznakaKlasy"
              data-testid="naglowek-odznaka"
              aria-haspopup="menu"
              :aria-expanded="otwarte"
              @click="toggle"
            >
              {{ etykietaStatusu(odznaka) }}
              <span class="lucide-chevron-down size-3.5" aria-hidden="true" />
            </button>
          </template>
        </MenuEtapu>
        <Button
          v-else-if="przyciskNastepnego"
          variant="solid"
          theme="blue"
          class="!text-white hover:!bg-blue-600 active:!bg-blue-700"
          :label="przyciskNastepnego.etykieta"
          data-testid="naglowek-nastepny"
          @click="przejdzDoZakladki(przyciskNastepnego.indeks)"
        />
        <span
          v-else-if="nastepny?.tekst && !(wariant === 'pasek' && zwarty)"
          class="flex max-w-xs items-center gap-1.5 text-sm text-ink-gray-5"
          data-testid="naglowek-nastepny-tekst"
        >
          <span v-if="nastepny.ikona" :class="'lucide-' + nastepny.ikona" class="size-4 shrink-0" aria-hidden="true" />
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
import {
  czasOd,
  czasWEtapie,
  czyZwarty,
  liczbaRzedowPaska,
  normalizujWariant,
  podzielNaRzedy,
  segmentKlasa,
  tekstNumeruEtapu,
  etykietaStatusu,
  etykietaWidoczna,
  tekstDalej,
  tekstEtapu,
} from '@/utils/dealNaglowek'

const props = defineProps({
  dealId: { type: String, required: true },
  doc: { type: Object, required: true },
  okruszki: { type: Array, default: () => [] },
  tabs: { type: Array, default: () => [] },
  opcjeStatusow: { type: Array, default: () => [] },
  assignees: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:assignees'])
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
// Odznaka wyniku: status poza procesem albo ukończony proces (CP "Projekt rozliczony").
const odznaka = computed(
  () =>
    offPipelineBadge(payload.value, status.value, statusType.value) ||
    (tryb.value === 'won' ? status.value : null),
)

const czas = computed(() => czasWEtapie(props.doc.status_change_log, status.value))

const doradca = computed(() => {
  const owner = props.doc.deal_owner
  if (!owner) return ''
  const u = getUser(owner)
  const nazwa = u?.full_name || owner
  const wiecej = Math.max(0, (props.assignees?.length || 0) - 1)
  return wiecej ? `${nazwa} +${wiecej}` : nazwa
})
// --- Wariant widoku etapów (Kroki / Pasek), pamiętany w localStorage ---------------
const KLUCZ_WARIANTU = 'volteo.naglowek.wariant'
function odczytajWariant() {
  try {
    return normalizujWariant(window.localStorage.getItem(KLUCZ_WARIANTU))
  } catch (e) {
    return normalizujWariant(null)
  }
}
const wariant = ref(odczytajWariant())
function ustawWariant(w) {
  wariant.value = normalizujWariant(w)
  try {
    window.localStorage.setItem(KLUCZ_WARIANTU, wariant.value)
  } catch (e) {
    /* localStorage niedostępny: wariant zostaje tylko na tę sesję */
  }
}

// --- Elementy paska ------------------------------------------------------------
const kontenerRef = ref(null)
const segmentyRef = ref(null)
const szerokosc = ref(0)
let obserwator = null
onMounted(() => {
  obserwator = new ResizeObserver(([wpis]) => {
    szerokosc.value = wpis?.contentRect?.width ?? 0
  })
  watch(
    [kontenerRef, segmentyRef],
    ([kroki, pasek]) => {
      obserwator.disconnect()
      const el = kroki || pasek
      if (el) {
        szerokosc.value = el.clientWidth
        obserwator.observe(el)
      }
    },
    { immediate: true },
  )
})
onBeforeUnmount(() => obserwator?.disconnect())

const liczbaEtapow = computed(() => payload.value?.steps?.length || 0)
const zwarty = computed(() => czyZwarty(liczbaEtapow.value, szerokosc.value))

const rzedyPaska = computed(() =>
  podzielNaRzedy(
    elementy.value,
    zwarty.value ? liczbaRzedowPaska(liczbaEtapow.value, szerokosc.value) : 1,
  ),
)

const elementy = computed(() =>
  (payload.value?.steps || []).map((s) => ({
    status: s.status,
    nazwa: __(s.status),
    numer: s.index + 1,
    stan: nodeStateForMode(tryb.value, s.index, biezacy.value),
    etykieta: etykietaWidoczna(s.index, biezacy.value, zwarty.value),
  })),
)

const kolkoBaza =
  'flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold'
function kolkoKlasa(stan) {
  if (stan === 'done') return 'bg-green-500 text-white'
  if (stan === 'current') return 'bg-blue-500 text-white ring-4 ring-surface-blue-3'
  if (stan === 'future') return 'border-2 border-outline-gray-3 bg-surface-base text-ink-gray-5'
  return 'border-2 border-outline-gray-2 bg-surface-gray-2 text-ink-gray-4'
}
function etykietaKlasa(stan) {
  if (stan === 'done') return 'text-ink-gray-8'
  if (stan === 'future') return 'text-ink-gray-5'
  return 'text-ink-gray-4'
}
// Odcinek za etapem i: zielony, gdy ten etap jest ukończony.
function liniaKlasa(i) {
  return elementy.value[i]?.stan === 'done' ? 'bg-green-500' : 'bg-surface-gray-3'
}

const odznakaKlasy = computed(() =>
  tryb.value === 'lost'
    ? 'border-outline-red-3 bg-surface-red-2 text-ink-red-8'
    : tryb.value === 'won'
      ? 'border-outline-green-3 bg-surface-green-2 text-ink-green-8'
      : 'border-outline-gray-2 bg-surface-gray-2 text-ink-gray-6',
)

const tekstStanu = computed(() =>
  biezacy.value >= 0
    ? tekstEtapu(biezacy.value, liczbaEtapow.value, __(status.value), czas.value)
    : '',
)
const tekstNastepnego = computed(() => {
  const t = tekstDalej(payload.value?.steps, biezacy.value)
  return t ? `${__('Dalej')}: ${__(t.slice('Dalej: '.length))}` : ''
})
const wyrownanie = computed(() => (biezacy.value > liczbaEtapow.value / 2 ? 'prawo' : 'lewo'))

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
  etapy: elementy.value.map((e) => ({
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

// --- Menu etapu ----------------------------------------------------------------
// Wyzwalacz dostarcza wołający (slot `trigger`); panel menu to zwykły blok pod
// nim, zamykany klikiem poza nim.
const MenuEtapu = defineComponent({
  props: {
    menu: { type: Object, required: true },
    wyrownanie: { type: String, default: 'lewo' },
    wariant: { type: String, default: 'pasek' },
  },
  emits: ['wybierz', 'przelacz'],
  setup(p, { emit: emitMenu, slots }) {
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
            h('span', null, [e.nazwa, e.biezacy && czas.value ? ` \u00b7 ${czas.value}` : '']),
            e.podpowiedz ? h('span', { class: 'text-xs font-normal text-ink-gray-5' }, e.podpowiedz) : null,
          ]),
        ],
      )
    }

    return () =>
      h('div', { class: 'relative inline-flex max-w-full', ref: korzen }, [
        slots.trigger?.({ toggle: () => (otwarte.value = !otwarte.value), otwarte: otwarte.value }),
        otwarte.value
          ? h(
              'div',
              {
                role: 'menu',
                'data-testid': 'menu-etapu',
                class:
                  'absolute top-full z-50 mt-1.5 w-72 rounded-lg bg-surface-elevation-2 p-1.5 shadow-2xl ring-1 ring-black ring-opacity-5 ' +
                  (p.wyrownanie === 'prawo' ? 'right-0' : 'left-0'),
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
                h('div', { class: 'my-1 h-px bg-outline-gray-2' }),
                h(
                  'button',
                  {
                    type: 'button',
                    'data-testid': 'menu-wariant',
                    class:
                      'flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-xs text-ink-gray-5 hover:bg-surface-gray-2',
                    onClick: () => {
                      otwarte.value = false
                      emitMenu('przelacz', p.wariant === 'pasek' ? 'kroki' : 'pasek')
                    },
                  },
                  [
                    __('Widok etapów') + ': ',
                    h('span', { class: p.wariant === 'kroki' ? 'font-semibold text-ink-gray-8' : '' }, __('Kroki')),
                    ' / ',
                    h('span', { class: p.wariant === 'pasek' ? 'font-semibold text-ink-gray-8' : '' }, __('Pasek')),
                  ],
                ),
              ],
            )
          : null,
      ])
  },
})
</script>
