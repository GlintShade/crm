// Konfiguracja i pomocnicze funkcje czystego JS (bez zależności od Vue,
// frappe-ui ani `@/utils`) dla zakładki "Pliki" na szansie (issue
// GlintShade/proenergy-crm-ops#203, uwaga 47) - feed KAŻDEGO załącznika
// szansy, na wzór zakładki Notatki (`utils/notatki.js`).
//
// Kontrakt wejściowy: wiersze zwrócone przez `crm.api.pliki.feed` (issue
// W4a/ops#199), patrz `crm/volteo_pliki.py::klasyfikuj_plik_szansy` po
// stronie backendu - każdy wiersz niesie co najmniej `klucz`, `file_name`,
// `file_url`, `file_size`, `file_type`, `kategoria`
// ('dokument'|'obraz'|'wideo'|'inny'), `zrodlo`, `zrodlo_etykieta`, `data`.
//
// Sort jest REUŻYTY z `utils/notatki.js` (`sortujFeed`) - obie funkcje
// sortują po tym samym polu `data` (string ISO "YYYY-MM-DD HH:mm:ss",
// porównywalny leksykograficznie), sygnatura identyczna
// (`(wiersze, kierunek) => wiersze`), więc duplikowanie tej samej pętli
// sortującej w drugim pliku nie dodałoby nic poza ryzykiem rozjazdu.
// `notatki.js` samo jest frappe-free (zero importów spoza `./dataPolska` i
// `./aktualizacje`, obie też frappe-free), więc import stąd nie wprowadza
// żadnej zależności od Vue/frappe-ui do tego pliku.
import { KIERUNKI_SORTU, sortujFeed } from './notatki'

// Tryby przełącznika u góry zakładki "Pliki" - kolejność jak w UI
// (Dokumenty / Zdjęcia i filmy / Wszystko), pierwszy element jest
// domyślny (decyzja właściciela, issue ops#203).
export const TRYB_DOKUMENTY = 'dokumenty'
export const TRYB_MEDIA = 'media'
export const TRYB_WSZYSTKO = 'wszystko'

export const TRYBY = [TRYB_DOKUMENTY, TRYB_MEDIA, TRYB_WSZYSTKO]

// Kategorie `crm.volteo_pliki.KATEGORIE` przypisane do trybu "Dokumenty":
// dokumenty biurowe (PDF, docx, xlsx...) ORAZ "inny" (nierozpoznane
// rozszerzenie) - "inny" ma zdecydowanie więcej wspólnego z dokumentem niż
// ze zdjęciem/filmem, więc nie zasługuje na trzeci, osobny tryb.
const KATEGORIE_DOKUMENTOW = new Set(['dokument', 'inny'])
const KATEGORIE_MEDIOW = new Set(['obraz', 'wideo'])

// Sortuje wiersze feedu Pliki - cienki alias `sortujFeed` z `utils/notatki.js`
// (patrz komentarz importu na górze pliku), udokumentowany pod własną nazwą
// domeny "Pliki".
export const sortuj = sortujFeed

// Re-eksport wartości kierunku sortu, żeby komponenty tej zakładki nie
// musiały importować `utils/notatki` bezpośrednio tylko po tę jedną stałą.
export { KIERUNKI_SORTU }

/**
 * Filtruje `wiersze` do tych pasujących do trybu przełącznika.
 * `wszystko` (albo dowolny nieznany/pusty tryb) nie filtruje niczego -
 * bezpieczny domyślny, żeby literówka w nazwie trybu nigdy nie ukryła
 * milcząco całego feedu.
 *
 * @param {Array<object>} wiersze
 * @param {string} tryb
 * @returns {Array<object>}
 */
export function filtrujTryb(wiersze, tryb) {
  const lista = Array.isArray(wiersze) ? wiersze : []
  if (tryb === TRYB_DOKUMENTY) {
    return lista.filter((w) => w && KATEGORIE_DOKUMENTOW.has(w.kategoria))
  }
  if (tryb === TRYB_MEDIA) {
    return lista.filter((w) => w && KATEGORIE_MEDIOW.has(w.kategoria))
  }
  return lista.filter(Boolean)
}

