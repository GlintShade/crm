<!--
  Zestaw tab, panel "Koszty i marża" (tylko administratorzy). Nazwa pliku
  odnosi się do DOMENY (koszty montażu/realizacji), nie do zakładki. Od ops#342
  panel stoi obok boksu "Wycena" (OZE) i jest zawsze rozwinięty; dla Czystego
  Powietrza (prop `zwijany`) zostaje zwijanym panelem pod treścią zakładki, jak
  dotąd. Czyta snapshot planowanych kosztów zapisany przez kalkulator
  (`CRM Deal.custom_koszty_json`, permlevel 2), pozwala administratorowi wpisać
  rzeczywisty koszt każdej linii (puste = wg planu), dodać nieplanowane pozycje
  i widzieć marżę/zysk na żywo przed zapisem. Koszty planowane i składniki
  marży edytuje wspólny edytor zestawu (ZestawEdycja.vue); tu są tylko do
  odczytu, razem z dopiskiem "Pierwotnie", gdy wartość była zmieniana ręcznie.

  Nie renderuje NIC, gdy nie ma użytecznego snapshotu: `custom_koszty_json`
  jest permlevel 2, więc Frappe po cichu pomija klucz w odpowiedzi dla ról bez
  odczytu (brak błędu, brak klucza). Deal sprzed b49 i błąd parsowania wyglądają
  tak samo: `null`, brak panelu, brak szumu w konsoli. O tym, czy panel jest
  widoczny, rodzic dowiaduje się z zdarzenia `widocznosc` (potrzebuje tego do
  wyboru układu dwóch kolumn). Zapis (`crm.api.koszty.volteo_koszty_zapisz`)
  jest autorytatywny po stronie serwera, ten komponent tylko wyświetla i edytuje.

  Cała arytmetyka na żywo (fallback do planu, różnica, marża/zysk) jest
  wyłącznie prezentacyjna i mieszka w `@/utils/montazKoszty.js`.

  Stan reaktywny deklarowany z góry z jawnymi `null`/`{}`/`[]` i zawsze
  ZASTĘPOWANY w całości, nigdy czytany przez `hasOwnProperty`/`in` (computed
  zbudowany na takim odczycie na obiekcie reaktywnym zamarza po pierwszym
  przeliczeniu).
