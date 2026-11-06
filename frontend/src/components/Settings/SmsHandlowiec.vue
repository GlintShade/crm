<template>
  <div class="flex h-full flex-col gap-8 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
        {{ __('SMS do handlowców') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Gdy ktoś umówi handlowcowi spotkanie, zmieni jego termin albo je odwoła, CRM wysyła handlowcowi SMS. Token SMSAPI, nadawca i tryb testowy są wspólne z SMS powitalnym i dyżurowym.',
          )
        }}
      </p>
    </div>

    <ErrorMessage class="mx-2" :message="blad" />

    <template v-if="listResource.loading && !state.zaladowano">
      <div class="text-p-sm text-ink-gray-5 px-2">{{ __('Wczytywanie…') }}</div>
    </template>
    <template v-else-if="state.zaladowano">
      <!-- Switches and status -->
      <div class="flex flex-col gap-3 px-2 max-w-2xl">
        <div
          class="flex items-center justify-between gap-4 rounded-lg border p-4"
        >
          <div class="flex flex-col gap-1">
            <p class="text-base-semibold">
              {{ __('SMS do handlowców włączony') }}
            </p>
            <p class="text-p-sm text-ink-gray-6">
              {{
                __(
                  'Handlowiec dostaje SMS o nowym spotkaniu i o zmianie terminu. Spotkania umówione przed włączeniem nie dostają SMS wstecz.',
                )
              }}
            </p>
          </div>
          <Switch
            :modelValue="Boolean(state.wlaczone)"
            :disabled="zapisuje"
            @update:modelValue="(val) => przelacz('handlowiec_wlaczone', val)"
          />
        </div>
        <div
          class="flex items-center justify-between gap-4 rounded-lg border p-4"
        >
          <div class="flex flex-col gap-1">
            <p class="text-base-semibold">
              {{ __('SMS o odwołaniu spotkania') }}
            </p>
            <p class="text-p-sm text-ink-gray-6">
              {{
                __(
                  'Poprzedni handlowiec dostaje SMS, gdy spotkanie zostanie odwołane albo przekazane innej osobie. Działa tylko przy włączonym SMS do handlowców.',
                )
              }}
            </p>
          </div>
          <Switch
            :modelValue="Boolean(state.odwolanieWlaczone)"
            :disabled="zapisuje"
            @update:modelValue="
              (val) => przelacz('handlowiec_odwolanie_wlaczone', val)
            "
          />
        </div>
        <div
          class="flex flex-col gap-1 rounded-lg border p-4 text-p-sm text-ink-gray-6"
        >
          <p v-if="state.tokenUstawiony">
            {{ __('Token SMSAPI: ustawiony.') }}
          </p>
          <p v-else class="text-ink-red-6">
            {{
              __(
                'Token SMSAPI: brak. Uzupełnij go w Desk, Volteo SMS Ustawienia (ten sam token co dla SMS powitalnego).',
              )
            }}
          </p>
          <p v-if="state.trybTestowy">
            {{
              __(
                'Tryb testowy SMSAPI włączony: żaden SMS nie wychodzi do sieci.',
              )
            }}
          </p>
          <p v-else>
            {{ __('Tryb testowy SMSAPI wyłączony: SMS-y wychodzą naprawdę.') }}
          </p>
          <p v-if="ciszaTekst">{{ ciszaTekst }}</p>
        </div>
      </div>

      <!-- Templates and daily limit -->
      <div class="flex flex-col gap-4 px-2 max-w-2xl">
        <div class="text-base-semibold">
          {{ __('Treści SMS do handlowców') }}
        </div>
        <div class="flex flex-col gap-1 text-p-sm text-ink-gray-6">
          <p>{{ __('Pola do wstawienia w treść:') }} {{ placeholderyTekst }}</p>
          <p>
            {{
              __(
                'Polskie znaki zamieniane na łacińskie, 160 miejsc GSM-7 to jedna część SMS. Podgląd pokazuje przykładowe dane.',
              )
            }}
          </p>
        </div>

        <div
          v-for="s in SZABLONY"
          :key="s.typ"
          class="flex flex-col gap-2 rounded-lg border p-4"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="text-p-base-medium">{{ __(s.etykieta) }}</div>
            <Button
              variant="ghost"
              size="sm"
              :label="__('Przywróć treść domyślną')"
              :disabled="
                zapisuje ||
                !state.domyslne[s.pole] ||
                formularz[s.pole] === state.domyslne[s.pole]
              "
              @click="zmienTresc(s, state.domyslne[s.pole])"
            />
          </div>
          <FormControl
            type="textarea"
            :rows="3"
            :modelValue="formularz[s.pole]"
            :disabled="zapisuje"
            @update:modelValue="(val) => zmienTresc(s, val)"
          />
          <div class="flex flex-col gap-1">
            <p class="text-p-sm text-ink-gray-6">{{ __('Podgląd SMS') }}</p>
            <div
              class="rounded-lg border p-3 text-p-base text-ink-gray-8 break-words"
            >
              {{ podglady[s.typ].tresc || '…' }}
            </div>
            <p class="text-p-sm text-ink-gray-6">
              {{ opisCzesci(podglady[s.typ].dlugosc, podglady[s.typ].czesci) }}
            </p>
            <p v-if="ostrzezenie(s.typ)" class="text-p-sm text-ink-amber-8">
              {{ ostrzezenie(s.typ) }}
            </p>
            <ErrorMessage :message="podglady[s.typ].blad" />
          </div>
        </div>

        <div class="flex flex-col gap-1">
          <FormControl
            class="w-32"
            type="number"
            min="0"
            max="1000"
            :label="__('Limit dzienny SMS do handlowców')"
            :modelValue="formularz.limit_dzienny_handlowiec"
            :disabled="zapisuje"
            @update:modelValue="zmienLimit"
          />
          <p class="text-p-sm text-ink-gray-6">{{ __('0 blokuje wysyłkę') }}</p>
          <p class="text-p-sm text-ink-gray-6">{{ licznikTekst }}</p>
        </div>
        <ErrorMessage :message="bladZapisu" />
        <div class="flex items-center gap-2">
          <Button
            variant="solid"
            :label="__('Zapisz treści i limit')"
            :loading="zapisuje"
            :disabled="!zmienione"
            @click="zapiszUstawienia"
          />
          <Button
            v-if="zmienione"
            variant="ghost"
            :label="__('Cofnij zmiany')"
            :disabled="zapisuje"
            @click="cofnijZmiany"
          />
        </div>
      </div>

      <!-- Test SMS -->
      <div class="flex flex-col gap-3 px-2 max-w-2xl">
        <div class="text-base-semibold">
          {{ __('SMS testowy do handlowca') }}
        </div>
        <div class="flex flex-wrap items-end gap-2">
          <FormControl
            v-model="test.typ"
            class="w-72"
            type="select"
            :label="__('Którą treść wysłać')"
            :options="opcjeTestu"
          />
          <Button
            variant="subtle"
            :label="__('Wyślij SMS testowy do mnie')"
            :loading="test.wysyla"
            :disabled="
              !state.tokenUstawiony || test.wysyla || zapisuje || zmienione
            "
            @click="wyslijTestowy"
          />
        </div>
        <p v-if="zmienione" class="text-p-sm text-ink-amber-8">
          {{
            __(
              'Masz niezapisane zmiany. SMS testowy wysyła zapisaną treść, więc najpierw zapisz albo cofnij zmiany.',
            )
          }}
        </p>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Wysyła zapisaną treść z przykładowymi danymi na numer zapisany przy Twoim koncie. Liczy się do limitu dziennego, cisza nocna go nie wstrzymuje.',
            )
          }}
        </p>
        <p
          v-if="test.wynik"
          class="text-p-sm"
          :class="test.wynikOk ? 'text-ink-gray-8' : 'text-ink-red-6'"
        >
          {{ test.wynik }}
        </p>
      </div>

      <!-- Rep phone numbers -->
      <div class="flex flex-col gap-4 px-2 max-w-2xl">
        <div class="text-base-semibold">{{ __('Numery handlowców') }}</div>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Numer z profilu użytkownika (pole Mobile No). Handlowiec bez poprawnego numeru nie dostanie SMS, a w Aktywności leada pojawi się wpis o pominięciu. Wpisz 9 cyfr numeru komórkowego, zapisze się jako +48.',
            )
          }}
        </p>
        <p
          v-if="state.handlowcy.length"
          class="text-p-sm"
          :class="bezNumeru ? 'text-ink-red-6' : 'text-ink-gray-6'"
        >
          {{
            __('Bez poprawnego numeru: {0} z {1} handlowców.', [
              bezNumeru,
              state.handlowcy.length,
            ])
          }}
        </p>
        <div
          v-if="!state.handlowcy.length"
          class="rounded-lg border p-3 text-p-sm text-ink-gray-5"
        >
          {{ __('Brak aktywnych kont z rolą handlowca (Volteo D2D Sales).') }}
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="h in state.handlowcy"
            :key="h.uzytkownik"
            class="flex flex-col gap-1 rounded-lg border p-3"
          >
            <div class="flex items-center gap-3">
              <UserAvatar :user="h.uzytkownik" size="sm" />
              <div class="flex w-48 shrink-0 flex-col">
                <span class="text-p-base text-ink-gray-8 truncate">{{
                  h.imie_nazwisko
                }}</span>
                <span v-if="!h.linia_leady" class="text-p-xs text-ink-gray-5">
                  {{ __('bez linii Leady') }}
                </span>
              </div>
              <FormControl
                class="flex-1"
                type="text"
                placeholder="500 100 200"
                :modelValue="telefonDraft[h.uzytkownik] ?? h.mobile_no"
                :disabled="Boolean(telefonZapisuje[h.uzytkownik])"
                @update:modelValue="(val) => zmienTelefon(h, val)"
              />
              <Badge
                v-if="stanNumeru(h).kod === 'brak'"
                variant="subtle"
                theme="red"
                :label="__('Brak numeru')"
              />
              <Badge
                v-else-if="stanNumeru(h).kod === 'niepoprawny'"
                variant="subtle"
                theme="red"
                :label="__('Niepoprawny numer')"
              />
              <Button
                variant="subtle"
                size="sm"
                :label="__('Zapisz')"
                :loading="Boolean(telefonZapisuje[h.uzytkownik])"
                :disabled="!telefonZmieniony(h)"
                @click="zapiszTelefon(h)"
              />
            </div>
            <ErrorMessage :message="telefonBlad[h.uzytkownik]" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import {
  createResource,
  toast,
  Switch,
  ErrorMessage,
  Button,
  FormControl,
  Badge,
} from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import {
  SZABLONY,
  POLE_LIMITU,
  formularzZeStanu,
  zmienionePola,
  czySaZmiany,
  walidujSzablon,
  walidujLimit,
  sortujHandlowcow,
  stanNumeru,
  liczBezNumeru,
  opisCzesci,
  ostrzezenieCzesci,
  opisCiszyNocnej,
  opisLicznikaDnia,
  listaPlaceholderow,
  wynikTestu,
  komunikatBledu,
} from '@/utils/smsHandlowiec'

