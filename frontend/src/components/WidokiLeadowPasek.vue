<template>
  <div
    v-if="tryb === 'typ' && pokazPasek"
    class="flex items-center gap-2"
    data-testid="widoki-leadow-przelacznik-wrap"
  >
    <div class="h-5 w-px shrink-0 bg-outline-gray-2" />
    <div
      class="inline-flex items-center rounded border border-outline-gray-2 overflow-hidden shrink-0"
      data-testid="widoki-leadow-przelacznik"
    >
      <button
        v-for="(typ, index) in typyWidoku"
        :key="typ.key"
        type="button"
        class="flex h-7 items-center gap-1.5 whitespace-nowrap px-2 text-base transition-colors"
        :class="[
          typ.key === aktywnyTyp
            ? 'bg-surface-gray-4 text-ink-gray-9'
            : 'text-ink-gray-6 hover:bg-surface-gray-2',
          index > 0 && 'border-l border-outline-gray-2',
        ]"
        :data-testid="`widoki-leadow-przelacznik-typ-${typ.key}`"
        @click="wybierzTyp(typ.key)"
      >
        <component :is="typ.icon" class="h-4 w-4" />
        <span>{{ typ.label }}</span>
      </button>
    </div>
  </div>

  <div
    v-else-if="tryb === 'filtry' && pokazPasek && zapisaneWidoki.length"
    class="flex items-center gap-1.5 sm:px-5 px-3 pt-3 pb-1"
    :class="isMobileView ? 'flex-nowrap overflow-x-auto' : 'flex-wrap'"
    data-testid="widoki-leadow-pasek"
  >
    <span class="shrink-0 whitespace-nowrap text-base text-ink-gray-5">
      Zapisane filtry:
    </span>

    <button
      v-for="widok in zapisaneWidoki"
      :key="widok.name"
      type="button"
      class="flex h-7 items-center gap-1 whitespace-nowrap rounded px-2 text-base transition-colors"
      :class="
        jestAktywnyWidok(widok)
          ? 'bg-surface-gray-4 text-ink-gray-9'
          : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3'
      "
      :data-testid="`widoki-leadow-pasek-widok-${widok.name}`"
      @click="wybierzWidok(widok)"
    >
      <span>{{ widok.label }}</span>
      <FeatherIcon
        v-if="jestAktywnyWidok(widok)"
        name="x"
        class="size-3.5"
        @click.stop="wyczyscWidok()"
      />
    </button>
  </div>
</template>
<script setup>
// VOLTEO (pasek widokow leadow, 2026-09-10, plan zatwierdzony przez
// wlasciciela; poprawka wizualna tego samego dnia po klik-tescie): jeden
// komponent, dwa tryby wybierane przez prop `tryb`, zeby odrozniac
// wizualnie TYP widoku od ZAPISANYCH FILTROW, zamiast mieszac je w jednym
// rzedzie chipow jak w pierwszej wersji.
//
// tryb="typ": segmentowany przelacznik Lista/Mapa, montowany w
// LayoutHeader (#left-header w Leads.vue), zaraz po ViewBreadcrumbs, z
// pionowa kreska oddzielajaca. `route.params.viewType` (Lista/Mapa) i
// ZACHOWUJE biezace query (w tym `?view`) - Mapa i Lista to dwie
// reprezentacje tego samego zapisanego widoku typu "list" (patrz
// utils/widokLeady.js).
//
// tryb="filtry": drugi rzad pod naglowkiem (nad paskiem filtrow szybkich),
// WYLACZNIE zapisane widoki (etykieta "Zapisane filtry:", bez __() - fraza
// nie wystepuje w pl.po, ale jest juz po polsku i nie potrzebuje katalogu).
// Renderuje sie TYLKO gdy jest co najmniej jeden zapisany widok - inaczej
// caly rzad znika, zamiast pokazywac sama etykiete.
//
// ŹRÓDŁO zapisanych widokow CELOWO NIE jest `leads.data.views` z
// ViewControls.vue (wersja sprzed klik-testu wlasciciela czerpala
// stamtad): ten zasob ma DWA watchery na route.query.view/
// route.params.viewType (linie ok. 1409 i 1423 ViewControls.vue), z
// ktorych drugi ma zlamany warunek wczesnego wyjscia (`value[1] ===
// value[0]` porownuje string z obiektem trasy, zawsze false), wiec
// reload() odpala sie DWUKROTNIE przy kazdej zmianie widoku - dwa
// nakladajace sie zapytania do crm.api.doc.get_data bez gwarancji
// kolejnosci odpowiedzi. Zamiast tego pasek czerpie z globalnego,
// niezaleznego magazynu `viewsStore()` (ten sam, z ktorego korzystaja
// AppSidebar.vue/MobileSidebar.vue dla "Public Views" i "Pinned Views") -
// jeden wspoldzielony zasob (cache 'crm-views'), bez zadnego watchera na
// trase, wiec stabilny niezaleznie od tego, ktory zapisany widok jest
// aktywny. Filtrowany lokalnie do type=="list" (alias Mapa->Lista, patrz
// utils/widokLeady.js), bez is_standard, tylko dt=="CRM Lead" (magazyn
// jest globalny, miesza doctype'y), posortowany wlasne -> publiczne ->
// przypiete, bez duplikatow. Klikniecie nawiguje tym samym ksztaltem push
// co ViewControls.vue (`standardViews`/`viewsDropdownOptions` onClick),
// zeby jego watchery na route.query.view przeladowaly liste tak samo,
// jakby uzytkownik wybral widok z rozwijanego przelacznika.
import ListIcon from '@/components/Icons/ListIcon.vue'
import MapaIcon from '~icons/lucide/map'
import { isMobileView } from '@/composables/settings'
import { viewsStore } from '@/stores/views'
import { FeatherIcon } from 'frappe-ui'
import { computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  tryb: {
    type: String,
    required: true,
    validator: (v) => ['typ', 'filtry'].includes(v),
  },
})

