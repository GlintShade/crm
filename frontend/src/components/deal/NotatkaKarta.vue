<!--
  Jedna notatka w strumieniu notatek szansy (issue #200, "W2 notatki na
  szansie"). Wspólny komponent dla wszystkich ośmiu zakładek (Zestaw, Umowa,
  Kredyt, Faktury dziś; Montaż, OSD, Dotacja, Trify w kolejnych issue) -
  bezstanowy co do zakładki, dostaje gotowy wpis z `crm.api.notatki.lista`
  jako prop.

  Decyzja właściciela: BEZ edycji i BEZ kosza - pomyłka to nowa notatka pod
  spodem, nie poprawka istniejącej. Ten komponent więc celowo nie ma żadnego
  przycisku edytuj/usuń, niezależnie od `can_delete` w odpowiedzi API (to
  pole istnieje dla przyszłego użycia gdzie indziej, nie tutaj).

  `pokazZakladke` (domyślnie false) pokazuje dodatkowy chip z nazwą
  zakładki wpisu - używany dopiero przez przyszły wspólny feed "Notatki"
  (inny issue), gdzie wpisy z różnych zakładek mieszają się na jednej
  liście i trzeba je rozróżnić. Żadne z czterech wywołań w tym issue tego
  nie ustawia.
-->
<template>
  <div class="rounded-lg border border-outline-gray-1 p-4">
    <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <UserAvatar :user="wpis.owner" size="sm" />
        <span class="text-sm font-medium text-ink-gray-8">{{ autor }}</span>
        <Badge variant="subtle" theme="gray" size="sm" :label="wpis.typ || __('Notatka')" />
        <Badge
          v-if="pokazZakladke"
          variant="subtle"
          theme="orange"
          size="sm"
          :label="etykietaZakladki(wpis.zakladka)"
        />
      </div>
      <span class="shrink-0 text-xs text-ink-gray-4">{{ dataTekst }}</span>
    </div>

    <div class="prose-f text-sm text-ink-gray-8" v-html="sanitizeHTML(wpis.tekst)" />

    <div v-if="dokumenty.length" class="mt-3 flex flex-wrap gap-2">
      <AttachmentItem v-for="p in dokumenty" :key="p.name" :label="p.file_name" :url="p.file_url" />
    </div>

    <div v-if="obrazy.length" class="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
      <img
        v-for="o in obrazy"
        :key="o.name"
        :src="o.file_url"
        :alt="o.file_name"
        loading="lazy"
        class="aspect-square cursor-pointer rounded-md border border-outline-gray-2 object-cover"
        @click="otworzPodglad(o.name)"
      />
    </div>

    <AudytPodgladZdjec v-model="podgladOtwarty" :zdjecia="podgladLista" v-model:indeks="podgladIndeks" />
  </div>
</template>

<script setup>
import AttachmentItem from '@/components/AttachmentItem.vue'
import AudytPodgladZdjec from '@/components/deal/AudytPodgladZdjec.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'
import { sanitizeHTML } from '@/utils'
import { indeksDlaKlucza } from '@/utils/audytPodglad'
import { formatujTermin } from '@/utils/dataPolska'
import { etykietaZakladki, nazwaAutora, plikiDoPodgladu, podzielPliki } from '@/utils/notatki'
import { Badge } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  // Jeden wpis w kształcie zwracanym przez crm.api.notatki.lista: { name,
  // zakladka, typ, data_zdarzenia, tekst, kredyt, owner, creation,
  // autor_nazwa, pliki: [{name, file_name, file_url, file_type, file_size}] }.
  wpis: { type: Object, required: true },
  pokazZakladke: { type: Boolean, default: false },
})

const { getUser } = usersStore()

const autor = computed(() => nazwaAutora(props.wpis, getUser))
const dataTekst = computed(() => formatujTermin(props.wpis.data_zdarzenia || props.wpis.creation))

const podzial = computed(() => podzielPliki(props.wpis.pliki))
const dokumenty = computed(() => podzial.value.dokumenty)
const obrazy = computed(() => podzial.value.obrazy)

const podgladLista = computed(() => plikiDoPodgladu(obrazy.value))
const podgladOtwarty = ref(false)
const podgladIndeks = ref(0)

function otworzPodglad(nazwa) {
  const idx = indeksDlaKlucza(podgladLista.value, nazwa)
  if (idx === -1) return
  podgladIndeks.value = idx
  podgladOtwarty.value = true
}
</script>
