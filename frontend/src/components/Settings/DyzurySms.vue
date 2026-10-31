<template>
  <div class="flex h-full flex-col gap-8 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
        {{ __('Dyżury SMS') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Po każdym nowym leadzie z Facebooka CRM wysyła SMS do osoby, która według grafiku ma teraz dyżur. Poza godzinami dyżuru SMS nie idzie, a lead zostaje w puli administracji.',
          )
        }}
      </p>
    </div>

    <ErrorMessage class="mx-2" :message="blad" />

    <template v-if="listResource.loading && !state.zaladowano">
      <div class="text-p-sm text-ink-gray-5 px-2">{{ __('Wczytywanie…') }}</div>
    </template>
    <template v-else>
      <!-- Switch + current duty -->
      <div class="flex flex-col gap-3 px-2 max-w-2xl">
        <div class="flex items-center justify-between gap-4 rounded-lg border p-4">
          <div class="flex flex-col gap-1">
            <p class="text-base-semibold">{{ __('SMS dyżurowy włączony') }}</p>
            <p class="text-p-sm text-ink-gray-6">{{ terazTekst }}</p>
          </div>
          <Switch
            :modelValue="Boolean(state.dyzurWlaczone)"
            :disabled="zapisuje"
            @update:modelValue="przelacz"
          />
        </div>
      </div>

      <!-- Weekly schedule -->
      <div class="flex flex-col gap-4 px-2 max-w-2xl">
        <div class="flex items-center justify-between">
          <div class="text-base-semibold">{{ __('Grafik tygodniowy') }}</div>
          <Button
            variant="subtle"
            size="sm"
            icon-left="plus"
            :label="__('Dodaj dyżur')"
            @click="otworzDialog(null)"
          />
        </div>
        <div class="flex flex-col rounded-lg border divide-y">
          <div v-for="dzien in DNI_TYGODNIA" :key="dzien" class="flex gap-4 p-3">
            <div class="w-28 shrink-0 text-p-base-medium text-ink-gray-8">{{ __(dzien) }}</div>
            <div class="flex flex-1 flex-col gap-1.5">
              <div v-if="!grupy[dzien].length" class="text-p-sm text-ink-gray-5">
                {{ __('Nikt nie ma dyżuru') }}
              </div>
              <div
                v-for="w in grupy[dzien]"
                :key="w.name"
                class="flex items-center justify-between gap-2"
                :class="{ 'opacity-60': !w.aktywny }"
              >
                <div class="flex items-center gap-2 text-p-sm text-ink-gray-8">
                  <UserAvatar :user="w.uzytkownik" size="sm" />
                  <span>{{ nazwa(w.uzytkownik) }}</span>
                  <span class="text-ink-gray-6"
                    >{{ formatujGodzine(w.od) }} - {{ formatujGodzine(w.do) }}</span
                  >
                  <span v-if="!w.aktywny" class="text-ink-gray-5">({{ __('wyłączony') }})</span>
                  <span v-if="brakNumeru(w.uzytkownik)" class="text-ink-gray-6">
                    {{ __('Brak numeru telefonu') }}
                  </span>
                </div>
                <div class="flex items-center gap-1">
                  <Button variant="ghost" size="sm" :label="__('Edytuj')" @click="otworzDialog(w)" />
                  <Button
                    variant="ghost"
                    size="sm"
                    theme="red"
                    :label="__('Usuń')"
                    :disabled="zapisuje"
                    @click="usun(w)"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Phone numbers -->
      <div class="flex flex-col gap-4 px-2 max-w-2xl">
        <div class="text-base-semibold">{{ __('Numery telefonów dyżurnych') }}</div>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Wpisz 9 cyfr numeru komórkowego, zapisze się jako +48. Osoba bez numeru nie dostanie SMS, a w grafiku pojawi się ostrzeżenie.') }}
        </p>
        <div class="flex flex-col gap-2">
          <div
            v-for="u in state.uzytkownicy"
            :key="u.name"
            class="flex items-center gap-3 rounded-lg border p-3"
          >
            <UserAvatar :user="u.name" size="sm" />
            <div class="w-48 shrink-0 text-p-base text-ink-gray-8">{{ u.full_name }}</div>
            <FormControl
              class="flex-1"
              type="text"
              placeholder="500 100 200"
              :modelValue="telefonDraft[u.name] ?? u.mobile_no"
              :disabled="zapisuje"
              @update:modelValue="(val) => (telefonDraft[u.name] = val)"
              @blur="zapiszTelefon(u)"
            />
          </div>
        </div>
      </div>
    </template>

    <Dialog v-model="dialog.otwarty" :options="{ title: dialog.name ? __('Edytuj dyżur') : __('Dodaj dyżur') }">
      <template #body-content>
        <div class="flex flex-col gap-4">
          <FormControl
            type="select"
            :label="__('Dzień tygodnia')"
            :options="opcjeDni"
            v-model="dialog.dzien"
          />
          <div class="grid grid-cols-2 gap-4">
            <FormControl type="text" :label="__('Od (GG:MM)')" placeholder="08:00" v-model="dialog.od" />
            <FormControl type="text" :label="__('Do (GG:MM)')" placeholder="18:00" v-model="dialog.do" />
          </div>
          <FormControl
            type="select"
            :label="__('Użytkownik')"
            :options="opcjeUzytkownikow"
            v-model="dialog.uzytkownik"
          />
          <FormControl type="checkbox" :label="__('Aktywny')" v-model="dialog.aktywny" />
          <ErrorMessage :message="dialog.blad" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="ghost" :label="__('Anuluj')" @click="dialog.otwarty = false" />
          <Button variant="solid" :label="__('Zapisz')" :loading="zapisuje" @click="zapiszDialog" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { createResource, toast, Switch, ErrorMessage, Button, FormControl, Dialog } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import {
  DNI_TYGODNIA,
  formatujGodzine,
  grupujPoDniach,
  naSekundy,
  walidujWiersz,
} from '@/utils/dyzury'

