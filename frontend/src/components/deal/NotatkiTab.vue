<!--
  Zakładka "Notatki" na szansie (issue ops#201, uwaga 40, faza 1 = tylko
  OZE; wygląd przebudowany na "wariant C" w issue ops#206) - jeden strumień
  ŁĄCZĄCY notatki z każdej zakładki (`Volteo Notatka`, `crm.api.notatki.
  feed`) z komentarzami wątku "Komentarze" zakładki Audyt (OZE i CP).
  Wyłącznie WIDOK: bez karty dodawania, edycji ani kosza - te operacje żyją
  na zakładce źródłowej (`NotatkiStrumien.vue` dla notatek, `AudytTab.vue`/
  `AudytCPTab.vue` dla komentarzy audytu).

  Bramka OZE ŻYJE W Deal.vue/MobileDeal.vue (`condition` na wpisie tabs), NIE
  tutaj - w odróżnieniu od `NotatkiStrumien.vue`, gdzie bramka żyje w
  komponencie właśnie dlatego, że te dwa pliki są edytowane równolegle przez
  inne issue tej paczki. Ten komponent renderuje się tylko wtedy, gdy jego
  zakładka w ogóle istnieje w tablicy `tabs` - drugi poziom bramkowania byłby
  zbędny (i niespójny z tym, jak reszta zakładek custom na tej stronie
  działa, np. `ZestawTab.vue`/`FakturyTab.vue`).

  UKŁAD (wariant C, desktop): górny pasek na całą szerokość (szukanie |
  podsumowanie | sortowanie), pod nim dwie kolumny - panel źródeł
  (`PanelZrodel.vue`, 200 px) po lewej, lista kart po prawej. Telefon
  (< 768 px, ten sam komponent montowany identycznie przez `MobileDeal.vue`
  - patrz komentarz w `PanelZrodel.vue`): `PanelZrodel.vue` sam zamienia się
  w poziomy rząd chipów (czyste CSS `md:`, bez JS-owego wykrywania
  szerokości), a pasek górny ląduje w dwóch wierszach (szukanie na całą
  szerokość, pod nim podsumowanie i sortowanie razem).

  CELOWO NIE jest to przebudowa `FiltrZrodel.vue` w miejscu - zobacz
  komentarz w nagłówku `PanelZrodel.vue` (konflikt z `PlikiTab.vue`, issue
  równoległe ops#203, już scalone do tego samego `volteo/b64-prep`, wciąż
  używa starego kontraktu `FiltrZrodel.vue` z wbudowanym sortem). Sort
  wyszedł z panelu źródeł do tego pliku - dokładnie jak wymaga brief -
  tylko że do nowego, dedykowanego panelu, nie do starego komponentu.

  Szukanie (`szukajWFeedzie`) jest WYŁĄCZNIE po stronie przeglądarki, bez
  parametru do API - filtruje treść (bez HTML), autora i nazwy plików, bez
  rozróżniania wielkości liter/ogonków. Podsumowanie (`podsumowanieFeedu`)
  liczy się na liście PO filtrze źródeł, PRZED szukaniem (decyzja
  właściciela, issue ops#206) - stąd `wpisyPoZrodlach` jako osobny computed
  między `wpisy` i `wpisyPoSzukaniu`, nie połączone w jeden krok.

  Filtr źródeł i kierunek sortowania są pamiętane w localStorage
  (`wczytajFiltr`/`zapiszFiltr`, klucz "notatki-filtr") - inicjalizowane
  RAZ, przy pierwszym dotarciu `zrodla` z API (ta sama zasada "raz, przy
  pierwszych danych" co domyślny stan rozwinięcia w `NotatkiStrumien.vue`),
  żeby ręczny wybór użytkownika nie był nadpisywany przy każdym `reload()`.
  Fraza szukania NIE jest zapamiętywana - zawsze startuje pusta, jak każde
  pole szukania w tej aplikacji (np. `Hierarchy.vue`).

  "Otwórz w zakładce" żyje teraz WEWNĄTRZ `NotatkaKarta.vue` (stopka karty,
  nie osobny przycisk pod nią) - ten komponent tylko nasłuchuje emitowane
  `otworz-zakladke` i zmienia hash trasy (`useActiveTabManager` w
  Deal.vue/MobileDeal.vue nasłuchuje `route.hash` i sam przełącza zakładkę).
-->
<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <div class="flex flex-col gap-3 border-b border-outline-gray-2 p-4">
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <TextInput
          v-model="fraza"
          type="text"
          :placeholder="__('Szukaj w notatkach')"
          :debounce="150"
          class="w-full md:w-[280px]"
        >
          <template #prefix>
            <span class="lucide-search size-4 text-ink-gray-6" aria-hidden="true" />
          </template>
        </TextInput>

        <div class="hidden items-center gap-4 md:flex">
          <PodsumowanieNotatek :podsumowanie="podsumowanie" />
          <div class="flex items-center gap-2">
            <span class="text-sm text-ink-gray-5">{{ __('Kolejność') }}</span>
            <Dropdown :options="opcjeSortu" placement="bottom-end">
              <template #default="{ open }">
                <Button
                  variant="ghost"
                  :label="etykietaSortu"
                  :iconRight="open ? 'chevron-up' : 'chevron-down'"
                />
              </template>
            </Dropdown>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between gap-3 md:hidden">
        <PodsumowanieNotatek :podsumowanie="podsumowanie" />
        <Dropdown :options="opcjeSortu" placement="bottom-end">
          <template #default="{ open }">
            <Button
              variant="ghost"
              size="sm"
              :label="etykietaSortu"
              :iconRight="open ? 'chevron-up' : 'chevron-down'"
            />
          </template>
        </Dropdown>
      </div>
    </div>

    <div class="flex flex-1 flex-col overflow-hidden md:flex-row">
      <PanelZrodel v-model="zaznaczoneZrodla" :zrodla="zrodla" />

      <div class="flex-1 overflow-y-auto p-4">
        <div v-if="feed.loading" class="py-10 text-center text-sm text-ink-gray-5">
          {{ __('Ładowanie…') }}
        </div>
        <div v-else-if="!wpisyPosortowane.length" class="py-10 text-center text-sm text-ink-gray-5">
          {{ fraza.trim() ? __('Brak wyników wyszukiwania.') : __('Brak notatek.') }}
        </div>
        <div v-else class="flex flex-col gap-5">
          <div v-for="grupa in grupyDni" :key="grupa.etykieta" class="flex flex-col gap-3">
            <div class="text-sm font-medium text-ink-gray-6">{{ grupa.etykieta }}</div>
            <div class="flex flex-col gap-2">
              <NotatkaKarta
                v-for="wpis in grupa.wpisy"
                :key="wpis.klucz"
                :wpis="jakoKartaWpis(wpis)"
                pokaz-zakladke
                tylko-godzina
                @otworz-zakladke="przejdzDoZakladki"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import NotatkaKarta from '@/components/deal/NotatkaKarta.vue'
import PanelZrodel from '@/components/deal/PanelZrodel.vue'
import PodsumowanieNotatek from '@/components/deal/PodsumowanieNotatek.vue'
import {
  KIERUNKI_SORTU,
  filtrujFeed,
  grupujPoDniu,
  podsumowanieFeedu,
  sortujFeed,
  szukajWFeedzie,
  wczytajFiltr,
  zapiszFiltr,
} from '@/utils/notatki'
import { Button, Dropdown, TextInput, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  dealId: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()

const feed = createResource({
  url: 'crm.api.notatki.feed',
  params: { deal: props.dealId },
  auto: true,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać notatek')),
})

const wpisy = computed(() => feed.data?.wpisy || [])
const zrodla = computed(() => feed.data?.zrodla || [])

const zaznaczoneZrodla = ref([])
const kierunek = ref(KIERUNKI_SORTU.NAJNOWSZE)
const fraza = ref('')

// Wczytanie filtra z localStorage dzieje się RAZ, przy pierwszym dotarciu
// `zrodla` - kolejne przeładowania (np. po powrocie na tę zakładkę) nie
// nadpisują już wyboru użytkownika w tej samej wizycie na stronie.
let filtrWczytany = false
watch(
  zrodla,
  (lista) => {
    if (filtrWczytany || !lista.length) return
    const wczytany = wczytajFiltr(lista.map((zrodlo) => zrodlo.klucz))
    zaznaczoneZrodla.value = wczytany.zaznaczone
    kierunek.value = wczytany.kierunek
    filtrWczytany = true
  },
  { immediate: true },
)

watch([zaznaczoneZrodla, kierunek], () => {
  if (!filtrWczytany) return
  zapiszFiltr(zaznaczoneZrodla.value, kierunek.value)
})

// Kolejność wymagana przez brief: podsumowanie liczy się PO filtrze źródeł,
// PRZED szukaniem - `wpisyPoZrodlach` jest więc osobnym krokiem, czytanym
// zarówno przez `podsumowanie` jak i (dalej filtrowany fraz) `wpisyPoSzukaniu`.
const wpisyPoZrodlach = computed(() => filtrujFeed(wpisy.value, zaznaczoneZrodla.value))
const podsumowanie = computed(() => podsumowanieFeedu(wpisyPoZrodlach.value))

const wpisyPoSzukaniu = computed(() => szukajWFeedzie(wpisyPoZrodlach.value, fraza.value))
const wpisyPosortowane = computed(() => sortujFeed(wpisyPoSzukaniu.value, kierunek.value))
const grupyDni = computed(() => grupujPoDniu(wpisyPosortowane.value))

const opcjeSortu = computed(() => [
  {
    label: __('Od najnowszych'),
    onClick: () => (kierunek.value = KIERUNKI_SORTU.NAJNOWSZE),
  },
  {
    label: __('Od najstarszych'),
    onClick: () => (kierunek.value = KIERUNKI_SORTU.NAJSTARSZE),
  },
])

const etykietaSortu = computed(() =>
  kierunek.value === KIERUNKI_SORTU.NAJSTARSZE ? __('Od najstarszych') : __('Od najnowszych'),
)

// Adaptuje kształt wpisu feedu (`klucz`/`zrodlo`/`data`/`autor`/
// `tekst_html`, patrz kontrakt `crm.api.notatki.feed`) na kształt, którego
// oczekuje `NotatkaKarta.vue` (`name`/`zakladka`/`data_zdarzenia`/`owner`/
// `tekst`, kształt `crm.api.notatki.lista()`) - dwa różne kontrakty API dla
// tego samego wspólnego komponentu karty, zamiast rozgałęziać samą kartę na
// "tryb notatki" i "tryb feedu".
function jakoKartaWpis(wpis) {
  return {
    name: wpis.klucz,
    zakladka: wpis.zrodlo,
    typ: wpis.typ,
    data_zdarzenia: wpis.data,
    creation: wpis.data,
    tekst: wpis.tekst_html,
    kredyt: wpis.kredyt,
    owner: wpis.autor,
    autor_nazwa: wpis.autor_nazwa,
    pliki: wpis.pliki,
    zakladka_hash: wpis.zakladka_hash,
  }
}

function przejdzDoZakladki(hash) {
  if (!hash) return
  router.push({ ...route, hash: `#${hash}` })
}
</script>
