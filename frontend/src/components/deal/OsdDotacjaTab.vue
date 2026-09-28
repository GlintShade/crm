<!--
  Zakładki "OSD" i "Dotacja" na szansie OZE (ops#202) - wyglądem identyczne
  z Montażem: karta ręcznego statusu (StatusZakladki.vue) nad strumieniem
  notatek tej zakładki (NotatkiStrumien.vue, issue W2). Ten komponent jest
  czystą kompozycją tych dwóch - cała logika żyje w nich, ten plik dostarcza
  wyłącznie prop `zakladka` do obu i wspólny scrollowany kontener.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <StatusZakladki :deal-id="dealId" :zakladka="zakladka" />
      <NotatkiStrumien :deal-id="dealId" :zakladka="zakladka" />
    </div>
  </div>
</template>

<script setup>
import NotatkiStrumien from '@/components/deal/NotatkiStrumien.vue'
import StatusZakladki from '@/components/deal/StatusZakladki.vue'

defineProps({
  dealId: { type: String, required: true },
  // "OSD" albo "Dotacja" - patrz crm.volteo_osd_dotacja.ZAKLADKI.
  zakladka: { type: String, required: true },
})
</script>
