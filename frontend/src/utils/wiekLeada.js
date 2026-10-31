// Wiek leada do 48 h jako "HH h MM m temu" (prosba wlasciciela 2026-10-31,
// kolumna "Data utworzenia" na liscie leadow). Czysta funkcja, zero importu
// z '@/utils' (pulapka baraila, patrz utils/leadyInline.js).

export const PROG_WIEKU_MS = 48 * 60 * 60 * 1000

const dwie = (n) => String(n).padStart(2, '0')

// createdMs, nowMs: epoch w ms. Zwraca napis albo null (poza oknem 48 h,
// przyszlosc, niepoprawne dane).
export function formatujWiekLeada(createdMs, nowMs) {
  const roznica = Number(nowMs) - Number(createdMs)
  if (!Number.isFinite(roznica) || roznica < 0 || roznica >= PROG_WIEKU_MS) {
    return null
  }
  const minuty = Math.floor(roznica / 60000)
  return `${dwie(Math.floor(minuty / 60))} h ${dwie(minuty % 60)} m temu`
}
