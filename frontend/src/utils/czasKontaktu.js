// VOLTEO (ops#309): lustro crm/volteo_leady_kontakt.py po stronie frontendu.
// Czas do pierwszego kontaktu to sekundy (Duration), wpisywane jako gg:mm,
// maksymalnie 24:00. Zero importu z '@/utils' (barel ciagnie unplugin-icons,
// ktorego vitest nie zna; patrz komentarz w utils/leadyInline.js).

export const MAKS_CZAS_S = 24 * 3600

// Sekundy -> "HH:MM" (z zerami wiodacymi); "" dla 0/puste/nieliczby.
export function formatujGgMm(sekundy) {
  const liczba = Number(sekundy)
  if (!liczba || liczba <= 0 || !Number.isFinite(liczba)) return ''
  const minuty = Math.floor(liczba / 60)
  const gg = String(Math.floor(minuty / 60)).padStart(2, '0')
  const mm = String(minuty % 60).padStart(2, '0')
  return `${gg}:${mm}`
}

// "H:MM", "HH:MM", "HHMM"/"HMM" (3-4 cyfry) lub "H"/"HH" (same godziny)
// -> sekundy; null dla nieparsowalnego (minuty musza byc 0..59). Gornej
// granicy nie sprawdza (to robi czyCzasPoprawny).
export function parsujGgMm(tekst) {
  if (tekst === null || tekst === undefined) return null
  const t = String(tekst).trim()
  if (!t) return null
  let godziny
  let minuty
  const m = t.match(/^(\d{1,3}):(\d{1,2})$/)
  if (m) {
    godziny = parseInt(m[1], 10)
    minuty = parseInt(m[2], 10)
  } else if (/^\d+$/.test(t)) {
    if (t.length <= 2) {
      godziny = parseInt(t, 10)
      minuty = 0
    } else if (t.length <= 4) {
      godziny = parseInt(t.slice(0, -2), 10)
      minuty = parseInt(t.slice(-2), 10)
    } else {
      return null
    }
  } else {
    return null
  }
  if (minuty > 59) return null
  return godziny * 3600 + minuty * 60
}

export function czyCzasPoprawny(sekundy) {
  return Number.isFinite(sekundy) && sekundy >= 0 && sekundy <= MAKS_CZAS_S
}