-->
<template>
  <div v-if="snapshot" data-testid="koszty-panel">
    <button
      v-if="zwijany"
      type="button"
      class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
      @click="expanded = !expanded"
    >
      <span>{{ __('Koszty i marża (widoczne tylko dla administratorów)') }}</span>
      <FeatherIcon :name="expanded ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
    </button>

    <div
      v-show="expanded"
      class="rounded-lg border border-dashed border-outline-amber-3 bg-surface-amber-2 p-3"
      :class="{ 'mt-2': zwijany }"
    >
      <div v-if="!zwijany" class="mb-3 flex flex-wrap items-baseline justify-between gap-x-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-ink-amber-8">{{ __('Koszty i marża') }}</div>
        <div class="text-xs text-ink-amber-8">{{ __('widoczne tylko dla administratorów') }}</div>
      </div>

      <!-- Ślady ręcznych edycji (zestaw, koszty planowane, marże): krótkie linie tekstu -->
      <div v-if="edycjaReczna" class="mb-1.5 text-xs text-ink-amber-8" data-testid="koszty-edycja-reczna">
        {{ edycjaReczna.tekst }}
      </div>
      <div v-if="edycjaPlanuTekst" class="mb-1.5 text-xs text-ink-amber-8" data-testid="koszty-edycja-planu">
        {{ edycjaPlanuTekst }}
      </div>
      <div v-if="edycjaMarzyTekst" class="mb-1.5 text-xs text-ink-amber-8" data-testid="koszty-edycja-marz">
        {{ edycjaMarzyTekst }}
      </div>

      <!-- Cost lines -->
      <div class="mk-head mt-2">
        <div>{{ __('Pozycja') }}</div>
        <div>{{ __('Koszt plan') }}</div>
        <div>{{ __('Rzeczywisty') }}</div>
      </div>

      <div v-for="linia in widoczneLinie" :key="linia.klucz" class="mk-row">
        <div class="mk-cell mk-cell-label">
          <div class="font-medium text-ink-gray-8">{{ linia.etykieta }}</div>
          <div v-if="linia.ilosc || linia.netto !== null" class="text-xs text-ink-gray-5">
            <template v-if="linia.ilosc">{{ linia.ilosc }} {{ jednostkaLabel(linia.jednostka) }} · </template>
            <template v-if="linia.netto !== null">{{ __('netto') }} {{ formatPln(linia.netto) }}</template>
            <template v-if="linia.prowizjaPlan !== null"> · {{ __('prowizja plan') }} {{ formatPln(linia.prowizjaPlan) }}</template>
          </div>
        </div>

        <div class="mk-cell tabular-nums">
          <span class="mk-mobile-label">{{ __('Koszt plan') }}: </span>{{ formatPln(linia.kosztPlan) }}
          <div v-if="!linia.czyKorekta && linia.kosztPlanPierwotny !== null" class="mk-pierwotny">
            {{ __('Pierwotnie') }}: {{ formatPln(linia.kosztPlanPierwotny) }}
          </div>
        </div>

        <div v-if="linia.czyKorekta" class="mk-cell">
          <span class="mk-badge">{{ __('wg planu') }}</span>
        </div>
        <div v-else class="mk-cell">
          <span class="mk-mobile-label">{{ __('Rzeczywisty') }}: </span>
          <input
            type="text"
            inputmode="decimal"
            class="mk-input"
            :value="edycje[linia.klucz]"
            :placeholder="formatPlnAmount(linia.kosztPlan)"
            :disabled="saving"
            @input="edycje[linia.klucz] = $event.target.value"
          />
          <span v-if="linia.wgPlanu" class="mk-badge">{{ __('wg planu') }}</span>
        </div>
      </div>

      <button
        v-if="puste.length"
        type="button"
        class="mk-link mk-puste"
        data-testid="koszty-puste-pozycje"
        @click="pokazPuste = !pokazPuste"
      >
        {{ pokazPuste ? __('Ukryj puste pozycje') : __('Pokaż {0} pustych pozycji', [puste.length]) }}
      </button>

      <!-- Extra cost positions -->
      <div class="mk-section">
        <div class="mk-section-title">{{ __('Dodatkowe pozycje') }}</div>
        <div v-if="!dodatkowe.length" class="text-xs text-ink-gray-5">{{ __('Brak dodatkowych pozycji.') }}</div>
        <div v-for="(wiersz, indeks) in dodatkowe" :key="wiersz.id || `nowa-${indeks}`" class="mk-dodatkowa-row">
          <input
            type="text"
            class="mk-input mk-input-nazwa"
            :value="wiersz.nazwa"
            :placeholder="__('Nazwa pozycji')"
            :disabled="saving"
            @input="ustawNazwaDodatkowa(indeks, $event.target.value)"
          />
          <input
            type="text"
            inputmode="decimal"
            class="mk-input mk-input-kwota"
            :value="wiersz.kwota"
            placeholder="0,00"
            :disabled="saving"
            @input="ustawKwoteDodatkowa(indeks, $event.target.value)"
          />
          <button
            type="button"
            class="mk-remove"
            :aria-label="__('Usuń pozycję')"
            :disabled="saving"
            @click="usunDodatkowa(indeks)"
          >
            <FeatherIcon name="x" class="h-3.5 w-3.5" />
          </button>
        </div>
        <Button variant="outline" size="sm" :label="__('Dodaj pozycję')" :disabled="saving" @click="dodajDodatkowa" />
      </div>

      <!-- PV i OZE: składniki marży planowej (tylko do odczytu) -->
      <div v-if="czyOze && skladnikiMarzy.length" class="mk-section">
        <div class="mk-section-title">{{ __('Składniki marży planowej') }}</div>
        <div v-for="skl in marze.skladniki" :key="skl.klucz" class="mk-skladnik-row">
          <span>{{ skl.etykieta }}</span>
          <span class="tabular-nums">
            {{ formatPln(skl.kwotaNowa) }}
            <span v-if="skl.pierwotny !== null" class="mk-pierwotny">{{ __('Pierwotnie') }}: {{ formatPln(skl.pierwotny) }}</span>
          </span>
        </div>
        <div class="mk-skladnik-row">
          <span>{{ __('Suma składników') }}</span>
          <span class="tabular-nums">{{ formatPln(marze.suma) }}</span>
        </div>
        <div v-if="marze.nierozdzielona !== 0" class="mk-skladnik-row" data-testid="koszty-marza-nierozdzielona">
          <span>{{ __('Nierozdzielona marża') }}</span>
          <span class="tabular-nums" :class="marze.nierozdzielona < 0 ? 'text-ink-red-6' : 'text-ink-amber-8'">
            {{ formatPln(marze.nierozdzielona) }}
          </span>
        </div>
      </div>

      <!-- Errors -->
      <ul v-if="wynik.bledy.length" class="mk-errors">
        <li v-for="(blad, i) in wynik.bledy" :key="i">{{ blad }}</li>
      </ul>

      <!-- Summary -->
      <div class="mk-summary">
        <div class="mk-summary-row">
          <span>{{ __('Netto') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.netto) }}</span>
        </div>
        <div class="mk-summary-row">
          <span>{{ __('Koszt (plan)') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.kosztPlan) }}</span>
        </div>
        <div class="mk-summary-row">
          <span>{{ __('Koszt (rzeczywisty)') }}</span>
          <span class="font-medium tabular-nums">{{ formatPln(wynik.razem.kosztRzeczywisty) }}</span>
        </div>
        <div class="mk-summary-row">
          <span>{{ __('Marża (plan)') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.marzaPlan) }}</span>
        </div>
        <div class="mk-summary-row mk-summary-highlight">
          <span>{{ __('Marża (rzeczywista)') }}</span>
          <span class="tabular-nums font-semibold" :class="compareClass(wynik.razem.marzaRzeczywista, wynik.razem.marzaPlan)">
            {{ formatPln(wynik.razem.marzaRzeczywista) }}
          </span>
        </div>
        <template v-if="wynik.razem.prowizjaPlan !== null">
          <div class="mk-summary-row">
            <span>{{ __('Prowizja (plan)') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.prowizjaPlan) }}</span>
          </div>
        </template>
        <div class="mk-summary-row">
          <span>{{ __('Zysk (plan)') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.zyskPlan) }}</span>
        </div>
        <div class="mk-summary-row mk-summary-highlight">
          <span>{{ __('Zysk (rzeczywisty)') }}</span>
          <span class="tabular-nums font-semibold" :class="compareClass(wynik.razem.zyskRzeczywisty, wynik.razem.zyskPlan)">
            {{ formatPln(wynik.razem.zyskRzeczywisty) }}
          </span>
        </div>
        <div v-if="wynik.razem.pozycjeWgPlanu > 0" class="mk-summary-footer">
          {{ wynik.razem.pozycjeWgPlanu }} {{ __('pozycji liczonych wg planu') }}
        </div>
      </div>

      <div class="mk-actions">
        <span v-if="wynik.bledy.length" class="mk-actions-hint">{{ __('Popraw błędy powyżej, aby zapisać') }}</span>
        <Button
          variant="solid"
          :loading="saving"
          :disabled="saving || wynik.bledy.length > 0"
          :label="__('Zapisz koszty rzeczywiste')"
          @click="zapiszKoszty"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, FeatherIcon, call, createResource, toast } from 'frappe-ui'
