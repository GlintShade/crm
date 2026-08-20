<!--
  Zestaw tab, bottom of content — admin-only actual-cost panel. The file is
  named for the domain it covers (koszty montażu/realizacji — installation/
  fulfilment costs), NOT for the tab it renders in: it is mounted at the
  very bottom of ZestawTab.vue's template (owner decision — an earlier
  version of this panel briefly lived in MontazTab.vue by mistake and was
  moved here; keep that history in mind if you go looking for it in the
  wrong tab). Reads the planned cost snapshot persisted by the calculator
  that created the deal (`CRM Deal.custom_koszty_json`, permlevel 2), lets
  an admin type in the real post-installation cost per line (or leave it
  blank to keep using the plan), add extra unplanned cost positions, and
  see the resulting marża/zysk update live before saving.

  Renders NOTHING when there is no usable snapshot: `custom_koszty_json` is
  permlevel 2, so Frappe silently drops the key from the get_value response
  for any role without read access to it (see ZestawTab.vue's own
  dealSubsidy fetch, a few components up in the same file, for the same
  pattern, verified empirically for this codebase) — there is no error,
  just an absent key. A pre-b49 deal (created before this snapshot existed)
  or a parse failure look identical from here: `null`, no panel, no console
  noise. Deliberately mounted outside ZestawTab's loading/empty/populated
  v-if chain, so it still renders for a deal with no BOM rows to show — the
  snapshot this panel reads is unrelated to whether the BOM itself is
  populated. This is a display+edit surface only; the server
  (`crm.api.koszty.volteo_koszty_zapisz`) is the sole source of truth once
  saved and re-derives every figure from what was actually sent, never from
  what this component displayed.

  All the live math (fallback to plan, delta, marża/zysk) is display-only
  and lives in `@/utils/montazKoszty.js` — see that file's header for why
  Number (not Decimal) is fine here.

  Reactive state is declared up front with explicit `null`/`{}`/`[]`
  defaults and is always REPLACED wholesale (`x.value = newThing`), never
  read via `hasOwnProperty`/`in` — see the header comment in
  DokumentyLista.vue and the trap writeup in ZestawTab.vue: a `computed`
  built on a `hasOwnProperty` read against a `reactive()`/`ref()` object
  registers no dependency and freezes at first evaluation. Plain property
  `get`/`set` (as used throughout this file) is unaffected — only the
  presence-check traps are the problem.
