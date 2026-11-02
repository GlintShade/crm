// Kalendarz spotkań handlowców (ops#318): czysta logika siatki, dat i kolorów.
//
// Frappe-free (bez importu `@/utils`, `frappe-ui`, dayjs ani `~icons`), ten sam
// wzorzec co dataPolska.js: Datetime parsowany TEKSTOWO, nigdy `new Date(string)`
// (interpretacja jako UTC przesunęłaby godzinę). Daty kalendarzowe to napisy
// `RRRR-MM-DD`; obiekt `Date` powstaje tylko z lokalnych składowych (rok, miesiąc,
// dzień), więc strefa czasowa nie ma wpływu na wynik.
import { DNI_TYGODNIA_SKROT, MIESIACE_SKROT } from './dataPolska'

export const OS_OD = 8
export const OS_DO = 18
export const DLUGOSC_SPOTKANIA_H = 1.5
export const PX_NA_GODZINE = 48
export const PX_NA_GODZINE_KOMPAKT = 30
export const STATUS_UMOWIONY = 'Umówiony'

const DNI_PELNE = [
  'niedziela',
  'poniedziałek',
  'wtorek',
  'środa',
  'czwartek',
  'piątek',
  'sobota',
]
const WZORZEC_DATY = /^(\d{4})-(\d{2})-(\d{2})$/
const WZORZEC_TERMINU =
  /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/

function d2(n) {
  return String(n).padStart(2, '0')
}

function iso(rok, miesiac, dzien) {
  return `${rok}-${d2(miesiac)}-${d2(dzien)}`
}

/** Rozbiera `RRRR-MM-DD` (także z doklejoną godziną); null, gdy niepoprawne. */
export function rozbierzDate(dataIso) {
  if (typeof dataIso !== 'string') return null
  const dopasowanie = WZORZEC_DATY.exec(dataIso.slice(0, 10))
  if (!dopasowanie) return null
  const rok = Number(dopasowanie[1])
  const miesiac = Number(dopasowanie[2])
  const dzien = Number(dopasowanie[3])
  const data = new Date(rok, miesiac - 1, dzien)
  if (
    data.getFullYear() !== rok ||
    data.getMonth() !== miesiac - 1 ||
    data.getDate() !== dzien
  ) {
    return null
  }
  return { rok, miesiac, dzien }
}

/** Rozbiera Datetime Frappe na datę i godzinę; null, gdy niepoprawny. */
export function rozbierzTermin(termin) {
  if (typeof termin !== 'string') return null
  const dopasowanie = WZORZEC_TERMINU.exec(termin)
  if (!dopasowanie) return null
  const data = rozbierzDate(
    `${dopasowanie[1]}-${dopasowanie[2]}-${dopasowanie[3]}`,
  )
  const godzina = Number(dopasowanie[4])
  const minuta = Number(dopasowanie[5])
  if (!data || godzina > 23 || minuta > 59) return null
  return { ...data, godzina, minuta }
}

export function dataTerminu(termin) {
  const t = rozbierzTermin(termin)
  return t ? iso(t.rok, t.miesiac, t.dzien) : ''
}

export function godzinaTekst(termin) {
  const t = rozbierzTermin(termin)
  return t ? `${d2(t.godzina)}:${d2(t.minuta)}` : ''
}

/** Dodaje `n` dni (także ujemne) do daty `RRRR-MM-DD`. */
export function dodajDni(dataIso, n) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  const wynik = new Date(d.rok, d.miesiac - 1, d.dzien + n)
  return iso(wynik.getFullYear(), wynik.getMonth() + 1, wynik.getDate())
}

/** Indeks dnia tygodnia, 0 = poniedziałek ... 6 = niedziela; -1 dla niepoprawnej daty. */
export function indeksDniaTygodnia(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return -1
  return (new Date(d.rok, d.miesiac - 1, d.dzien).getDay() + 6) % 7
}

export function czyWeekend(dataIso) {
  return indeksDniaTygodnia(dataIso) >= 5
}

export function dzisIso(teraz = new Date()) {
  return iso(teraz.getFullYear(), teraz.getMonth() + 1, teraz.getDate())
}

export function czyDzis(dataIso, teraz = new Date()) {
  return dataIso === dzisIso(teraz)
}

/** `{ od: poniedziałek, do: niedziela }` tygodnia zawierającego `dataIso`. */
export function zakresTygodnia(dataIso) {
  const idx = indeksDniaTygodnia(dataIso)
  if (idx < 0) return { od: '', do: '' }
  const od = dodajDni(dataIso.slice(0, 10), -idx)
  return { od, do: dodajDni(od, 6) }
}