import { formatPln, formatPlnAmount } from '@/utils/money'
import { formatujDataGodzine } from '@/utils/dataPolska'
import { usersStore } from '@/stores/users'
import {
  parseSnapshot,
  przeliczRzeczywiste,
  zbudujPayload,
  przeliczSkladnikiMarzy,
} from '@/utils/montazKoszty'

const props = defineProps({
  dealId: { type: String, required: true },
  // Czyste Powietrze: panel zostaje zwijany (domyślnie zwinięty), jak dotąd.
  zwijany: { type: Boolean, default: false },
})
const emit = defineEmits(['widocznosc'])

// --- State (declared up front, always replaced wholesale) -----------------
const snapshot = ref(null) // parsed custom_koszty_json, or null (see header)
const edycje = ref({}) // klucz -> raw typed "koszt rzeczywisty" string
const dodatkowe = ref([]) // [{id?, nazwa, kwota}], raw, in-progress
const expanded = ref(!props.zwijany) // zawsze rozwinięty, poza trybem zwijanym (CP)
const saving = ref(false)
const pokazPuste = ref(false)

// --- Load -------------------------------------------------------------------
// Permlevel-2 field: Frappe drops `custom_koszty_json` from the response
// entirely for any role without read access, so a non-admin's fetch
// SUCCEEDS with the key simply absent (parseSnapshot(undefined) -> null).
createResource({
  url: 'frappe.client.get_value',
  params: {
    doctype: 'CRM Deal',
    filters: props.dealId,
    fieldname: 'custom_koszty_json',
  },
  auto: true,
  onSuccess: (data) => {
    seedFromSnapshot(parseSnapshot(data?.custom_koszty_json))
  },
  onError: () => {
    seedFromSnapshot(null)
  },
})