const API = 'crm.api.sms_handlowiec_panel.'

// Wszystkie klucze deklarowane z gory, tablice i obiekty zawsze podmieniane na nowe
// (nigdy hasOwnProperty na reactive(), patrz CLAUDE.md).
const state = reactive({
  wlaczone: 0,
  odwolanieWlaczone: 0,
  trybTestowy: 0,
  tokenUstawiony: false,
  wyslaneDzis: null,
  limit: 0,
  ciszaOd: '',
  ciszaDo: '',
  placeholdery: [],
  przyklady: {},
  domyslne: {},
  handlowcy: [],
  zapisane: formularzZeStanu(null),
  zaladowano: false,
})
const formularz = reactive(formularzZeStanu(null))
const podglady = reactive(
  Object.fromEntries(
    SZABLONY.map((s) => [
      s.typ,
      { tresc: '', dlugosc: 0, czesci: 1, ostrzezenie: '', blad: '' },
    ]),
  ),
)
const podgladTimery = {}
const podgladNr = Object.fromEntries(SZABLONY.map((s) => [s.typ, 0]))
const blad = ref('')
const bladZapisu = ref('')
const zapisuje = ref(false)
const test = reactive({
  typ: SZABLONY[0].typ,
  wysyla: false,
  wynik: '',
  wynikOk: true,
})
const telefonDraft = reactive({})
const telefonBlad = reactive({})
const telefonZapisuje = reactive({})

