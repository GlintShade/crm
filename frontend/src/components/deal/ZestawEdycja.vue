<!--
  Tryb edycji zestawu OZE (ops#272), osadzony w ZestawTab.vue, tylko dla
  administracji (kosmetyka; serwer pilnuje sam w crm.api.zestaw).

  Przepływ: stan formularza (niemutowalny, utils/zestawEdycja.js) -> po każdej
  zmianie wierszy lub ceny, z opóźnieniem 350 ms, `volteo_zestaw_podglad`
  (serwer liczy WSZYSTKIE pochodne, tu zero matematyki cen) -> przycisk
  "Zapisz zmiany" otwiera okno z różnicami -> `volteo_zestaw_zapisz`.
  Odpowiedzi starsze niż ostatnie wywołanie podglądu są ignorowane (licznik).
  Natywne inputy, bez refów na komponentach frappe-ui.
-->
<template>
  <div class="mb-4 rounded-lg border border-outline-amber-3 p-3">
    <div class="mb-2 flex items-center justify-between">
      <div class="text-sm font-semibold text-ink-amber-8">{{ __('Edycja zestawu (administracja)') }}</div>
      <div class="flex items-center gap-2">
        <span v-if="przelicza" class="text-xs text-ink-gray-5">{{ __('Przeliczanie...') }}</span>
        <Button :label="__('Anuluj')" variant="outline" size="sm" @click="anuluj" />
        <Button
          :label="__('Zapisz zmiany')"
          variant="solid"
          size="sm"
          data-testid="zestaw-zapisz-zmiany"
          :disabled="!mozeZapisac"
          :loading="otwieranieOkna"
          @click="otworzOkno"
        />
      </div>
    </div>

    <div
      v-if="bannerUmowy"
      class="mb-3 rounded-md border p-2 text-sm"
      :class="bannerUmowy.krytyczny ? 'border-outline-red-3 bg-surface-red-2 text-ink-red-8' : 'border-outline-amber-3 bg-surface-amber-2 text-ink-amber-8'"
      data-testid="zestaw-baner-umowy"
    >
      {{ bannerUmowy.tekst }}
    </div>

    <!-- Wiersze -->
    <div class="overflow-x-auto rounded-md border border-outline-gray-2">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="bg-surface-gray-2 text-ink-gray-5">
            <th class="px-2 py-2 text-left font-medium">{{ __('TYP') }}</th>
            <th class="px-2 py-2 text-left font-medium">{{ __('NAZWA') }}</th>
            <th class="w-24 px-2 py-2 text-right font-medium">{{ __('ILOŚĆ') }}</th>
            <th class="w-24 px-2 py-2 text-left font-medium">{{ __('JEDNOSTKA') }}</th>
            <th class="w-44 px-2 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(w, i) in stan.wiersze" :key="w.klucz" class="border-t border-outline-gray-1" data-testid="zestaw-wiersz">
            <td class="px-2 py-1.5 align-top">
              <select
                class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none w-full"
                :value="wartoscSelectaTypu(w)"
                data-testid="zestaw-typ"
                @change="zmienTyp(i, w, $event.target.value)"
              >
                <option value="">{{ __('(wybierz)') }}</option>
                <option v-for="t in typy" :key="t" :value="t">{{ t }}</option>
                <option :value="TYP_INNY">{{ __('Inny') }}</option>
              </select>
              <input
                v-if="typWlasny(w)"
                class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none mt-1 w-full"
                type="text"
                :value="w.typ"
                :placeholder="__('Własny typ')"
                @input="stan = zmienPoleWiersza(stan, i, 'typ', $event.target.value)"
              />
            </td>
            <td class="px-2 py-1.5 align-top">
              <input
                class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none w-full"
                type="text"
                :value="w.nazwa"
                data-testid="zestaw-nazwa"
                @input="stan = zmienPoleWiersza(stan, i, 'nazwa', $event.target.value)"
              />
            </td>
            <td class="px-2 py-1.5 align-top">
              <input
                class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none w-full text-right"
                type="number"
                step="0.01"
                min="0"
                :value="w.ilosc"
                data-testid="zestaw-ilosc"
                @input="stan = zmienPoleWiersza(stan, i, 'ilosc', $event.target.value)"
              />
            </td>
            <td class="px-2 py-1.5 align-top">
              <input
                class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none w-full"
                type="text"
                :value="w.jednostka"
                @input="stan = zmienPoleWiersza(stan, i, 'jednostka', $event.target.value)"
              />
            </td>
            <td class="whitespace-nowrap px-2 py-1.5 text-right align-top">
              <Button variant="ghost" size="sm" :label="__('W górę')" :disabled="i === 0" @click="stan = przesunWiersz(stan, i, -1)" />
              <Button variant="ghost" size="sm" :label="__('W dół')" :disabled="i === stan.wiersze.length - 1" @click="stan = przesunWiersz(stan, i, 1)" />
              <Button variant="ghost" size="sm" theme="red" :label="__('Usuń')" data-testid="zestaw-usun" @click="usun(i)" />
            </td>
          </tr>
          <tr v-if="!stan.wiersze.length">
            <td colspan="5" class="px-2 py-3 text-center text-ink-gray-5">{{ __('Brak pozycji.') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="mt-2">
      <Button :label="__('Dodaj pozycję')" variant="outline" size="sm" data-testid="zestaw-dodaj" @click="stan = dodajWiersz(stan)" />
    </div>

    <!-- Cena -->
    <div class="mt-4 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Cena') }}</div>
    <div class="mt-1 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      <label v-for="pole in poleCenyWejscie" :key="pole.klucz" class="flex flex-col gap-0.5 text-xs text-ink-gray-6">
        <span>{{ pole.etykieta }}</span>
        <input
          class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none"
          type="number"
          step="0.01"
          :value="stan.cena[pole.klucz]"
          :data-testid="`zestaw-cena-${pole.klucz}`"
          @input="stan = zmienPoleCeny(stan, pole.klucz, $event.target.value)"
        />
        <span v-if="pole.podpowiedz" class="text-[11px] text-ink-gray-4">{{ pole.podpowiedz }}</span>
      </label>
    </div>
    <div class="mt-2 text-xs text-ink-gray-5">
      <span v-if="cenaPodglad.zasady_dotacji">{{ __('Zasady dotacji') }}: {{ cenaPodglad.zasady_dotacji }}. </span>
      <span v-if="cenaPodglad.typ_klienta">{{ __('Typ klienta') }}: {{ cenaPodglad.typ_klienta }}.</span>
    </div>

    <div class="mt-2 rounded-md bg-surface-gray-1 p-2 text-sm" data-testid="zestaw-pochodne">
      <div v-for="p in pochodne" :key="p.klucz" class="flex justify-between py-0.5 text-ink-gray-7">
        <span>{{ p.etykieta }}</span>
        <span :data-testid="`zestaw-pochodna-${p.klucz}`">{{ p.wartosc }}</span>
      </div>
    </div>

    <div v-if="blad" class="mt-2 rounded-md border border-outline-red-3 bg-surface-red-2 p-2 text-sm text-ink-red-8" data-testid="zestaw-blad">
      {{ blad }}
    </div>
    <div v-for="o in ostrzezenia" :key="o" class="mt-2 rounded-md border border-outline-amber-3 bg-surface-amber-2 p-2 text-sm text-ink-amber-8">
      {{ o }}
    </div>

    <!-- Konfiguracja -->
    <template v-if="maKonfiguracje">
      <div class="mt-4 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Konfiguracja (do umowy)') }}</div>
      <div class="mt-1 overflow-x-auto rounded-md border border-outline-gray-2">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="bg-surface-gray-2 text-ink-gray-5">
              <th class="px-2 py-2 text-left font-medium">{{ __('POLE') }}</th>
              <th class="px-2 py-2 text-left font-medium">{{ __('BYŁO') }}</th>
              <th class="px-2 py-2 text-left font-medium">{{ __('BĘDZIE') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pole in polaKonfiguracji" :key="pole" class="border-t border-outline-gray-1">
              <td class="px-2 py-1.5 text-ink-gray-6">{{ etykietaPolaKonfiguracji(pole) }}</td>
              <td class="px-2 py-1.5 text-ink-gray-6">{{ pokazBylo(pole) }}</td>
              <td class="px-2 py-1.5">
                <input
                  class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none w-full"
                  type="text"
                  :value="stan.konfiguracja[pole]"
                  :data-testid="`zestaw-konf-${pole}`"
                  @input="stan = zmienPoleKonfiguracji(stan, pole, $event.target.value)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="ostrzezenieFalownika" class="mt-2 rounded-md border border-outline-amber-3 bg-surface-amber-2 p-2 text-sm text-ink-amber-8">
        {{ ostrzezenieFalownika }}
      </div>
    </template>
    <div v-else-if="dostep.konfiguracja_info" class="mt-4 text-sm text-ink-gray-6">
      {{ dostep.konfiguracja_info }}
    </div>

    <Dialog v-model:open="okno.otwarte" :title="__('Potwierdź zmiany zestawu')" size="lg">
      <template #default>
        <div class="flex flex-col gap-3 text-sm" data-testid="zestaw-okno">
          <div v-if="rozniceOkna.dodane.length">
            <div class="font-medium text-ink-gray-8">{{ __('Dodane') }}</div>
            <div v-for="t in rozniceOkna.dodane" :key="t" class="text-ink-gray-7">+ {{ t }}</div>
          </div>
          <div v-if="rozniceOkna.usuniete.length">
            <div class="font-medium text-ink-gray-8">{{ __('Usunięte') }}</div>
            <div v-for="t in rozniceOkna.usuniete" :key="t" class="text-ink-gray-7">- {{ t }}</div>
          </div>
          <div v-if="rozniceOkna.zmienione.length">
            <div class="font-medium text-ink-gray-8">{{ __('Zmienione') }}</div>
            <div v-for="t in rozniceOkna.zmienione" :key="t" class="text-ink-gray-7">{{ t }}</div>
          </div>
          <div v-if="rozniceOkna.cena.length">
            <div class="font-medium text-ink-gray-8">{{ __('Cena (przed -> po)') }}</div>
            <div v-for="c in rozniceOkna.cena" :key="c.etykieta" class="text-ink-gray-7">
              {{ c.etykieta }}: {{ c.przed }} -> {{ c.po }}
            </div>
          </div>
          <div v-if="rozniceOkna.konfiguracja.length">
            <div class="font-medium text-ink-gray-8">{{ __('Konfiguracja') }}</div>
            <div v-for="c in rozniceOkna.konfiguracja" :key="c.etykieta" class="text-ink-gray-7">
              {{ c.etykieta }}: {{ c.przed }} -> {{ c.po }}
            </div>
          </div>
          <div
            v-if="!rozniceOkna.dodane.length && !rozniceOkna.usuniete.length && !rozniceOkna.zmienione.length && !rozniceOkna.cena.length && !rozniceOkna.konfiguracja.length"
            class="text-ink-gray-5"
          >
            {{ __('Brak widocznych różnic.') }}
          </div>
          <label class="flex flex-col gap-0.5 text-xs text-ink-gray-6">
            <span>{{ __('Powód zmiany') }} ({{ __('opcjonalnie') }})</span>
            <textarea
              v-model="okno.powod"
              class="rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none"
              rows="2"
              maxlength="500"
              data-testid="zestaw-powod"
            ></textarea>
          </label>
          <div v-if="okno.blad" class="rounded-md border border-outline-red-3 bg-surface-red-2 p-2 text-ink-red-8">
            {{ okno.blad }}
            <Button v-if="okno.konflikt" class="ml-2" size="sm" variant="outline" :label="__('Odśwież')" @click="odswiez" />
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" variant="outline" @click="okno.otwarte = false" />
          <Button
            :label="__('Zapisz')"
            variant="solid"
            data-testid="zestaw-okno-zapisz"
            :loading="okno.zapis"
            @click="zapisz"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, call } from 'frappe-ui'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { formatPln } from '@/utils/money'
import {
  ETYKIETY_KONFIGURACJI,
  ETYKIETY_POL_CENY,
  POLA_CENY_WEJSCIE,
  POLA_KONFIGURACJI,
  TYP_INNY,
  czyBladWersji,
  czyTypInny,
  czyZmieniony,
  dodajWiersz,
  doWywolania,
  doZapisu,
  komunikatBledu,
  przesunWiersz,
  roznicaDoOkna,
  stanZOdpowiedzi,
  usunWiersz,
  zastosujPropozycje,
  zmienPoleCeny,
  zmienPoleKonfiguracji,
  zmienPoleWiersza,
} from '@/utils/zestawEdycja'

const props = defineProps({
  dealId: { type: String, required: true },
  // Odpowiedź `volteo_zestaw_get` (dozwolone === true).
  dostep: { type: Object, required: true },
})
const emit = defineEmits(['saved', 'cancel', 'refresh'])

const OPOZNIENIE_PODGLADU_MS = 350

const poczatkowy = stanZOdpowiedzi(props.dostep)
const stan = ref(poczatkowy)
// Wiersze, w których admin wybrał "Inny" (wolny tekst typu), zanim wpisał cokolwiek.
const wlasneTypy = ref([])

const podglad = ref(null)
const przelicza = ref(false)
const blad = ref('')
const otwieranieOkna = ref(false)
const okno = reactive({ otwarte: false, powod: '', zapis: false, blad: '', konflikt: false })

const typy = computed(() => props.dostep.typy || [])
const zmieniony = computed(() => czyZmieniony(poczatkowy, stan.value))
const mozeZapisac = computed(() => zmieniony.value && !blad.value && !przelicza.value && stan.value.wiersze.length > 0)

const polaKonfiguracji = POLA_KONFIGURACJI
const maKonfiguracje = computed(() => Object.keys(props.dostep.konfiguracja || {}).length > 0)

const poleCenyWejscie = POLA_CENY_WEJSCIE.map((klucz) => ({
  klucz,
  etykieta: __(ETYKIETY_POL_CENY[klucz]),
  podpowiedz: klucz === 'dodatki_bez_ulgi_brutto' ? __('klimatyzacja i ładowarka EV nie wchodzą do ulgi') : '',
}))

const cenaPodglad = computed(() => podglad.value?.cena || props.dostep.cena || {})
const ostrzezenia = computed(() => {
  const z = podglad.value?.ostrzezenia || []
  const k = podglad.value?.konfiguracja_propozycja?._ostrzezenia || []
  return [...new Set([...z, ...k])]
})

const pochodne = computed(() => {
  const c = cenaPodglad.value
  const kwoty = [
    ['brutto', __('Cena brutto'), c.brutto],
    ['cena_po_dotacji', __('Cena po dotacji'), c.cena_po_dotacji],
    ['ulga_kwota', __('Kwota ulgi'), c.ulga_kwota],
    ['cena_po_uldze', __('Cena po uldze'), c.cena_po_uldze],
    ['rata_brutto', __('Rata brutto'), c.rata_brutto],
    ['rata_po_dotacji', __('Rata po dotacji'), c.rata_po_dotacji],
    ['rata_po_uldze', __('Rata po uldze'), c.rata_po_uldze],
  ]
  return kwoty.map(([klucz, etykieta, v]) => ({
    klucz,
    etykieta,
    wartosc: v == null ? '-' : klucz.startsWith('rata') ? `${formatPln(v)} /mies.` : formatPln(v),
  }))
})

const bannerUmowy = computed(() => {
  const u = props.dostep.umowa
  if (!u || !u.istnieje) return null
  if (u.mozna_regenerowac) {
    return {
      krytyczny: false,
      tekst: __('Szansa ma wygenerowaną umowę. Po zapisie wygeneruj PDF umowy ponownie w zakładce Umowa.'),
    }
  }
  return {
    krytyczny: true,
    tekst:
      __('Umowa jest w Autenti lub podpisana (status: {0}). Zmiana zestawu nie zmieni dokumentu. Zapisz zmianę jako aneks i opisz go w powodzie.', [
        u.autenti_status || '-',
      ]),
  }
})

const ostrzezenieFalownika = computed(() => {
  const falownik = stan.value.wiersze.find((w) => w.typ === 'Falownik')
  const konf = String(stan.value.konfiguracja.custom_falownik ?? '').trim()
  if (!falownik || konf === '') return ''
  if (falownik.nazwa.trim() === konf) return ''
  return __('Pole Falownik w konfiguracji różni się od nazwy pozycji Falownik. Umowa może wtedy pokazać błędną liczbę falowników.')
})

function etykietaPolaKonfiguracji(pole) {
  return __(ETYKIETY_KONFIGURACJI[pole])
}

function pokazBylo(pole) {
  const v = (props.dostep.konfiguracja || {})[pole]
  return v == null || v === '' ? '-' : String(v)
}

function typWlasny(w) {
  return wlasneTypy.value.includes(w.klucz) || czyTypInny(w.typ, typy.value)
}

function wartoscSelectaTypu(w) {
  return typWlasny(w) ? TYP_INNY : w.typ
}

function zmienTyp(indeks, w, wartosc) {
  if (wartosc === TYP_INNY) {
    wlasneTypy.value = [...wlasneTypy.value, w.klucz]
    stan.value = zmienPoleWiersza(stan.value, indeks, 'typ', '')
    return
  }
  wlasneTypy.value = wlasneTypy.value.filter((k) => k !== w.klucz)
  stan.value = zmienPoleWiersza(stan.value, indeks, 'typ', wartosc)
}

function usun(indeks) {
  stan.value = usunWiersz(stan.value, indeks)
}

// ---- podgląd ----
let licznikWywolan = 0
let czasomierz = null

async function przelicz() {
  licznikWywolan += 1
  const moj = licznikWywolan
  przelicza.value = true
  try {
    const odp = await call('crm.api.zestaw.volteo_zestaw_podglad', {
      deal: props.dealId,
      ...doWywolania(stan.value),
    })
    if (moj !== licznikWywolan) return false
    podglad.value = odp
    blad.value = ''
    stan.value = zastosujPropozycje(stan.value, odp?.konfiguracja_propozycja)
    return true
  } catch (err) {
    if (moj !== licznikWywolan) return false
    blad.value = komunikatBledu(err, __('Nie udało się przeliczyć zestawu.'))
    return false
  } finally {
    if (moj === licznikWywolan) przelicza.value = false
  }
}

// Klucz = to, co faktycznie idzie do podglądu (wiersze + cena); zmiana samej
// konfiguracji nie wywołuje serwera.
const kluczPodgladu = computed(() => JSON.stringify(doWywolania(stan.value)))
watch(kluczPodgladu, () => {
  if (czasomierz) clearTimeout(czasomierz)
  przelicza.value = true
  czasomierz = setTimeout(przelicz, OPOZNIENIE_PODGLADU_MS)
})
onBeforeUnmount(() => {
  if (czasomierz) clearTimeout(czasomierz)
  licznikWywolan += 1
})

// ---- potwierdzenie i zapis ----
const rozniceOkna = computed(() =>
  roznicaDoOkna(
    podglad.value?.roznice,
    props.dostep.cena,
    podglad.value?.cena,
    props.dostep.konfiguracja,
    stan.value.konfiguracja,
  ),
)

async function otworzOkno() {
  if (czasomierz) {
    clearTimeout(czasomierz)
    czasomierz = null
  }
  otwieranieOkna.value = true
  try {
    // Zawsze świeży podgląd tuż przed oknem: różnice muszą odpowiadać stanowi.
    const ok = await przelicz()
    if (!ok) return
    okno.powod = ''
    okno.blad = ''
    okno.konflikt = false
    okno.otwarte = true
  } finally {
    otwieranieOkna.value = false
  }
}

async function zapisz() {
  okno.zapis = true
  okno.blad = ''
  okno.konflikt = false
  try {
    const odp = await call('crm.api.zestaw.volteo_zestaw_zapisz', {
      deal: props.dealId,
      ...doZapisu(stan.value, okno.powod),
      modified: props.dostep.modified,
    })
    okno.otwarte = false
    emit('saved', odp)
  } catch (err) {
    okno.blad = komunikatBledu(err, __('Nie udało się zapisać zestawu.'))
    okno.konflikt = czyBladWersji(okno.blad)
  } finally {
    okno.zapis = false
  }
}

function odswiez() {
  okno.otwarte = false
  emit('refresh')
}

function anuluj() {
  if (zmieniony.value && !window.confirm(__('Porzucić niezapisane zmiany zestawu?'))) return
  emit('cancel')
}
</script>
