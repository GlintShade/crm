// Podpowiedz przy polu "Czas do pierwszego kontaktu" w panelu bocznym leada
// (b83): wiek leada liczony od `creation` plus gotowa wartosc gg:mm do
// przepisania przez CC. Nic nie wpisuje do pola, wartosc wpisuje czlowiek.
//
// Czysta funkcja, importy tylko wzgledne (bez barelu '@/utils', ktory ciagnie
// unplugin-icons i psuje vitest, patrz utils/leadyInline.js).

import { formatujWiekLeada } from './wiekLeada'
import { formatujGgMm } from './czasKontaktu'

// Gorna granica tego, co CzasGgMmInput przyjmie i pokaze: 999:59.
export const MAKS_SEKUND_POLA = (999 * 60 + 59) * 60

const dwie = (n) => String(n).padStart(2, '0')

// createdMs: epoch w ms. Data i godzina w strefie przegladarki, 24 h,
// format polski "DD.MM.RRRR, GG:MM". null dla niepoprawnych danych.
export function formatujDateUtworzenia(createdMs) {
  if (createdMs === null || createdMs === undefined || createdMs === '') {
    return null
  }
  const d = new Date(Number(createdMs))
  if (Number.isNaN(d.getTime())) return null
  return (
    `${dwie(d.getDate())}.${dwie(d.getMonth() + 1)}.${d.getFullYear()}, ` +
    `${dwie(d.getHours())}:${dwie(d.getMinutes())}`
  )
}

// Wiek leada jako wartosc pola "gg:mm" (pelne minuty w dol). null gdy
// ponizej minuty, w przyszlosci, powyzej 999:59 albo dla zlych danych.
export function podpowiedzGgMm(createdMs, nowMs) {
  const roznica = Number(nowMs) - Number(createdMs)
  if (!Number.isFinite(roznica) || roznica < 0) return null
  const sekundy = Math.floor(roznica / 60000) * 60
  if (sekundy > MAKS_SEKUND_POLA) return null
  return formatujGgMm(sekundy) || null
}

// Czesci podpowiedzi osobno: `opis` moze byc w UI obciety (waska kolumna
// siatki kart), `ggmm` nigdy, bo to wartosc do przepisania; `pelny` to
// calosc (np. do `title`). null gdy brak `creation`. `ggmm` null ponizej
// minuty i powyzej 999:59.
export function czesciPodpowiedzi(createdMs, nowMs) {
  const wiek = formatujWiekLeada(createdMs, nowMs)
  const data = wiek || formatujDateUtworzenia(createdMs)
  if (!data) return null
  const opis = `utworzono ${data}`
  const ggmm = podpowiedzGgMm(createdMs, nowMs)
  return { opis, ggmm, pelny: ggmm ? `${opis} (${ggmm})` : opis }
}

// Pelny tekst podpowiedzi, np.
//   "utworzono 02 h 40 m temu (02:40)"
//   "utworzono 01.11.2026, 09:15 (75:20)"
//   "utworzono 01.08.2026, 09:15"            (ponad 999:59, bez gg:mm)
// Do 48 h wiek z formatujWiekLeada (ten sam format co na liscie leadow),
// starszy lead: data i godzina utworzenia. null gdy brak `creation`.
export function podpowiedzCzasuKontaktu(createdMs, nowMs) {
  return czesciPodpowiedzi(createdMs, nowMs)?.pelny ?? null
}

// Podpowiedz tylko dla pustego i edytowalnego pola (decyzja koordynatora
// b83): po wpisaniu wartosci albo przy polu tylko do odczytu chowamy.
export function czyPokazacPodpowiedz(wartosc, tylkoOdczyt) {
  if (tylkoOdczyt) return false
  const liczba = Number(wartosc)
  return !wartosc || !Number.isFinite(liczba) || liczba <= 0
}