/**
 * Replace the local editable state wholesale from a fresh snapshot (initial
 * load, or the server's response after a successful save).
 */
function seedFromSnapshot(nowySnapshot) {
  snapshot.value = nowySnapshot
  // Rodzic wybiera układ dwóch kolumn po tym, czy panel ma co pokazać.
  emit('widocznosc', Boolean(nowySnapshot))

  const edycjeInit = {}
  for (const linia of nowySnapshot?.linie || []) {
    edycjeInit[linia.klucz] = linia.koszt_rzeczywisty != null ? String(linia.koszt_rzeczywisty) : ''
  }
  edycje.value = edycjeInit

  dodatkowe.value = (nowySnapshot?.dodatkowe || []).map((d) => ({
    id: d.id,
    nazwa: d.nazwa || '',
    kwota: d.kwota != null ? String(d.kwota) : '',
  }))
}

// --- Derived / display --------------------------------------------------
const wynik = computed(() => przeliczRzeczywiste(snapshot.value, edycje.value, dodatkowe.value))
const { getUser } = usersStore()
const czyOze = computed(() => ['pv', 'oze'].includes(snapshot.value?.linia_produktowa))

// Linie z kosztem planowanym 0,00 i bez kosztu rzeczywistego chowamy pod
// odnośnikiem (tylko OZE; panel CP wygląda jak dotąd).
const puste = computed(() =>
  czyOze.value ? wynik.value.linie.filter((l) => !l.czyKorekta && l.kosztPlan === 0 && l.kosztRzeczywisty === null) : [],
)
const widoczneLinie = computed(() =>
  pokazPuste.value ? wynik.value.linie : wynik.value.linie.filter((l) => !puste.value.includes(l)),
)

// Baner ręcznej edycji zestawu (ops#273): czytany wprost ze snapshotu, jawny
// null, bez mutacji. Powód pomijany, gdy pusty; osoba: pełne imię albo e-mail.
const edycjaReczna = computed(() => {
  const ed = snapshot.value?.edycja_reczna ?? null
  if (!ed) return null
  const kiedy = formatujDataGodzine(ed.kiedy)
  const kto = (ed.kto && getUser(ed.kto)?.full_name) || ed.kto || ''
  const powod = String(ed.powod ?? '').trim()
  const nettoPrzed = Number(ed.netto_przed)
  const szczegoly = [kto, powod ? `${__('powód')}: ${powod}` : ''].filter(Boolean).join(', ')
  const tekst =
    `${__('Zestaw zmieniony ręcznie')}${kiedy ? ' ' + kiedy : ''}` +
    `${szczegoly ? ' (' + szczegoly + ')' : ''}. ` +
    `${__('Koszty planowane pochodzą z pierwotnej konfiguracji')}` +
    `${Number.isFinite(nettoPrzed) ? ' (' + __('netto przed zmianą') + ': ' + formatPln(nettoPrzed) + ')' : ''} ` +
    `${__('i mogą być nieaktualne.')}`
  return { tekst }
})

// Baner ostatniej edycji planu: kto, kiedy, pierwotna suma planu (bez śladu, gdy brak).
const edycjaPlanuTekst = computed(() => {
  const ed = snapshot.value?.edycja_planu ?? null
  if (!ed) return ''
  const kiedy = formatujDataGodzine(ed.kiedy)
  const kto = (ed.kto && getUser(ed.kto)?.full_name) || ed.kto || ''
  const pierwotna = Number(ed.koszt_plan_pierwotny)
  return (
    `${__('Koszty planowane zmienione ręcznie')}${kiedy ? ' ' + kiedy : ''}${kto ? ' (' + kto + ')' : ''}` +
    `${Number.isFinite(pierwotna) ? '. ' + __('Pierwotna suma kosztów planowanych') + ': ' + formatPln(pierwotna) : ''}.`
  )
})

