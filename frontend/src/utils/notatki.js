// Konfiguracja i pomocnicze funkcje czystego JS (bez zależności od Vue,
// frappe-ui ani `@/utils`) dla wspólnego strumienia notatek na zakładkach
// szansy (Zestaw, Umowa, Kredyt, Faktury dziś; Montaż, OSD, Dotacja, Trify w
// kolejnych issue) - issue #200 ("W2 notatki na szansie"). Renderuje je
// jeden wspólny komponent, NotatkiStrumien.vue, sterowany prop `zakladka`.
//
// Lustro backendu (issue W1, równolegle): `crm/volteo_notatki.py::TYPY_PER_
// ZAKLADKA` - zmieniać oba miejsca razem. Doctype `Volteo Notatka` i API
// `crm.api.notatki.*` są wspólne dla wszystkich ośmiu zakładek już teraz
// (fazowanie dotyczy wyłącznie tego, KTÓRA zakładka dostaje UI w danym
// issue, nie schematu/backendu).
//
// Import z `aktualizacje.js` (NIE z barrelu `@/utils`) jest jawnie
// dozwolony przez brief tego issue: `zdjeciaDoGalerii` (mapowanie surowego
// wiersza File na kształt podglądu {klucz,url,etykieta}) jest identyczne
// dla notatek, więc `plikiDoPodgladu` niżej jest tylko udokumentowanym
// aliasem - nie duplikuje logiki. `tekstPusty` (wykrywanie pustej treści
// TipTap) jest importowane wprost z `aktualizacje.js` w komponentach, które
// go potrzebują (NotatkiStrumien.vue), z tego samego powodu. `aktualizacje.js`
// samo jest frappe-free (zero importów), więc to nie wprowadza żadnej
// zależności od Vue/frappe-ui do tego pliku.
import { zdjeciaDoGalerii } from './aktualizacje'
// Import z `dataPolska.js` (NIE z barrelu `@/utils`) dla grupowania feedu po
// dniu, niżej - `dataPolska.js` samo jest frappe-free (zero importów), więc
// to nie wprowadza zależności od Vue/frappe-ui do tego pliku, ten sam
// wyjątek udokumentowany jak import `zdjeciaDoGalerii` powyżej.
import { DNI_TYGODNIA_SKROT, MIESIACE_SKROT } from './dataPolska'

// Bazowy zestaw typów notatki, wspólny dla większości zakładek. Kolejność
// ma znaczenie: pierwszy element jest domyślnie zaznaczony w selekcie
// "Dodaj notatkę".
const TYPY_BAZA = ['Notatka', 'Telefon', 'Wizyta', 'Ustalenie', 'Problem', 'Dokument']

// Montaż dokłada własny typ na końcu bazowego zestawu (lustro
// crm/volteo_notatki.py, NIE mylić z odrębnym doctype `Volteo Montaz
// Update`/AktualizacjeTab.vue - to inny, nowszy strumień, na razie bez UI).
const TYPY_MONTAZ = [...TYPY_BAZA, 'Termin montażu']

// Trify ma własny, całkowicie odrębny zestaw typów (lustro
// crm/volteo_notatki.py, identyczny z TRIFY.typy w aktualizacje.js - te dwa
// strumienie są niezależnymi doctype'ami, zestaw typów tylko przypadkiem
// się pokrywa, zmieniać każdy osobno jeśli kiedyś się rozjadą).
const TYPY_TRIFY = ['Notatka', 'Wniosek Trify', 'Decyzja Trify', 'Umowa Trify', 'Wypłata Trify', 'Problem']