/** Siedem dat `RRRR-MM-DD` od poniedziałku. */
export function dniTygodnia(poniedzialek) {
  if (!rozbierzDate(poniedzialek)) return []
  return Array.from({ length: 7 }, (_, i) => dodajDni(poniedzialek, i))
}

/** Zakres widoku: dla tygodnia pon..niedz, dla dnia jeden dzień. */
export function zakresWidoku(dataIso, widok) {
  if (widok === 'dzien') return { od: dataIso, do: dataIso }
  return zakresTygodnia(dataIso)
}

/** Przesunięcie daty kotwicy o krok widoku (tydzień = 7 dni, dzień = 1). */
export function przesunKotwice(dataIso, widok, kierunek) {
  return dodajDni(dataIso, (widok === 'dzien' ? 1 : 7) * kierunek)
}

function skrotDnia(d) {
  return `${d.dzien} ${MIESIACE_SKROT[d.miesiac - 1]}`
}

/** "2 lis do 8 lis 2026"; przy różnych latach rok przy obu końcach. */
export function etykietaZakresu(od, doDnia) {
  const a = rozbierzDate(od)
  const b = rozbierzDate(doDnia)
  if (!a || !b) return ''
  if (a.rok === b.rok) return `${skrotDnia(a)} do ${skrotDnia(b)} ${b.rok}`
  return `${skrotDnia(a)} ${a.rok} do ${skrotDnia(b)} ${b.rok}`
}

/** "poniedziałek, 2 lis 2026". */
export function etykietaDnia(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  const dzienTygodnia =
    DNI_PELNE[new Date(d.rok, d.miesiac - 1, d.dzien).getDay()]
  return `${dzienTygodnia}, ${skrotDnia(d)} ${d.rok}`
}

/** "pon. 2" do etykiety wiersza/kolumny dnia. */
export function etykietaDniaKrotka(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  const skrot =
    DNI_TYGODNIA_SKROT[new Date(d.rok, d.miesiac - 1, d.dzien).getDay()]
  return `${skrot} ${d.dzien}`
}

/** "pon. 2 lis" do nagłówka kolumny w widoku pionowym. */
export function etykietaDniaZMiesiacem(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  return `${etykietaDniaKrotka(dataIso)} ${MIESIACE_SKROT[d.miesiac - 1]}`
}

export function czyUmowiony(status) {
  return status === STATUS_UMOWIONY
}

export function liczbaUmowionych(lista) {
  return (lista || []).filter((s) => czyUmowiony(s.status)).length
}

/** Początek spotkania w godzinach dziesiętnych (10:30 => 10.5); null, gdy brak terminu. */
export function poczatekWGodzinach(termin) {
  const t = rozbierzTermin(termin)
  return t ? t.godzina + t.minuta / 60 : null
}

/**
 * Zakres osi godzin: domyślnie 8 do 18, ale spotkanie poza zakresem rozszerza oś
 * (nigdy nie jest ukrywane). Koniec spotkania = początek + `dlugoscH`.
 */
export function osGodzin(
  spotkania,
  od = OS_OD,
  doGodziny = OS_DO,
  dlugoscH = DLUGOSC_SPOTKANIA_H,
) {
  let minimum = od
  let maksimum = doGodziny
  for (const s of spotkania || []) {
    const start = poczatekWGodzinach(s.termin)
    if (start === null) continue
    minimum = Math.min(minimum, Math.floor(start))
    maksimum = Math.max(maksimum, Math.ceil(start + dlugoscH))
  }
  return { od: Math.max(0, minimum), do: Math.min(24, maksimum) }
}

/** Godziny do nagłówka i linii siatki: od, od+1, ..., do. */
export function godzinyOsi(od, doGodziny) {
  const wynik = []
  for (let g = od; g <= doGodziny; g += 1) wynik.push(g)
  return wynik
}

/** Pozycja poziomego paska w % szerokości osi (początek i szerokość). */
export function pozycjaPaska(
  termin,
  od = OS_OD,
  doGodziny = OS_DO,
  dlugoscH = DLUGOSC_SPOTKANIA_H,
) {
  const start = poczatekWGodzinach(termin)
  const zakres = doGodziny - od
  if (start === null || zakres <= 0) return { leftPct: 0, widthPct: 0 }
  const lewo = Math.max(0, ((start - od) / zakres) * 100)
  const szerokosc = Math.min((dlugoscH / zakres) * 100, 100 - lewo)
  return { leftPct: lewo, widthPct: Math.max(0, szerokosc) }
}

/** Wysokość godziny w widoku pionowym: pełna (jeden handlowiec) albo kompaktowa (karta w tablicy). */
export function skalaPionowa(kompakt) {
  return kompakt ? PX_NA_GODZINE_KOMPAKT : PX_NA_GODZINE
}

