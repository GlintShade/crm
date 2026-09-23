// Pomocnicze funkcje czystego JS (bez zależności od Vue) dla podglądu zdjęć
// w zakładce Audyt (OZE i CP). Budują listę pozycji do przewijania w modalu
// AudytPodgladZdjec.vue z dowolnego zestawu slotów/dokumentów/zdjęć, bez
// żadnej wiedzy o strukturze konkretnej zakładki.

// Rozpoznaje, czy dany URL wskazuje na plik PDF (odporne na `?query`/`#hash`
// i wielkość liter), ta sama reguła, którą AudytPhotoSlot stosował lokalnie
// jako `isPdfValue`.
export function jestPdf(url) {
  return /\.pdf(?:[?#]|$)/i.test(url || '')
}

// Nazwa pliku wydobyta z URL-a (ostatni segment ścieżki, bez `?query`/`#hash`,
// zdekodowany), ta sama reguła, którą AudytPhotoSlot stosował lokalnie jako
// `fileNameFromUrl`.
export function nazwaPlikuZUrl(url) {
  if (!url) return ''
  const path = url.split(/[?#]/)[0]
  const last = path.split('/').pop() || path
  try {
    return decodeURIComponent(last)
  } catch (e) {
    return last
  }
}

// Buduje nową listę pozycji do podglądu (kolejność wejściowa zachowana),
// pomijając sloty bez URL-a i sloty z PDF-em (PDF-y zostają otwierane w
// nowej karcie, nigdy w modalu). Nie mutuje wejściowej tablicy.
export function zbudujListePodgladu(pozycje) {
  if (!Array.isArray(pozycje)) return []
  return pozycje.filter((p) => p && p.url && !jestPdf(p.url))
}

// Indeks pozycji o danym kluczu w liście podglądu, albo -1 gdy nie ma takiej
// pozycji (np. slot był PDF-em i został odfiltrowany).
export function indeksDlaKlucza(lista, klucz) {
  if (!Array.isArray(lista)) return -1
  return lista.findIndex((p) => p && p.klucz === klucz)
}

// Nawigacja po liście z zawijaniem: z ostatniej pozycji w prawo wraca na
// pierwszą, z pierwszej w lewo wraca na ostatnią. `kierunek` to 1 (w prawo)
// albo -1 (w lewo). Dla pustej/nieprawidłowej długości zwraca 0.
export function przesunIndeks(indeks, dlugosc, kierunek) {
  if (!Number.isFinite(dlugosc) || dlugosc <= 0) return 0
  return ((indeks + kierunek) % dlugosc + dlugosc) % dlugosc
}