// Klucz -> { etykieta, typy, placeholder, pusty }. `etykieta`/`placeholder`/
// `pusty` to surowy polski tekst - tłumaczenie przez __() dzieje się w
// komponencie (NIGDY na poziomie modułu, pułapka eager chunk, patrz
// aktualizacje.js i CLAUDE.md).
export const ZAKLADKI = {
  Zestaw: {
    etykieta: 'Zestaw',
    typy: TYPY_BAZA,
    placeholder: 'Np. Klient chce zmienić producenta falownika…',
    pusty: 'Brak notatek w Zestawie.',
  },
  Umowa: {
    etykieta: 'Umowa',
    typy: TYPY_BAZA,
    placeholder: 'Np. Klient prosi o przesunięcie terminu podpisania umowy…',
    pusty: 'Brak notatek w Umowie.',
  },
  Kredyt: {
    etykieta: 'Kredyt',
    typy: TYPY_BAZA,
    placeholder: 'Np. Bank prosi o dodatkowy dokument…',
    pusty: 'Brak notatek w Kredycie.',
  },
  Faktury: {
    etykieta: 'Faktury',
    typy: TYPY_BAZA,
    placeholder: 'Np. Faktura korygująca w przygotowaniu…',
    pusty: 'Brak notatek w Fakturach.',
  },
  Montaz: {
    etykieta: 'Montaż',
    typy: TYPY_MONTAZ,
    placeholder: 'Np. Umówiono termin montażu na 20.07…',
    pusty: 'Brak notatek w Montażu.',
  },
  OSD: {
    etykieta: 'OSD',
    typy: TYPY_BAZA,
    placeholder: 'Np. Zgłoszenie do OSD złożone 03.09…',
    pusty: 'Brak notatek w OSD.',
  },
  Dotacja: {
    etykieta: 'Dotacja',
    typy: TYPY_BAZA,
    placeholder: 'Np. Wniosek o dotację złożony…',
    pusty: 'Brak notatek w Dotacji.',
  },
  Trify: {
    etykieta: 'Trify',
    typy: TYPY_TRIFY,
    placeholder: 'Np. Złożono wniosek Trify 03.09… (@ aby wspomnieć użytkownika)',
    pusty: 'Brak notatek Trify.',
  },
}

// Lista typów dostępnych na danej zakładce (pusta tablica dla nieznanego
// klucza, nigdy undefined - bezpieczne jako `:options` FormControl).
export function typyDla(zakladka) {
  return ZAKLADKI[zakladka]?.typy || []
}

// Etykieta wyświetlana zakładki (surowy polski tekst, do __() w
// komponencie). Dla nieznanego klucza zwraca sam klucz, żeby chip
// zakładki (przyszły feed) nigdy nie pokazał pustego napisu.
export function etykietaZakladki(zakladka) {
  return ZAKLADKI[zakladka]?.etykieta || zakladka || ''
}

// Lista dla `allowedFileTypes` FilesUploader: MIME plus kropka-rozszerzenie,
// ten sam wzorzec co TYPY_PLIKOW_WIDEO w audytPodglad.js (Android czasem
// wysyła puste `file.type`, więc rozszerzenia są konieczne, nie kosmetyczne;
// celowo nigdy samo `image/*`).
export const TYPY_PLIKOW_NOTATKI = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
  '.pdf',
  '.jpg',
  '.jpeg',
  '.png',
  '.webp',
]

const ROZSZERZENIA_OBRAZOW = new Set(['jpg', 'jpeg', 'png', 'webp'])

