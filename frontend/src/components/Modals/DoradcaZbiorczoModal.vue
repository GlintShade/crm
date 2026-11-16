<!--
  VOLTEO (ops#365): zbiorcze "Przypisz do" na liscie szans zmienia doradce
  (`deal_owner`) ta sama regula serwera co przycisk "Zmien doradce" w naglowku
  szansy. Zapis przez `crm.api.szansa_doradca.zmien_doradce_zbiorczo` (tylko
  administratorzy, serwer odmawia niezaleznie). Po akcji okno pokazuje
  podsumowanie: ile zmieniono i ktore szanse pominieto wraz z powodem.
-->
<template>
  <Dialog v-model:open="show" :title="__('Zmień doradcę')" size="sm">
    <template #default>
      <div v-if="!podsumowanie" class="flex flex-col gap-4">
        <FormControl
          type="select"
          :label="__('Doradca')"
          v-model="wybrany"
          :options="opcje"
          :disabled="doradcyResource.loading"
          :placeholder="__('Wybierz opcję')"
        />
        <p class="text-sm text-ink-gray-5">
          {{ __('Doradca zostanie zmieniony w {0} zaznaczonych szansach.', [liczba]) }}
        </p>
        <ErrorMessage :message="blad" />
      </div>
      <div v-else class="flex flex-col gap-3" data-testid="doradca-zbiorczo-podsumowanie">
        <p class="text-sm text-ink-gray-9">
          {{ __('Zmieniono doradcę w {0} szansach.', [podsumowanie.zmieniono]) }}
        </p>
        <div v-if="podsumowanie.pominieto.length" class="flex flex-col gap-1">
          <p class="text-sm text-ink-gray-7">
            {{ __('Pominięto: {0}', [podsumowanie.pominieto.length]) }}
          </p>
          <ul class="max-h-48 overflow-y-auto text-sm text-ink-gray-6">
            <li v-for="p in podsumowanie.pominieto" :key="p.deal">
              <span class="font-medium text-ink-gray-8">{{ p.deal }}</span>: {{ p.powod }}
            </li>
          </ul>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button v-if="podsumowanie" variant="solid" :label="__('Zamknij')" @click="zamknij" />
        <template v-else>
          <Button :label="__('Anuluj')" @click="show = false" />
          <Button
            variant="solid"
            :label="__('Zapisz')"
            :loading="wysylanie"
            :disabled="!wybrany || !liczba || wysylanie"
            @click="zapisz"
          />
        </template>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  selections: { type: Set, default: () => new Set() },
})
const emit = defineEmits(['reload'])
const show = defineModel({ type: Boolean, default: false })

const wybrany = ref('')
const wysylanie = ref(false)
const blad = ref('')
const podsumowanie = ref(null)

const liczba = computed(() => props.selections.size)

const doradcyResource = createResource({
  url: 'crm.api.szansa_doradca.doradcy',
  auto: false,
})

const opcje = computed(() => [
  { label: '', value: '' },
  ...(doradcyResource.data || []).map((d) => ({
    label: d.full_name || d.user,
    value: d.user,
  })),
])

watch(
  show,
  (otwarte) => {
    if (!otwarte) return
    wybrany.value = ''
    blad.value = ''
    podsumowanie.value = null
    if (!doradcyResource.data) doradcyResource.fetch()
  },
  { immediate: true },
)

async function zapisz() {
  if (!wybrany.value || wysylanie.value) return
  wysylanie.value = true
  blad.value = ''
  try {
    podsumowanie.value = await call('crm.api.szansa_doradca.zmien_doradce_zbiorczo', {
      szanse: Array.from(props.selections),
      doradca: wybrany.value,
    })
    emit('reload')
  } catch (err) {
    blad.value = err.messages?.[0] || __('Nie udało się zmienić doradcy.')
  } finally {
    wysylanie.value = false
  }
}

function zamknij() {
  show.value = false
}
</script>
