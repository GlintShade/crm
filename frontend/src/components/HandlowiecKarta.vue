<!--
  Karta "Handlowiec" w panelu bocznym szansy i leada (ops#366): zbudowana jak
  karta "Klient" (KartaSekcji, awatar z inicjalem, e-mail, klikalny telefon).
  Tylko backoffice i administratorzy: dla handlowca i CC komponent sie nie
  renderuje, wiec nie wola tez endpointu (serwer i tak zwroci 403).
  Zrodlo: deal_owner (szansa) albo lead_owner (lead), przekazane jako `wlasciciel`.
-->
<template>
  <div v-if="widoczna" class="shrink-0 px-3 pb-2 pt-3">
    <KartaSekcji
      :label="__('Handlowiec')"
      :nazwa="SEKCJA_HANDLOWIEC"
      :summary="podsumowanie"
      :opened="otwarte"
      @toggle="przelaczOtwarte"
    >
      <div v-if="!wlasciciel" class="text-[12.5px] text-ink-gray-5" data-testid="handlowiec-brak">
        {{ __('Brak przypisanego handlowca') }}
      </div>
      <div
        v-else-if="!mozePobrac"
        class="flex min-w-0 items-center gap-2 text-base leading-5 text-ink-gray-9"
        data-testid="handlowiec-tylko-nazwa"
      >
        <div
          class="flex h-6 w-6 shrink-0 select-none items-center justify-center rounded-full bg-surface-gray-3 text-sm uppercase text-ink-gray-9"
        >
          {{ nazwaWlasciciela?.[0] }}
        </div>
        <span class="truncate">{{ nazwaWlasciciela }}</span>
      </div>
      <div v-else-if="blad" class="text-[12.5px] text-ink-gray-5" data-testid="handlowiec-blad">
        {{ __('Nie udało się pobrać danych handlowca.') }}
      </div>
      <div v-else-if="!dane" class="flex justify-center py-2">
        <LoadingIndicator class="size-4" />
      </div>
      <div v-else class="flex min-w-0 flex-col gap-2" data-testid="handlowiec-dane">
        <div class="flex min-w-0 items-center gap-2 text-base leading-5 text-ink-gray-9">
          <Avatar
            v-if="dane.user_image"
            :label="dane.full_name"
            :image="dane.user_image"
            size="md"
          />
          <div
            v-else
            class="flex h-6 w-6 shrink-0 select-none items-center justify-center rounded-full bg-surface-gray-3 text-sm uppercase text-ink-gray-9"
          >
            {{ dane.full_name?.[0] }}
          </div>
          <span class="truncate">{{ dane.full_name }}</span>
        </div>
        <div v-if="dane.email" class="flex min-w-0 items-center gap-2 text-sm text-ink-gray-7">
          <span class="lucide-mail size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
          <a :href="'mailto:' + dane.email" class="truncate hover:underline" @click.stop>
            {{ dane.email }}
          </a>
        </div>
        <div v-if="telefon" class="flex min-w-0 items-center gap-2 text-sm text-ink-gray-7">
          <span class="lucide-phone size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
          <TelefonLink :numer="telefon" />
        </div>
      </div>
    </KartaSekcji>
  </div>
</template>

<script setup>
import KartaSekcji from '@/components/KartaSekcji.vue'
import TelefonLink from '@/components/TelefonLink.vue'
import { Avatar, LoadingIndicator, createResource } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { useStanSekcjiPanelu } from '@/composables/useStanSekcjiPanelu'
import { SEKCJA_HANDLOWIEC } from '@/utils/stanSekcjiPanelu'
import { czyPobracKontakt } from '@/utils/handlowiecKarta'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  // E-mail (name) przypisanego handlowca: deal_owner albo lead_owner.
  wlasciciel: { type: String, default: '' },
  startZwiniete: { type: Boolean, default: false },
})

const { isVolteoAdmin, isBackend, getUser } = usersStore()
// Ta sama bramka co serwerowe ROLE_ODCZYTU_KONTAKTU (admin, backoffice).
const widoczna = computed(() => isVolteoAdmin() || isBackend())

const stanSekcji = useStanSekcjiPanelu(() => props.doctype)
const otwarte = computed(() =>
  stanSekcji.czyOtwarta(SEKCJA_HANDLOWIEC, !props.startZwiniete),
)
function przelaczOtwarte() {
  stanSekcji.ustaw(SEKCJA_HANDLOWIEC, !otwarte.value)
}

const blad = ref(false)
const zasob = createResource({
  url: 'crm.api.volteo_uzytkownicy.dane_kontaktowe_uzytkownika',
  makeParams: () => ({ email: props.wlasciciel }),
  onSuccess: () => {
    blad.value = false
  },
  onError: () => {
    blad.value = true
  },
})
const mozePobrac = computed(() => czyPobracKontakt(props.wlasciciel))
const nazwaWlasciciela = computed(
  () => (props.wlasciciel && getUser(props.wlasciciel).full_name) || props.wlasciciel,
)
// Dane tylko, gdy naleza do biezacego wlasciciela (po zmianie nie pokazujemy
// poprzedniego handlowca, a spozniona starsza odpowiedz nic nie nadpisuje).
const dane = computed(() =>
  mozePobrac.value && zasob.data?.name === props.wlasciciel ? zasob.data : null,
)
const telefon = computed(() => dane.value?.mobile_no || dane.value?.phone || '')
const podsumowanie = computed(() => {
  if (!props.wlasciciel) return __('Brak przypisanego handlowca')
  if (!mozePobrac.value) return nazwaWlasciciela.value
  return dane.value?.full_name || ''
})

// Odswiezenie po zmianie handlowca ("Doradca" / "Zmien handlowca"); bez
// zapytania dla roli bez dostepu i bez wlasciciela.
watch(
  () => [widoczna.value, props.wlasciciel],
  ([ok, email]) => {
    blad.value = false
    if (ok && czyPobracKontakt(email)) zasob.fetch()
    else zasob.data = null
  },
  { immediate: true },
)
</script>