-->
<template>
  <div v-if="snapshot" class="mt-4">
    <button
      type="button"
      class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
      @click="expanded = !expanded"
    >
      <span>{{ __('Koszty i marża — widoczne tylko dla administratorów') }}</span>
      <FeatherIcon :name="expanded ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
    </button>

    <div v-show="expanded" class="mt-2 rounded-lg border border-dashed border-outline-amber-3 bg-surface-amber-2 p-3">
      <!-- Cost lines -->
      <div class="mk-head">
        <div>{{ __('Pozycja') }}</div>
        <div>{{ __('Koszt plan') }}</div>
        <div>{{ __('Koszt rzeczywisty') }}</div>
        <div>{{ __('Różnica') }}</div>
      </div>

      <div v-for="linia in wynik.linie" :key="linia.klucz" class="mk-row">
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
        </div>

        <div class="mk-cell">
          <span class="mk-mobile-label">{{ __('Koszt rzeczywisty') }}: </span>
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

        <div class="mk-cell tabular-nums" :class="deltaClass(linia.delta)">
          <span class="mk-mobile-label">{{ __('Różnica') }}: </span>{{ formatDelta(linia.delta) }}
        </div>
      </div>

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

      <!-- PV-only: read-only planned margin components -->
      <div v-if="snapshot.linia_produktowa === 'pv' && skladnikiMarzy.length" class="mk-section">
        <div class="mk-section-title">{{ __('Składniki marży planowej') }}</div>
        <div v-for="skl in skladnikiMarzy" :key="skl.klucz" class="mk-skladnik-row">
          <span>{{ skl.etykieta }}</span>
          <span class="tabular-nums">{{ formatPln(skl.kwota) }}</span>
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
          <span>{{ __('Koszt — plan') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.kosztPlan) }}</span>
        </div>
        <div class="mk-summary-row">
          <span>{{ __('Koszt — rzeczywisty') }}</span>
          <span class="font-medium tabular-nums">{{ formatPln(wynik.razem.kosztRzeczywisty) }}</span>
        </div>
        <div class="mk-summary-row">
          <span>{{ __('Marża — plan') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.marzaPlan) }}</span>
        </div>
        <div class="mk-summary-row mk-summary-highlight">
          <span>{{ __('Marża — rzeczywista') }}</span>
          <span class="tabular-nums font-semibold" :class="compareClass(wynik.razem.marzaRzeczywista, wynik.razem.marzaPlan)">
            {{ formatPln(wynik.razem.marzaRzeczywista) }}
          </span>
        </div>
        <template v-if="wynik.razem.prowizjaPlan !== null">
          <div class="mk-summary-row">
            <span>{{ __('Prowizja — plan') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.prowizjaPlan) }}</span>
          </div>
        </template>
        <div class="mk-summary-row">
          <span>{{ __('Zysk — plan') }}</span><span class="tabular-nums">{{ formatPln(wynik.razem.zyskPlan) }}</span>
        </div>
        <div class="mk-summary-row mk-summary-highlight">
          <span>{{ __('Zysk — rzeczywisty') }}</span>
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
import { parseSnapshot, przeliczRzeczywiste, zbudujPayload } from '@/utils/montazKoszty'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- State (declared up front, always replaced wholesale — never mutated
// in place beyond a single leaf key/value set, and never read via
// hasOwnProperty/in; see header comment above). --------------------------
const snapshot = ref(null) // parsed custom_koszty_json, or null (see header)
const edycje = ref({}) // klucz -> raw typed "koszt rzeczywisty" string
const dodatkowe = ref([]) // [{id?, nazwa, kwota}] — raw, in-progress
const expanded = ref(false) // collapsed by default (screenshare-safe, mirrors KalkulatorTab.vue)
const saving = ref(false)

// --- Load -------------------------------------------------------------------
// Permlevel-2 field: Frappe drops `custom_koszty_json` from the response
// entirely for any role without read access, so a non-admin's fetch
// SUCCEEDS with the key simply absent — there is no error path to handle
// here for the "not an admin" case, only for genuine fetch failures, and
// both end up rendering nothing (parseSnapshot(undefined) -> null).
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
 * load, or the server's response after a successful save). Never mutates
 * the previous state in place.
 */
function seedFromSnapshot(nowySnapshot) {
  snapshot.value = nowySnapshot

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
const skladnikiMarzy = computed(() => snapshot.value?.skladniki_marzy || [])

function jednostkaLabel(jednostka) {
  return jednostka === 'm2' ? 'm²' : jednostka || ''
}

function formatDelta(delta) {
  const formatted = formatPln(delta)
  return delta > 0 ? `+${formatted}` : formatted
}

function deltaClass(delta) {
  if (delta > 0) return 'text-ink-red-6'
  if (delta < 0) return 'text-ink-green-6'
  return 'text-ink-gray-6'
}

// Actual vs plan comparison for the summary highlight rows: a lower actual
// margin/profit than planned is a red flag (cost overrun ate into it), a
// higher one is a green result — equal stays neutral gray.
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
// method, not a Server Script, and a bare method name resolves only for
// Server Scripts (see the api-call-path trap documented in UmowaTab.vue —
// AudytTab.vue's Server Script calls by bare name look like a valid pattern
// to copy here and silently are not, producing an HTTP 417 at runtime).
async function zapiszKoszty() {
  // Belt and braces alongside the disabled-button binding above (guards
  // Enter-key submits and any other path that bypasses the button's
  // :disabled state): a garbage/negative line value would silently CLEAR a
  // previously saved actual (zbudujPayload sends null for it), and an
  // invalid/over-length dodatkowa row would silently DROP a previously
  // saved row from the full-replacement payload. Never save while `bledy`
  // is non-empty.
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

// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) — but that
// pattern was blind to the actual shape of errors thrown by frappe-ui's
// call() (see frontend/node_modules/frappe-ui/src/utils/frappeRequest.js
// ~L82-124): call() consumes _server_messages itself and re-throws an
// error whose `message` is just "{url} {exc_type}" and whose `messages` is
// the already-parsed array of server message strings (the Polish text
// lives there, not under `_server_messages`/`exception`). Without the
// `err.messages` branch below, the name-mismatch ValidationError always
// fell through to the raw "{url} {exc_type}" fallback instead of the
// server's Polish message. The old `_server_messages`/`exception` branches
// are kept as a fallback for any caller that isn't call().
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Nie udało się zapisać kosztów rzeczywistych')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Nie udało się zapisać kosztów rzeczywistych')
    }
    if (err && err.messages && err.messages.length) return err.messages[0]
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Nie udało się zapisać kosztów rzeczywistych')
}
</script>

<style scoped>
/* Column layout on desktop; collapses to a single stacked column per row on
   narrow viewports (ZestawTab, which mounts this panel, also renders inside
   MobileDeal.vue — same self-responsive behaviour applies there, no
   layout change needed on the move from MontazTab.vue). Mirrors the amber
   "admin only" treatment already used across the deal tabs
   (KalkulatorTab.vue, KalkulatorCPTab.vue, ZestawTab.vue), and the
   `.kalk-input` editable-cell styling from KalkulatorCPTab.vue's
   commission-modeling sandbox. */
.mk-head {
  display: grid;
  grid-template-columns: minmax(160px, 2fr) minmax(90px, 1fr) minmax(150px, 1fr) minmax(90px, 1fr);
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
  grid-template-columns: minmax(160px, 2fr) minmax(90px, 1fr) minmax(150px, 1fr) minmax(90px, 1fr);
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
