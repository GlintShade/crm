<!--
  Galeria "Zdjęcia i filmy z realizacji" w zakładce Montaż (AktualizacjeTab.vue,
  konfig.zdjecia === true, ops#191; filmy dodane w b66). Od ops#307 ten sam
  komponent obsługuje też sekcję "Protokół montażu" (prop `rodzaj="protokol"`,
  PDF/JPG/PNG, limit 10); cała różnica siedzi w `GALERIE_MONTAZU`
  (utils/aktualizacje.js), wartość `zdjecia` odtwarza dawną galerię 1:1. Jedna galeria per
  szansa, nie per wpis strumienia Montaż: widoczna dla każdego, kto widzi
  szansę, edytowalna (dodawanie/usuwanie) przez każdego z prawem zapisu
  szansy.

  Model danych, zero nowego schematu: pliki to zwykłe wiersze `File`
  podpięte pod `CRM Deal` ze znacznikiem `attached_to_field = "zdjecia_montaz"`
  (patrz `crm/api/montaz.py`, `crm.volteo_pliki.czy_media_montazu`). Do
  pierwszego pliku sekcja to jeden kompaktowy wiersz; po wgraniu plików
  rozwija się w siatkę kafelków. Filmy renderują się jako kafelek z ikoną i
  nazwą pliku, NIGDY jako `<video>` w siatce (patrz `AudytPhotoSlot.vue`) -
  odtwarzacz żyje wyłącznie w modalu podglądu.

  Limit 20 (zdjęcia i filmy razem) jest miękki: przy 20 przycisk "Dodaj
  zdjęcia lub filmy" znika i licznik pokazuje "20 / 20", ale serwer nie
  blokuje (upload idzie przez rdzeń `upload_file`, nie przez ten moduł) -
  `restrictions.maxNumberOfFiles` niżej jest wyłącznie pomocą w UI, nie
  egzekwowaniem.
-->
<template>
  <div class="rounded-lg border border-outline-gray-2 p-3">
    <div class="flex items-center gap-2">
      <div class="text-base font-medium text-ink-gray-8">{{ __(konfig.naglowek) }}</div>
      <Badge v-if="zdjecia.length" :label="licznikEtykieta" />
      <div v-else class="text-xs text-ink-gray-5">{{ __(konfig.pusty) }}</div>
      <div class="flex-1" />
      <Button
        v-if="mozeDodac"
        size="sm"
        variant="subtle"
        :iconLeft="konfig.ikona"
        :label="__(konfig.przycisk)"
        @click="showUploader = true"
      />
    </div>

    <div v-if="zdjecia.length" class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div
        v-for="z in zdjecia"
        :key="z.klucz"
        class="group relative aspect-square overflow-hidden rounded-md border border-outline-gray-2"
      >
        <img
          v-if="!jestWideo(z.url) && !jestPdf(z.url)"
          :src="z.url"
          :alt="z.etykieta"
          loading="lazy"
          class="h-full w-full cursor-pointer object-cover"
          @click="otworzPodglad(z.klucz)"
        />
        <div
          v-else
          class="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 px-2"
          @click="otworzPodglad(z.klucz)"
        >
          <FilePdfIcon v-if="jestPdf(z.url)" class="size-8 text-ink-gray-5" />
          <FileVideoIcon v-else class="size-8 text-ink-gray-5" />
          <span class="w-full truncate text-center text-xs text-ink-gray-6">{{ z.etykieta }}</span>
        </div>
        <div
          v-if="canEdit"
          class="pointer-events-none absolute inset-0 flex items-end justify-end p-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:none)]:opacity-100 [@media(hover:none)]:bg-gradient-to-t [@media(hover:none)]:from-black/50 [@media(hover:none)]:to-transparent"
        >
          <Button
            class="pointer-events-auto"
            size="sm"
            variant="subtle"
            theme="red"
            icon="lucide-trash-2"
            :tooltip="__('Usuń')"
            @click.stop="usun(z)"
          />
        </div>
      </div>
    </div>

    <FilesUploader
      v-if="showUploader"
      v-model="showUploader"
      doctype="CRM Deal"
      :docname="dealId"
      :fieldname="konfig.fieldname"
      :options="opcjeUploadu"
      @after="zasob.reload()"
    />

    <AudytPodgladZdjec v-model="podgladOtwarty" :zdjecia="podgladLista" v-model:indeks="podgladIndeks" />
  </div>
</template>

<script setup>
import AudytPodgladZdjec from '@/components/deal/AudytPodgladZdjec.vue'
import FilePdfIcon from '@/components/Icons/FilePdfIcon.vue'
import FileVideoIcon from '@/components/Icons/FileVideoIcon.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { globalStore } from '@/stores/global'
import { GALERIE_MONTAZU, zdjeciaDoGalerii } from '@/utils/aktualizacje'
import { indeksDlaKlucza, jestPdf, jestWideo, zbudujListePodgladu } from '@/utils/audytPodglad'
import { Badge, Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
  rodzaj: {
    type: String,
    default: 'zdjecia',
    validator: (v) => Object.keys(GALERIE_MONTAZU).includes(v),
  },
})

