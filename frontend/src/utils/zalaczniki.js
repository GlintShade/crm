// Edycja nazwy pliku PRZED wysłaniem załącznika (issue ops#74).
//
// Osoba wgrywająca plik może zmienić tylko trzon nazwy — rozszerzenie
// zostaje stałym sufiksem, dokładanym automatycznie z oryginalnej nazwy
// pliku. Reguły walidacji trzonu są lustrzanym odbiciem serwerowych z
// `crm/volteo_zalaczniki.py` (komunikaty identyczne, żeby błąd wyglądał
// tak samo niezależnie od tego, czy złapie go frontend, czy serwer przy
// zmianie nazwy istniejącego załącznika).

export const MAKS_DLUGOSC = 140
// Maksymalna dopuszczalna długość pełnej nazwy pliku (trzon + rozszerzenie).

const ZAKAZANE = new Set(['/', '\\'])
// Znaki niedozwolone w trzonie nazwy — ukośniki mogłyby zostać odczytane
// jako separator ścieżki gdziekolwiek dalej nazwa pliku trafia do systemu
// plików.

/**
 * Dzieli nazwę pliku na trzon i rozszerzenie (z kropką).
 *
 * Kropka musi być na pozycji > 0, więc plik zaczynający się od kropki
 * (np. ".gitignore") jest traktowany jako sam trzon, bez rozszerzenia —
 * tak samo jak plik bez żadnej kropki. Wielokropkowe nazwy (np. "a.b.pdf")
 * dzielą się na ostatniej kropce.
 *
 * @param {string|null|undefined} nazwa
 * @returns {{ trzon: string, rozszerzenie: string }}
 */
export function podzielNazwe(nazwa) {
  const bezpiecznaNazwa = nazwa || ''
  const kropka = bezpiecznaNazwa.lastIndexOf('.')
  if (kropka > 0) {
    return {
      trzon: bezpiecznaNazwa.slice(0, kropka),
      rozszerzenie: bezpiecznaNazwa.slice(kropka),
    }
  }
  return { trzon: bezpiecznaNazwa, rozszerzenie: '' }
}

/**
 * Składa pełną nazwę pliku z trzonu (obciętego z białych znaków na
 * brzegach) i rozszerzenia.
 *
 * @param {string} trzon
 * @param {string} [rozszerzenie]
 * @returns {string}
 */
export function zlozNazwe(trzon, rozszerzenie = '') {
  return (trzon || '').trim() + (rozszerzenie || '')
}

/**
 * Waliduje trzon nazwy pliku — te same reguły co serwerowe
 * `crm/volteo_zalaczniki.py::nowa_nazwa_pliku`, z identycznymi komunikatami
 * po polsku.
 *
 * @param {string} trzon
 * @param {string} [rozszerzenie]
 * @returns {string|null} komunikat błędu, albo `null` gdy trzon jest poprawny
 */
export function sprawdzTrzon(trzon, rozszerzenie = '') {
  const oczyszczonyTrzon = (trzon || '').trim()
  if (!oczyszczonyTrzon) {
    return 'Nazwa pliku nie może być pusta.'
  }
  const zawieraZakazany = [...oczyszczonyTrzon].some(
    (znak) => ZAKAZANE.has(znak) || znak.charCodeAt(0) < 32,
  )
  if (zawieraZakazany) {
    return 'Nazwa pliku nie może zawierać ukośników ani znaków sterujących.'
  }
  if (zlozNazwe(oczyszczonyTrzon, rozszerzenie).length > MAKS_DLUGOSC) {
    return `Nazwa pliku może mieć najwyżej ${MAKS_DLUGOSC} znaków.`
  }
  return null
}
