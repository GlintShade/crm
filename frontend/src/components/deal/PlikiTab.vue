<!--
  Zakładka "Pliki" na szansie OZE (issue GlintShade/proenergy-crm-ops#203,
  uwaga 47) - zastępuje upstreamowy widok `Attachments` (który zostaje
  wyłącznie plikami podpiętymi wprost pod `CRM Deal`) feedem KAŻDEGO
  załącznika szansy: faktury, umowa/kredyt (podpisane i systemowe PDF),
  zdjęcia/dokumenty audytu OZE i CP, zdjęcia z Montażu, pliki notatek,
  załączniki komentarzy, e-maile, plik leada źródłowego i "luzem" - na wzór
  zakładki Notatki (`NotatkiTab.vue`, ta sama struktura: `FiltrZrodel`,
  localStorage, `createResource`).

  Kontrakt API: `crm.api.pliki.feed(deal)` (issue W4a/ops#199) - patrz
  `crm/api/pliki.py` i `crm/volteo_pliki.py` po stronie backendu.

  Bramka OZE ŻYJE TUTAJ, DODATKOWO do warunku w Deal.vue/MobileDeal.vue (te
  pliki są edytowane równolegle przez inne issue tej paczki, kolizje są
  pewne) - ten sam wzorzec co `NotatkiStrumien.vue`: czyta zbuforowany
  dokument szansy przez `getCachedDocumentResource('CRM Deal', dealId)`
  (już utworzony i ładowany przez Deal.vue/MobileDeal.vue, więc to nie jest
  drugie zapytanie o tę samą szansę), renderuje `null` (żaden DOM), gdy
  `custom_rodzaj_umowy` nie jest w OZE_RODZAJE - żeby bezpośrednie wejście
  na `#attachments` przed załadowaniem dokumentu (gdy warunek w Deal.vue
  jeszcze nie zna `custom_rodzaj_umowy` i chwilowo renderuje upstreamowe
  `Activities`) nie migało między dwoma widokami dłużej niż raz.

  Tryb przełącznika (Dokumenty/Zdjęcia i filmy/Wszystko) świadomie NIE jest
  zapamiętywany w localStorage - zawsze startuje od "Dokumenty" (decyzja
  właściciela, issue ops#203); tylko wybór źródeł i kierunek sortu
  przeżywają przeładowanie (`wczytajUstawienia`/`zapiszUstawienia`, klucz
  "pliki-filtr", ta sama zasada "raz, przy pierwszych danych" co w
  `NotatkiTab.vue`).

  Podgląd obrazów/wideo idzie przez `AudytPodgladZdjec.vue` (jeden
  odtwarzacz, tylko w modalu) - kliknięcie wiersza obrazu/wideo otwiera
  modal na liście `dlaPodgladu(wierszePosortowane)` (czyli DOKŁADNIE to, co
  jest aktualnie widoczne po filtrach/trybie/sorcie), kliknięcie wiersza
  dokumentu/innego otwiera plik w nowej karcie, jak dziś `AttachmentArea.vue`.
-->
<template>
  <div v-if="ozeWidoczne" class="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <TabButtons v-model="tryb" :options="opcjeTrybu" />
      <div class="flex flex-wrap items-center gap-2">
        <FiltrZrodel
          v-model="zaznaczoneZrodla"
          :zrodla="zrodlaZLicznikiem"
          :kierunek="kierunek"
          @update:kierunek="(nowyKierunek) => (kierunek = nowyKierunek)"
        />
        <Button
          v-if="canUpload"
          variant="solid"
          iconLeft="lucide-upload"
          :label="__('Prześlij plik')"
          @click="showUploader = true"
        />
      </div>
    </div>

    <div v-if="feed.loading" class="py-10 text-center text-sm text-ink-gray-5">
      {{ __('Ładowanie…') }}
    </div>
    <div v-else-if="!wierszePosortowane.length" class="py-10 text-center text-sm text-ink-gray-5">
      {{ tekstPusty }}
    </div>
    <div v-else class="flex flex-col divide-y divide-outline-gray-1">
      <PlikWiersz
        v-for="wiersz in wierszePosortowane"
        :key="wiersz.klucz"
        :wiersz="wiersz"
        :can-rename="canRename"
        @otworz="otworz"
        @zmien-nazwe="otworzZmianeNazwy"
        @usun="usun"
        @przejdz-do-zakladki="przejdzDoZakladki"
      />
    </div>

    <FilesUploader
      v-if="showUploader"
      v-model="showUploader"
      doctype="CRM Deal"
      :docname="dealId"
      :options="opcjeUploadu"
      @after="feed.reload()"
    />

    <AudytPodgladZdjec v-model="podgladOtwarty" :zdjecia="podgladLista" v-model:indeks="podgladIndeks" />

    <!-- Zmień nazwę pliku - dokładnie to samo wywołanie co ołówek w
         AttachmentArea.vue (issue ops#73): jedna definicja "zmiana nazwy
         załącznika" na cały fork. -->
    <Dialog
      v-model:open="dialogNazwy.otwarty"
      :title="__('Zmień nazwę pliku')"
      size="sm"
      @close="zamknijZmianeNazwy"
    >
      <template #default>
        <div class="flex flex-col gap-4">
          <div class="flex items-end gap-2">
            <FormControl
              v-model="dialogNazwy.trzon"
              type="text"
              :label="__('Nazwa pliku')"
              class="flex-1"
              :disabled="dialogNazwy.zapis"
            />
            <div class="mb-1.5 truncate text-p-base text-ink-gray-5">
              {{ dialogNazwy.rozszerzenie }}
            </div>
          </div>
          <ErrorMessage :message="dialogNazwy.blad" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="zamknijZmianeNazwy" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            :loading="dialogNazwy.zapis"
            :disabled="!dialogNazwy.trzon.trim()"
            @click="zapiszNazwe"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import AudytPodgladZdjec from '@/components/deal/AudytPodgladZdjec.vue'
import FiltrZrodel from '@/components/deal/FiltrZrodel.vue'
import PlikWiersz from '@/components/deal/PlikWiersz.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { globalStore } from '@/stores/global'
import {
  KIERUNKI_SORTU,
  TRYB_DOKUMENTY,
  TRYB_MEDIA,
  TRYB_WSZYSTKO,
  dlaPodgladu,
  filtrujTryb,
  filtrujZrodla,
  ikonaDla,
  liczbyZrodelPoTrybie,
  sortuj,
  wczytajUstawienia,
  zapiszUstawienia,
} from '@/utils/pliki'
import { podzielNazwe } from '@/utils/zalaczniki'
import {
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  TabButtons,
  call,
  createResource,
  getCachedDocumentResource,
  toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  dealId: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()
const { $dialog } = globalStore()

// Lustro `NotatkiStrumien.vue`/`Deal.vue` (OZE_RODZAJE, crm/volteo_pipeline.py) -
// patrz komentarz w bloku <template> powyżej dla uzasadnienia "dodatkowej"
// bramki tutaj, obok tej w Deal.vue/MobileDeal.vue.
const OZE_RODZAJE = new Set(['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii'])
const dealDoc = computed(() => getCachedDocumentResource('CRM Deal', props.dealId))
const ozeWidoczne = computed(() => OZE_RODZAJE.has(dealDoc.value?.doc?.custom_rodzaj_umowy))

const feed = createResource({
  url: 'crm.api.pliki.feed',
  params: { deal: props.dealId },
  auto: true,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać plików')),
})

const wiersze = computed(() => feed.data?.wiersze || [])
const zrodlaKatalog = computed(() => feed.data?.zrodla || [])
const canUpload = computed(() => Boolean(feed.data?.can_upload))
const canRename = computed(() => Boolean(feed.data?.can_rename))

const opcjeTrybu = computed(() => [
  { label: __('Dokumenty'), value: TRYB_DOKUMENTY },
  { label: __('Zdjęcia i filmy'), value: TRYB_MEDIA },
  { label: __('Wszystko'), value: TRYB_WSZYSTKO },
])

// Domyślnie "Dokumenty" przy KAŻDYM wejściu na zakładkę - świadomie NIE
// zapamiętywane w localStorage, patrz komentarz w bloku <template>.
const tryb = ref(TRYB_DOKUMENTY)

const zaznaczoneZrodla = ref([])
const kierunek = ref(KIERUNKI_SORTU.NAJNOWSZE)

// Wczytanie ustawień z localStorage dzieje się RAZ, przy pierwszym
// dotarciu `zrodla` z API - ten sam wzorzec co `NotatkiTab.vue`, żeby
// ręczny wybór użytkownika nie był nadpisywany przy każdym `reload()`.
let ustawieniaWczytane = false
watch(
  zrodlaKatalog,
  (lista) => {
    if (ustawieniaWczytane || !lista.length) return
    const wczytane = wczytajUstawienia(lista.map((zrodlo) => zrodlo.klucz))
    zaznaczoneZrodla.value = wczytane.zaznaczone
    kierunek.value = wczytane.kierunek
    ustawieniaWczytane = true
  },
  { immediate: true },
)

watch([zaznaczoneZrodla, kierunek], () => {
  if (!ustawieniaWczytane) return
  zapiszUstawienia(zaznaczoneZrodla.value, kierunek.value)
})

// Liczniki w pasku filtra liczą TYLKO bieżący tryb (Dokumenty/Zdjęcia i
// filmy/Wszystko) - lista źródeł sama w sobie zostaje pełnym katalogiem z
// API (FiltrZrodel.vue pokazuje wszystkie możliwe źródła niezależnie od
// tego, czy akurat mają jakieś wpisy w tym trybie).
const zrodlaZLicznikiem = computed(() => {
  const liczniki = liczbyZrodelPoTrybie(wiersze.value, tryb.value)
  return zrodlaKatalog.value.map((zrodlo) => ({ ...zrodlo, liczba: liczniki[zrodlo.klucz] || 0 }))
})

const wierszeWTrybie = computed(() => filtrujTryb(wiersze.value, tryb.value))
const wierszePrzefiltrowane = computed(() => filtrujZrodla(wierszeWTrybie.value, zaznaczoneZrodla.value))
const wierszePosortowane = computed(() => sortuj(wierszePrzefiltrowane.value, kierunek.value))

const tekstPusty = computed(() => {
  if (tryb.value === TRYB_DOKUMENTY) return __('Brak dokumentów.')
  if (tryb.value === TRYB_MEDIA) return __('Brak zdjęć i filmów.')
  return __('Brak plików.')
})

// Podgląd obrazów/wideo: lista DOKŁADNIE tego, co jest aktualnie widoczne
// (po trybie/źródłach/sorcie), żeby strzałki poprzedni/następny w modalu
// nawigowały po tym samym zestawie, który użytkownik widzi w tle.
const podgladLista = computed(() => dlaPodgladu(wierszePosortowane.value))
const podgladOtwarty = ref(false)
const podgladIndeks = ref(0)

function otworz(wiersz) {
  const klucz = ikonaDla(wiersz)
  if (klucz === 'obraz' || klucz === 'wideo') {
    const idx = podgladLista.value.findIndex((p) => p.klucz === wiersz.klucz)
    if (idx === -1) return
    podgladIndeks.value = idx
    podgladOtwarty.value = true
    return
  }
  window.open(wiersz.file_url, '_blank', 'noopener')
}

function przejdzDoZakladki(wiersz) {
  if (!wiersz?.zakladka) return
  router.push({ ...route, hash: `#${wiersz.zakladka}` })
}

// Upload "luzem": forkowy FilesUploader z doctype/docname, BEZ fieldname
// (plik trafia na CRM Deal z pustym attached_to_field, klasyfikowany przez
// backend jako źródło "luzem") i allowWebLink false - wzór MontazZdjecia.vue.
const opcjeUploadu = {
  folder: 'Home/Attachments',
  allowMultiple: true,
  allowWebLink: false,
}

const showUploader = ref(false)

// `@after` odpala TYLKO po ostatnim pliku wsadu (FilesUploader.vue,
// `attachFile`), więc odświeżenie feedu dzieje się też w
// `watch(showUploader)` przy zamknięciu dialogu - wzór MontazZdjecia.vue.
watch(showUploader, (otwarty) => {
  if (!otwarty) feed.reload()
})

// Zmiana nazwy pliku - dokładnie to samo wywołanie co ołówek w
// AttachmentArea.vue (issue ops#73). Kształt deklarowany z góry, plik
// zawsze jawny `null` (nigdy usuwany kluczem) - patrz pułapka
// hasOwnProperty-na-reactive w CLAUDE.md (tu użyty zwykły obiekt `ref`,
// więc pułapka nie dotyczy bezpośrednio, ale konwencja zostaje spójna).
const dialogNazwy = ref({
  otwarty: false,
  plik: null,
  trzon: '',
  rozszerzenie: '',
  blad: '',
  zapis: false,
})

function otworzZmianeNazwy(wiersz) {
  const { trzon, rozszerzenie } = podzielNazwe(wiersz.file_name)
  dialogNazwy.value = {
    otwarty: true,
    plik: wiersz,
    trzon,
    rozszerzenie,
    blad: '',
    zapis: false,
  }
}

function zamknijZmianeNazwy() {
  dialogNazwy.value = { otwarty: false, plik: null, trzon: '', rozszerzenie: '', blad: '', zapis: false }
}

async function zapiszNazwe() {
  dialogNazwy.value = { ...dialogNazwy.value, zapis: true, blad: '' }
  try {
    await call('crm.api.volteo_zmien_nazwe_zalacznika', {
      name: dialogNazwy.value.plik.klucz,
      nowy_trzon: dialogNazwy.value.trzon,
    })
    zamknijZmianeNazwy()
    feed.reload()
  } catch (err) {
    dialogNazwy.value = {
      ...dialogNazwy.value,
      zapis: false,
      blad: err?.messages?.[0] || __('Nie udało się zmienić nazwy.'),
    }
  }
}

// Kasowanie WYŁĄCZNIE przez `crm.api.pliki.usun` (nigdy
// `frappe.client.delete`/`crm.api.delete_attachment`) - serwer sam
// odrzuca każdy plik, który nie jest dokładnie "luzem"
// (`PlikWiersz.vue` i tak pokazuje kosz tylko wtedy, gdy
// `wiersz.mozna_usunac`, ale ta bramka jest tylko wygodą UI, prawdziwa
// żyje na serwerze).
function usun(wiersz) {
  $dialog({
    title: __('Usuń plik'),
    message: __('Czy na pewno usunąć ten plik? Tej operacji nie można cofnąć.'),
    actions: [
      {
        label: __('Usuń'),
        theme: 'red',
        variant: 'solid',
        onClick: async (close) => {
          try {
            await call('crm.api.pliki.usun', { deal: props.dealId, name: wiersz.klucz })
            await feed.reload()
            close()
          } catch (err) {
            toast.error(err?.messages?.[0] || err?.message || __('Nie udało się usunąć pliku'))
          }
        },
      },
    ],
  })
}
</script>