const route = useRoute()
const router = useRouter()

const { views: wszystkieWidoki } = viewsStore()

const typyWidoku = [
  { key: 'list', label: __('List'), icon: markRaw(ListIcon) },
  { key: 'mapa', label: __('Mapa'), icon: markRaw(MapaIcon) },
]

const aktywnyTyp = computed(() =>
  route.params.viewType === 'mapa' ? 'mapa' : 'list',
)

// Oba tryby maja sens tylko dla Lista/Mapa - na Kanban i Grupuj wg znikaja
// calkowicie (te widoki nie maja odpowiednika w segmentowanym przelaczniku).
const pokazPasek = computed(
  () => !['kanban', 'group_by'].includes(route.params.viewType),
)

function wybierzTyp(viewType) {
  router.push({
    name: 'Leads',
    params: { viewType },
    query: route.query,
  })
}

// Zapisane widoki leadow ograniczone do type=="list" (Mapa dzieli TEN SAM
// zapisany widok co Lista - patrz utils/widokLeady.js), bez widokow
// standardowych, w kolejnosci wlasne -> publiczne -> przypiete, bez
// duplikatow (widok publiczny-i-przypiety naraz liczy sie raz, w grupie
// publicznych).
const zapisaneWidoki = computed(() => {
  const listowe = (wszystkieWidoki.data || []).filter(
    (widok) =>
      widok.dt === 'CRM Lead' &&
      (widok.type || 'list') === 'list' &&
      !widok.is_standard,
  )
  const wlasne = listowe.filter((widok) => !widok.pinned && !widok.public)
  const publiczne = listowe.filter(
    (widok) => widok.public && !wlasne.includes(widok),
  )
  const przypiete = listowe.filter(
    (widok) =>
      widok.pinned &&
      !wlasne.includes(widok) &&
      !publiczne.includes(widok),
  )
  return [...wlasne, ...publiczne, ...przypiete]
})

function jestAktywnyWidok(widok) {
  return (
    route.query.view != null && String(route.query.view) === String(widok.name)
  )
}

function wybierzWidok(widok) {
  if (jestAktywnyWidok(widok)) {
    wyczyscWidok()
    return
  }
  router.push({
    name: 'Leads',
    params: { viewType: aktywnyTyp.value },
    query: { ...route.query, view: widok.name },
  })
}

function wyczyscWidok() {
  const { view: _pomijane, ...pozostaleQuery } = route.query
  router.push({
    name: 'Leads',
    params: { viewType: aktywnyTyp.value },
    query: pozostaleQuery,
  })
}
</script>
