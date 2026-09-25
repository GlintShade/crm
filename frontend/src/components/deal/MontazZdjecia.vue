<!--
  Galeria "Zdjęcia z realizacji" w zakładce Montaż (AktualizacjeTab.vue,
  konfig.zdjecia === true, ops#191). Jedna galeria per szansa, nie per wpis
  strumienia Montaż: widoczna dla każdego, kto widzi szansę, edytowalna
  (dodawanie/usuwanie) przez każdego z prawem zapisu szansy.

  Model danych, zero nowego schematu: zdjęcia to zwykłe wiersze `File`
  podpięte pod `CRM Deal` ze znacznikiem `attached_to_field = "zdjecia_montaz"`
  (patrz `crm/api/montaz.py`). Do pierwszego zdjęcia sekcja to jeden
  kompaktowy wiersz; po wgraniu zdjęć rozwija się w siatkę kafelków.

  Limit 20 zdjęć jest miękki: przy 20 przycisk "Dodaj zdjęcia" znika i
  licznik pokazuje "20 / 20", ale serwer nie blokuje (upload idzie przez
  rdzeń `upload_file`, nie przez ten moduł) - `restrictions.maxNumberOfFiles`
  niżej jest wyłącznie pomocą w UI, nie egzekwowaniem.
-->
<template>
  <div class="rounded-lg border border-outline-gray-2 p-3">
    <div class="flex items-center gap-2">
      <div class="text-base font-medium text-ink-gray-8">{{ __('Zdjęcia z realizacji') }}</div>
      <Badge v-if="zdjecia.length" :label="licznikEtykieta" />
      <div v-else class="text-xs text-ink-gray-5">{{ __('Brak zdjęć') }}</div>
      <div class="flex-1" />
      <Button
        v-if="mozeDodac"
        size="sm"
        variant="subtle"
        iconLeft="lucide-camera"
        :label="__('Dodaj zdjęcia')"
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
          :src="z.url"
          :alt="z.etykieta"
          loading="lazy"
          class="h-full w-full cursor-pointer object-cover"
          @click="otworzPodglad(z.klucz)"
        />
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
      fieldname="zdjecia_montaz"
      :options="opcjeUploadu"
      @after="zasob.reload()"
    />

    <AudytPodgladZdjec v-model="podgladOtwarty" :zdjecia="podgladLista" v-model:indeks="podgladIndeks" />
  </div>
</template>

<script setup>
import AudytPodgladZdjec from '@/components/deal/AudytPodgladZdjec.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { globalStore } from '@/stores/global'
import { zdjeciaDoGalerii } from '@/utils/aktualizacje'
import { indeksDlaKlucza, zbudujListePodgladu } from '@/utils/audytPodglad'
import { Badge, Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

const { $dialog } = globalStore()

const MAX_ZDJEC = 20

// Pełna kropkowana ścieżka OBOWIĄZKOWA (pułapka HTTP 417 na gołej nazwie
// metody, udokumentowana przy innych whitelisted API forka).
const zasob = createResource({
  url: 'crm.api.montaz.zdjecia_montazu',
  params: { deal: props.dealId },
  auto: true,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać zdjęć')),
})

const zdjecia = computed(() => zdjeciaDoGalerii(zasob.data?.zdjecia))
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
    allowedFileTypes: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
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

const podgladLista = computed(() => zbudujListePodgladu(zdjecia.value))
const podgladOtwarty = ref(false)
const podgladIndeks = ref(0)

function otworzPodglad(klucz) {
  const idx = indeksDlaKlucza(podgladLista.value, klucz)
  if (idx === -1) return
  podgladIndeks.value = idx
  podgladOtwarty.value = true
}

function usun(z) {
  $dialog({
    title: __('Usuń zdjęcie'),
    message: __('Czy na pewno usunąć to zdjęcie?'),
    actions: [
      {
        label: __('Usuń'),
        theme: 'red',
        variant: 'solid',
        onClick: async (close) => {
          try {
            await call('crm.api.montaz.usun_zdjecie_montazu', { deal: props.dealId, name: z.klucz })
            await zasob.reload()
            close()
          } catch (err) {
            toast.error(err?.messages?.[0] || err?.message || __('Nie udało się usunąć zdjęcia'))
          }
        },
      },
    ],
  })
}
</script>
