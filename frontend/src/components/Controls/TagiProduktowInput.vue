<template>
  <div
    class="flex min-h-[28px] w-full flex-wrap items-center gap-1 py-0.5"
  >
    <Button
      v-for="token in tokeny"
      :key="token"
      :label="token"
      theme="gray"
      variant="subtle"
      size="sm"
      class="rounded bg-surface-gray-2"
    >
      <template v-if="!readOnly" #suffix>
        <span
          class="lucide-x h-3.5 cursor-pointer"
          aria-hidden="true"
          @click.stop="usunToken(token)"
        />
      </template>
    </Button>
    <Autocomplete
      v-if="!readOnly && dostepneOpcje.length"
      class="min-w-[110px] flex-1"
      value=""
      :options="dostepneOpcjeAutocomplete"
      :placeholder="__('Dodaj') + '...'"
      @change="(o) => dodajToken(o?.value)"
    />
    <div
      v-else-if="!readOnly && !tokeny.length && !dostepneOpcje.length"
      class="text-sm text-ink-gray-4"
    >
      {{ __('Brak opcji') }}
    </div>
  </div>
</template>

<script setup>
// Kontrolka panelu bocznego dla pol "produktow leada"
// (`custom_posiadane_produkty`/`custom_produkt_procesu`, issue ops#150,
// model A+): pole Data zostaje nosnikiem (string tokenow ze slownika w
// kanonicznej kolejnosci, zlaczony "+"), a ta kontrolka pokazuje/edytuje
// je jak zbior tagow -- chipy z "x" (wzor `TableMultiselectInput.vue`) +
// dodawanie z listy opcji (Autocomplete, TYLKO wartosci ze slownika, bez
// wolnego tekstu).
//
// Kanoniczna kolejnosc/slownik NIE sa tu zaszyte (patrz `NAZWY_POL_TAGOW`
// w `utils/tagiProduktow.js` po co ten komponent w ogole istnieje): ten
// komponent dociąga je z serwera przez `crm.api.doc.get_filterable_fields`
// (ta sama funkcja, ktorej `crm.api.doc._dolacz_tagi_lead` doklada
// `options`/`volteo_tagi` dla tych dwoch pol, ops#150 pkt 3) i znajduje w
// wyniku wpis o `fieldname === props.field.fieldname`. Powod, dla ktorego
// `SidePanelLayout.vue` samo nie przekazuje juz gotowych opcji: pola
// panelu bocznego pochodza z definicji layoutu (`CRM Fields Layout`),
// ktora NIE przechodzi przez `get_filterable_fields` i wiec nie niesie
// `options` -- ten komponent jest jedynym miejscem w panelu bocznym, ktore
// musi je dociagnac osobno. Cache-klucz (`['filterableFields', doctype]`)
// jest identyczny jak w `Filter.vue`, wiec gdy oba komponenty zyja na tej
// samej stronie (panel boczny + otwarty Filtr listy), createResource
// dzieli ten sam zasob zamiast dublowac zapytanie.
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import { opcjeTagow, rozbijTagi, zlaczTagi } from '@/utils/tagiProduktow'
import { Button, createResource } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  field: { type: Object, required: true },
  value: { type: String, default: '' },
  doctype: { type: String, default: 'CRM Lead' },
})

const emit = defineEmits(['change'])

const readOnly = computed(() => Boolean(props.field?.read_only))

const polaFiltrowalne = createResource({
  url: 'crm.api.doc.get_filterable_fields',
  cache: ['filterableFields', props.doctype],
  params: { doctype: props.doctype },
  auto: true,
})

const polTagu = computed(() =>
  polaFiltrowalne.data?.find((f) => f.fieldname === props.field?.fieldname),
)

// Kanoniczna kolejnosc tokenow tego konkretnego pola (np. PV/ME/PC/...
// dla custom_posiadane_produkty, PV/PVME/ME/PC/CP dla
// custom_produkt_procesu) -- pusta dopoki `polaFiltrowalne` sie nie
// zaladuje (pierwsze renderowanie panelu), wtedy chipy nadal pokazuja
// juz zapisana wartosc (`tokeny` nizej nie zalezy od `kolejnosc`), tylko
// dodawanie nowego tagu i przycisk "Dodaj" czekaja na dane.
const kolejnosc = computed(() => opcjeTagow(polTagu.value))

const tokeny = computed(() => rozbijTagi(props.value))

const dostepneOpcje = computed(() =>
  kolejnosc.value.filter((token) => !tokeny.value.includes(token)),
)

const dostepneOpcjeAutocomplete = computed(() =>
  dostepneOpcje.value.map((token) => ({ label: token, value: token })),
)

function dodajToken(token) {
  if (!token) return
  emit('change', zlaczTagi([...tokeny.value, token], kolejnosc.value))
}

function usunToken(token) {
  emit(
    'change',
    zlaczTagi(
      tokeny.value.filter((t) => t !== token),
      kolejnosc.value,
    ),
  )
}
</script>
