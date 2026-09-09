<!--
  VOLTEO (issue #95): masowy przydzial leadow do osoby CC z listy leadow
  (`ListBulkActions.vue`, galaz CRM Lead, tylko dla isVolteoAdmin()). Admin
  wybiera osobe CC (lista z `crm.api.volteo_leady.osoby_cc`, admin-only) i
  albo przydziela dokladnie zaznaczone wiersze, albo -- gdy zaznaczenie nie
  obejmuje wszystkich leadow pasujacych do biezacego filtra -- odhacza
  "Wszystkie pasujace do filtra (N)". N to `list.data.total_count`, ten sam
  licznik, ktorego `ViewControls.vue` uzywa dla "Export all N record(s)":
  frappe-ui "zaznacz wszystko" w liscie obejmuje tylko zaladowana strone,
  wiec to jedyne miarodajne zrodlo pelnej liczby. Filtry przy tej opcji to
  polaczenie `default_filters` (filtry widoku) i `filters` (filtry
  uzytkownika) z `list.params` -- dokladnie ten sam sposob, w jaki
  `crm.api.doc.get_data` je laczy po stronie backendu przed policzeniem
  `total_count` (`filters.update(default_filters)`), zeby N na ekranie i
  zbior faktycznie przydzielany po stronie serwera (`przydziel_cc`, ktora
  filtry przepuszcza przez `_sprawdz_filtry` i `frappe.get_list`) odpowiadaly
  sobie 1:1.

  Zapis idzie przez `crm.api.volteo_leady.przydziel_cc`: leady z JUZ
  ustawionym `custom_cc` (dowolnym) sa pomijane po stronie serwera i wracaja
  w `pominieto`, wiec ten modal nie probuje przewidywac wyniku z wyprzedzeniem
  -- pokazuje rozbicie `przydzielono/pominieto/nieznane` dopiero w tostie po
  odpowiedzi. Limit jednego wywolania to `LIMIT_PRZYDZIAL_CC` (2000) --
  ostrzegamy w tostie, gdy `N` z checkboxa przekracza limit zwrocony przez
  API, bo wtedy serwer i tak przytnie liste do pierwszych 2000 dopasowan.
-->
<template>
  <Dialog v-model:open="show" :title="__('Przypisz do CC')" size="sm">
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          type="select"
          :label="__('Osoba CC')"
          v-model="wybranyCc"
          :options="opcjeCc"
          :disabled="osobyCc.loading"
        />
        <FormControl
          v-if="pokazCheckboxWszystkie"
          type="checkbox"
          v-model="wszystkiePasujace"
          :label="__('Wszystkie pasujące do filtra ({0})', [totalCount])"
        />
        <p class="text-sm text-ink-gray-5">
          {{ __('Leady już przypisane innej osobie CC zostaną pominięte.') }}
        </p>
        <ErrorMessage :message="blad" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Anuluj')" @click="show = false" />
        <Button
          variant="solid"
          :label="__('Przypisz {0} leadów', [liczbaDoPrzydzialu])"
          :loading="wysylanie"
          :disabled="!wybranyCc || !liczbaDoPrzydzialu || wysylanie"
          @click="przydziel"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  selections: { type: Set, default: () => new Set() },
  list: { type: Object, default: null },
})

const emit = defineEmits(['reload'])

const show = defineModel({ type: Boolean, default: false })

const wybranyCc = ref('')
const wszystkiePasujace = ref(false)
const wysylanie = ref(false)
const blad = ref('')

const osobyCc = createResource({
  url: 'crm.api.volteo_leady.osoby_cc',
  auto: false,
})

const opcjeCc = computed(() => {
  const lista = (osobyCc.data || []).map((cc) => ({
    label: cc.full_name || cc.user,
    value: cc.user,
  }))
  return [{ label: '', value: '' }, ...lista]
})

const totalCount = computed(() => props.list?.data?.total_count ?? 0)

// Checkbox "wszystkie pasujace" ma sens tylko, gdy filtr obejmuje WIECEJ
// leadow niz zaznaczono recznie -- inaczej to ten sam zbior pod inna nazwa.
const pokazCheckboxWszystkie = computed(
  () => totalCount.value > props.selections.size,
)

const liczbaDoPrzydzialu = computed(() =>
  wszystkiePasujace.value ? totalCount.value : props.selections.size,
)

watch(
  () => show.value,
  (open) => {
    if (!open) return
    blad.value = ''
    wybranyCc.value = ''
    wszystkiePasujace.value = false
    if (!osobyCc.data) {
      osobyCc.fetch()
    }
  },
  { immediate: true },
)

function zbudujFiltry() {
  return {
    ...(props.list?.params?.default_filters || {}),
    ...(props.list?.params?.filters || {}),
  }
}

async function przydziel() {
  if (!wybranyCc.value || !liczbaDoPrzydzialu.value || wysylanie.value) return
  wysylanie.value = true
  blad.value = ''
  try {
    const payload = { cc: wybranyCc.value }
    if (wszystkiePasujace.value) {
      payload.filters = JSON.stringify(zbudujFiltry())
    } else {
      payload.leady = JSON.stringify(Array.from(props.selections))
    }
    const wynik = await call('crm.api.volteo_leady.przydziel_cc', payload)

    const czesci = [__('Przypisano: {0}', [wynik.przydzielono])]
    if (wynik.pominieto) {
      czesci.push(__('Pominięto (już przypisane): {0}', [wynik.pominieto]))
    }
    if (wynik.nieznane) {
      czesci.push(__('Nieznane: {0}', [wynik.nieznane]))
    }
    toast.success(czesci.join(', '))

    if (wszystkiePasujace.value && totalCount.value > wynik.limit) {
      toast.warning(
        __('Osiągnięto limit {0} leadów na jedno wywołanie, pozostałe pomiń i uruchom przydział ponownie.', [
          wynik.limit,
        ]),
      )
    }

    show.value = false
    // Wywolujacy (ListBulkActions.vue) laczy przeladowanie listy i
    // odznaczenie zaznaczonych wierszy w jednym miejscu (`reload()`), tak
    // samo jak dla EditValueModal/AssignmentModal -- ten modal nie
    // duplikuje tej logiki, tylko sygnalizuje sukces.
    emit('reload')
  } catch (err) {
    blad.value = err.messages?.[0] || __('Nie udało się przypisać leadów do CC.')
  } finally {
    wysylanie.value = false
  }
}
</script>
