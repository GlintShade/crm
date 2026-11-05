<!--
  Naglowek panelu bocznego szansy i leada (ops#326): imie klienta, telefon z
  przyciskiem Zadzwon, e-mail, numer rekordu jako chip z kopiowaniem,
  przelacznik "Ukryj puste". Zwijanie panelu to dolna kontrolka strony. Zastepuje dawny 45 px pasek z
  samym numerem rekordu.
-->
<template>
  <div class="flex shrink-0 flex-col gap-1 border-b px-4 py-3" data-testid="panel-naglowek">
    <div class="mb-1 flex min-w-0 items-center gap-1.5">
      <button
        v-if="mozeOtworzyc"
        type="button"
        class="grid h-7 shrink-0 place-items-center pl-2 pr-1 text-ink-gray-5 hover:text-ink-gray-8"
        :title="__('Otwórz klienta')"
        :aria-label="__('Otwórz klienta')"
        data-testid="panel-klient-ikona"
        @click="emit('otworz-klienta')"
      >
        <span class="lucide-user size-3.5" aria-hidden="true" />
      </button>
      <div
        class="min-w-0 flex-1 truncate text-[15px] font-semibold text-ink-gray-9"
        :class="mozeOtworzyc ? 'cursor-pointer hover:underline' : ''"
        :title="imie"
        data-testid="panel-klient-imie"
        @click="mozeOtworzyc && emit('otworz-klienta')"
      >
        {{ imie || __('Brak klienta') }}
      </div>
      <slot name="akcje" />
    </div>
    <div class="flex flex-col items-start gap-1">
      <div v-if="telefon" :class="wiersz" data-testid="panel-telefon-wiersz">
        <button
          v-if="href && wlasneZadzwon"
          type="button"
          :class="glowny"
          :title="__('Zadzwoń')"
          data-testid="panel-telefon"
          @click="emit('zadzwon')"
        >
          <span :class="ikona" class="lucide-phone" aria-hidden="true" />
          <span class="truncate">{{ telefonWyswietlany }}</span>
        </button>
        <a
          v-else-if="href"
          :href="href"
          :class="glowny"
          :title="__('Zadzwoń')"
          data-testid="panel-telefon"
        >
          <span :class="ikona" class="lucide-phone" aria-hidden="true" />
          <span class="truncate">{{ telefonWyswietlany }}</span>
        </a>
        <span v-else :class="glowny" data-testid="panel-telefon">
          <span :class="ikona" class="lucide-phone" aria-hidden="true" />
          <span class="truncate">{{ telefonWyswietlany }}</span>
        </span>
        <button
          type="button"
          :class="kopiuj"
          :title="__('Kopiuj numer telefonu')"
          data-testid="panel-telefon-kopiuj"
          @click.stop.prevent="copyToClipboard(telefonSurowy)"
        >
          <span class="lucide-copy size-3.5" aria-hidden="true" />
        </button>
      </div>
      <div v-if="email" :class="wiersz" data-testid="panel-email-wiersz">
        <a
          :href="'mailto:' + email"
          :class="glowny"
          :title="__('Napisz e-mail')"
          data-testid="panel-email"
        >
          <span :class="ikona" class="lucide-mail" aria-hidden="true" />
          <span class="truncate">{{ email }}</span>
        </a>
        <button
          type="button"
          :class="kopiuj"
          :title="__('Kopiuj e-mail')"
          data-testid="panel-email-kopiuj"
          @click.stop.prevent="copyToClipboard(email)"
        >
          <span class="lucide-copy size-3.5" aria-hidden="true" />
        </button>
      </div>
    </div>
    <div class="flex h-7 min-w-0 items-center gap-2">
      <div :class="wiersz" data-testid="panel-rekord-wiersz">
        <button
          type="button"
          :class="glowny"
          :title="__('Kopiuj numer')"
          data-testid="panel-rekord"
          @click="copyToClipboard(rekord)"
        >
          <UmowaIcon :class="ikona" aria-hidden="true" />
          <span class="truncate">{{ __(rekord) }}</span>
        </button>
        <button
          type="button"
          :class="kopiuj"
          :title="__('Kopiuj numer')"
          data-testid="panel-rekord-kopiuj"
          @click.stop.prevent="copyToClipboard(rekord)"
        >
          <span class="lucide-copy size-3.5" aria-hidden="true" />
        </button>
      </div>
      <div class="ml-auto flex shrink-0 items-center gap-1.5 text-xs text-ink-gray-5">
        <template v-if="pokazSynchronizacjeSekcji">
          <span>{{ __('Synchronizuj') }}</span>
          <Switch size="sm" v-model="synchronizujSekcje" />
        </template>
        <span>{{ __('Ukryj puste') }}</span>
        <Switch size="sm" v-model="ukryjPuste" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button, Switch } from 'frappe-ui'
import UmowaIcon from '@/components/Icons/UmowaIcon.vue'
import { copyToClipboard } from '@/utils'
import { telHref } from '@/utils/telefon'
import { formatTelefon } from '@/utils/panelBoczny'
import { useUkryjPustePola } from '@/composables/useUkryjPustePola'
import { useSynchronizujSekcje } from '@/composables/useSynchronizujSekcje'

const props = defineProps({
  imie: { type: String, default: '' },
  telefon: { type: String, default: '' },
  email: { type: String, default: '' },
  rekord: { type: String, required: true },
  mozeOtworzyc: { type: Boolean, default: false },
  wlasneZadzwon: { type: Boolean, default: false },
  // VOLTEO (b84): przelacznik "Synchronizuj" (sekcje tego panelu vs zakladka
  // "Szczegoly") -- tylko tam, gdzie ten drugi widok istnieje (dzis: lead).
  // Szansa (Deal.vue) tez uzywa tego naglowka, ale bez zakladki "Szczegoly"
  // z wlasnym SidePanelLayout, wiec tam przelacznik zostaje ukryty.
  pokazSynchronizacjeSekcji: { type: Boolean, default: false },
})
const emit = defineEmits(['otworz-klienta', 'zadzwon'])

// Jeden format dla telefonu, e-maila i numeru rekordu.
const wiersz =
  'flex h-7 min-w-0 max-w-full items-center gap-1 rounded-md bg-surface-gray-2 pl-2 pr-1 text-[13px] text-ink-gray-8 hover:bg-surface-gray-3'
const glowny = 'flex h-full min-w-0 items-center gap-1.5'
const ikona = 'size-3.5 shrink-0 text-ink-gray-5'
const kopiuj =
  'grid size-5 shrink-0 place-items-center rounded text-ink-gray-5 hover:text-ink-gray-8'
// Do schowka idzie numer bez spacji, z plusem, jesli byl.
const telefonSurowy = computed(() => {
  const t = (props.telefon || '').trim()
  return (t.startsWith('+') ? '+' : '') + t.replace(/\D/g, '')
})

const { ukryjPuste } = useUkryjPustePola()
const { synchronizujSekcje } = useSynchronizujSekcje()
const href = computed(() => telHref(props.telefon))
const telefonWyswietlany = computed(() => formatTelefon(props.telefon))
</script>
