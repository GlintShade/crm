<template>
  <div class="flex h-full flex-col gap-8 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
        {{ __('Automatyzacje') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Reguły automatycznego przesuwania statusu szansy i powiadomień zespołu. Reguły zakłada wyłącznie skrypt ops — tutaj tylko je włączasz, wybierasz odbiorców i kanały.',
          )
        }}
      </p>
    </div>

    <ErrorMessage class="mx-2" :message="listError" />

    <template v-if="listResource.loading && !state.reguly.length">
      <div class="text-p-sm text-ink-gray-5 px-2">{{ __('Wczytywanie…') }}</div>
    </template>
    <template v-else-if="!state.reguly.length">
      <div class="text-p-sm text-ink-gray-5 px-2">
        {{ __('Brak reguł automatyzacji — zasiewa je skrypt ops.') }}
      </div>
    </template>
    <template v-else>
      <!-- Status automations -->
      <div v-if="regulyStatusu.length" class="flex flex-col gap-4 px-2">
        <div class="text-base-semibold">{{ __('Automatyzacje statusów') }}</div>
        <div class="flex flex-col gap-2 max-w-2xl">
          <div
            v-for="row in regulyStatusu"
            :key="row.klucz"
            class="flex items-center justify-between gap-4 rounded-lg border p-4"
          >
            <p class="text-p-base text-ink-gray-8">{{ row.opis }}</p>
            <Switch
              :modelValue="Boolean(row.wlaczona)"
              :disabled="isSaving(row.klucz)"
              @update:modelValue="(val) => persist(row, { wlaczona: val ? 1 : 0 })"
            />
          </div>
        </div>
      </div>

      <div v-if="regulyStatusu.length && regulyPowiadomien.length" class="border-t mx-2" />

      <!-- Notification rules -->
      <div v-if="regulyPowiadomien.length" class="flex flex-col gap-4 px-2">
        <div class="text-base-semibold">{{ __('Powiadomienia') }}</div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div
            v-for="row in regulyPowiadomien"
            :key="row.klucz"
            class="flex flex-col gap-4 rounded-lg border p-4"
          >
            <div class="flex items-start justify-between gap-4">
              <p class="text-p-base text-ink-gray-8">{{ row.opis }}</p>
              <Switch
                :modelValue="Boolean(row.wlaczona)"
                :disabled="isSaving(row.klucz)"
                @update:modelValue="(val) => persist(row, { wlaczona: val ? 1 : 0 })"
              />
            </div>

            <!-- Recipients -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs-medium text-ink-gray-5">{{ __('Odbiorcy') }}</label>
              <div class="flex flex-wrap items-center gap-1.5">
                <div
                  v-for="email in row.odbiorcy"
                  :key="email"
                  class="flex items-center gap-1.5 rounded-full border border-outline-gray-1 bg-surface-gray-2 py-0.5 pl-1 pr-1.5 text-p-sm text-ink-gray-7"
                >
                  <UserAvatar :user="email" size="sm" />
                  <span>{{ getUser(email).full_name }}</span>
                  <button
                    type="button"
                    class="disabled:opacity-50"
                    :disabled="isSaving(row.klucz)"
                    @click="removeOdbiorca(row, email)"
                  >
                    <span class="lucide-x h-3 w-3 text-ink-gray-6" aria-hidden="true" />
                  </button>
                </div>

                <Autocomplete
                  :options="dostepniUzytkownicy(row)"
                  value=""
                  placement="bottom-start"
                  @change="(option) => addOdbiorca(row, option)"
                >
                  <template #target="{ togglePopover }">
                    <Button
                      variant="ghost"
                      size="sm"
                      icon-left="plus"
                      :label="__('Dodaj odbiorcę')"
                      :disabled="isSaving(row.klucz)"
                      @click="togglePopover"
                    />
                  </template>
                  <template #item-prefix="{ option }">
                    <UserAvatar class="mr-2" :user="option.value" size="sm" />
                  </template>
                  <template #item-label="{ option }">
                    <Tooltip :text="option.value">
                      <div class="cursor-pointer text-ink-gray-9">
                        {{ getUser(option.value).full_name }}
                      </div>
                    </Tooltip>
                  </template>
                </Autocomplete>
              </div>
            </div>

            <FormControl
              type="checkbox"
              :label="__('Przypisany handlowiec')"
              :description="__('dynamicznie: właściciel danej szansy')"
              :modelValue="Boolean(row.odbiorca_handlowiec)"
              :disabled="isSaving(row.klucz)"
              @update:modelValue="(val) => persist(row, { odbiorca_handlowiec: val ? 1 : 0 })"
            />

            <!-- Channels -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs-medium text-ink-gray-5">{{ __('Kanały') }}</label>
              <div class="flex flex-col gap-1.5">
                <FormControl
                  type="checkbox"
                  :label="__('W aplikacji (dzwonek)')"
                  :modelValue="Boolean(row.kanal_bell)"
                  :disabled="isSaving(row.klucz)"
                  @update:modelValue="(val) => persist(row, { kanal_bell: val ? 1 : 0 })"
                />
                <FormControl
                  type="checkbox"
                  class="opacity-60"
                  :label="__('E-mail (wkrótce)')"
                  :modelValue="Boolean(row.kanal_email)"
                  :disabled="isSaving(row.klucz)"
                  @update:modelValue="(val) => persist(row, { kanal_email: val ? 1 : 0 })"
                />
                <FormControl
                  type="checkbox"
                  class="opacity-60"
                  :label="__('SMS (wkrótce)')"
                  :modelValue="Boolean(row.kanal_sms)"
                  :disabled="isSaving(row.klucz)"
                  @update:modelValue="(val) => persist(row, { kanal_sms: val ? 1 : 0 })"
                />
              </div>
            </div>
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
  Tooltip,
  ErrorMessage,
  Button,
  FormControl,
} from 'frappe-ui'
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'

