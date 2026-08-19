<template>
  <div
    class="flex min-h-screen flex-col items-center justify-center gap-6 bg-surface-gray-1 px-4 py-10"
  >
    <div class="w-full max-w-2xl rounded-2xl bg-surface-white p-6 sm:p-8">
      <h1 class="text-2xl-semibold text-ink-gray-9">
        {{ __('Oświadczenie o zachowaniu poufności') }}
      </h1>
      <p class="mt-2 text-p-base text-ink-gray-6">
        {{
          __(
            'Aby korzystać z CRM ProEnergy, zapoznaj się z poniższym oświadczeniem i podpisz je, wpisując swoje imię i nazwisko.',
          )
        }}
      </p>

      <div class="my-5 h-px border-t border-outline-gray-2" />

      <!-- Loading: tresc is explicitly null until the fetch resolves, never a
           hasOwnProperty/key-presence check (see CLAUDE.md's Vue-reactive
           trap that froze the CP admin panel for the same reason). -->
      <div
        v-if="tresc === null && !loadError"
        class="flex items-center justify-center gap-2 py-14 text-ink-gray-5"
      >
        <LoadingIndicator class="size-4" />
        <span>{{ __('Wczytywanie oświadczenia…') }}</span>
      </div>

      <div v-else-if="loadError" class="flex flex-col gap-3">
        <ErrorMessage :message="loadError" />
        <Button
          variant="outline"
          :label="__('Spróbuj ponownie')"
          @click="loadOswiadczenie"
        />
      </div>

      <template v-else>
        <div
          class="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4 text-p-base text-ink-gray-8"
        >
          {{ tresc.tresc }}
        </div>

        <div class="mt-5">
          <FormControl
            v-model="imieNazwisko"
            type="text"
            :label="__('Imię i nazwisko')"
            :placeholder="tresc.imie_nazwisko"
            :disabled="signing || signed"
          />
          <p class="mt-1.5 text-p-sm text-ink-gray-5">
            {{ __('Wpisz: {0}', [tresc.imie_nazwisko]) }}
          </p>
        </div>

        <ErrorMessage class="mt-3" :message="signError" />

        <div class="mt-5 flex items-center justify-between gap-4">
          <Button
            variant="ghost"
            :label="__('Wyloguj się')"
            @click="logout.submit()"
          />
          <Button
            variant="solid"
            :label="__('Podpisuję')"
            :loading="signing"
            :disabled="!imieNazwisko.trim() || signing || signed"
            @click="podpisz"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { sessionStore } from '@/stores/session'
import {
  Button,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  call,
  toast,
  usePageMeta,
} from 'frappe-ui'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { logout } = sessionStore()

// Explicit `null` initial state throughout — never a bare reactive
// key-presence check. See CLAUDE.md: hasOwnProperty against a reactive()
// object registers no dependency in Vue's proxy handler and freezes a
// computed at its first read; this page instead gates every branch on an
// explicit ref value (`null` = not yet loaded / failed).
const tresc = ref(null)
const loadError = ref(null)
const imieNazwisko = ref('')
const signing = ref(false)
const signError = ref(null)
const signed = ref(false)

async function loadOswiadczenie() {
  loadError.value = null
  tresc.value = null
  try {
    const data = await call('crm.api.oswiadczenie.volteo_oswiadczenie_tresc')
    tresc.value = data
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  }
}

async function podpisz() {
  if (signing.value || signed.value || !imieNazwisko.value.trim()) return
  signing.value = true
  signError.value = null
  try {
    await call('crm.api.oswiadczenie.volteo_podpisz_oswiadczenie', {
      imie_nazwisko: imieNazwisko.value.trim(),
    })
    signed.value = true
    toast.success(
      __(
        'Podpisano. Kopia dokumentu została wysłana na Twój adres e-mail.',
      ),
    )
    // The boot flag drove the router guard that sent us here; flip it
    // client-side so the guard lets the very next navigation through
    // without waiting for a fresh page boot.
    window.volteo_wymaga_oswiadczenia = false
    router.replace({ name: 'Home' })
  } catch (err) {
    signError.value = extractErrorMessage(err)
  } finally {
    signing.value = false
  }
}

// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) so a Polish
// frappe.throw ValidationError (e.g. the name-mismatch error) surfaces its
// exact server message instead of a generic fallback.
function extractErrorMessage(err) {
  try {
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Wystąpił błąd - spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd - spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd - spróbuj ponownie')
}

onMounted(loadOswiadczenie)

usePageMeta(() => ({ title: __('Oświadczenie o zachowaniu poufności') }))
</script>
