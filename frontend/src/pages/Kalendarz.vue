<!--
  Strona /kalendarz (ops#318): nagłówek strony z paskiem nawigacji i treść
  kalendarza z KalendarzWidok.vue, tego samego komponentu co widok "Kalendarz"
  w Leadach (pages/Leads.vue). Stan (tydzień, widok) trzyma KalendarzWidok i
  udostępnia go przez expose, a pasek w LayoutHeader tylko go czyta.
-->
<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <KalendarzPasek
          czesc="lewa"
          :etykieta="kal?.etykieta || ''"
          :widok="kal?.stan.widok"
          @przesun="(k) => kal?.przesun(k)"
          @dzis="kal?.dzis()"
        >
          <template #tytul>
            <span class="text-lg font-semibold text-ink-gray-9">{{
              __('Kalendarz')
            }}</span>
          </template>
        </KalendarzPasek>
      </template>
      <template #right-header>
        <KalendarzPasek
          czesc="prawa"
          :etykieta="kal?.etykieta || ''"
          :widok="kal?.stan.widok"
          @update:widok="(v) => kal && (kal.stan.widok = v)"
          @nowe="kal?.otworzModal({})"
        />
      </template>
    </LayoutHeader>

    <div class="flex-1 overflow-y-auto p-4">
      <KalendarzWidok ref="kal" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePageMeta } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import KalendarzPasek from '@/components/kalendarz/KalendarzPasek.vue'
import KalendarzWidok from '@/components/kalendarz/KalendarzWidok.vue'

usePageMeta(() => ({ title: __('Kalendarz') }))

const kal = ref(null)
</script>