/** Pozycja bloku w widoku pionowym w pikselach (góra i wysokość). */
export function pozycjaBlokuPion(
  termin,
  od = OS_OD,
  pxNaH = PX_NA_GODZINE,
  dlugoscH = DLUGOSC_SPOTKANIA_H,
) {
  const start = poczatekWGodzinach(termin)
  if (start === null) return { topPx: 0, heightPx: 0 }
  return {
    topPx: Math.max(0, (start - od) * pxNaH),
    heightPx: dlugoscH * pxNaH,
  }
}

/** Pozycja kreski "teraz" w % osi; null, gdy poza osią. */
export function pozycjaTeraz(
  teraz = new Date(),
  od = OS_OD,
  doGodziny = OS_DO,
) {
  const h = teraz.getHours() + teraz.getMinutes() / 60
  if (h < od || h > doGodziny) return null
  return ((h - od) / (doGodziny - od)) * 100
}

/** Zaokrągla minuty od północy do najbliższej półgodziny. */
export function zaokraglijDo30(minuty) {
  return Math.round(minuty / 30) * 30
}

/** Godzina `HH:MM` z kliknięcia w pozycji `xPct` (0..100) na osi `od..do`, co 30 min. */
export function godzinaZKlikniecia(xPct, od = OS_OD, doGodziny = OS_DO) {
  const wzgledne = Math.min(100, Math.max(0, xPct))
  const minuty = zaokraglijDo30((od + (wzgledne / 100) * (doGodziny - od)) * 60)
  const ograniczone = Math.min(
    Math.max(minuty, od * 60),
    Math.max(od * 60, doGodziny * 60 - 30),
  )
  return `${d2(Math.floor(ograniczone / 60))}:${d2(ograniczone % 60)}`
}

/** Godzina `HH:MM` z kliknięcia w pionie (`yPx` od góry siatki), co 30 min. */
export function godzinaZKliknieciaPion(
  yPx,
  od = OS_OD,
  doGodziny = OS_DO,
  pxNaH = PX_NA_GODZINE,
) {
  const minuty = zaokraglijDo30((od + Math.max(0, yPx) / pxNaH) * 60)
  const ograniczone = Math.min(
    Math.max(minuty, od * 60),
    Math.max(od * 60, doGodziny * 60 - 30),
  )
  return `${d2(Math.floor(ograniczone / 60))}:${d2(ograniczone % 60)}`
}

/** Opcje godzin do modalu: 06:00 do 21:00 co 30 min. */
export function opcjeGodzin(od = 6, doGodziny = 21) {
  const wynik = []
  for (let m = od * 60; m <= doGodziny * 60; m += 30) {
    wynik.push(`${d2(Math.floor(m / 60))}:${d2(m % 60)}`)
  }
  return wynik
}

/** Datetime dla API: `RRRR-MM-DD GG:MM:00`; '' gdy brak daty lub godziny. */
export function terminDoApi(dataIso, godzina) {
  if (!rozbierzDate(dataIso) || !/^\d{2}:\d{2}$/.test(godzina || '')) return ''
  return `${dataIso} ${godzina}:00`
}

// Kolory handlowców: wyłącznie tokeny motywu frappe-ui (nigdy rose/emerald/sky/lime,
// które nie istnieją w presecie). Klasy jako pełne literały, żeby Tailwind je wykrył.
const PALETA = [
  {
    pelny: 'bg-surface-blue-6',
    jasny: 'bg-surface-blue-2',
    tekst: 'text-ink-blue-8',
    ramka: 'border-outline-blue-3',
  },
  {
    pelny: 'bg-surface-green-6',
    jasny: 'bg-surface-green-2',
    tekst: 'text-ink-green-8',
    ramka: 'border-outline-green-3',
  },
  {
    pelny: 'bg-surface-violet-6',
    jasny: 'bg-surface-violet-2',
    tekst: 'text-ink-violet-8',
    ramka: 'border-outline-violet-3',
  },
  {
    pelny: 'bg-surface-pink-6',
    jasny: 'bg-surface-pink-2',
    tekst: 'text-ink-pink-8',
    ramka: 'border-outline-pink-3',
  },
  {
    pelny: 'bg-surface-cyan-6',
    jasny: 'bg-surface-cyan-2',
    tekst: 'text-ink-cyan-8',
    ramka: 'border-outline-cyan-3',
  },
  {
    pelny: 'bg-surface-orange-6',
    jasny: 'bg-surface-orange-2',
    tekst: 'text-ink-orange-8',
    ramka: 'border-outline-orange-3',
  },
]

