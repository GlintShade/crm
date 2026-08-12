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
import { reactive, ref, computed } from 'vue'
import { createResource, toast, Dialog, ErrorMessage } from 'frappe-ui'
import { validateEmail, copyToClipboard } from '@/utils'

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
</script>