const konfig = GALERIE_MONTAZU[props.rodzaj]

const { $dialog } = globalStore()

const MAX_ZDJEC = konfig.limit

// Pełna kropkowana ścieżka OBOWIĄZKOWA (pułapka HTTP 417 na gołej nazwie
// metody, udokumentowana przy innych whitelisted API forka).
const zasob = createResource({
  url: konfig.endpointLista,
  params: { deal: props.dealId },
  auto: true,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać plików')),
})

const zdjecia = computed(() => zdjeciaDoGalerii(zasob.data?.[konfig.kluczListy]))
const canEdit = computed(() => !!zasob.data?.can_edit)
const mozeDodac = computed(() => canEdit.value && zdjecia.value.length < MAX_ZDJEC)
const licznikEtykieta = computed(() =>
  zdjecia.value.length >= MAX_ZDJEC ? `${MAX_ZDJEC} / ${MAX_ZDJEC}` : String(zdjecia.value.length),
)

const opcjeUploadu = computed(() => ({
  folder: 'Home/Attachments',
  allowMultiple: true,
  allowWebLink: false,
  restrictions: {
    allowedFileTypes: konfig.typyPlikow,
    maxNumberOfFiles: Math.max(MAX_ZDJEC - zdjecia.value.length, 0),
  },
}))

const showUploader = ref(false)

// @after emituje się TYLKO po ostatnim pliku wsadu (FilesUploader.vue,
// attachFile: `if (i === files.value.length - 1)`), więc pojedyncza próba
// wielu plików naraz, z których część padnie, nie odświeży listy dla
// udanych. `showUploader` wraca na false po zamknięciu dialogu w każdym
// przypadku (sukces, anulowanie, częściowy błąd), więc watch tutaj jest
// jedynym pewnym miejscem odświeżenia po zamknięciu.
watch(showUploader, (otwarty) => {
  if (!otwarty) zasob.reload()
})

// PDF-y zostają otwierane w nowej karcie (natywna przeglądarka PDF jest lepsza
// niż iframe w modalu), decyzja właściciela, tak samo jak w AudytPhotoSlot.vue.
const podgladLista = computed(() => zbudujListePodgladu(zdjecia.value.filter((z) => !jestPdf(z.url))))
const podgladOtwarty = ref(false)
const podgladIndeks = ref(0)

function otworzPodglad(klucz) {
  const plik = zdjecia.value.find((z) => z.klucz === klucz)
  if (plik && jestPdf(plik.url)) {
    window.open(plik.url, '_blank', 'noopener')
    return
  }
  const idx = indeksDlaKlucza(podgladLista.value, klucz)
  if (idx === -1) return
  podgladIndeks.value = idx
  podgladOtwarty.value = true
}

function usun(z) {
  $dialog({
    title: __('Usuń plik'),
    message: __('Czy na pewno usunąć ten plik?'),
    actions: [
      {
        label: __('Usuń'),
        theme: 'red',
        variant: 'solid',
        onClick: async (close) => {
          try {
            await call(konfig.endpointUsun, { deal: props.dealId, name: z.klucz })
            await zasob.reload()
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
