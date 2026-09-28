<!--
  Zakładka "Notatki" na szansie (issue ops#201, uwaga 40, faza 1 = tylko
  OZE) - jeden strumień ŁĄCZĄCY notatki z każdej zakładki (`Volteo Notatka`,
  `crm.api.notatki.feed`) z komentarzami wątku "Komentarze" zakładki Audyt
  (OZE i CP). Wyłącznie WIDOK: bez karty dodawania, edycji ani kosza - te
  operacje żyją na zakładce źródłowej (`NotatkiStrumien.vue` dla notatek,
  `AudytTab.vue`/`AudytCPTab.vue` dla komentarzy audytu).

  Bramka OZE ŻYJE W Deal.vue/MobileDeal.vue (`condition` na wpisie tabs), NIE
  tutaj - w odróżnieniu od `NotatkiStrumien.vue`, gdzie bramka żyje w
  komponencie właśnie dlatego, że te dwa pliki są edytowane równolegle przez
  inne issue tej paczki. Ten komponent renderuje się tylko wtedy, gdy jego
  zakładka w ogóle istnieje w tablicy `tabs` - drugi poziom bramkowania byłby
  zbędny (i niespójny z tym, jak reszta zakładek custom na tej stronie
  działa, np. `ZestawTab.vue`/`FakturyTab.vue`).

  Filtr źródeł i kierunek sortowania są pamiętane w localStorage
  (`wczytajFiltr`/`zapiszFiltr`, klucz "notatki-filtr") - inicjalizowane
  RAZ, przy pierwszym dotarciu `zrodla` z API (ta sama zasada "raz, przy
  pierwszych danych" co domyślny stan rozwinięcia w `NotatkiStrumien.vue`),
  żeby ręczny wybór użytkownika nie był nadpisywany przy każdym `reload()`.

  "Przejdź do zakładki" zmienia hash trasy (`useActiveTabManager` w
  Deal.vue/MobileDeal.vue nasłuchuje `route.hash` i sam przełącza zakładkę) -
  `wpis.zakladka_hash` jest już gotowym, małym literami hashem bez "#"
  (policzonym serwerowo w `crm.volteo_notatki.normalizuj_notatke`/
  `normalizuj_komentarz_audytu`).
-->
<template>
  <div class="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
    <FiltrZrodel
      v-model="zaznaczoneZrodla"
      :zrodla="zrodla"
      :kierunek="kierunek"
      @update:kierunek="(nowyKierunek) => (kierunek = nowyKierunek)"
    />

    <div v-if="feed.loading" class="py-10 text-center text-sm text-ink-gray-5">
      {{ __('Ładowanie…') }}
    </div>
    <div v-else-if="!wpisyPrzefiltrowane.length" class="py-10 text-center text-sm text-ink-gray-5">
      {{ __('Brak notatek.') }}
    </div>
    <div v-else class="flex flex-col gap-5">
      <div v-for="grupa in grupyDni" :key="grupa.etykieta" class="flex flex-col gap-3">
        <div class="text-sm font-medium text-ink-gray-6">{{ grupa.etykieta }}</div>
        <div class="flex flex-col gap-2">
          <div v-for="wpis in grupa.wpisy" :key="wpis.klucz" class="flex flex-col gap-1">
            <NotatkaKarta
              :wpis="jakoKartaWpis(wpis)"
              pokaz-zakladke
              tylko-godzina
              :ikona-zakladki="ikonaDlaZrodla(wpis.zrodlo)"
              :etykieta-zakladki-override="wpis.zrodlo_etykieta"
            />
            <Button
              variant="ghost"
              size="sm"
              class="self-end"
              iconRight="arrow-up-right"
              :label="__('Przejdź do zakładki')"
              @click="przejdzDoZakladki(wpis.zakladka_hash)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import AudytIcon from '@/components/Icons/AudytIcon.vue'
import FakturyIcon from '@/components/Icons/FakturyIcon.vue'
import KredytIcon from '@/components/Icons/KredytIcon.vue'
import MontazIcon from '@/components/Icons/MontazIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TrifyIcon from '@/components/Icons/TrifyIcon.vue'
import UmowaIcon from '@/components/Icons/UmowaIcon.vue'
import ZestawIcon from '@/components/Icons/ZestawIcon.vue'
import FiltrZrodel from '@/components/deal/FiltrZrodel.vue'
import NotatkaKarta from '@/components/deal/NotatkaKarta.vue'
import {
  KIERUNKI_SORTU,
  filtrujFeed,
  grupujPoDniu,
  sortujFeed,
  wczytajFiltr,
  zapiszFiltr,
} from '@/utils/notatki'
import { Button, createResource, toast } from 'frappe-ui'
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

const wpisyPrzefiltrowane = computed(() => filtrujFeed(wpisy.value, zaznaczoneZrodla.value))
const wpisyPosortowane = computed(() => sortujFeed(wpisyPrzefiltrowane.value, kierunek.value))
const grupyDni = computed(() => grupujPoDniu(wpisyPosortowane.value))

// OSD/Dotacja nie mają jeszcze własnych ikon (powstają w równoległym issue,
// OsdIcon/DotacjaIcon) - każdy nieznany klucz źródła (w tym te dwa, na
// razie) spada na NoteIcon zamiast na pustą/brakującą ikonę.
const IKONY_ZRODEL = {
  Zestaw: ZestawIcon,
  Umowa: UmowaIcon,
  Kredyt: KredytIcon,
  Faktury: FakturyIcon,
  Montaz: MontazIcon,
  Trify: TrifyIcon,
  Audyt: AudytIcon,
  AudytCP: AudytIcon,
}

function ikonaDlaZrodla(zrodlo) {
  return IKONY_ZRODEL[zrodlo] || NoteIcon
}

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
  }
}

function przejdzDoZakladki(hash) {
  if (!hash) return
  router.push({ ...route, hash: `#${hash}` })
}
</script>
