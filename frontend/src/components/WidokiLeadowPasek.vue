<template>
  <div
    v-if="pokazPasek"
    class="flex items-center gap-1.5 sm:px-5 px-3 pt-3 pb-1"
    :class="isMobileView ? 'flex-nowrap overflow-x-auto' : 'flex-wrap'"
    data-testid="widoki-leadow-pasek"
  >
    <button
      v-for="typ in typyWidoku"
      :key="typ.key"
      type="button"
      class="flex h-7 items-center gap-1.5 whitespace-nowrap rounded px-2 text-base transition-colors"
      :class="
        typ.key === aktywnyTyp
          ? 'bg-surface-gray-4 text-ink-gray-9'
          : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3'
      "
      :data-testid="`widoki-leadow-pasek-typ-${typ.key}`"
      @click="wybierzTyp(typ.key)"
    >
      <component :is="typ.icon" class="h-4 w-4" />
      <span>{{ typ.label }}</span>
    </button>

    <div
      v-if="zapisaneWidoki.length"
      class="h-5 w-px shrink-0 bg-outline-gray-2"
    />

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
// wlasciciela): pasek chipow nad lista leadow (miedzy LayoutHeader a
// ViewControls), niezalezny od rozwijanego przelacznika w naglowku
// (ViewBreadcrumbs.vue), ktory zostaje bez zmian.
//
// Lewa grupa przelacza `route.params.viewType` (Lista/Mapa) i ZACHOWUJE
// biezace query (w tym `?view`) - Mapa i Lista to dwie reprezentacje tego
// samego zapisanego widoku typu "list" (patrz utils/widokLeady.js).
//
// Prawa grupa listuje zapisane widoki tego doctype'u (props.views, ten sam
// zbior co ViewControls.vue czerpie z `leads.data.views` w Leads.vue),
// ograniczone do type=="list" (alias Mapa->Lista), bez is_standard,
// posortowane wlasne -> publiczne -> przypiete, bez duplikatow. Klikniecie
// nawiguje tym samym ksztaltem push co ViewControls.vue (`standardViews`/
// `viewsDropdownOptions` onClick), zeby jego watchery na route.query.view
// przeladowaly liste tak samo, jakby uzytkownik wybral widok z rozwijanego
// przelacznika.
import ListIcon from '@/components/Icons/ListIcon.vue'
import MapaIcon from '~icons/lucide/map'
import { isMobileView } from '@/composables/settings'
import { FeatherIcon } from 'frappe-ui'
import { computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  views: { type: Array, default: () => [] },
})

const route = useRoute()
const router = useRouter()

const typyWidoku = [
  { key: 'list', label: __('List'), icon: markRaw(ListIcon) },
  { key: 'mapa', label: __('Mapa'), icon: markRaw(MapaIcon) },
]

const aktywnyTyp = computed(() =>
  route.params.viewType === 'mapa' ? 'mapa' : 'list',
)

// Pasek ma sens tylko dla Lista/Mapa - na Kanban i Grupuj wg znika
// calkowicie (te widoki nie maja odpowiednika w lewej grupie).
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
  const listowe = (props.views || []).filter(
    (widok) => (widok.type || 'list') === 'list' && !widok.is_standard,
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