/**
 * Filtruje `wiersze` do tych, których `zrodlo` jest w `zaznaczone` (lista
 * albo Set kluczy) - ta sama semantyka co `filtrujFeed` w
 * `utils/notatki.js`: pusty wybór daje pusty wynik (lista wielokrotnego
 * wyboru bez żadnego zaznaczenia oznacza "nic nie pokazuj", nie "pokaż
 * wszystko", inaczej "Wyczyść" nie robiłoby nic widocznego).
 *
 * @param {Array<object>} wiersze
 * @param {Array<string>|Set<string>} zaznaczone
 * @returns {Array<object>}
 */
export function filtrujZrodla(wiersze, zaznaczone) {
  const zbior = zaznaczone instanceof Set ? zaznaczone : new Set(zaznaczone || [])
  if (zbior.size === 0) return []
  return (Array.isArray(wiersze) ? wiersze : []).filter((w) => w && zbior.has(w.zrodlo))
}

/**
 * Liczba wpisów per źródło, w OBRĘBIE danego trybu (`tryb` filtruje
 * `wiersze` PRZED liczeniem) - liczniki w pasku filtra mają pokazywać, ile
 * wpisów danego źródła jest widocznych w bieżącym trybie (Dokumenty/
 * Zdjęcia i filmy/Wszystko), nie ile jest ich w całym feedzie niezależnie
 * od trybu.
 *
 * @param {Array<object>} wiersze
 * @param {string} tryb
 * @returns {Record<string, number>}
 */
export function liczbyZrodelPoTrybie(wiersze, tryb) {
  const liczniki = {}
  for (const w of filtrujTryb(wiersze, tryb)) {
    liczniki[w.zrodlo] = (liczniki[w.zrodlo] || 0) + 1
  }
  return liczniki
}

function _rozszerzenie(fileName) {
  const nazwa = String(fileName || '').trim()
  const idx = nazwa.lastIndexOf('.')
  if (idx <= 0) return ''
  return nazwa.slice(idx + 1).toLowerCase()
}

// Klucze zwracane przez `ikonaDla` - komponent (`PlikWiersz.vue`) mapuje je
// na konkretne ikony SFC (`FilePdfIcon`/`FileImageIcon`/`FileVideoIcon`/
// `FileTextIcon`/`FileIcon`). Ten moduł jest frappe-free, więc nie może sam
// importować komponentów Vue - zwraca tylko semantyczny klucz, testowalny
// bez żadnej zależności.
export const IKONA_PDF = 'pdf'
export const IKONA_OBRAZ = 'obraz'
export const IKONA_WIDEO = 'wideo'
export const IKONA_DOKUMENT = 'dokument'
export const IKONA_INNY = 'inny'

/**
 * Klucz ikony dla jednego wiersza feedu. PDF dostaje własną ikonę mimo że
 * backendowa `kategoria` traktuje go jako "dokument" razem z docx/xlsx/...
 * - rozpoznanie PDF po rozszerzeniu nazwy pliku (nie po `file_type`, które
 * bywa puste, ta sama zasada co `crm.volteo_pliki.kategoria_pliku`).
 * Obraz dostaje miniaturę (renderowaną przez komponent z `file_url`), nie
 * ikonę - `ikonaDla` i tak zwraca `IKONA_OBRAZ`, żeby wołający miał jeden
 * spójny sposób rozpoznania tego przypadku.
 *
 * @param {object} wiersz
 * @returns {string}
 */
export function ikonaDla(wiersz) {
  if (!wiersz) return IKONA_INNY
  if (_rozszerzenie(wiersz.file_name) === 'pdf') return IKONA_PDF
  if (wiersz.kategoria === 'obraz') return IKONA_OBRAZ
  if (wiersz.kategoria === 'wideo') return IKONA_WIDEO
  if (wiersz.kategoria === 'dokument') return IKONA_DOKUMENT
  return IKONA_INNY
}

const JEDNOSTKI_ROZMIARU = ['B', 'KB', 'MB', 'GB', 'TB']

/**
 * Formatuje rozmiar pliku w bajtach na czytelny napis ("12.34 KB").
 * Wejście niepoprawne/ujemne/NaN daje "0 B" zamiast rzucać albo pokazać
 * "NaN" w wierszu listy.
 *
 * @param {number|string|null|undefined} bajty
 * @returns {string}
 */
export function formatujRozmiar(bajty) {
  let rozmiar = Number(bajty)
  if (!Number.isFinite(rozmiar) || rozmiar < 0) rozmiar = 0

  let indeksJednostki = 0
  while (rozmiar >= 1024 && indeksJednostki < JEDNOSTKI_ROZMIARU.length - 1) {
    rozmiar /= 1024
    indeksJednostki++
  }

  const cyfryPoPrzecinku = indeksJednostki === 0 ? 0 : 2
  return `${rozmiar.toFixed(cyfryPoPrzecinku)} ${JEDNOSTKI_ROZMIARU[indeksJednostki]}`
}