const skladnikiMarzy = computed(() => snapshot.value?.skladniki_marzy || [])
// Składniki marży tylko do odczytu: bez wpisanych zmian (edycję robi wspólny edytor zestawu).
const marze = computed(() => przeliczSkladnikiMarzy(snapshot.value, {}))
const edycjaMarzyTekst = computed(() => {
  const ed = snapshot.value?.edycja_marzy ?? null
  if (!ed) return ''
  const kiedy = formatujDataGodzine(ed.kiedy)
  const kto = (ed.kto && getUser(ed.kto)?.full_name) || ed.kto || ''
  return `${__('Składniki marży zmienione ręcznie')}${kiedy ? ' ' + kiedy : ''}${kto ? ' (' + kto + ')' : ''}.`
})

function jednostkaLabel(jednostka) {
  return jednostka === 'm2' ? 'm²' : jednostka || ''
}

// Actual vs plan comparison for the summary highlight rows: a lower actual
// margin/profit than planned is a red flag (cost overrun ate into it), a
// higher one is a green result; equal stays neutral gray.
function compareClass(rzeczywiste, plan) {
  if (rzeczywiste < plan) return 'text-ink-red-6'
  if (rzeczywiste > plan) return 'text-ink-green-6'
  return 'text-ink-gray-8'
}

// --- Extra cost positions: always full-array immutable replacement ---------
function dodajDodatkowa() {
  dodatkowe.value = [...dodatkowe.value, { nazwa: '', kwota: '' }]
}
function usunDodatkowa(indeks) {
  dodatkowe.value = dodatkowe.value.filter((_, i) => i !== indeks)
}
function ustawNazwaDodatkowa(indeks, wartosc) {
  dodatkowe.value = dodatkowe.value.map((w, i) => (i === indeks ? { ...w, nazwa: wartosc } : w))
}
function ustawKwoteDodatkowa(indeks, wartosc) {
  dodatkowe.value = dodatkowe.value.map((w, i) => (i === indeks ? { ...w, kwota: wartosc } : w))
}

