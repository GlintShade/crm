<!--
  Zakładka "Rozliczenia" na szansie (ops#282, paczka rozliczeń prowizji).
  Widoczna WYŁĄCZNIE dla isVolteoAdmin() (Deal.vue, `condition`), serwer i tak
  odrzuca innych (`crm.api.rozliczenia._wymagaj_admina`). Układ wg makiety
  E-polaczenie-B-i-C, ekran 1 i okno "Oznacz wypłacone".

  Każda mutacja zwraca świeży widok szansy (jak `dla_szansy`), a po niej
  przeładowujemy `CRM Deal` w cache dokumentów (getCachedDocumentResource),
  żeby chip w nagłówku Deal.vue pokazał nowy licznik. Brak `cache` w
  createResource (pułapka z b63: komponent montowany wielokrotnie).
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-4xl flex-col gap-4">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <div class="text-lg font-semibold text-ink-gray-8">{{ __('Rozliczenie prowizji') }}</div>
          <span
            class="rounded border border-outline-amber-3 bg-surface-amber-2 px-2 py-0.5 text-xs text-ink-amber-8"
          >
            {{ __('Tylko admin i core admin') }}
          </span>
        </div>
        <Button :label="__('Dodaj odbiorcę')" iconLeft="plus" :disabled="!wolneRole.length" @click="otworzDodanie" />
      </div>

      <div v-if="widok.loading && !dane" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="widok.error && !dane" class="py-8 text-center text-sm text-ink-red-4">
        {{ komunikatBledu(widok.error) }}
      </div>

      <template v-else-if="dane">
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
            <div class="text-xs text-ink-gray-5">{{ __('Prowizje łącznie') }}</div>
            <div class="text-xl font-semibold text-ink-gray-8">{{ zl(dane.podsumowanie.lacznie) }}</div>
          </div>
          <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
            <div class="text-xs text-ink-gray-5">{{ __('Wypłacono') }}</div>
            <div class="text-xl font-semibold text-ink-green-3">{{ zl(dane.podsumowanie.wyplacono) }}</div>
          </div>
          <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
            <div class="text-xs text-ink-gray-5">{{ __('Pozostało') }}</div>
            <div class="text-xl font-semibold text-ink-amber-8">{{ zl(dane.podsumowanie.pozostalo) }}</div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <Badge
            v-if="dane.podsumowanie.stan"
            :theme="motywStanu(dane.podsumowanie.stan)"
            variant="subtle"
            :label="
              dane.podsumowanie.licznik
                ? `${__(dane.podsumowanie.stan)} ${dane.podsumowanie.licznik}`
                : __(dane.podsumowanie.stan)
            "
          />
          <a href="#" class="text-sm text-ink-blue-link underline" @click.prevent="otworzRejestr">
            {{ __('Otwórz w rejestrze prowizji') }}
          </a>
          <span class="flex-1" />
          <Button
            variant="subtle"
            :label="__('Nalicz ze snapshotu')"
            :disabled="!dane.mozna_naliczyc"
            :loading="zajety === 'nalicz'"
            @click="naliczWiersze"
          />
          <Button
            variant="solid"
            :label="__('Oznacz wszystkie jako wypłacone')"
            :disabled="!doWyplaty.length"
            @click="otworzWyplate(doWyplaty)"
          />
        </div>

        <div
          v-if="!dane.wiersze.length"
          class="rounded-lg border border-outline-gray-2 py-10 text-center text-sm text-ink-gray-5"
        >
          {{ __('Brak odbiorców. Kliknij Nalicz ze snapshotu albo Dodaj odbiorcę.') }}
        </div>
        <div v-else class="overflow-x-auto rounded-lg border border-outline-gray-2">
          <table class="w-full table-fixed border-collapse text-sm">
            <colgroup>
              <col style="width: 17%" />
              <col style="width: 11%" />
              <col style="width: 13%" />
              <col style="width: 13%" />
              <col style="width: 11%" />
              <col style="width: 14%" />
              <col style="width: 6%" />
              <col style="width: 15%" />
            </colgroup>
            <thead>
              <tr class="bg-surface-gray-2 text-ink-gray-5">
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Odbiorca') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Rola') }}</th>
                <th class="px-3 py-2.5 text-right font-medium">{{ __('Kwota') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Status') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Data') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Oznaczył') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Potw.') }}</th>
                <th class="px-3 py-2.5 text-left font-medium">{{ __('Akcje') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="w in dane.wiersze"
                :key="w.name"
                class="border-t border-outline-gray-1"
                :title="w.uwaga || ''"
              >
                <td class="truncate whitespace-nowrap px-3 py-2.5 text-ink-gray-8">
                  {{ w.odbiorca_nazwa || '-' }}
                </td>
                <td class="truncate whitespace-nowrap px-3 py-2.5 text-ink-gray-6">{{ __(w.rola) }}</td>
                <td class="px-3 py-2">
                  <input
                    v-if="w.status !== STATUS_WYPLACONE"
                    type="number"
                    step="0.01"
                    min="0"
                    class="w-full rounded border border-outline-gray-2 bg-surface-base px-2 py-1 text-right text-sm text-ink-gray-8"
                    :value="kwotaEdycji[w.name] ?? w.kwota"
                    @input="kwotaEdycji[w.name] = $event.target.value"
                    @blur="zapiszKwote(w)"
                    @keydown.enter="$event.target.blur()"
                  />
                  <div v-else class="truncate whitespace-nowrap text-right text-ink-gray-8">{{ zl(w.kwota) }}</div>
                </td>
                <td class="truncate whitespace-nowrap px-3 py-2.5">
                  <Badge :theme="motywWiersza(w.status)" variant="subtle" size="sm" :label="__(w.status)" />
                </td>
                <td class="truncate whitespace-nowrap px-3 py-2.5 text-ink-gray-6">
                  {{ w.data_wyplaty || '-' }}
                </td>
                <td class="truncate whitespace-nowrap px-3 py-2.5 text-ink-gray-6">
                  {{ w.oznaczyl ? nazwaUzytkownika(w.oznaczyl) : '-' }}
                </td>
                <td class="px-3 py-2.5">
                  <a
                    v-if="w.potwierdzenie"
                    :href="w.potwierdzenie"
                    target="_blank"
                    rel="noopener"
                    class="text-ink-blue-link underline"
                    :title="nazwaPliku(w.potwierdzenie)"
                  >
                    {{ __('Plik') }}
                  </a>
                  <FileUploader
                    v-else
                    :upload-args="{
                      doctype: 'Volteo Rozliczenie',
                      docname: w.name,
                      fieldname: 'potwierdzenie',
                      private: true,
                    }"
                    @success="odswiez"
                    @failure="() => toast.error(__('Nie udało się wysłać pliku.'))"
                  >
                    <template #default="{ openFileSelector, uploading }">
                      <button
                        type="button"
                        class="text-ink-blue-link"
                        :disabled="uploading"
                        :title="__('Dodaj potwierdzenie')"
                        @click="openFileSelector"
                      >
                        {{ uploading ? '…' : '+' }}
                      </button>
                    </template>
                  </FileUploader>
                </td>
                <td class="px-3 py-2">
                  <div class="flex items-center gap-1">
                    <Button
                      v-if="w.status === STATUS_WYPLACONE"
                      size="sm"
                      :label="__('Cofnij')"
                      @click="pytanie = { typ: 'cofnij', wiersz: w }"
                    />
                    <Button
                      v-else
                      size="sm"
                      variant="solid"
                      :label="__('Wypłacone')"
                      :disabled="w.status !== STATUS_DO_WYPLATY"
                      @click="otworzWyplate([w])"
                    />
                    <Dropdown v-if="w.status !== STATUS_WYPLACONE" :options="menuWiersza(w)" placement="right">
                      <Button size="sm" variant="ghost" icon="more-horizontal" />
                    </Dropdown>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <div class="mb-2 text-sm font-medium text-ink-gray-7">{{ __('Historia') }}</div>
          <div v-if="!dane.historia.length" class="text-sm text-ink-gray-5">{{ __('Brak wpisów.') }}</div>
          <div v-else class="flex flex-col gap-2 border-l-2 border-outline-gray-2 pl-3">
            <div v-for="(h, i) in dane.historia" :key="i" class="text-sm text-ink-gray-8">
              <div class="text-xs text-ink-gray-5">{{ h.kiedy }}</div>
              {{ h.tekst }}
            </div>
          </div>
        </div>

        <div
          class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
        >
          {{ __('Tylko admin i core admin: zakładka jest niewidoczna dla handlowca i backoffice. Rozliczenie nie zmienia etapu procesu.') }}
        </div>
      </template>
    </div>

    <!-- Okno: Oznacz wypłacone -->
    <Dialog v-model:open="wyplata.otwarte" :title="tytulWyplaty" size="sm">
      <template #default>
        <div class="flex flex-col gap-3">
          <FormControl type="text" :label="__('Kwota')" :model-value="kwotaWyplaty" disabled />
          <FormControl type="date" :label="__('Data wypłaty')" v-model="wyplata.data" />
          <FormControl type="textarea" :label="__('Uwaga')" :rows="2" v-model="wyplata.uwaga" />
          <div class="text-xs text-ink-gray-5">
            {{ __('Potwierdzenie (PDF, JPG) dodasz po zapisie, plusem w kolumnie Potw.') }}
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="wyplata.otwarte = false" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            :loading="zajety === 'wyplata'"
            :disabled="!wyplata.data"
            @click="zapiszWyplate"
          />
        </div>
      </template>
    </Dialog>

    <!-- Okno: Dodaj odbiorcę -->
    <Dialog v-model:open="dodanie.otwarte" :title="__('Dodaj odbiorcę')" size="sm">
      <template #default>
        <div class="flex flex-col gap-3">
          <FormControl type="select" :label="__('Rola')" :options="opcjeRol" v-model="dodanie.rola" />
          <div>
            <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Odbiorca') }}</div>
            <Link doctype="User" v-model="dodanie.odbiorca" :hide-me="true" />
          </div>
          <FormControl type="number" :label="__('Kwota')" step="0.01" min="0" v-model="dodanie.kwota" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="dodanie.otwarte = false" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            :loading="zajety === 'dodaj'"
            :disabled="!dodanie.rola || dodanie.kwota === '' || dodanie.kwota === null"
            @click="zapiszDodanie"
          />
        </div>
      </template>
    </Dialog>

    <!-- Potwierdzenie: Cofnij / Usuń -->
    <Dialog v-model:open="pytanieOtwarte" :title="tytulPytania" size="sm">
      <template #default>
        <div class="text-sm text-ink-gray-7">{{ trescPytania }}</div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="pytanie = null" />
          <Button
            :label="pytanie?.typ === 'usun' ? __('Usuń') : __('Cofnij wypłatę')"
            variant="solid"
            theme="red"
            :loading="zajety === 'pytanie'"
            @click="wykonajPytanie"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { formatPln } from '@/utils/money'
import {
  Badge,
  Button,
  Dialog,
  Dropdown,
  FileUploader,
  FormControl,
  call,
  createResource,
  getCachedDocumentResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  dealId: { type: String, required: true },
})