export function kolorHandlowca(index) {
  const n = Number.isInteger(index) && index >= 0 ? index : 0
  return PALETA[n % PALETA.length]
}

export const LICZBA_KOLOROW = PALETA.length

/** Inicjały (maks. 2 litery, wielkie) z imienia i nazwiska; '' dla pustego. */
export function inicjaly(fullName) {
  const slowa = String(fullName || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!slowa.length) return ''
  const pierwsza = slowa[0][0]
  const druga = slowa.length > 1 ? slowa[slowa.length - 1][0] : ''
  return (pierwsza + druga).toLocaleUpperCase('pl-PL')
}

/** Grupuje spotkania po dacie `RRRR-MM-DD`, każda grupa posortowana po terminie. */
export function pogrupujPoDniach(lista) {
  const wynik = {}
  for (const s of lista || []) {
    const dzien = dataTerminu(s.termin)
    if (!dzien) continue
    if (!wynik[dzien]) wynik[dzien] = []
    wynik[dzien].push(s)
  }
  for (const dzien of Object.keys(wynik)) {
    wynik[dzien] = [...wynik[dzien]].sort((a, b) =>
      a.termin < b.termin ? -1 : a.termin > b.termin ? 1 : 0,
    )
  }
  return wynik
}

/** Tooltip paska: "HH:MM Imię Nazwisko, Miasto". */
export function opisSpotkania(s) {
  const godzina = godzinaTekst(s.termin)
  const czesci = [[godzina, s.lead_name].filter(Boolean).join(' ')]
  if (s.miasto) czesci.push(s.miasto)
  return czesci.filter(Boolean).join(', ')
}

function liczbaSpotkan(n) {
  if (n === 1) return '1 spotkanie'
  const reszta10 = n % 10
  const reszta100 = n % 100
  if (reszta10 >= 2 && reszta10 <= 4 && !(reszta100 >= 12 && reszta100 <= 14))
    return `${n} spotkania`
  return `${n} spotkań`
}

/** "umówionych" w odmianie do chipa na karcie: "3 umówione" / "1 umówione" / "0 umówionych". */
export function etykietaUmowionych(n) {
  if (n === 1) return '1 umówione'
  const reszta10 = n % 10
  const reszta100 = n % 100
  if (reszta10 >= 2 && reszta10 <= 4 && !(reszta100 >= 12 && reszta100 <= 14))
    return `${n} umówione`
  return `${n} umówionych`
}

/** Podpowiedź w modalu: "Jan Kowalski ma tego dnia 2 spotkania: 10:00, 13:30"; '' gdy brak. */
export function podpowiedzDnia(imie, lista, dataIso) {
  const doDnia = (lista || []).filter((s) => dataTerminu(s.termin) === dataIso)
  if (!doDnia.length) return ''
  const godziny = [...doDnia]
    .sort((a, b) => (a.termin < b.termin ? -1 : 1))
    .map((s) => godzinaTekst(s.termin))
    .join(', ')
  return `${imie} ma tego dnia ${liczbaSpotkan(doDnia.length)}: ${godziny}`
}

export const WIDOKI = ['tydzien', 'dzien']
export const TRYBY_WSZYSCY = ['tablica', 'jeden']
export const ORIENTACJE = ['poziomo', 'pionowo']

/** Klucz localStorage per użytkownik. */
export function kluczStanu(user) {
  return `volteo_kalendarz:${user || ''}`
}

/**
 * Stan widoku z surowego JSON-a z localStorage, z walidacją każdego pola i
 * domyślnymi wartościami (zakres "wlasny": od razu pionowo, jeden handlowiec).
 */
export function wczytajStan(surowy, zakres) {
  const domyslny = {
    widok: 'tydzien',
    tryb: 'tablica',
    orientacja: zakres === 'wlasny' ? 'pionowo' : 'poziomo',
    handlowiec: '',
    filtr: [],
  }
  let dane = null
  try {
    dane = surowy ? JSON.parse(surowy) : null
  } catch (e) {
    dane = null
  }
  if (!dane || typeof dane !== 'object') return domyslny
  return {
    widok: WIDOKI.includes(dane.widok) ? dane.widok : domyslny.widok,
    tryb: TRYBY_WSZYSCY.includes(dane.tryb) ? dane.tryb : domyslny.tryb,
    orientacja: ORIENTACJE.includes(dane.orientacja)
      ? dane.orientacja
      : domyslny.orientacja,
    handlowiec: typeof dane.handlowiec === 'string' ? dane.handlowiec : '',
    filtr: Array.isArray(dane.filtr)
      ? dane.filtr.filter((x) => typeof x === 'string')
      : [],
  }
}
