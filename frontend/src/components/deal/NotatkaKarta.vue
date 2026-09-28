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
  zakładki wpisu - używany przez wspólny feed "Notatki" (issue ops#201),
  gdzie wpisy z różnych zakładek/źródeł mieszają się na jednej liście i
  trzeba je rozróżnić. Żadne z czterech wywołań na samych zakładkach
  (Zestaw/Umowa/Kredyt/Faktury) tego nie ustawia.

  `ikonaZakladki` (opcjonalny komponent) i `etykietaZakladkiOverride`
  (opcjonalny string) pozwalają wywołującemu nadpisać ikonę/etykietę chipu
  zakładki zamiast wyliczania jej z `etykietaZakladki(wpis.zakladka)` - feed
  potrzebuje TEGO, bo jego wpisy mają pole `zakladka` ustawione na klucz
  `zrodlo` (który obejmuje też "Audyt"/"AudytCP", spoza ośmiu zakładek
  `Volteo Notatka`, i backend już policzył dla nich `zrodlo_etykieta`), a
  ikona źródła (Zestaw/Umowa/.../Audyt) nie ma żadnego odpowiednika na
  samym wpisie. Bez override chip zachowuje się identycznie jak dotąd.

  `tylkoGodzina` (domyślnie false) pokazuje w prawym górnym rogu wyłącznie
  godzinę 24h (np. "17:00") zamiast pełnej daty z `formatujTermin` - feed
  włącza to, bo dzień jest tam już pokazany raz, w nagłówku grupy dnia
  (`grupujPoDniu` w utils/notatki.js); pokazywanie pełnej daty na KAŻDEJ
  karcie pod nagłówkiem "Dziś" byłoby zwykłą powtórką.
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
          :label="etykietaChipu"
        >
          <template v-if="ikonaZakladki" #prefix>
            <component :is="ikonaZakladki" class="h-2.5 w-2.5" />
          </template>
        </Badge>
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
  ikonaZakladki: { type: [Object, Function], default: null },
  etykietaZakladkiOverride: { type: String, default: '' },
  tylkoGodzina: { type: Boolean, default: false },
})

const { getUser } = usersStore()

const autor = computed(() => nazwaAutora(props.wpis, getUser))
const etykietaChipu = computed(
  () => props.etykietaZakladkiOverride || etykietaZakladki(props.wpis.zakladka),
)

// Wyciąga wyłącznie "HH:mm" z surowego Datetime Frappe ("YYYY-MM-DD
// HH:mm[:ss]") - celowo NIE przez `new Date(string)` (interpretacja jako
// UTC przesunęłaby godzinę), sam koniec stringa wystarcza, bez potrzeby
// pełnego parsowania jak w `formatujTermin`.
function godzinaZTekstu(dataCzas) {
  if (!dataCzas) return ''
  // Ułamek sekundy w `(?:\.\d+)?` lustrzany w WZORZEC_DATY_CZASU dataPolska.js.
  const dopasowanie = /(\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/.exec(String(dataCzas).trim())
  return dopasowanie ? `${dopasowanie[1]}:${dopasowanie[2]}` : ''
}

const dataTekst = computed(() => {
  const surowa = props.wpis.data_zdarzenia || props.wpis.creation
  return props.tylkoGodzina ? godzinaZTekstu(surowa) : formatujTermin(surowa)
})

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