const STATUS_DO_WYPLATY = 'Do wypłaty'
const STATUS_WYPLACONE = 'Wypłacone'
const STATUS_WSTRZYMANE = 'Wstrzymane'
const STATUS_NIE_DOTYCZY = 'Nie dotyczy'
const ROLE = ['Handlowiec', 'Manager', 'Partner']
const API = 'crm.api.rozliczenia.'

const router = useRouter()
const { getUser } = usersStore()

const dane = ref(null)
const zajety = ref('')
const kwotaEdycji = reactive({})

// Bez `cache`: komponent bywa montowany wielokrotnie (pułapka z b63).
const widok = createResource({
  url: API + 'dla_szansy',
  params: { deal: props.dealId },
  auto: true,
  onSuccess: (d) => (dane.value = d),
})

const doWyplaty = computed(() => (dane.value?.wiersze || []).filter((w) => w.status === STATUS_DO_WYPLATY))
const wolneRole = computed(() => {
  const mamy = new Set((dane.value?.wiersze || []).map((w) => w.rola))
  return ROLE.filter((r) => !mamy.has(r))
})
const opcjeRol = computed(() => wolneRole.value.map((r) => ({ label: __(r), value: r })))

function zl(v) {
  return formatPln(Number(v) || 0)
}

function nazwaUzytkownika(email) {
  return getUser(email)?.full_name || email
}