const zmienione = computed(() => czySaZmiany(formularz, state.zapisane))
const ciszaTekst = computed(() => opisCiszyNocnej(state.ciszaOd, state.ciszaDo))
const licznikTekst = computed(() =>
  opisLicznikaDnia(state.wyslaneDzis, state.limit),
)
const placeholderyTekst = computed(() =>
  listaPlaceholderow(state.placeholdery, state.przyklady).join(', '),
)
const bezNumeru = computed(() => liczBezNumeru(state.handlowcy))
const opcjeTestu = computed(() =>
  SZABLONY.map((s) => ({ label: __(s.etykieta), value: s.typ })),
)

// Stan z API. Pole formularza bez niezapisanej zmiany przejmuje wartosc z serwera,
// pole edytowane zostaje (chyba ze jest w `nadpisz`, czyli wlasnie zapisane).
function zastosujStan(data, nadpisz = []) {
  const stareZapisane = state.zapisane
  const noweZapisane = formularzZeStanu(data)
  const doPodgladu = []
  for (const [pole, wartosc] of Object.entries(noweZapisane)) {
    const bezZmian =
      String(formularz[pole] ?? '') === String(stareZapisane[pole] ?? '')
    if (!state.zaladowano || bezZmian || nadpisz.includes(pole)) {
      if (String(formularz[pole] ?? '') !== String(wartosc ?? ''))
        doPodgladu.push(pole)
      formularz[pole] = wartosc
    }
  }
  state.zapisane = noweZapisane
  state.wlaczone = data?.handlowiec_wlaczone ? 1 : 0
  state.odwolanieWlaczone = data?.handlowiec_odwolanie_wlaczone ? 1 : 0
  state.trybTestowy = data?.tryb_testowy ? 1 : 0
  state.tokenUstawiony = Boolean(data?.token_ustawiony)
  state.wyslaneDzis = data?.wyslane_dzis ?? null
  state.limit = data?.[POLE_LIMITU] ?? 0
  state.ciszaOd = data?.cisza_od || ''
  state.ciszaDo = data?.cisza_do || ''
  state.placeholdery = [...(data?.placeholdery || [])]
  state.przyklady = { ...(data?.dane_przykladowe || {}) }
  state.domyslne = { ...(data?.tresci_domyslne || {}) }
  state.handlowcy = sortujHandlowcow(data?.handlowcy)
  const pierwszy = !state.zaladowano
  state.zaladowano = true
  for (const s of SZABLONY) {
    if (pierwszy || doPodgladu.includes(s.pole)) odswiezPodglad(s)
  }
}

