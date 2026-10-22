<!--
  Paragon wyceny kalkulatora OZE (prawa kolumna). Czysta prezentacja: każda
  kwota pochodzi z odpowiedzi serwera (`summary`), tu nie ma matematyki
  cenowej. Jedyne obliczenie to proporcje paska (udzialyCeny), do rysowania.
-->
<template>
  <div v-if="summary.lines.length" class="flex flex-col gap-3">
    <div class="rounded-xl border border-outline-gray-3 bg-surface-gray-1 p-4">
      <template v-if="indywidualny">
        <div class="text-xs text-ink-gray-5">Klient zapłaci po dotacji i uldze</div>
        <div class="mt-1 whitespace-nowrap text-3xl font-bold tabular-nums text-ink-gray-9">{{ formatPln(summary.cena_po_uldze) }}</div>
        <div class="mt-1 text-sm text-ink-gray-6">
          <span class="whitespace-nowrap font-semibold tabular-nums text-ink-gray-8">{{ formatPln(summary.raty.po_uldze) }}</span>
          /mies. przez {{ okresLat }} lat
        </div>
      </template>
      <template v-else>
        <div class="text-xs text-ink-gray-5">Cena brutto</div>
        <div class="mt-1 whitespace-nowrap text-3xl font-bold tabular-nums text-ink-gray-9">{{ formatPln(summary.brutto) }}</div>
        <div class="mt-1 text-sm tabular-nums text-ink-gray-6">netto {{ formatPln(summary.netto) }}</div>
      </template>
    </div>

    <template v-if="indywidualny">
      <div>
        <div class="mb-1 text-xs text-ink-gray-5">Z ceny brutto {{ formatPln(summary.brutto) }}:</div>
        <div class="flex h-2 overflow-hidden rounded-full bg-surface-gray-3">
          <div class="bg-surface-gray-7" :style="{ width: udzialy.klient + '%' }"></div>
          <div class="bg-surface-green-3" :style="{ width: udzialy.dotacja + '%' }"></div>
          <div class="bg-surface-gray-4" :style="{ width: udzialy.ulga + '%' }"></div>
        </div>
        <div class="mt-1 text-xs text-ink-gray-5">
          klient {{ udzialy.klient }}% · dotacja {{ udzialy.dotacja }}% · ulga {{ udzialy.ulga }}%
        </div>
      </div>

      <div class="text-sm tabular-nums">
        <div class="flex justify-between gap-2 py-0.5 font-semibold text-ink-gray-9">
          <span>Cena brutto</span><span class="whitespace-nowrap">{{ formatPln(summary.brutto) }}</span>
        </div>
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
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
        <div class="flex justify-between gap-2 py-0.5 text-ink-gray-7">
          <span>Po dotacji</span><span class="whitespace-nowrap">{{ formatPln(summary.raty.po_dotacji) }}</span>
        </div>
        <div class="flex justify-between gap-2 py-0.5 font-semibold text-ink-gray-9">
          <span>Po dotacji i uldze</span><span class="whitespace-nowrap">{{ formatPln(summary.raty.po_uldze) }}</span>
        </div>
      </div>
    </template>

    <div>
      <div class="text-xs tabular-nums text-ink-gray-5">
        Netto {{ formatPln(summary.netto) }} · VAT {{ summary.vat_rate }}% {{ formatPln(summary.vat) }}
      </div>
      <button
        type="button"
        class="mt-1 flex items-center gap-1 text-xs font-medium text-ink-gray-6 hover:text-ink-gray-8"
        :aria-expanded="skladniki"
        @click="skladniki = !skladniki"
      >
        <FeatherIcon :name="skladniki ? 'chevron-up' : 'chevron-down'" class="h-3.5 w-3.5" />
        Składniki ({{ summary.lines.length }})
      </button>
      <div v-if="skladniki" class="mt-1">
        <div
          v-for="(ln, i) in summary.lines" :key="i"
          class="flex items-center gap-2 border-t border-outline-gray-1 py-1.5 text-sm first:border-t-0"
        >
          <span class="min-w-[88px] text-ink-gray-5">{{ ln.typ }}</span>
          <span class="flex-1 text-ink-gray-8">{{ ln.nazwa }}</span>
          <span class="tabular-nums text-ink-gray-7">×{{ formatQty(ln.ilosc) }}</span>
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
})

const skladniki = ref(false)
const indywidualny = computed(() => props.typKlienta === 'indywidualny')
const udzialy = computed(() => udzialyCeny(props.summary))

function formatQty(q) {
  return String(Number(q) || 0)
}
</script>