// Wszystkie klucze deklarowane z gory, tablice zawsze podmieniane na nowe
// (nigdy hasOwnProperty na reactive(), patrz CLAUDE.md).
const state = reactive({
  wiersze: [],
  uzytkownicy: [],
  dyzurWlaczone: 0,
  dyzurniTeraz: [],
  zaladowano: false,
})
const blad = ref('')
const zapisuje = ref(false)
const telefonDraft = reactive({})

const dialog = reactive({
  otwarty: false,
  name: null,
  dzien: DNI_TYGODNIA[0],
  od: '08:00',
  do: '18:00',
  uzytkownik: '',
  aktywny: true,
  blad: '',
})

const listResource = createResource({
  url: 'crm.api.dyzury.volteo_dyzury_lista',
  auto: true,
  onSuccess: (data) => {
    state.wiersze = data?.wiersze || []
    state.uzytkownicy = data?.uzytkownicy || []
    state.dyzurWlaczone = data?.dyzur_wlaczone || 0
    state.dyzurniTeraz = data?.dyzurni_teraz || []
    state.zaladowano = true
    blad.value = ''
  },
  onError: (err) => {
    blad.value = err?.messages?.[0] || __('Nie udało się wczytać grafiku dyżurów')
  },
})

const grupy = computed(() => grupujPoDniach(state.wiersze))
const opcjeDni = computed(() => DNI_TYGODNIA.map((d) => ({ label: __(d), value: d })))
const opcjeUzytkownikow = computed(() =>
  state.uzytkownicy.map((u) => ({ label: u.full_name, value: u.name })),
)

function nazwa(email) {
  return state.uzytkownicy.find((u) => u.name === email)?.full_name || email
}

function brakNumeru(email) {
  const u = state.uzytkownicy.find((x) => x.name === email)
  return Boolean(u) && !u.ma_numer
}

const terazTekst = computed(() => {
  if (!state.dyzurniTeraz.length) return __('Teraz nikt nie ma dyżuru')
  return __('Teraz dyżur: {0}', [state.dyzurniTeraz.map(nazwa).join(', ')])
})

function bladZSerwera(err, domyslny) {
  return err?.messages?.[0] || domyslny
}

function wywolaj(url, params, onSuccess, domyslnyBlad, onError) {
  zapisuje.value = true
  createResource({
    url,
    params,
    auto: true,
    onSuccess: () => {
      zapisuje.value = false
      onSuccess?.()
    },
    onError: (err) => {
      zapisuje.value = false
      const komunikat = bladZSerwera(err, domyslnyBlad)
      if (onError) onError(komunikat)
      else toast.error(komunikat)
    },
  })
}

function przelacz(val) {
  wywolaj(
    'crm.api.dyzury.volteo_dyzury_przelacznik',
    { dyzur_wlaczone: val ? 1 : 0 },
    () => {
      state.dyzurWlaczone = val ? 1 : 0
      toast.success(val ? __('SMS dyżurowy włączony') : __('SMS dyżurowy wyłączony'))
    },
    __('Nie udało się zmienić ustawienia'),
  )
}

function otworzDialog(wiersz) {
  dialog.name = wiersz?.name || null
  dialog.dzien = wiersz?.dzien_tygodnia || DNI_TYGODNIA[0]
  dialog.od = wiersz ? formatujGodzine(wiersz.od) : '08:00'
  dialog.do = wiersz ? formatujGodzine(wiersz.do) : '18:00'
  dialog.uzytkownik = wiersz?.uzytkownik || state.uzytkownicy[0]?.name || ''
  dialog.aktywny = wiersz ? Boolean(wiersz.aktywny) : true
  dialog.blad = ''
  dialog.otwarty = true
}

function zapiszDialog() {
  const komunikat = walidujWiersz(dialog.dzien, dialog.od, dialog.do)
  if (komunikat) {
    dialog.blad = komunikat
    return
  }
  if (!dialog.uzytkownik) {
    dialog.blad = __('Wybierz użytkownika.')
    return
  }
  wywolaj(
    'crm.api.dyzury.volteo_dyzur_zapisz',
    {
      name: dialog.name,
      dzien_tygodnia: dialog.dzien,
      od: naSekundy(dialog.od),
      do: naSekundy(dialog.do),
      uzytkownik: dialog.uzytkownik,
      aktywny: dialog.aktywny ? 1 : 0,
    },
    () => {
      dialog.otwarty = false
      listResource.reload()
    },
    __('Nie udało się zapisać dyżuru'),
    (msg) => (dialog.blad = msg),
  )
}

function usun(wiersz) {
  wywolaj(
    'crm.api.dyzury.volteo_dyzur_usun',
    { name: wiersz.name },
    () => listResource.reload(),
    __('Nie udało się usunąć dyżuru'),
  )
}

function zapiszTelefon(u) {
  const nowy = (telefonDraft[u.name] ?? u.mobile_no ?? '').trim()
  if (nowy === (u.mobile_no || '')) return
  wywolaj(
    'crm.api.dyzury.volteo_dyzur_telefon_zapisz',
    { uzytkownik: u.name, mobile_no: nowy },
    () => {
      delete telefonDraft[u.name]
      toast.success(__('Numer telefonu zapisany'))
      listResource.reload()
    },
    __('Nie udało się zapisać numeru'),
  )
}
</script>
