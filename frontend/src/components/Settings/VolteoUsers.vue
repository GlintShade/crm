<template>
  <div class="flex h-full flex-col gap-8 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
        {{ __('Konta Volteo') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Zakładaj konta i zmieniaj role bez wysyłki zaproszenia e-mail — ta instalacja nie ma skonfigurowanej skrzynki pocztowej.',
          )
        }}
      </p>
    </div>

    <!-- Create account -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Nowe konto') }}</div>
      <div class="grid grid-cols-2 gap-4 max-w-2xl">
        <FormControl
          v-model="createForm.email"
          type="email"
          :label="__('E-mail')"
          placeholder="jan.kowalski@proenergy.pro"
          :disabled="createUser.loading"
        />
        <FormControl
          v-model="createForm.rola"
          type="select"
          :label="__('Rola')"
          :options="roleOptions"
          :disabled="createUser.loading"
        />
        <FormControl
          v-model="createForm.imie"
          type="text"
          :label="__('Imię')"
          placeholder="Jan"
          :disabled="createUser.loading"
        />
        <FormControl
          v-model="createForm.nazwisko"
          type="text"
          :label="__('Nazwisko')"
          placeholder="Kowalski"
          :disabled="createUser.loading"
        />
      </div>
      <ErrorMessage class="max-w-2xl" :message="createError" />
      <div>
        <Button
          :label="__('Utwórz konto')"
          variant="solid"
          icon-left="user-plus"
          :loading="createUser.loading"
          @click="submitCreate"
        />
      </div>
    </div>

    <div class="border-t mx-2" />

    <!-- Change role -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Zmiana roli istniejącego użytkownika') }}</div>
      <p class="text-p-sm text-ink-gray-5 max-w-2xl">
        {{
          __(
            'Zmiana roli nadpisuje wcześniejszą rolę Volteo tego użytkownika. Rola „Sales User” pozostaje przypisana niezależnie od wyboru poniżej.',
          )
        }}
      </p>
      <div class="grid grid-cols-2 gap-4 max-w-2xl">
        <FormControl
          v-model="roleForm.email"
          type="email"
          :label="__('E-mail')"
          placeholder="jan.kowalski@proenergy.pro"
          :disabled="changeRole.loading"
        />
        <FormControl
          v-model="roleForm.rola"
          type="select"
          :label="__('Nowa rola')"
          :options="roleOptions"
          :disabled="changeRole.loading"
        />
      </div>
      <ErrorMessage class="max-w-2xl" :message="roleError" />
      <div>
        <Button
          :label="__('Zmień rolę')"
          variant="solid"
          icon-left="refresh-cw"
          :loading="changeRole.loading"
          @click="submitRoleChange"
        />
      </div>
    </div>

    <div class="border-t mx-2" />

    <!-- Product-line access switch (issue #16) + Leady module switch (issue #27) -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Dostęp do linii produktowych') }}</div>
      <p class="text-p-sm text-ink-gray-5 max-w-2xl">
        {{
          __(
            'Wyłączenie linii ukrywa Kalkulator i Dokumenty tej linii dla wskazanego użytkownika i blokuje jej użycie po stronie serwera. Wyłączenie „Leady” ukrywa moduł Leady (listę i mapę) i blokuje przydzielanie temu użytkownikowi. Nie dotyczy kont System Manager / Volteo Core Admin / Volteo Backend — te zawsze mają pełny dostęp.',
          )
        }}
      </p>
      <div class="grid grid-cols-2 gap-4 max-w-2xl items-end">
        <FormControl
          v-model="linieForm.email"
          type="email"
          :label="__('E-mail')"
          placeholder="jan.kowalski@proenergy.pro"
          :disabled="setLinie.loading"
        />
        <div class="flex flex-col gap-2">
          <FormControl
            type="checkbox"
            :label="__('Linia OZE')"
            :modelValue="Boolean(linieForm.oze)"
            :disabled="setLinie.loading"
            @update:modelValue="(val) => (linieForm.oze = val ? 1 : 0)"
          />
          <FormControl
            type="checkbox"
            :label="__('Linia Czyste Powietrze')"
            :modelValue="Boolean(linieForm.cp)"
            :disabled="setLinie.loading"
            @update:modelValue="(val) => (linieForm.cp = val ? 1 : 0)"
          />
          <FormControl
            type="checkbox"
            :label="__('Leady')"
            :modelValue="Boolean(linieForm.leady)"
            :disabled="setLinie.loading"
            @update:modelValue="(val) => (linieForm.leady = val ? 1 : 0)"
          />
        </div>
      </div>
      <p v-if="linieHint" class="text-p-sm text-ink-gray-5 max-w-2xl">{{ linieHint }}</p>
      <ErrorMessage class="max-w-2xl" :message="linieError" />
      <div>
        <Button
          :label="__('Zapisz dostęp')"
          variant="solid"
          icon-left="check"
          :loading="setLinie.loading"
          @click="submitLinie"
        />
      </div>
    </div>

    <div class="border-t mx-2" />

    <!-- Commission visibility + tier (issue #51) -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Prowizje') }}</div>
      <p class="text-p-sm text-ink-gray-5 max-w-2xl">
        {{
          __(
            'Wyłączenie widoczności ukrywa dane o prowizji w kalkulatorze Czyste Powietrze dla wskazanego użytkownika. Poziom decyduje o tym, która stawka nadprowizji się do niego stosuje. Nie dotyczy kont System Manager / Volteo Core Admin / Volteo Backend — te zawsze widzą prowizje.',
          )
        }}
      </p>
      <div class="grid grid-cols-2 gap-4 max-w-2xl items-end">
        <FormControl
          v-model="prowizjeForm.email"
          type="email"
          :label="__('E-mail')"
          placeholder="jan.kowalski@proenergy.pro"
          :disabled="setProwizje.loading"
        />
        <FormControl
          v-model="prowizjeForm.poziom"
          type="select"
          :label="__('Poziom prowizji')"
          :options="poziomProwizjiOptions"
          :disabled="setProwizje.loading"
        />
        <FormControl
          type="checkbox"
          :label="__('Widzi prowizje')"
          :modelValue="Boolean(prowizjeForm.widzi)"
          :disabled="setProwizje.loading"
          @update:modelValue="(val) => (prowizjeForm.widzi = val ? 1 : 0)"
        />
      </div>
      <p v-if="prowizjeHint" class="text-p-sm text-ink-gray-5 max-w-2xl">{{ prowizjeHint }}</p>
      <ErrorMessage class="max-w-2xl" :message="prowizjeError" />
      <div>
        <Button
          :label="__('Zapisz prowizje')"
          variant="solid"
          icon-left="check"
          :loading="setProwizje.loading"
          @click="submitProwizje"
        />
      </div>
    </div>

    <!-- Password reveal dialog: shown exactly once, right after account creation -->
    <Dialog
      v-model:open="showPasswordDialog"
      :title="__('Konto utworzone')"
      :dismissible="false"
      :size="'md'"
      @close="closePasswordDialog"
    >
      <template #default>
        <div class="flex flex-col gap-4">
          <div class="flex gap-2 border rounded p-3 text-ink-red-6 bg-surface-red-1">
            <span class="lucide-alert-triangle size-4 mt-0.5 shrink-0" aria-hidden="true" />
            <p class="text-p-sm">
              {{
                __(
                  'To hasło pokazuje się tylko raz i nie da się go później odzyskać. Przekaż je nowemu użytkownikowi innym kanałem (np. rozmowa, SMS) — nie zostanie zapisane w CRM.',
                )
              }}
            </p>
          </div>

          <div class="flex flex-col gap-1">
            <label class="block text-xs text-ink-gray-5">{{ __('Użytkownik') }}</label>
            <div class="text-p-base text-ink-gray-8">{{ createdAccount.user }}</div>
          </div>

          <div class="flex flex-col gap-1">
            <label class="block text-xs text-ink-gray-5">{{ __('Hasło') }}</label>
            <div
              class="flex items-center justify-between gap-2 p-2 rounded bg-surface-gray-2 font-mono text-p-base text-ink-gray-8"
            >
              <span class="select-all break-all">{{ createdAccount.haslo }}</span>
              <Button
                :label="__('Kopiuj')"
                variant="ghost"
                icon-left="copy"
                @click="copyToClipboard(createdAccount.haslo)"
              />
            </div>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end">
          <Button
            :label="__('Hasło przekazałem, zamknij')"
            variant="solid"
            @click="closePasswordDialog"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { createResource, toast, Dialog, ErrorMessage } from 'frappe-ui'
import { validateEmail, copyToClipboard } from '@/utils'
import { usersStore } from '@/stores/users'

const { getUser, allUsers } = usersStore()

// Exactly the four Volteo roles the server accepts. Never offer
// "System Manager" here — the server refuses it, and listing it would be
// misleading.
const VOLTEO_ROLES = [
  { value: 'Volteo D2D Sales', label: __('Volteo D2D Sales') },
  { value: 'Volteo Backend', label: __('Volteo Backend') },
  { value: 'Volteo Ecom Sales', label: __('Volteo Ecom Sales') },
  { value: 'Volteo Core Admin', label: __('Volteo Core Admin') },
]

const roleOptions = computed(() => VOLTEO_ROLES)

// --- Create account ---------------------------------------------------

function emptyCreateForm() {
  return {
    email: '',
    imie: '',
    nazwisko: '',
    rola: VOLTEO_ROLES[0].value,
  }
}

const createForm = reactive(emptyCreateForm())
const createError = ref('')

// Holds the one-time server response so the reveal dialog can render it.
// Cleared as soon as the dialog is consciously closed — never persisted,
// never logged.
const createdAccount = reactive({ user: '', haslo: '' })
const showPasswordDialog = ref(false)

const createUser = createResource({
  url: 'crm.api.volteo_uzytkownicy.volteo_utworz_uzytkownika',
  makeParams: () => ({
    email: createForm.email.trim(),
    imie: createForm.imie.trim(),
    nazwisko: createForm.nazwisko.trim(),
    rola: createForm.rola,
  }),
  onSuccess: (data) => {
    createdAccount.user = data.user
    createdAccount.haslo = data.haslo
    showPasswordDialog.value = true
    createError.value = ''
    Object.assign(createForm, emptyCreateForm())
    toast.success(__('Konto {0} zostało utworzone', [data.user]))
  },
  onError: (err) => {
    createError.value = err?.messages?.[0] || __('Nie udało się utworzyć konta')
  },
})

function submitCreate() {
  createError.value = ''

  if (!createForm.email.trim() || !createForm.imie.trim() || !createForm.nazwisko.trim()) {
    createError.value = __('Wypełnij e-mail, imię i nazwisko')
    return
  }
  if (!validateEmail(createForm.email.trim())) {
    createError.value = __('Podaj poprawny adres e-mail')
    return
  }
  if (!createForm.rola) {
    createError.value = __('Wybierz rolę')
    return
  }

  createUser.submit()
}

function closePasswordDialog() {
  showPasswordDialog.value = false
  // Wipe the one-time secret from reactive state the moment the dialog is
  // dismissed — nothing about it may outlive this screen.
  createdAccount.user = ''
  createdAccount.haslo = ''
}

// --- Change role --------------------------------------------------------

function emptyRoleForm() {
  return {
    email: '',
    rola: VOLTEO_ROLES[0].value,
  }
}

const roleForm = reactive(emptyRoleForm())
const roleError = ref('')

const changeRole = createResource({
  url: 'crm.api.volteo_uzytkownicy.volteo_zmien_role',
  makeParams: () => ({
    email: roleForm.email.trim(),
    rola: roleForm.rola,
  }),
  onSuccess: (data) => {
    roleError.value = ''
    toast.success(__('Rola użytkownika {0} została zmieniona', [data.user]))
    Object.assign(roleForm, emptyRoleForm())
  },
  onError: (err) => {
    roleError.value = err?.messages?.[0] || __('Nie udało się zmienić roli')
  },
})

function submitRoleChange() {
  roleError.value = ''

  if (!roleForm.email.trim()) {
    roleError.value = __('Podaj e-mail użytkownika')
    return
  }
  if (!validateEmail(roleForm.email.trim())) {
    roleError.value = __('Podaj poprawny adres e-mail')
    return
  }
  if (!roleForm.rola) {
    roleError.value = __('Wybierz rolę')
    return
  }

  changeRole.submit()
}

// --- Product-line access switch (issue #16) + Leady module switch (issue #27) --

function emptyLinieForm() {
  return {
    email: '',
    oze: 1,
    cp: 1,
    // Default OFF, unlike oze/cp above — matches the safe-rollout default
    // recommended for issue #27 (ops/crm-linia-leady.py: BACKFILL_DOMYSLNA=0).
    // Unchecked by default so a blind save (no matched user, or admin who
    // doesn't touch the checkbox) never grants Leady access by accident.
    leady: 0,
  }
}

const linieForm = reactive(emptyLinieForm())
const linieError = ref('')

// Looked up WITHOUT calling getUser() directly on arbitrary typed text —
// getUser() synthesizes and permanently caches a stub entry (role: null, no
// custom_linia_* fields) for any email it doesn't already know, which would
// pollute the store with junk on every keystroke of a typo/in-progress email.
// allUsers (crm.api.session.get_users, USER_FIELDS incl. custom_linia_oze/cp)
// is searched first; only once a real match is confirmed is getUser(email)
// called, which then just returns that same cached record safely.
const linieMatchedUser = computed(() => {
  const email = linieForm.email.trim()
  if (!email) return null
  return (allUsers.value || []).find((u) => u.name === email) || null
})

const linieHint = computed(() => {
  const email = linieForm.email.trim()
  if (!email || !validateEmail(email)) return ''
  return linieMatchedUser.value
    ? __('Aktualne ustawienia wczytane dla {0}', [email])
    : __(
        'Nie znaleziono użytkownika o takim adresie — przy zapisie zostaną użyte wartości z formularza.',
      )
})

// Prefill the checkboxes from the matched user's CURRENT flags the moment a
// match is found, instead of leaving the admin editing blind against the
// form defaults — a 0 set by a previous admin decision must not be silently
// re-enabled just because the form defaults to "on". Undefined treated as 1
// for oze/cp (pre-ops-script data, before custom_linia_oze/cp existed on the
// site — the pre-#16 behaviour was unrestricted access). Undefined treated
// as 0 for leady (issue #27's safe-rollout default — there is no
// pre-existing "everyone already had it" behaviour to preserve for a module
// that never had per-user access control before).
watch(
  () => linieForm.email,
  () => {
    const user = linieMatchedUser.value
    if (!user) return
    const cached = getUser(user.name) // safe: match already confirmed above
    linieForm.oze = cached.custom_linia_oze === undefined ? 1 : cached.custom_linia_oze ? 1 : 0
    linieForm.cp = cached.custom_linia_cp === undefined ? 1 : cached.custom_linia_cp ? 1 : 0
    linieForm.leady = cached.custom_linia_leady ? 1 : 0
  },
)

const setLinie = createResource({
  url: 'crm.api.volteo_uzytkownicy.volteo_ustaw_linie',
  makeParams: () => ({
    email: linieForm.email.trim(),
    oze: linieForm.oze ? 1 : 0,
    cp: linieForm.cp ? 1 : 0,
    leady: linieForm.leady ? 1 : 0,
  }),
  onSuccess: (data) => {
    linieError.value = ''
    toast.success(__('Dostęp do linii produktowych zapisany dla {0}', [data.user]))
    // Mutate the store's cached record in place (same object reference the
    // fast-fetch resource, usersByName and getUser() all share) so a second
    // edit of the same user prefills the just-saved values, not the stale
    // ones from before this save.
    const target = (allUsers.value || []).find((u) => u.name === data.user)
    if (target) {
      target.custom_linia_oze = data.custom_linia_oze
      target.custom_linia_cp = data.custom_linia_cp
      target.custom_linia_leady = data.custom_linia_leady
    }
    Object.assign(linieForm, emptyLinieForm())
  },
  onError: (err) => {
    linieError.value = err?.messages?.[0] || __('Nie udało się zapisać dostępu do linii')
  },
})

function submitLinie() {
  linieError.value = ''

  if (!linieForm.email.trim()) {
    linieError.value = __('Podaj e-mail użytkownika')
    return
  }
  if (!validateEmail(linieForm.email.trim())) {
    linieError.value = __('Podaj poprawny adres e-mail')
    return
  }

  setLinie.submit()
}

// --- Commission visibility + tier (issue #51) --------------------------

// Mirrors crm.api.VOLTEO_POZIOMY_PROWIZJI — kept as a local literal here
// the same way the backend keeps its own copy in crm_invitation.py, since
// the frontend has no shared import path into that backend module.
const POZIOMY_PROWIZJI = ['Handlowiec', 'Manager', 'Partner']

const poziomProwizjiOptions = computed(() =>
  POZIOMY_PROWIZJI.map((poziom) => ({ value: poziom, label: __(poziom) })),
)

function emptyProwizjeForm() {
  return {
    email: '',
    widzi: 1,
    poziom: 'Handlowiec',
  }
}

const prowizjeForm = reactive(emptyProwizjeForm())
const prowizjeError = ref('')

// Same lookup discipline as linieMatchedUser above: never call getUser() on
// arbitrary typed text (stub-cache trap), only on an email already
// confirmed present in allUsers.
const prowizjeMatchedUser = computed(() => {
  const email = prowizjeForm.email.trim()
  if (!email) return null
  return (allUsers.value || []).find((u) => u.name === email) || null
})

const prowizjeHint = computed(() => {
  const email = prowizjeForm.email.trim()
  if (!email || !validateEmail(email)) return ''
  return prowizjeMatchedUser.value
    ? __('Aktualne ustawienia wczytane dla {0}', [email])
    : __(
        'Nie znaleziono użytkownika o takim adresie — przy zapisie zostaną użyte wartości z formularza.',
      )
})

// Prefill from the matched user's CURRENT settings, same fail-open display
// as the linie section: undefined custom_widzi_prowizje is treated as
// visible (1) rather than hidden (0), since a `User` row predating
// ops/crm-prowizje-uzytkownik.py should read the same as an explicit
// default-on value, matching the schema's own Check default 1. An
// unrecognised/missing poziom falls back to "Handlowiec", the narrowest
// tier — same rule as the backend's volteo_poziom_prowizji().
watch(
  () => prowizjeForm.email,
  () => {
    const user = prowizjeMatchedUser.value
    if (!user) return
    const cached = getUser(user.name) // safe: match already confirmed above
    prowizjeForm.widzi = cached.custom_widzi_prowizje === 0 ? 0 : 1
    prowizjeForm.poziom = POZIOMY_PROWIZJI.includes(cached.custom_poziom_prowizji)
      ? cached.custom_poziom_prowizji
      : 'Handlowiec'
  },
)

const setProwizje = createResource({
  url: 'crm.api.volteo_uzytkownicy.volteo_ustaw_prowizje',
  makeParams: () => ({
    email: prowizjeForm.email.trim(),
    widzi_prowizje: prowizjeForm.widzi ? 1 : 0,
    poziom_prowizji: prowizjeForm.poziom,
  }),
  onSuccess: (data) => {
    prowizjeError.value = ''
    toast.success(__('Ustawienia prowizji zapisane dla {0}', [data.user]))
    // Mutate the store's cached record in place — same pattern as setLinie
    // above — so a second edit of the same user prefills the just-saved
    // values, not the stale ones from before this save.
    const target = (allUsers.value || []).find((u) => u.name === data.user)
    if (target) {
      target.custom_widzi_prowizje = data.custom_widzi_prowizje
      target.custom_poziom_prowizji = data.custom_poziom_prowizji
    }
    Object.assign(prowizjeForm, emptyProwizjeForm())
  },
  onError: (err) => {
    prowizjeError.value = err?.messages?.[0] || __('Nie udało się zapisać ustawień prowizji')
  },
})

function submitProwizje() {
  prowizjeError.value = ''

  if (!prowizjeForm.email.trim()) {
    prowizjeError.value = __('Podaj e-mail użytkownika')
    return
  }
  if (!validateEmail(prowizjeForm.email.trim())) {
    prowizjeError.value = __('Podaj poprawny adres e-mail')
    return
  }

  setProwizje.submit()
}
</script>