/**
 * Wiersze feedu zawężone do obrazów i wideo, w kształcie oczekiwanym przez
 * modal podglądu (`@/utils/audytPodglad`, `{ klucz, url, etykieta }`) -
 * NIE `zdjeciaDoGalerii` z `aktualizacje.js` (ten alias oczekuje pola
 * `name`, kontrakt `crm.api.montaz`/`crm.api.notatki`; feed Pliki niesie
 * `klucz`, kontrakt `crm.api.pliki.feed`, inny kształt tego samego
 * pomysłu). Zachowuje kolejność wejściową, nie mutuje wejścia.
 *
 * @param {Array<object>} wiersze
 * @returns {Array<{klucz: string, url: string, etykieta: string}>}
 */
export function dlaPodgladu(wiersze) {
  return (Array.isArray(wiersze) ? wiersze : [])
    .filter((w) => w && w.file_url && (w.kategoria === 'obraz' || w.kategoria === 'wideo'))
    .map((w) => ({ klucz: w.klucz, url: w.file_url, etykieta: w.file_name || '' }))
}

const KLUCZ_LOCALSTORAGE = 'pliki-filtr'

/**
 * Odczytuje ustawienia zakładki Pliki (zaznaczone źródła + kierunek sortu)
 * zapisane w localStorage (klucz "pliki-filtr") - `try/catch` na odczycie,
 * bo localStorage może rzucić (tryb prywatny, zablokowane site data) albo
 * zwrócić coś, co nie parsuje się jako JSON, ta sama zasada co
 * `wczytajFiltr` w `utils/notatki.js`. Tryb przełącznika (Dokumenty/Media/
 * Wszystko) świadomie NIE jest tu przechowywany - domyślnie zawsze
 * "Dokumenty" przy każdym wejściu na zakładkę (decyzja właściciela, issue
 * ops#203), tylko wybór źródeł i kierunek sortu przeżywają przeładowanie.
 *
 * `kluczeDostepne` (zwykle `zrodla.map(z => z.klucz)` z odpowiedzi API)
 * jest zawsze domyślnym i przycinającym zbiorem: zapis sprzed
 * usunięcia/przemianowania źródła nie zostawia martwego wpisu.
 *
 * @param {Array<string>} kluczeDostepne
 * @returns {{ zaznaczone: Array<string>, kierunek: string }}
 */
export function wczytajUstawienia(kluczeDostepne) {
  const dostepne = Array.isArray(kluczeDostepne) ? kluczeDostepne : []
  const domyslny = { zaznaczone: [...dostepne], kierunek: KIERUNKI_SORTU.NAJNOWSZE }

  try {
    const surowe = localStorage.getItem(KLUCZ_LOCALSTORAGE)
    if (!surowe) return domyslny

    const zapisany = JSON.parse(surowe)
    const zaznaczoneZapisane = Array.isArray(zapisany?.zaznaczone)
      ? zapisany.zaznaczone.filter((klucz) => dostepne.includes(klucz))
      : null

    const kierunek =
      zapisany?.kierunek === KIERUNKI_SORTU.NAJSTARSZE
        ? KIERUNKI_SORTU.NAJSTARSZE
        : KIERUNKI_SORTU.NAJNOWSZE

    return {
      zaznaczone: zaznaczoneZapisane && zaznaczoneZapisane.length ? zaznaczoneZapisane : [...dostepne],
      kierunek,
    }
  } catch {
    return domyslny
  }
}

/**
 * Zapisuje ustawienia zakładki Pliki do localStorage - `try/catch` na
 * zapisie (patrz `wczytajUstawienia`), cichy brak zapisu zamiast rzucania.
 *
 * @param {Array<string>} zaznaczone
 * @param {string} kierunek
 */
export function zapiszUstawienia(zaznaczone, kierunek) {
  try {
    localStorage.setItem(
      KLUCZ_LOCALSTORAGE,
      JSON.stringify({ zaznaczone: Array.isArray(zaznaczone) ? zaznaczone : [], kierunek }),
    )
  } catch {
    // localStorage niedostępny (tryb prywatny, zablokowane site data) -
    // ustawienia po prostu nie przetrwają przeładowania, reszta działa dalej.
  }
}