function nazwaPliku(url) {
  return decodeURIComponent(String(url).split('/').pop() || '')
}

function motywWiersza(status) {
  return { [STATUS_WYPLACONE]: 'green', [STATUS_DO_WYPLATY]: 'orange', [STATUS_WSTRZYMANE]: 'red' }[status] || 'gray'
}

function motywStanu(stan) {
  return { Rozliczone: 'green', 'Częściowo rozliczone': 'orange', Wstrzymane: 'red' }[stan] || 'gray'
}

function komunikatBledu(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err?._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs?.length) return JSON.parse(msgs[0]).message || __('Wystąpił błąd, spróbuj ponownie')
    }
    if (err?.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd, spróbuj ponownie')
    }
    if (err?.message) return err.message
  } catch (e) {
    /* spadamy do domyślnego komunikatu */
  }
  return __('Wystąpił błąd, spróbuj ponownie')
}

// Przeładowanie dokumentu szansy w cache, z którego Deal.vue czyta licznik chipu.
async function przeladujSzanse() {
  try {
    await getCachedDocumentResource('CRM Deal', props.dealId)?.reload()
  } catch (e) {
    /* chip odświeży się przy następnym wczytaniu szansy */
  }
}

async function odswiez() {
  try {
    dane.value = await call(API + 'dla_szansy', { deal: props.dealId })
  } catch (err) {
    toast.error(komunikatBledu(err))
  }
  await przeladujSzanse()
}