// --- Save ---------------------------------------------------------------
// Full dotted path is mandatory: crm.api.koszty is a whitelisted fork API
// method, not a Server Script (a bare name resolves only for Server Scripts).
async function zapiszKoszty() {
  // Belt and braces alongside the disabled-button binding above: never save
  // while `bledy` is non-empty (a garbage value would silently CLEAR a saved
  // actual, an invalid row would silently DROP a saved extra row).
  if (!snapshot.value || saving.value || wynik.value.bledy.length) return
  saving.value = true
  try {
    const payload = zbudujPayload(snapshot.value, edycje.value, dodatkowe.value)
    const data = await call('crm.api.koszty.volteo_koszty_zapisz', {
      deal: props.dealId,
      koszty_rzeczywiste: payload.koszty_rzeczywiste,
      dodatkowe: payload.dodatkowe,
    })
    seedFromSnapshot(parseSnapshot(data?.koszty))
    toast.success(__('Zapisano koszty rzeczywiste'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    saving.value = false
  }
}

// frappe-ui call() consumes _server_messages itself and re-throws an error
// whose `message` is just "{url} {exc_type}" and whose `messages` is the
// already-parsed array of server message strings (the Polish text lives
// there). The older `_server_messages`/`exception` branches stay as a
// fallback for any caller that isn't call().
function extractErrorMessage(err, domyslny = __('Nie udało się zapisać kosztów rzeczywistych')) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || domyslny
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || domyslny
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return domyslny
}
</script>

<style scoped>
/* Column layout on desktop; collapses to a single stacked column per row on
   narrow viewports (ZestawTab, which mounts this panel, also renders inside
   MobileDeal.vue; same self-responsive behaviour applies there, no
   layout change needed on the move from MontazTab.vue). Mirrors the amber
   "admin only" treatment already used across the deal tabs
   (KalkulatorTab.vue, KalkulatorCPTab.vue, ZestawTab.vue), and the
   `.kalk-input` editable-cell styling from KalkulatorCPTab.vue's
   commission-modeling sandbox. */
.mk-head {
  display: grid;
  grid-template-columns: minmax(120px, 2fr) minmax(90px, 1fr) minmax(120px, 1fr);
  gap: 6px 12px;
  padding-bottom: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--ink-amber-8);
}
.mk-row {
  display: grid;
  grid-template-columns: minmax(120px, 2fr) minmax(90px, 1fr) minmax(120px, 1fr);
  gap: 6px 12px;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid var(--outline-amber-3);
}
.mk-cell {
  font-size: 14px;
  color: var(--ink-gray-7);
}
.mk-mobile-label {
  display: none;
}
.mk-input {
  height: 28px;
  width: 100%;
  max-width: 140px;
  border-radius: 0.25rem;
  border: 1px solid var(--outline-gray-1);
  background: var(--surface-base);
  padding: 0 8px;
  font-size: 14px;
  color: var(--ink-gray-8);
  outline: none;
}
.mk-input:hover {
  border-color: var(--outline-gray-3);
}
.mk-input:focus {
  border-color: var(--outline-gray-4);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.mk-input:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.mk-pierwotny {
  margin-left: 6px;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ink-gray-5);
}
.mk-link {
  margin-left: 6px;
  font-size: 11px;
  color: var(--ink-gray-6);
  text-decoration: underline;
}
.mk-link:hover {
  color: var(--ink-gray-8);
}
.mk-puste {
  display: block;
  margin: 8px 0 0;
}
.mk-badge {
  margin-left: 6px;
  display: inline-block;
  border-radius: 999px;
  background: var(--surface-gray-3);
  padding: 1px 8px;
  font-size: 11px;
  color: var(--ink-gray-6);
  white-space: nowrap;
}
.mk-section {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--outline-amber-3);
}
.mk-section-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--ink-amber-8);
}
.mk-dodatkowa-row {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
}
.mk-input-nazwa {
  max-width: none;
  flex: 2 1 200px;
}
.mk-input-kwota {
  max-width: 120px;
  flex: 1 1 100px;
}
.mk-remove {
  display: flex;
  height: 24px;
  width: 24px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  color: var(--ink-gray-5);
}
.mk-remove:hover {
  background: var(--surface-gray-3);
  color: var(--ink-red-6);
}
.mk-remove:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.mk-skladnik-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  font-size: 14px;
  color: var(--ink-gray-7);
}
.mk-errors {
  margin-top: 10px;
  border-radius: 0.5rem;
  border: 1px solid var(--outline-red-3);
  background: var(--surface-red-2);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--ink-red-7);
  list-style: disc;
  list-style-position: inside;
}
.mk-summary {
  margin-top: 14px;
  max-width: 360px;
  border-radius: 0.5rem;
  border: 1px solid var(--outline-gray-2);
  background: var(--surface-base);
  padding: 10px 12px;
  font-size: 14px;
}
.mk-summary-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  color: var(--ink-gray-7);
}
.mk-summary-highlight {
  margin-top: 4px;
  border-top: 1px solid var(--outline-gray-2);
  padding-top: 4px;
  color: var(--ink-gray-9);
}
.mk-summary-footer {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-gray-5);
}
.mk-actions {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}
.mk-actions-hint {
  font-size: 12px;
  color: var(--ink-gray-5);
}

@media (max-width: 640px) {
  .mk-head {
    display: none;
  }
  .mk-row {
    grid-template-columns: 1fr;
    gap: 4px;
    border: 1px solid var(--outline-amber-3);
    border-radius: 0.5rem;
    padding: 10px;
    margin-top: 8px;
  }
  .mk-row:first-child {
    margin-top: 0;
  }
  .mk-mobile-label {
    display: inline;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--ink-gray-5);
  }
  .mk-input {
    max-width: none;
  }
  .mk-dodatkowa-row {
    flex-wrap: wrap;
  }
  .mk-input-nazwa {
    flex: 1 1 100%;
  }
  .mk-input-kwota {
    flex: 1 1 auto;
    max-width: none;
  }
  .mk-summary {
    max-width: none;
  }
}
</style>