const listResource = createResource({
  url: API + 'volteo_sms_handlowiec_lista',
  auto: true,
  onSuccess: (data) => {
    zastosujStan(data)
    blad.value = ''
  },
  onError: (err) => {
    blad.value = komunikatBledu(
      err,
      __('Nie udało się wczytać ustawień SMS do handlowców'),
    )
  },
})

function odswiezPodglad(s) {
  const nr = ++podgladNr[s.typ]
  createResource({
    url: API + 'volteo_sms_handlowiec_podglad',
    params: { tresc: formularz[s.pole] },
    auto: true,
    onSuccess: (data) => {
      if (nr !== podgladNr[s.typ]) return
      const p = podglady[s.typ]
      p.tresc = data?.tresc || ''
      p.dlugosc = data?.dlugosc || 0
      p.czesci = data?.czesci || 1
      p.ostrzezenie = data?.ostrzezenie || ''
      p.blad = data?.blad || ''
    },
    onError: (err) => {
      if (nr !== podgladNr[s.typ]) return
      const p = podglady[s.typ]
      p.tresc = ''
      p.dlugosc = 0
      p.czesci = 1
      p.ostrzezenie = ''
      p.blad = komunikatBledu(err, __('Nie udało się pobrać podglądu SMS'))
    },
  })
}

function ostrzezenie(typ) {
  const p = podglady[typ]
  if (p.blad) return ''
  return p.ostrzezenie || ostrzezenieCzesci(p.czesci) || ''
}

function zmienTresc(s, val) {
  formularz[s.pole] = val ?? ''
  bladZapisu.value = ''
  clearTimeout(podgladTimery[s.typ])
  podgladTimery[s.typ] = setTimeout(() => odswiezPodglad(s), 400)
}

function zmienLimit(val) {
  formularz[POLE_LIMITU] = val
  bladZapisu.value = ''
}

function cofnijZmiany() {
  for (const s of SZABLONY) {
    if (formularz[s.pole] !== state.zapisane[s.pole])
      zmienTresc(s, state.zapisane[s.pole])
  }
  formularz[POLE_LIMITU] = state.zapisane[POLE_LIMITU]
  bladZapisu.value = ''
}

