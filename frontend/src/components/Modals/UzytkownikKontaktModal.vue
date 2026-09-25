<!--
  VOLTEO (ops#188, b63): okno danych kontaktowych konta, otwierane z listy
  Settings -> Uzytkownicy (Users.vue) klikniciem w wiersz. Dla backoffice
  (Volteo Backend) lista jest read-only (brak dropdownu roli, brak menu
  "..."), a to okno pokazuje wylacznie dane kontaktowe: imie i nazwisko,
  e-mail, telefon komorkowy, telefon, czy konto jest wlaczone. Bez roli, bez
  przelozonego, bez linii produktowych, bez prowizji.

  Dane pochodza z crm.api.volteo_uzytkownicy.dane_kontaktowe_uzytkownika
  (bramkowany rola, patrz backend), nie z crm.api.session.get_users, bo tamta
  lista jest odczytywana przez kazdego handlowca i CC przy starcie sesji i
  nie ma zwracac numerow telefonow wszystkim.
-->
<template>
  <Dialog v-model:open="show" :options="{ size: 'sm' }">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
            {{ __('Dane kontaktowe') }}
          </h3>
          <Button
            icon="lucide-x"
            variant="ghost"
            class="w-7"
            @click="show = false"
          />
        </div>

        <div v-if="resource.loading" class="flex justify-center py-4">
          <LoadingIndicator class="size-5" />
        </div>

        <div v-else-if="dane" class="flex flex-col gap-4">
          <div class="flex items-center gap-3">
            <Avatar :image="dane.user_image" :label="dane.full_name" size="xl" />
            <div class="text-lg-medium text-ink-gray-9">
              {{ dane.full_name }}
            </div>
          </div>

          <div class="flex flex-col gap-3">
            <div class="flex flex-col gap-1">
              <div class="text-p-sm text-ink-gray-5">{{ __('E-mail') }}</div>
              <div class="text-base text-ink-gray-8">
                <a :href="'mailto:' + dane.email" class="hover:underline">{{ dane.email }}</a>
              </div>
            </div>

            <div class="flex flex-col gap-1">
              <div class="text-p-sm text-ink-gray-5">{{ __('Telefon komórkowy') }}</div>
              <div class="text-base text-ink-gray-8">
                <TelefonLink v-if="dane.mobile_no" :numer="dane.mobile_no" />
                <span v-else class="text-ink-gray-5">{{ __('brak') }}</span>
              </div>
            </div>

            <div class="flex flex-col gap-1">
              <div class="text-p-sm text-ink-gray-5">{{ __('Telefon') }}</div>
              <div class="text-base text-ink-gray-8">
                <TelefonLink v-if="dane.phone" :numer="dane.phone" />
                <span v-else class="text-ink-gray-5">{{ __('brak') }}</span>
              </div>
            </div>

            <div class="flex flex-col gap-1">
              <div class="text-p-sm text-ink-gray-5">{{ __('Konto') }}</div>
              <div class="text-base text-ink-gray-8">
                <Badge
                  :label="dane.enabled ? __('Aktywne') : __('Wyłączone')"
                  :theme="dane.enabled ? 'green' : 'gray'"
                  variant="subtle"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import TelefonLink from '@/components/TelefonLink.vue'
import { Avatar, Badge, Button, Dialog, LoadingIndicator, createResource, toast } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  email: { type: String, required: true },
})

const show = defineModel({ type: Boolean, default: false })

const resource = createResource({
  url: 'crm.api.volteo_uzytkownicy.dane_kontaktowe_uzytkownika',
  params: { email: props.email },
  auto: true,
  onError: (e) => {
    toast.error(e?.messages?.[0] || __('Nie udało się pobrać danych użytkownika.'))
  },
})

const dane = computed(() => resource.data)
</script>
