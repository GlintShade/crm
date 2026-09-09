<!--
  VOLTEO (issue #96, dwupoziomowy przydzial CC->handlowiec): samodzielny
  przycisk "Przekaz handlowcowi" z wlasnym Dialogiem w srodku, bez
  zaleznosci od trasy ani od zadnego rodzica poza `docname` -- ten sam
  komponent ma posluzyc panelowi na mapie leadow (issue L08/#97), gdzie nie
  ma dostepu do kontekstu strony leada. Wzorzec self-contained "przycisk +
  wlasny popover/dialog" jak `AssignTo.vue`, nie modal sterowany z zewnatrz
  jak pliki w `components/Modals/`.

  Lista handlowcow idzie z `crm.api.volteo_leady.handlowcy` (dostepna dla CC
  i adminow -- inaczej niz `widoczni_uzytkownicy`, ktora daloby CC spoza
  hierarchii pusta liste), zapis przez `crm.api.volteo_leady.
  przekaz_handlowcowi`. Widocznosc SAMEGO przycisku w miejscu uzycia
  (Lead.vue: isCallCenter() || isVolteoAdmin()) jest tylko kosmetyczna (UX)
  -- serwer egzekwuje uprawnienia niezaleznie (admin/BYPASS_ROLES albo CC
  ustawiony jako custom_cc na TYM leadzie).
-->
<template>
  <Button
    :label="__('Przekaż handlowcowi')"
    icon-left="lucide-user-check"
    @click="otworz"
  />
  <Dialog v-model:open="show" :title="__('Przekaż handlowcowi')" size="sm">
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          type="select"
          :label="__('Handlowiec')"
          v-model="wybranyHandlowiec"
          :options="opcjeHandlowcow"
          :disabled="handlowcyResource.loading"
        />
        <ErrorMessage :message="blad" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Anuluj')" @click="show = false" />
        <Button
          variant="solid"
          :label="__('Przekaż')"
          :loading="wysylanie"
          :disabled="!wybranyHandlowiec || wysylanie"
          @click="przekaz"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  docname: { type: String, required: true },
})

const emit = defineEmits(['przekazano'])

const show = ref(false)
const wybranyHandlowiec = ref('')
const wysylanie = ref(false)
const blad = ref('')

const handlowcyResource = createResource({
  url: 'crm.api.volteo_leady.handlowcy',
  auto: false,
})

const opcjeHandlowcow = computed(() => {
  const lista = (handlowcyResource.data || []).map((h) => ({
    label: h.full_name || h.user,
    value: h.user,
  }))
  return [{ label: '', value: '' }, ...lista]
})

function otworz() {
  blad.value = ''
  wybranyHandlowiec.value = ''
  show.value = true
  if (!handlowcyResource.data) {
    handlowcyResource.fetch()
  }
}

async function przekaz() {
  if (!wybranyHandlowiec.value || wysylanie.value) return
  wysylanie.value = true
  blad.value = ''
  try {
    await call('crm.api.volteo_leady.przekaz_handlowcowi', {
      lead: props.docname,
      handlowiec: wybranyHandlowiec.value,
    })
    toast.success(__('Lead przekazany handlowcowi.'))
    show.value = false
    emit('przekazano', {
      docname: props.docname,
      handlowiec: wybranyHandlowiec.value,
    })
  } catch (err) {
    blad.value = err.messages?.[0] || __('Nie udało się przekazać leada handlowcowi.')
  } finally {
    wysylanie.value = false
  }
}
</script>