function zapiszUstawienia() {
  const ladunek = zmienionePola(formularz, state.zapisane)
  for (const s of SZABLONY) {
    if (ladunek[s.pole] === undefined) continue
    const komunikat = walidujSzablon(ladunek[s.pole], state.placeholdery)
    if (komunikat) {
      bladZapisu.value = `${__(s.etykieta)}: ${komunikat}`
      return
    }
  }
  if (ladunek[POLE_LIMITU] !== undefined) {
    const komunikat = walidujLimit(formularz[POLE_LIMITU])
    if (komunikat) {
      bladZapisu.value = komunikat
      return
    }
  }
  if (!Object.keys(ladunek).length) return
  zapisz(
    ladunek,
    () => toast.success(__('Ustawienia SMS do handlowców zapisane')),
    (msg) => (bladZapisu.value = msg),
  )
}

function przelacz(pole, val) {
  const komunikaty =
    pole === 'handlowiec_wlaczone'
      ? [__('SMS do handlowców włączony'), __('SMS do handlowców wyłączony')]
      : [
          __('SMS o odwołaniu spotkania włączony'),
          __('SMS o odwołaniu spotkania wyłączony'),
        ]
  zapisz(
    { [pole]: val ? 1 : 0 },
    () => toast.success(val ? komunikaty[0] : komunikaty[1]),
    (msg) => toast.error(msg),
  )
}

function zapisz(ladunek, poSukcesie, poBledzie) {
  zapisuje.value = true
  createResource({
    url: API + 'volteo_sms_handlowiec_zapisz',
    params: ladunek,
    auto: true,
    onSuccess: (data) => {
      zapisuje.value = false
      zastosujStan(data, Object.keys(ladunek))
      poSukcesie?.()
    },
    onError: (err) => {
      zapisuje.value = false
      poBledzie(
        komunikatBledu(
          err,
          __('Nie udało się zapisać ustawień SMS do handlowców'),
        ),
      )
    },
  })
}

function wyslijTestowy() {
  if (zmienione.value) return
  test.wysyla = true
  test.wynik = ''
  createResource({
    url: API + 'volteo_sms_handlowiec_test',
    params: { typ: test.typ },
    auto: true,
    onSuccess: (data) => {
      test.wysyla = false
      // {ok: false, powod} to odmowa bez wyjatku (limit, blad SMSAPI)
      const wynik = wynikTestu(data)
      test.wynik = wynik.tekst
      test.wynikOk = wynik.ok
      if (wynik.ok) toast.success(wynik.tekst)
      else toast.error(wynik.tekst)
      listResource.reload()
    },
    onError: (err) => {
      test.wysyla = false
      test.wynik = komunikatBledu(err, __('Nie udało się wysłać SMS testowego'))
      test.wynikOk = false
      toast.error(test.wynik)
    },
  })
}

function zmienTelefon(h, val) {
  telefonDraft[h.uzytkownik] = val ?? ''
  telefonBlad[h.uzytkownik] = ''
}

function telefonZmieniony(h) {
  const draft = telefonDraft[h.uzytkownik]
  if (draft === undefined || draft === null) return false
  return String(draft).trim() !== String(h.mobile_no || '')
}

function zapiszTelefon(h) {
  if (!telefonZmieniony(h)) return
  const uzytkownik = h.uzytkownik
  const nowy = String(telefonDraft[uzytkownik]).trim()
  telefonZapisuje[uzytkownik] = true
  telefonBlad[uzytkownik] = ''
  createResource({
    url: 'crm.api.dyzury.volteo_dyzur_telefon_zapisz',
    params: { uzytkownik, mobile_no: nowy },
    auto: true,
    onSuccess: (data) => {
      telefonZapisuje[uzytkownik] = false
      telefonDraft[uzytkownik] = undefined
      const zapisany = data?.mobile_no ?? nowy
      // kolejnosc zostaje do nastepnego wczytania, zeby wiersz nie uciekal spod kursora
      state.handlowcy = state.handlowcy.map((x) =>
        x.uzytkownik === uzytkownik
          ? { ...x, mobile_no: zapisany, numer_ok: Boolean(zapisany) }
          : x,
      )
      toast.success(__('Numer telefonu zapisany'))
    },
    onError: (err) => {
      telefonZapisuje[uzytkownik] = false
      telefonBlad[uzytkownik] = komunikatBledu(
        err,
        __('Nie udało się zapisać numeru'),
      )
    },
  })
}
</script>
