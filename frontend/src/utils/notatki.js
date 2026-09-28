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
