<!--
  Zakładka "Montaż" na szansach OZE (issue #204, migracja Montazu do
  Volteo Notatka) - wyglądem analogiczna do OsdDotacjaTab.vue: galeria
  "Zdjęcia z realizacji" (MontazZdjecia.vue, ops#191, bez zmian) nad
  strumieniem notatek tej zakładki (NotatkiStrumien.vue, zakladka="Montaz",
  issue W2). Ten komponent jest czystą kompozycją tych dwóch - cała logika
  żyje w nich, ten plik dostarcza wyłącznie prop `dealId` do obu i wspólny
  scrollowany kontener.

  WYŁĄCZNIE dla szans OZE - Deal.vue/MobileDeal.vue renderują ten komponent
  tylko gdy `czyOze(doc.custom_rodzaj_umowy)` jest prawdą (lustro
  `crm/volteo_pipeline.py::OZE_RODZAJE`); na Czyste Powietrze zakładka
  Montaż zostaje przy dotychczasowym `AktualizacjeTab` + `Volteo Montaz
  Update` (faza 2 tego strumienia, osobny cykl) - `NotatkiStrumien.vue` samo
  też renderuje `null` dla CP jako druga linia obrony (bramka OZE żyje w
  `NotatkiStrumien.vue`, nie tutaj), ale ten plik i tak nie jest montowany
  na CP dzięki warunkowi w Deal.vue/MobileDeal.vue.

  `NotatkiPrywatne.vue` (issue #213) na samej górze - strumień notatek
  administracji, zupełnie osobny doctype (`Volteo Notatka Prywatna`) od
  `Volteo Notatka` poniżej, widoczny wyłącznie dla System Manager / Volteo
  Core Admin (bramka żyje wewnątrz tamtego komponentu, nie tutaj - dla
  każdego innego użytkownika renderuje `null` i nie wysyła żadnego żądania).
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <NotatkiPrywatne :deal-id="dealId" />
      <MontazZdjecia :deal-id="dealId" />
      <NotatkiStrumien :deal-id="dealId" zakladka="Montaz" />
    </div>
  </div>
</template>

<script setup>
import MontazZdjecia from '@/components/deal/MontazZdjecia.vue'
import NotatkiPrywatne from '@/components/deal/NotatkiPrywatne.vue'
import NotatkiStrumien from '@/components/deal/NotatkiStrumien.vue'

defineProps({
  dealId: { type: String, required: true },
})
</script>