// Wywołanie mutacji zwracającej świeży widok szansy.
async function mutuj(klucz, metoda, argumenty, komunikat) {
  zajety.value = klucz
  try {
    const wynik = await call(API + metoda, argumenty)
    if (wynik && wynik.wiersze) dane.value = wynik
    else await odswiez()
    if (komunikat) toast.success(komunikat)
    await przeladujSzanse()
    return true
  } catch (err) {
    toast.error(komunikatBledu(err))
    return false
  } finally {
    zajety.value = ''
  }
}

function naliczWiersze() {
  return mutuj('nalicz', 'nalicz', { deal: props.dealId }, __('Naliczono odbiorców.'))
}

function otworzRejestr() {
  router.push({ name: 'RozliczeniaProwizji', query: { szansa: props.dealId } }).catch(() => {
    router.push({ path: '/rozliczenia-prowizji', query: { szansa: props.dealId } })
  })
}

async function zapiszKwote(w) {
  const wpisana = kwotaEdycji[w.name]
  delete kwotaEdycji[w.name]
  if (wpisana === undefined || String(wpisana).trim() === '') return
  if (Number(wpisana) === Number(w.kwota)) return
  await mutuj('kwota', 'zmien_kwote', { nazwa: w.name, kwota: String(wpisana) }, __('Zmieniono kwotę.'))
}

// --- Oznacz wypłacone ---
const wyplata = reactive({ otwarte: false, wiersze: [], data: '', uwaga: '' })

function dzisiaj() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function otworzWyplate(wiersze) {
  if (!wiersze.length) return
  wyplata.wiersze = wiersze
  wyplata.data = dzisiaj()
  wyplata.uwaga = ''
  wyplata.otwarte = true
}