function rozszerzenieZNazwy(nazwa) {
  const czysta = String(nazwa || '').split(/[?#]/)[0]
  const idx = czysta.lastIndexOf('.')
  if (idx === -1) return ''
  return czysta.slice(idx + 1).toLowerCase()
}

// Dzieli listę plików wpisu (kształt `crm.api.notatki.lista`: {name,
// file_name, file_url, file_type, file_size}) na dokumenty (PDF i wszystko,
// co nie jest rozpoznanym obrazem) i obrazy, po rozszerzeniu nazwy pliku -
// NIE po `file_type` (pole File bywa puste/niespójne, ta sama zasada, którą
// AttachmentItem.vue stosuje przez `mime.getType(nazwa)`). Zachowuje
// kolejność wejściową w obu listach, nie mutuje wejścia.
export function podzielPliki(pliki) {
  const dokumenty = []
  const obrazy = []
  for (const p of Array.isArray(pliki) ? pliki : []) {
    if (!p) continue
    const rozszerzenie = rozszerzenieZNazwy(p.file_name || p.file_url)
    if (ROZSZERZENIA_OBRAZOW.has(rozszerzenie)) {
      obrazy.push(p)
    } else {
      dokumenty.push(p)
    }
  }
  return { dokumenty, obrazy }
}

// Mapuje obrazy wpisu na kształt podglądu wspólny z zakładką Audyt/Montaż
// (@/utils/audytPodglad, klucz/url/etykieta) - alias `zdjeciaDoGalerii` z
// aktualizacje.js, patrz komentarz importu na górze pliku.
export function plikiDoPodgladu(obrazy) {
  return zdjeciaDoGalerii(obrazy)
}

// Imię i nazwisko autora wpisu: `autor_nazwa` z API (nazwa wyliczona
// serwerowo w chwili dodania, przeżywa zmianę nazwiska/dezaktywację konta),
// w braku tego pola `getUser(owner).full_name` z usersStore, ostatecznie
// sam e-mail (owner) jeśli i to zawiedzie.
export function nazwaAutora(wpis, getUser) {
  if (!wpis) return ''
  if (wpis.autor_nazwa) return wpis.autor_nazwa
  const user = typeof getUser === 'function' ? getUser(wpis.owner) : null
  if (user?.full_name) return user.full_name
  return wpis.owner || ''
}

// Rodzaje umowy OZE (lustro `crm/volteo_pipeline.py` i
// `frontend/src/pages/Deal.vue` OZE_RODZAJE, ok. linii 602) - Faza 1 tego
// strumienia notatek pokazuje się WYŁĄCZNIE na szansach tych trzech
// rodzajów, nigdy na Czyste Powietrze (dostanie schemat w fazie 2, ale nie
// UI tego issue).
export const OZE_RODZAJE = new Set(['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii'])

export function czyOze(rodzaj) {
  return OZE_RODZAJE.has(rodzaj)
}

// ---------------------------------------------------------------------
// Feed "Notatki" (issue ops#201, uwaga 40) - strumień łączący notatki z
// każdej zakładki z komentarzami wątku "Komentarze" zakładki Audyt (OZE i
// CP). Lustro backendu `crm/volteo_notatki.py::ZRODLA_FEEDU`/
// `etykieta_zrodla` - zmieniać oba miejsca razem.

// Etykiety wszystkich dziesięciu możliwych źródeł feedu (osiem zakładek
// Volteo Notatka plus komentarze Audytu OZE/CP) - lustro backendowego
// `ZRODLA_FEEDU` (kolejność) + `ETYKIETY_ZAKLADEK`/`ETYKIETY_ZRODEL_
// DODATKOWYCH` (etykiety) połączonych w jeden słownik po stronie frontu,
// bo tu nie ma potrzeby rozróżniać "zakładka notatki" od "audyt" - feed
// traktuje je jednolicie jako "źródło". Backend i tak zwraca własne
// `zrodlo_etykieta` per wpis oraz listę `zrodla` (z licznikami) w
// `crm.api.notatki.feed` - ten słownik służy WYŁĄCZNIE jako domyślny,
// pełny zestaw kluczy przed pierwszą odpowiedzią API (żeby lista
// wielokrotnego wyboru i `wczytajFiltr` miały co pokazać/porównać zanim
// `zrodla` z serwera dotrze).
export const ETYKIETY_ZRODEL = {
  Zestaw: 'Zestaw',
  Umowa: 'Umowa',
  Kredyt: 'Kredyt',
  Faktury: 'Faktury',
  Montaz: 'Montaż',
  OSD: 'OSD',
  Dotacja: 'Dotacja',
  Trify: 'Trify',
  Audyt: 'Audyt',
  AudytCP: 'Audyt CP',
}

// Kolory per źródło (issue ops#206, "wariant C") - JEDNA mapa, klucz źródła
// -> pełne literały klas Tailwind (`krawedz` dla lewej krawędzi 5px karty,
// `tlo`+`tekst` dla etykiety zakładki w nagłówku karty, `kwadracik` dla
// kropki koloru w panelu źródeł) - etykieta, krawędź i kwadracik na każdym
// z trzech miejsc (karta, panel, chip mobile) ZAWSZE z tej samej mapy,
// żeby "Zestaw" nie mógł mieć innego koloru w panelu niż na karcie.
//
// Klasy są wypisane literałami, nie budowane string-template (`bg-${x}-100`)
// - Tailwind JIT skanuje tylko literalny tekst źródeł, string budowany w
// runtime jest dla skanera niewidoczny i zostaje wypurgowany z finalnego
// CSS (ten sam wymóg co `COLOR_BUTTON_CLASS_MAP` w utils/statusColors.js).
//
// PUŁAPKA znaleziona przy weryfikacji builda (grep po skompilowanym CSS):
// `frappe-ui`'s tailwind preset (`node_modules/frappe-ui/tailwind/plugin.js`,
// `theme: { colors: colorPalette }`) PODMIENIA całą paletę kolorów Tailwind
// zamiast ją rozszerzać - dostępne rodziny to WYŁĄCZNIE gray/blue/green/red/
// orange/amber/yellow/teal/cyan/purple/pink/violet (plus czerń/biel/overlay),
// żadnych sky/emerald/rose/lime/indigo/slate spoza tej listy. Klasa spoza
// tej listy (np. `bg-rose-600`) jest dla Tailwinda nieznanym literałem -
// build przechodzi bez błędu, ale generuje ZERO CSS dla niej (cichy brak
// koloru, nie awaria). Brief issue sugerował rose/sky/emerald/lime - te
// cztery źródła (Audyt/AudytCP, Trify, Faktury, Dotacja) dostały tu
// najbliższe odpowiedniki z dostępnej palety zamiast literalnie tych nazw.
//
// Warianty `dark:` na tle/tekście etykiety (nie na krawędzi/kwadraciku,
// które są już wystarczająco nasycone w obu motywach) - CLAUDE.md "Ciemny
// motyw: tokeny, nie paleta" mówi o preferowaniu tokenów semantycznych nad
// literałami palety, ale w tym konkretnym przypadku kolor JEST znaczeniem
// (identyfikacja źródła), nie tylko dekoracją - literał + jawny wariant
// `dark:` jest tu celowym, udokumentowanym wyjątkiem, tak jak
// `COLOR_BUTTON_CLASS_MAP` obok niego robi to samo z `!bg-`/`!text-`.
export const KOLORY_ZRODEL = {
  Zestaw: {
    krawedz: 'border-l-amber-600',
    tlo: 'bg-amber-100 dark:bg-amber-900/40',
    tekst: 'text-amber-800 dark:text-amber-200',
    kwadracik: 'bg-amber-600',
  },
  Umowa: {
    krawedz: 'border-l-blue-600',
    tlo: 'bg-blue-100 dark:bg-blue-900/40',
    tekst: 'text-blue-800 dark:text-blue-200',
    kwadracik: 'bg-blue-600',
  },
  Kredyt: {
    krawedz: 'border-l-violet-600',
    tlo: 'bg-violet-100 dark:bg-violet-900/40',
    tekst: 'text-violet-800 dark:text-violet-200',
    kwadracik: 'bg-violet-600',
  },
  // Odstępstwo od makiety: brief sugerował emerald, niedostępny w tym
  // projekcie (patrz komentarz wyżej) - green jest najbliższym odpowiednikiem
  // z dostępnej palety.
  Faktury: {
    krawedz: 'border-l-green-600',
    tlo: 'bg-green-100 dark:bg-green-900/40',
    tekst: 'text-green-800 dark:text-green-200',
    kwadracik: 'bg-green-600',
  },
  Montaz: {
    krawedz: 'border-l-orange-600',
    tlo: 'bg-orange-100 dark:bg-orange-900/40',
    tekst: 'text-orange-800 dark:text-orange-200',
    kwadracik: 'bg-orange-600',
  },
  OSD: {
    krawedz: 'border-l-teal-600',
    tlo: 'bg-teal-100 dark:bg-teal-900/40',
    tekst: 'text-teal-800 dark:text-teal-200',
    kwadracik: 'bg-teal-600',
  },
  // Odstępstwo od makiety: brief sugerował lime, niedostępny w tym projekcie
  // (patrz komentarz wyżej) - yellow jest najbliższym odpowiednikiem.
  Dotacja: {
    krawedz: 'border-l-yellow-600',
    tlo: 'bg-yellow-100 dark:bg-yellow-900/40',
    tekst: 'text-yellow-800 dark:text-yellow-200',
    kwadracik: 'bg-yellow-600',
  },
  // Odstępstwo od makiety: brief sugerował sky, niedostępny w tym projekcie
  // (patrz komentarz wyżej) - cyan jest najbliższym odpowiednikiem.
  Trify: {
    krawedz: 'border-l-cyan-600',
    tlo: 'bg-cyan-100 dark:bg-cyan-900/40',
    tekst: 'text-cyan-800 dark:text-cyan-200',
    kwadracik: 'bg-cyan-600',
  },
  // Odstępstwo od makiety: brief sugerował rose, niedostępny w tym projekcie
  // (patrz komentarz wyżej) - pink jest najbliższym odpowiednikiem. Audyt i
  // AudytCP dzielą celowo ten sam kolor (dwa źródła tego samego rodzaju
  // zdarzenia - komentarze audytu OZE i CP).
  Audyt: {
    krawedz: 'border-l-pink-600',
    tlo: 'bg-pink-100 dark:bg-pink-900/40',
    tekst: 'text-pink-800 dark:text-pink-200',
    kwadracik: 'bg-pink-600',
  },
  AudytCP: {
    krawedz: 'border-l-pink-600',
    tlo: 'bg-pink-100 dark:bg-pink-900/40',
    tekst: 'text-pink-800 dark:text-pink-200',
    kwadracik: 'bg-pink-600',
  },
}

// Kolor domyślny (szary) dla źródła nieznanego `KOLORY_ZRODEL` - celowo NIE
// jest kluczem tej mapy (żeby `Object.keys(KOLORY_ZRODEL)` zostało dokładnie
// dziesięcioma prawdziwymi źródłami, bez sztucznego "fallback" wśród nich).
const KOLOR_ZRODLA_DOMYSLNY = {
  krawedz: 'border-l-gray-400',
  tlo: 'bg-gray-100 dark:bg-gray-800/40',
  tekst: 'text-gray-700 dark:text-gray-300',
  kwadracik: 'bg-gray-400',
}

// Zestaw kolorów dla jednego źródła (klucz `zakladka`/`zrodlo` wpisu) -
// nieznany/pusty klucz dostaje `KOLOR_ZRODLA_DOMYSLNY` (szary), nigdy
// `undefined`, żeby wywołujący mógł bezpiecznie czytać `.krawedz` itd. bez
// dodatkowego opcjonalnego łańcuchowania.
export function kolorZrodla(klucz) {
  return KOLORY_ZRODEL[klucz] || KOLOR_ZRODLA_DOMYSLNY
}

// Kierunki sortowania dropdownu feedu - wartości to dosłownie to, co
// backendowe `crm.volteo_notatki.posortuj(kierunek=...)` rozumie
// ("desc"/inny niż "desc" = rosnąco), żeby nie mieć dwóch słowników
// kierunków w dwóch językach po dwóch stronach.
export const KIERUNKI_SORTU = {
  NAJNOWSZE: 'desc',
  NAJSTARSZE: 'asc',
}

// Wyciąga wyłącznie "HH:mm" z surowego Datetime Frappe ("YYYY-MM-DD
// HH:mm[:ss]", separator dnia/godziny spacja albo "T", sekundy i ich
// ułamek opcjonalne) - celowo NIE przez `new Date(string)` (interpretacja
// jako UTC przesunęłaby godzinę, ten sam powód co `formatujTermin` w
// dataPolska.js), sam koniec stringa wystarcza. Eksportowana stąd (nie z
// dataPolska.js) bo to funkcja domeny feedu Notatki - używana zarówno przez
// godzinę "tylko HH:mm" na karcie (`NotatkaKarta.vue`, gdzie żyje udokumen-
// towany bliźniaczy lokalny odpowiednik z tego samego powodu co
// `dataPolska.js`'s `WZORZEC_DATY_CZASU`) jak i przez podsumowanie paska
// górnego (`ostatnia {dzień} {godzina}`).
export function godzinaZTekstu(dataCzas) {
  if (!dataCzas) return ''
  const dopasowanie = /(\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/.exec(String(dataCzas).trim())
  return dopasowanie ? `${dopasowanie[1]}:${dopasowanie[2]}` : ''
}

const KLUCZ_LOCALSTORAGE = 'notatki-filtr'

// Rozbija string "YYYY-MM-DD..." (separator dnia/godziny spacja albo "T",
// godzina/sekundy opcjonalne) na składniki kalendarzowe - NIE używa
// `new Date(string)` na wejściu tekstowym z tego samego powodu co
// `formatujTermin` w dataPolska.js (interpretacja jako UTC przesunęłaby
// dzień). Przyjmuje też obiekt Date wprost (lokalne składniki).
function _dzienKalendarzowy(dataCzas) {
  if (dataCzas instanceof Date) {
    if (Number.isNaN(dataCzas.getTime())) return null
    return {
      rok: dataCzas.getFullYear(),
      miesiac: dataCzas.getMonth() + 1,
      dzien: dataCzas.getDate(),
    }
  }
  if (typeof dataCzas === 'string') {
    const dopasowanie = /^(\d{4})-(\d{2})-(\d{2})/.exec(dataCzas)
    if (!dopasowanie) return null
    return {
      rok: Number(dopasowanie[1]),
      miesiac: Number(dopasowanie[2]),
      dzien: Number(dopasowanie[3]),
    }
  }
  return null
}

function _kluczDnia(skladniki) {
  return `${skladniki.rok}-${String(skladniki.miesiac).padStart(2, '0')}-${String(skladniki.dzien).padStart(2, '0')}`
}

// Różnica w pełnych dniach kalendarzowych między dwoma zestawami składników
// (a - b), liczona na lokalnej północy - odporna na przesunięcia czasu
// letniego/zimowego (inaczej niż proste dzielenie różnicy milisekund przez
// 86400000).
function _roznicaDni(a, b) {
  const da = new Date(a.rok, a.miesiac - 1, a.dzien)
  const db = new Date(b.rok, b.miesiac - 1, b.dzien)
  return Math.round((da - db) / 86400000)
}

// Etykieta dnia dla nagłówka grupy feedu: "Dziś", "Wczoraj", albo pełna
// polska data bez godziny (np. "pt., 25 wrz 2026"). `teraz` domyślnie
// bieżący moment, jawnie podawany w testach dla determinizmu na granicy
// północy.
export function etykietaDnia(dataCzas, teraz = new Date()) {
  const skladniki = _dzienKalendarzowy(dataCzas)
  const dzisiaj = _dzienKalendarzowy(teraz)
  if (!skladniki || !dzisiaj) return ''

  const roznica = _roznicaDni(dzisiaj, skladniki)
  if (roznica === 0) return 'Dziś'
  if (roznica === 1) return 'Wczoraj'

  const dzienTygodnia = DNI_TYGODNIA_SKROT[new Date(skladniki.rok, skladniki.miesiac - 1, skladniki.dzien).getDay()]
  const miesiacSkrot = MIESIACE_SKROT[skladniki.miesiac - 1]
  return `${dzienTygodnia}, ${skladniki.dzien} ${miesiacSkrot} ${skladniki.rok}`
}

// Grupuje wpisy feedu (już posortowane przez wywołującego, patrz
// `sortujFeed`) po dniu kalendarzowym ich pola `data`, zachowując kolejność
// wejściową - kolejne wpisy tego samego dnia trafiają do tej samej grupy
// (grupy nie są ponownie sortowane ani scalane nie-sąsiadująco, bo wejście
// jest już posortowane chronologicznie). Zwraca `[{ etykieta, wpisy }]`;
// wpis bez rozpoznawalnej daty trafia do własnej grupy z pustą etykietą
// zamiast znikać z feedu.
export function grupujPoDniu(wpisy, teraz = new Date()) {
  const grupy = []
  const indeksPoKluczu = new Map()

  for (const wpis of Array.isArray(wpisy) ? wpisy : []) {
    if (!wpis) continue
    const skladniki = _dzienKalendarzowy(wpis.data)
    const klucz = skladniki ? _kluczDnia(skladniki) : '\u0000brak-daty'

    if (!indeksPoKluczu.has(klucz)) {
      indeksPoKluczu.set(klucz, grupy.length)
      grupy.push({ etykieta: etykietaDnia(wpis.data, teraz), wpisy: [] })
    }
    grupy[indeksPoKluczu.get(klucz)].wpisy.push(wpis)
  }

  return grupy
}

// Filtruje wpisy feedu do tych, których `zrodlo` jest w `zaznaczone` (lista
// albo Set kluczy). Pusty wybór daje pusty wynik (decyzja świadoma: lista
// wielokrotnego wyboru bez żadnego zaznaczenia oznacza "nic nie pokazuj",
// nie "pokaż wszystko" - inaczej "Wyczyść" nie robiłoby nic widocznego).
export function filtrujFeed(wpisy, zaznaczone) {
  const zbior = zaznaczone instanceof Set ? zaznaczone : new Set(zaznaczone || [])
  if (zbior.size === 0) return []
  return (Array.isArray(wpisy) ? wpisy : []).filter((wpis) => wpis && zbior.has(wpis.zrodlo))
}

// Sortuje wpisy feedu po polu `data` (string ISO "YYYY-MM-DD HH:mm:ss",
// porównywalny leksykograficznie) - nie mutuje wejścia. `kierunek` inny niż
// `KIERUNKI_SORTU.NAJSTARSZE` sortuje malejąco (najnowsze pierwsze),
// spójnie z domyślnym zachowaniem backendowego `posortuj`.
export function sortujFeed(wpisy, kierunek = KIERUNKI_SORTU.NAJNOWSZE) {
  const lista = Array.isArray(wpisy) ? [...wpisy] : []
  const malejaco = kierunek !== KIERUNKI_SORTU.NAJSTARSZE
  return lista.sort((a, b) => {
    const da = a?.data || ''
    const db = b?.data || ''
    if (da === db) return 0
    if (malejaco) return da < db ? 1 : -1
    return da < db ? -1 : 1
  })
}

// Rozkłada string na formę porównywalną bez rozróżniania wielkości liter i
// znaków diakrytycznych ("ogonków") - `normalize('NFD')` rozbija znak
// akcentowany (np. "ą") na literę bazową + oddzielny znak diakrytyczny,
// usuwany przez wzorzec `[̀-ͯ]`; polskie "ł"/"Ł" NIE mają takiego
// rozkładu (odrębny punkt kodowy Unicode, nie litera + diakrytyk), więc
// wymagają osobnego podstawienia - bez niego "łańcuch" i "lancuch" by się
// nie dopasowały.
function _normalizujDoWyszukiwania(tekst) {
  return String(tekst ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/ł/g, 'l')
    .replace(/Ł/g, 'L')
    .toLowerCase()
    .trim()
}

// Wyciąga czysty tekst z HTML treści notatki/komentarza - lustro prywatnego
// `htmlNaTekst()` w `aktualizacje.js` (ten sam trik: div.innerHTML ->
// textContent), duplikowane tutaj zamiast eksportowane stamtąd z tego
// samego powodu udokumentowanego w nagłówku `aktualizacje.js` (unikanie
// przypadkowego importu barrela `@/utils` przez transitywny łańcuch) -
// `notatki.js` ma być frappe-free bez importu `@/utils`, a duplikacja
// dwóch linijek jest tańsza niż ryzyko tej pułapki.
function _htmlNaTekst(html) {
  const div = document.createElement('div')
  div.innerHTML = html || ''
  return div.textContent || div.innerText || ''
}

// Filtruje wpisy feedu do tych pasujących do `fraza` po treści (bez
// znaczników HTML), imieniu i nazwisku autora, oraz nazwach załączonych
// plików - bez rozróżniania wielkości liter i znaków diakrytycznych (patrz
// `_normalizujDoWyszukiwania`). Pusta/samo-białoznakowa fraza zwraca
// wejście bez zmian (nie pustą listę - w odróżnieniu od `filtrujFeed`,
// pusta fraza wyszukiwania znaczy "brak filtra", nie "nic nie pokazuj").
// Nie mutuje wejścia.
export function szukajWFeedzie(wpisy, fraza) {
  const lista = Array.isArray(wpisy) ? wpisy : []
  const zapytanie = _normalizujDoWyszukiwania(fraza)
  if (!zapytanie) return lista

  return lista.filter((wpis) => {
    if (!wpis) return false

    const tresc = _normalizujDoWyszukiwania(_htmlNaTekst(wpis.tekst_html || wpis.tekst || ''))
    if (tresc.includes(zapytanie)) return true

    const autor = _normalizujDoWyszukiwania(wpis.autor_nazwa || wpis.autor || wpis.owner || '')
    if (autor.includes(zapytanie)) return true

    const pliki = Array.isArray(wpis.pliki) ? wpis.pliki : []
    return pliki.some((p) => _normalizujDoWyszukiwania(p?.file_name).includes(zapytanie))
  })
}

// Podsumowanie liczbowe feedu dla paska górnego ("17 notatek | 6
// załączników | ostatnia dziś 15:25 | autorzy: 2") - wywołujący (`Notatki
// Tab.vue`) liczy to na liście PO filtrze źródeł, PRZED wyszukiwaniem
// (decyzja właściciela, issue ops#206): podsumowanie ma odpowiadać na
// "ile jest w wybranych źródłach", nie na "ile pasuje do bieżącej frazy".
//
// `ostatnia` to string ISO ("YYYY-MM-DD HH:mm:ss", porównywalny leksyko-
// graficznie jak wszędzie indziej w tym pliku) najpóźniejszego wpisu, albo
// `null` dla pustej listy - wywołujący formatuje go do postaci "dziś
// 15:25" przez `etykietaDnia`/`godzinaZTekstu`, ten moduł zwraca surowe
// dane, nie gotowy tekst (ten sam podział odpowiedzialności co
// `grupujPoDniu`/`etykietaDnia`).
//
// `autorzy` liczy UNIKALNYCH autorów po `autor`/`owner` (identyfikator
// konta), nie po `autor_nazwa` (wyświetlana nazwa) - dwa wpisy tego samego
// konta mają zawsze ten sam `autor`, nawet gdyby `autor_nazwa` się kiedyś
// rozjechało (zmiana nazwiska między wpisami).
export function podsumowanieFeedu(wpisy) {
  const lista = Array.isArray(wpisy) ? wpisy : []
  let zalaczniki = 0
  let ostatnia = null
  const autorzy = new Set()

  for (const wpis of lista) {
    if (!wpis) continue
    zalaczniki += Array.isArray(wpis.pliki) ? wpis.pliki.length : 0
    if (wpis.data && (!ostatnia || wpis.data > ostatnia)) ostatnia = wpis.data
    const kluczAutora = wpis.autor || wpis.owner || wpis.autor_nazwa
    if (kluczAutora) autorzy.add(kluczAutora)
  }

  return { notatki: lista.length, zalaczniki, ostatnia, autorzy: autorzy.size }
}

// Odczytuje filtr feedu zapisany w localStorage (klucz "notatki-filtr"),
// per przeglądarkę/użytkownika - `try/catch` na odczycie, bo localStorage
// może rzucić (tryb prywatny, zablokowane site data) albo zwrócić coś, co
// nie parsuje się jako JSON. `kluczeDostepne` (lista kluczy źródeł, zwykle
// `zrodla.map(z => z.klucz)` z odpowiedzi API) jest ZAWSZE domyślnym i
// filtrującym zbiorem: zaznaczenie zapisane wcześniej jest przycinane do
// kluczy, które nadal istnieją, żeby źródło usunięte/przemianowane między
// sesjami nie zostawiło martwego, niezaznaczalnego wpisu w zapisanym
// stanie. Domyślnie (brak zapisu, zapis niepoprawny, albo pusty po
// przycięciu) wszystko jest zaznaczone.
export function wczytajFiltr(kluczeDostepne) {
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

// Zapisuje filtr feedu do localStorage - `try/catch` na zapisie (patrz
// `wczytajFiltr`), cichy brak zapisu zamiast rzucania: filtr po prostu nie
// przetrwa przeładowania w tej jednej sesji, reszta aplikacji działa dalej.
export function zapiszFiltr(zaznaczone, kierunek) {
  try {
    localStorage.setItem(
      KLUCZ_LOCALSTORAGE,
      JSON.stringify({ zaznaczone: Array.isArray(zaznaczone) ? zaznaczone : [], kierunek }),
    )
  } catch {
    // localStorage niedostępny (tryb prywatny, zablokowane site data) -
    // filtr po prostu nie przetrwa przeładowania, reszta działa dalej.
  }
}
