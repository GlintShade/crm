<!-- Wybor wielu osob (ops#411, "Do wiadomosci" w TaskModal.vue): pole wygladem jak
  wybor osoby odpowiedzialnej, lista z wyszukiwaniem i awatarami (klik przelacza,
  lista zostaje otwarta), wybrani jako chipy POD polem. Wartosc: wiersze `[{user}]`. -->
<template>
  <div ref="korzen" class="min-w-0">
    <button
      type="button"
      class="flex h-7 w-full items-center justify-between gap-2 rounded bg-surface-gray-2 px-2 text-left text-base text-ink-gray-4 transition-colors hover:bg-surface-gray-3"
      data-testid="wybor-osob-pole"
      :aria-expanded="otwarte"
      @click="otwarte = !otwarte"
      @keydown.esc.stop="otwarte = false"
    >
      <span class="truncate">{{ placeholder || __('Dodaj osoby') }}</span>
      <FeatherIcon
        name="chevron-down"
        class="h-4 w-4 shrink-0 transition-transform"
        :class="otwarte ? 'rotate-180' : ''"
      />
    </button>

    <!-- Lista INLINE pod polem (bez teleportu): w otwartym oknie zadania (Dialog) panel
      w #frappeui-popper-root dostawal pointer-events: none, a klik w niego byl dla Dialogu
      "poza oknem" i zamykal je. W normalnym przeplywie nic nie przycina i nie zaslania
      chipow: lista rozpycha kolumne, a ta przewija sie pionowo. -->
    <div
      v-if="otwarte"
      class="mt-1 min-w-0 rounded-lg bg-surface-elevation-2 p-1.5 text-base shadow-sm ring-1 ring-outline-gray-2"
      data-testid="wybor-osob-lista"
      @keydown.esc.stop="otwarte = false"
    >
      <input
        ref="poleSzukaj"
        v-model="szukaj"
        type="text"
        class="form-input mb-1 w-full"
        :placeholder="__('Szukaj osoby')"
        data-testid="wybor-osob-szukaj"
      />
      <div class="max-h-[12rem] overflow-y-auto overflow-x-hidden">
        <div v-if="!opcje.length" class="px-2 py-1 text-base text-ink-gray-5">
          {{ __('Brak wyników') }}
        </div>
        <button
          v-for="o in opcje"
          :key="o.name"
          type="button"
          class="flex w-full min-w-0 items-center gap-2 rounded px-2 py-1 text-left text-base text-ink-gray-8 hover:bg-surface-gray-3"
          :title="o.name"
          :data-testid="`wybor-osob-opcja-${o.name}`"
          @click="przelacz(o.name)"
        >
          <UserAvatar :user="o.name" size="sm" />
          <span class="min-w-0 flex-1 truncate">{{ o.full_name || o.name }}</span>
          <FeatherIcon
            v-if="wybrane.includes(o.name)"
            name="check"
            class="h-4 w-4 shrink-0"
            data-testid="wybor-osob-check"
          />
        </button>
      </div>
    </div>

    <div
      v-if="chipy.length"
      class="mt-2 flex max-h-[7.5rem] min-w-0 flex-wrap gap-1 overflow-y-auto overflow-x-hidden"
      data-testid="wybor-osob-chipy"
    >
      <span
        v-for="c in chipy"
        :key="c.login"
        class="flex min-w-0 items-center gap-1 rounded bg-surface-gray-3 py-0.5 pl-1 pr-1 text-sm text-ink-gray-8"
        style="max-width: 100%"
        :title="c.login"
      >
        <UserAvatar :user="c.login" size="xs" class="shrink-0" />
        <span class="min-w-0 truncate">{{ c.nazwa }}</span>
        <button
          type="button"
          class="shrink-0 rounded text-ink-gray-5 hover:text-ink-gray-9"
          :aria-label="__('Usuń osobę')"
          @click="przelacz(c.login)"
        >
          <FeatherIcon name="x" class="h-3.5 w-3.5" />
        </button>
      </span>
    </div>
  </div>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'
import {
  chipyOsob,
  loginyZWierszy,
  opcjeOsob,
  przelaczOsobe,
} from '@/utils/wyborOsob'
import { FeatherIcon } from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  // Osoba odpowiedzialna: nie jest oferowana (serwer i tak by ja usunal z listy).
  wykonawca: { type: String, default: null },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const { getUser, users } = usersStore()
const poleSzukaj = ref(null)
const otwarte = ref(false)
const szukaj = ref('')

const korzen = ref(null)
// Klik poza polem i lista (ale wewnatrz okna) zamyka liste; chipy tez sa "w srodku".
function poza(e) {
  if (otwarte.value && !korzen.value?.contains(e.target)) otwarte.value = false
}
onMounted(() => document.addEventListener('mousedown', poza, true))
onBeforeUnmount(() => document.removeEventListener('mousedown', poza, true))

// Po otwarciu fokus na wyszukiwarce (zwykly <input>, nie komponent frappe-ui).
watch(otwarte, (o) => {
  if (o) nextTick(() => poleSzukaj.value?.focus())
  else szukaj.value = ''
})

// `users.data?.crmUsers` wprost (nie destrukturyzowany computed), jak w TaskModal.vue.
const opcje = computed(() =>
  opcjeOsob(users.data?.crmUsers, props.wykonawca, szukaj.value),
)
const wybrane = computed(() => loginyZWierszy(props.modelValue))
const chipy = computed(() => chipyOsob(props.modelValue, getUser))

function przelacz(login) {
  emit('update:modelValue', przelaczOsobe(props.modelValue, login))
}
</script>
