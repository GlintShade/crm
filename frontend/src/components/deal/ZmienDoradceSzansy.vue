<!--
  VOLTEO (ops#336): przycisk "Doradca" w naglowku szansy z oknem "Zmien doradce".
  Zastepuje upstreamowy AssignTo, ktory dodawal tylko ToDo i nie zmienial
  `deal_owner`. Zapis przez `crm.api.szansa_doradca.zmien_doradce` (serwer
  egzekwuje role niezaleznie; klikalnosc przycisku jest tylko UX).
-->
<template>
  <button
    v-if="moze"
    type="button"
    class="flex items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-surface-gray-2"
    data-testid="naglowek-doradca"
    @click="otworz"
  >
    <span class="text-xs text-ink-gray-5">{{ __('Doradca') }}</span>
    <span class="text-ink-gray-9">{{ nazwaObecnego || __('Przypisz') }}</span>
    <span class="lucide-chevron-down size-3.5 text-ink-gray-5" aria-hidden="true" />
  </button>
  <div
    v-else
    class="flex items-center gap-2 px-1.5 py-1 text-sm"
    data-testid="naglowek-doradca"
  >
    <span class="text-xs text-ink-gray-5">{{ __('Doradca') }}</span>
    <span class="text-ink-gray-9">{{ nazwaObecnego || '-' }}</span>
  </div>

  <Dialog v-model:open="show" :title="__('Zmień doradcę')" size="sm">
    <template #default>
      <div class="flex flex-col gap-4">
        <div
          v-if="obecnyPozaLista"
          class="text-sm text-ink-gray-6"
          data-testid="doradca-obecnie"
        >
          {{ __('Obecnie: {0}', [nazwaObecnego]) }}
        </div>
        <FormControl
          type="select"
          :label="__('Doradca')"
          v-model="wybrany"
          :options="opcje"
          :disabled="doradcyResource.loading"
          :placeholder="__('Wybierz opcję')"
        />
        <ErrorMessage :message="blad" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Anuluj')" @click="show = false" />
        <Button
          variant="solid"
          :label="__('Zapisz')"
          :loading="wysylanie"
          :disabled="!wybrany || wysylanie || wybrany === props.doradca"
          @click="zapisz"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'
import { usersStore } from '@/stores/users'

const props = defineProps({
  dealId: { type: String, required: true },
  // Aktualny doradca szansy (deal_owner); pusty = brak.
  doradca: { type: String, default: '' },
})
const emit = defineEmits(['zmieniono'])

const { getUser, isVolteoAdmin, isBackend } = usersStore()

const moze = computed(() => Boolean(isVolteoAdmin() || isBackend()))
const nazwaObecnego = computed(() => {
  if (!props.doradca) return ''
  return getUser(props.doradca)?.full_name || props.doradca
})

const show = ref(false)
const wybrany = ref('')
const wysylanie = ref(false)
const blad = ref('')

const doradcyResource = createResource({
  url: 'crm.api.szansa_doradca.doradcy',
  auto: false,
})

const obecnyPozaLista = computed(
  () =>
    Boolean(props.doradca) &&
    Boolean(doradcyResource.data) &&
    !doradcyResource.data.some((d) => d.user === props.doradca),
)

const opcje = computed(() => {
  const lista = (doradcyResource.data || []).map((d) => ({
    label: d.full_name || d.user,
    value: d.user,
  }))
  return [{ label: '', value: '' }, ...lista]
})

function otworz() {
  blad.value = ''
  wybrany.value = props.doradca || ''
  show.value = true
  if (!doradcyResource.data) doradcyResource.fetch()
}

async function zapisz() {
  if (!wybrany.value || wysylanie.value) return
  wysylanie.value = true
  blad.value = ''
  try {
    await call('crm.api.szansa_doradca.zmien_doradce', {
      deal: props.dealId,
      doradca: wybrany.value,
    })
    toast.success(__('Doradca szansy zmieniony.'))
    show.value = false
    emit('zmieniono', { deal: props.dealId, doradca: wybrany.value })
  } catch (err) {
    blad.value = err.messages?.[0] || __('Nie udało się zmienić doradcy szansy.')
  } finally {
    wysylanie.value = false
  }
}
</script>