const tytulWyplaty = computed(() => {
  const w = wyplata.wiersze
  if (w.length === 1) {
    const nazwa = w[0].odbiorca_nazwa
    return `${__('Oznacz wypłacone')}: ${__(w[0].rola)}${nazwa ? ', ' + nazwa : ''}`
  }
  return `${__('Oznacz wypłacone')}: ${w.length}`
})

const kwotaWyplaty = computed(() =>
  zl(wyplata.wiersze.reduce((suma, w) => suma + (Number(w.kwota) || 0), 0)),
)

async function zapiszWyplate() {
  zajety.value = 'wyplata'
  try {
    await call(API + 'oznacz_wyplacone', {
      nazwy: wyplata.wiersze.map((w) => w.name),
      data_wyplaty: wyplata.data,
      uwaga: wyplata.uwaga || '',
    })
    wyplata.otwarte = false
    toast.success(__('Oznaczono jako wypłacone.'))
    await odswiez()
  } catch (err) {
    toast.error(komunikatBledu(err))
  } finally {
    zajety.value = ''
  }
}

// --- Dodaj odbiorcę ---
const dodanie = reactive({ otwarte: false, rola: '', odbiorca: '', kwota: '' })

function otworzDodanie() {
  dodanie.rola = wolneRole.value[0] || ''
  dodanie.odbiorca = ''
  dodanie.kwota = ''
  dodanie.otwarte = true
}

async function zapiszDodanie() {
  const ok = await mutuj(
    'dodaj',
    'dodaj_odbiorce',
    {
      deal: props.dealId,
      rola: dodanie.rola,
      odbiorca: dodanie.odbiorca || null,
      kwota: String(dodanie.kwota),
    },
    __('Dodano odbiorcę.'),
  )
  if (ok) dodanie.otwarte = false
}

// --- Menu "..." oraz potwierdzenia ---
function menuWiersza(w) {
  const ustaw = (status) => () =>
    mutuj('status', 'ustaw_status', { nazwa: w.name, status }, __('Zmieniono status.'))
  const opcje = []
  if (w.status !== STATUS_DO_WYPLATY) opcje.push({ label: __('Do wypłaty'), onClick: ustaw(STATUS_DO_WYPLATY) })
  if (w.status !== STATUS_WSTRZYMANE) opcje.push({ label: __('Wstrzymaj'), onClick: ustaw(STATUS_WSTRZYMANE) })
  if (w.status !== STATUS_NIE_DOTYCZY) opcje.push({ label: __('Nie dotyczy'), onClick: ustaw(STATUS_NIE_DOTYCZY) })
  opcje.push({ label: __('Usuń'), onClick: () => (pytanie.value = { typ: 'usun', wiersz: w }) })
  return opcje
}

const pytanie = ref(null)
const pytanieOtwarte = computed({
  get: () => !!pytanie.value,
  set: (v) => {
    if (!v) pytanie.value = null
  },
})
const tytulPytania = computed(() => (pytanie.value?.typ === 'usun' ? __('Usunąć odbiorcę?') : __('Cofnąć wypłatę?')))
const trescPytania = computed(() => {
  const w = pytanie.value?.wiersz
  if (!w) return ''
  const kto = `${__(w.rola)}${w.odbiorca_nazwa ? ', ' + w.odbiorca_nazwa : ''} (${zl(w.kwota)})`
  return pytanie.value.typ === 'usun'
    ? `${__('Wiersz zostanie usunięty:')} ${kto}`
    : `${__('Wiersz wróci do statusu Do wypłaty:')} ${kto}`
})

async function wykonajPytanie() {
  const { typ, wiersz } = pytanie.value
  zajety.value = 'pytanie'
  const ok =
    typ === 'usun'
      ? await mutuj('pytanie', 'usun_odbiorce', { nazwa: wiersz.name }, __('Usunięto odbiorcę.'))
      : await mutuj('pytanie', 'cofnij', { nazwa: wiersz.name }, __('Cofnięto wypłatę.'))
  if (ok) pytanie.value = null
}
</script>