// Reactive state declares every key up front and is always replaced with a
// fresh array on update — never gated on key presence (see CLAUDE.md:
// hasOwnProperty on a reactive() object breaks Vue's dependency tracking
// and froze the CP admin panel for its entire lifetime).
const state = reactive({ reguly: [] })
const listError = ref('')

const { users, getUser } = usersStore()

const listResource = createResource({
  url: 'crm.api.automatyzacje.volteo_automatyzacje_lista',
  auto: true,
  onSuccess: (data) => {
    state.reguly = data || []
    listError.value = ''
  },
  onError: (err) => {
    listError.value = err?.messages?.[0] || __('Nie udało się wczytać reguł automatyzacji')
  },
})

const regulyStatusu = computed(() => state.reguly.filter((row) => row.typ === 'Status'))
const regulyPowiadomien = computed(() => state.reguly.filter((row) => row.typ === 'Powiadomienie'))

function dostepniUzytkownicy(row) {
  const wybrani = new Set(row.odbiorcy || [])
  return (users.data?.crmUsers || [])
    .filter((user) => !wybrani.has(user.name))
    .map((user) => ({ label: user.full_name, value: user.name }))
}

// --- Save (immediate, per-field) -----------------------------------------

// Keyed by `klucz`; read via direct property access only (never
// hasOwnProperty) so Vue's reactive `get` trap keeps tracking each row's
// in-flight state correctly.
const saving = reactive({})

function isSaving(klucz) {
  return Boolean(saving[klucz])
}

function replaceRow(klucz, nextRow) {
  state.reguly = state.reguly.map((row) => (row.klucz === klucz ? nextRow : row))
}

const saveResource = createResource({
  url: 'crm.api.automatyzacje.volteo_automatyzacja_zapisz',
})

function persist(row, patch) {
  const previous = row
  const optimistic = { ...row, ...patch }
  replaceRow(row.klucz, optimistic)
  saving[row.klucz] = true

  saveResource.submit(
    {
      klucz: optimistic.klucz,
      wlaczona: optimistic.wlaczona ? 1 : 0,
      odbiorcy: JSON.stringify(optimistic.odbiorcy || []),
      odbiorca_handlowiec: optimistic.odbiorca_handlowiec ? 1 : 0,
      kanal_bell: optimistic.kanal_bell ? 1 : 0,
      kanal_email: optimistic.kanal_email ? 1 : 0,
      kanal_sms: optimistic.kanal_sms ? 1 : 0,
    },
    {
      onSuccess: (data) => {
        replaceRow(data.klucz, data)
        saving[row.klucz] = false
        toast.success(__('Zapisano'))
      },
      onError: (err) => {
        replaceRow(row.klucz, previous)
        saving[row.klucz] = false
        toast.error(err?.messages?.[0] || __('Nie udało się zapisać'))
      },
    },
  )
}

function addOdbiorca(row, option) {
  const email = option?.value
  if (!email || (row.odbiorcy || []).includes(email)) return
  persist(row, { odbiorcy: [...(row.odbiorcy || []), email] })
}

function removeOdbiorca(row, email) {
  persist(row, { odbiorcy: (row.odbiorcy || []).filter((e) => e !== email) })
}
</script>
