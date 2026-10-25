<!--
  Paragon wyceny kalkulatora OZE (prawa kolumna). Czysta prezentacja: każda
  kwota pochodzi z odpowiedzi serwera (`summary`), tu nie ma matematyki
  cenowej. Jedyne obliczenie to proporcje paska (udzialyCeny), do rysowania.
-->
<template>
  <div v-if="summary.lines.length" class="flex flex-col gap-3">
    <div class="rounded-xl border border-outline-gray-3 bg-surface-gray-1 p-4">
      <template v-if="zUlga">
        <div class="text-xs text-ink-gray-5">{{ pokazDotacje ? 'Klient zapłaci po dotacji i uldze' : 'Klient zapłaci po uldze' }}</div>
        <div class="mt-1 whitespace-nowrap text-3xl font-bold tabular-nums text-ink-gray-9">{{ formatPln(summary.cena_po_uldze) }}</div>
        <div class="mt-1 text-sm text-ink-gray-6">
          <span class="whitespace-nowrap font-semibold tabular-nums text-ink-gray-8">{{ formatPln(summary.raty.po_uldze) }}</span>
          /mies. przez {{ okresLat }} lat
        </div>
      </template>
      <template v-else>
        <div class="text-xs text-ink-gray-5">Cena brutto</div>
        <div class="mt-1 whitespace-nowrap text-3xl font-bold tabular-nums text-ink-gray-9">{{ formatPln(summary.brutto) }}</div>
        <div v-if="pokazRate" class="mt-1 text-sm text-ink-gray-6">
          <span class="whitespace-nowrap font-semibold tabular-nums text-ink-gray-8">{{ formatPln(summary.raty.brutto) }}</span>
          /mies. przez {{ okresLat }} lat
        </div>
      </template>
    </div>

    <template v-if="zUlga">
      <div>
        <div class="mb-1 text-xs text-ink-gray-5">Z ceny brutto {{ formatPln(summary.brutto) }}:</div>
        <div class="flex h-2 overflow-hidden rounded-full bg-surface-gray-3">
          <div class="bg-surface-gray-7" :style="{ width: udzialy.klient + '%' }"></div>
          <div v-if="pokazDotacje" class="bg-surface-green-3" :style="{ width: udzialy.dotacja + '%' }"></div>
          <div class="bg-surface-gray-4" :style="{ width: udzialy.ulga + '%' }"></div>
        </div>
        <div class="mt-1 text-xs text-ink-gray-5">
          klient {{ udzialy.klient }}%<template v-if="pokazDotacje"> · dotacja {{ udzialy.dotacja }}%</template> · ulga {{ udzialy.ulga }}%
        </div>
      </div>

      <div class="text-sm tabular-nums">
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-9">
          <span>Cena netto</span><span class="whitespace-nowrap">{{ formatPln(summary.netto) }}</span>
        </div>
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>VAT {{ summary.vat_rate }}%</span><span class="whitespace-nowrap">{{ formatPln(summary.vat) }}</span>
        </div>
        <div class="mt-0.5 flex justify-between gap-2 border-t border-outline-gray-2 pt-1 font-semibold text-ink-gray-9">
          <span>Cena brutto</span><span class="whitespace-nowrap">{{ formatPln(summary.brutto) }}</span>
        </div>
        <div v-if="pokazDotacje" class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>Dotacja ({{ String(zasadyDotacji || '').toLowerCase() }})</span>
          <span class="whitespace-nowrap text-ink-green-6">− {{ formatPln(summary.dotacja) }}</span>
        </div>
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>Ulga termo. {{ ulgaPct }}%</span>
          <span class="whitespace-nowrap text-ink-green-6">− {{ formatPln(summary.ulga) }}</span>
        </div>
      </div>

      <div class="rounded-lg border border-outline-gray-2 p-2.5 text-sm tabular-nums">
        <div class="mb-1 text-xs text-ink-gray-5">Rata miesięczna, {{ okresLat }} lat</div>
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>Pełna kwota</span><span class="whitespace-nowrap">{{ formatPln(summary.raty.brutto) }}</span>
        </div>
        <div v-if="pokazDotacje" class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>Po dotacji</span><span class="whitespace-nowrap">{{ formatPln(summary.raty.po_dotacji) }}</span>
        </div>
        <div class="flex justify-between gap-2 py-0.5 font-semibold text-ink-gray-9">
          <span>{{ pokazDotacje ? 'Po dotacji i uldze' : 'Po uldze' }}</span><span class="whitespace-nowrap">{{ formatPln(summary.raty.po_uldze) }}</span>
        </div>
      </div>
    </template>

    <div v-else class="text-sm tabular-nums">
      <div class="flex justify-between gap-2 py-0.5 text-ink-gray-9">
        <span>Cena netto</span><span class="whitespace-nowrap">{{ formatPln(summary.netto) }}</span>
      </div>
      <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
        <span>VAT {{ summary.vat_rate }}%</span><span class="whitespace-nowrap">{{ formatPln(summary.vat) }}</span>
      </div>
      <div class="mt-0.5 flex justify-between gap-2 border-t border-outline-gray-2 pt-1 font-semibold text-ink-gray-9">
        <span>Cena brutto</span><span class="whitespace-nowrap">{{ formatPln(summary.brutto) }}</span>
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-2.5 text-sm">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-2 text-left text-xs font-medium text-ink-gray-5 hover:text-ink-gray-7"
        :aria-expanded="skladniki"
        @click="skladniki = !skladniki"
      >
        <span>Składniki ({{ summary.lines.length }})</span>
        <FeatherIcon :name="skladniki ? 'chevron-up' : 'chevron-down'" class="h-3.5 w-3.5 shrink-0" />
      </button>
      <div v-if="skladniki" class="mt-1.5">
        <div
          v-for="(ln, i) in summary.lines" :key="i"
          class="grid grid-cols-[7rem_1fr_auto] items-baseline gap-x-2 border-t border-outline-gray-1 py-1.5 first:border-t-0"
        >
          <span class="break-words text-ink-gray-5">{{ ln.typ }}</span>
          <span class="break-words text-ink-gray-8">{{ ln.nazwa }}</span>
          <span class="text-right tabular-nums text-ink-gray-7">×{{ formatQty(ln.ilosc) }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="text-sm text-ink-gray-5">Uzupełnij konfigurację, aby zobaczyć wycenę.</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { formatPln } from '@/utils/money'
import { udzialyCeny } from '@/utils/pvForm'

const props = defineProps({
  summary: { type: Object, required: true },
  typKlienta: { type: String, default: 'indywidualny' },
  zasadyDotacji: { type: String, default: '' },
  ulgaPct: { type: Number, default: 12 },
  okresLat: { type: Number, default: 10 },
  // Nowe rodzaje OZE (Rozbudowa, Klimatyzacja, Pompa, Kociol) nie maja dotacji;
  // domyslne wartosci zachowuja wyglad paragonu kalkulatora PV.
  pokazDotacje: { type: Boolean, default: true },
  pokazUlge: { type: Boolean, default: true },
  // Rata przy cenie brutto, gdy nie ma ulgi (domyslnie ukryta jak dotad).
  pokazRate: { type: Boolean, default: false },
})

const skladniki = ref(false)
const zUlga = computed(() => props.pokazUlge && props.typKlienta === 'indywidualny')
const udzialy = computed(() => udzialyCeny(props.summary))

function formatQty(q) {
  return String(Number(q) || 0)
}
</script>
