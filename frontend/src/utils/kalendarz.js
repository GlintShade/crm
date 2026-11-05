// Kalendarz spotkań handlowców (ops#318): czysta logika siatki, dat i kolorów.
//
// Frappe-free (bez importu `@/utils`, `frappe-ui`, dayjs ani `~icons`), ten sam
// wzorzec co dataPolska.js: Datetime parsowany TEKSTOWO, nigdy `new Date(string)`
// (interpretacja jako UTC przesunęłaby godzinę). Daty kalendarzowe to napisy
// `RRRR-MM-DD`; obiekt `Date` powstaje tylko z lokalnych składowych (rok, miesiąc,
// dzień), więc strefa czasowa nie ma wpływu na wynik.
import { DNI_TYGODNIA_SKROT, MIESIACE_SKROT } from './dataPolska'

export const OS_OD = 8
export const OS_DO = 22
export const DLUGOSC_SPOTKANIA_H = 2
export const PX_NA_GODZINE = 36
export const PX_NA_GODZINE_KOMPAKT = 27
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

function dzienMiesiacSkrot(d) {
  return `${d.dzien} ${MIESIACE_SKROT[d.miesiac - 1]}`
}

/** "2 lis do 8 lis 2026"; przy różnych latach rok przy obu końcach. */
export function etykietaZakresu(od, doDnia) {
  const a = rozbierzDate(od)
  const b = rozbierzDate(doDnia)
  if (!a || !b) return ''
  if (a.rok === b.rok)
    return `${dzienMiesiacSkrot(a)} do ${dzienMiesiacSkrot(b)} ${b.rok}`
  return `${dzienMiesiacSkrot(a)} ${a.rok} do ${dzienMiesiacSkrot(b)} ${b.rok}`
}

/** "poniedziałek, 2 lis 2026". */
export function etykietaDnia(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  const dzienTygodnia =
    DNI_PELNE[new Date(d.rok, d.miesiac - 1, d.dzien).getDay()]
  return `${dzienTygodnia}, ${dzienMiesiacSkrot(d)} ${d.rok}`
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
 * Zakres osi godzin: domyślnie 8 do 22, ale spotkanie poza zakresem rozszerza oś
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

/** Poczatek polgodzinnego slotu, w ktorym lezy `minuty` (z tolerancja na float). */
export function podlogaDo30(minuty) {
  return Math.floor(minuty / 30 + 1e-6) * 30
}

/** Godzina `HH:MM` z kliknięcia w pozycji `xPct` (0..100) na osi `od..do`, co 30 min. */
export function godzinaZKlikniecia(xPct, od = OS_OD, doGodziny = OS_DO) {
  const wzgledne = Math.min(100, Math.max(0, xPct))
  const minuty = podlogaDo30((od + (wzgledne / 100) * (doGodziny - od)) * 60)
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
  const minuty = podlogaDo30((od + Math.max(0, yPx) / pxNaH) * 60)
  const ograniczone = Math.min(
    Math.max(minuty, od * 60),
    Math.max(od * 60, doGodziny * 60 - 30),
  )
  return `${d2(Math.floor(ograniczone / 60))}:${d2(ograniczone % 60)}`
}

/** Godziny dziesietne z `HH:MM`. */
function godzinaDoLiczby(godzina) {
  const [h, m] = godzina.split(':').map(Number)
  return h + m / 60
}

/**
 * Blok 30 min, ktory przypisze klik w pozycji `xPct` (poziomo). Ta sama
 * godzina co `godzinaZKlikniecia`, plus left/width w % do podswietlenia.
 */
export function blokKlikniecia(xPct, od = OS_OD, doGodziny = OS_DO) {
  const godzina = godzinaZKlikniecia(xPct, od, doGodziny)
  const start = godzinaDoLiczby(godzina)
  return {
    godzina,
    ...stylOdcinkaPoziomo(start, start + 0.5, od, doGodziny),
  }
}

/** Blok 30 min dla kliku w pionie (`yPx` od gory siatki): top/height w px. */
export function blokKliknieciaPion(
  yPx,
  od = OS_OD,
  doGodziny = OS_DO,
  pxNaH = PX_NA_GODZINE,
) {
  const godzina = godzinaZKliknieciaPion(yPx, od, doGodziny, pxNaH)
  const start = godzinaDoLiczby(godzina)
  return { godzina, ...stylOdcinkaPion(start, start + 0.5, od, pxNaH) }
}

/** Opcje godzin do modalu: 06:00 do 21:00 co 30 min. */
export function opcjeGodzin(od = 6, doGodziny = 22) {
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

// ---------------------------------------------------------------------------
// Runda UI (ops#318): wspólna oś, ścieżki dni, linie, etykiety, dymek.
// ---------------------------------------------------------------------------

export const MIN_SZEROKOSC_PASKA_PX = 44
export const WYSOKOSC_NAGLOWKA_DNI_PX = 28

/** Wymiary ścieżek dni w karcie poziomej: pełna (`duzy`) albo kompaktowa (tablica). */
export function wymiaryTorow(duzy) {
  return duzy
    ? { sciezkaPx: 32, odstepPx: 7, kolumnaDniPx: 58 }
    : { sciezkaPx: 22, odstepPx: 5, kolumnaDniPx: 58 }
}

/** Nazwisko klienta = ostatni człon `lead_name`; '' dla pustego. */
export function nazwisko(leadName) {
  const slowa = String(leadName || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  return slowa.length ? slowa[slowa.length - 1] : ''
}

/** Skrót dnia tygodnia bez kropki ("pon"). */
export function skrotDnia(dataIso) {
  const d = rozbierzDate(dataIso)
  if (!d) return ''
  return DNI_TYGODNIA_SKROT[
    new Date(d.rok, d.miesiac - 1, d.dzien).getDay()
  ].replace('.', '')
}

/** Numer dnia miesiąca ("2"); '' dla niepoprawnej daty. */
export function numerDnia(dataIso) {
  const d = rozbierzDate(dataIso)
  return d ? String(d.dzien) : ''
}

/**
 * Wspólna oś godzin dla wielu list spotkań (tablica): zakres 8 do 22 rozszerzony
 * o spotkania WSZYSTKICH podanych handlowców, żeby karty obok siebie miały te
 * same kolumny. `mapa` = { user: [spotkania] }, `uzytkownicy` = widoczni.
 */
export function osWspolna(mapa, uzytkownicy, od = OS_OD, doGodziny = OS_DO) {
  const wszystkie = []
  for (const u of uzytkownicy || [])
    wszystkie.push(...((mapa && mapa[u]) || []))
  return osGodzin(wszystkie, od, doGodziny)
}

/**
 * Chip liczby spotkań w nagłówku karty: liczba umówionych ("1 umówione",
 * "3 umówione", "5 umówionych"). Szary chip (wolny=true): "wolny cały tydzień"
 * (w widoku dnia "wolny cały dzień") tylko gdy NIE MA żadnych spotkań, a gdy są
 * wyłącznie niepotwierdzone, "0 umówionych".
 */
export function etykietaChipa(spotkania, okres = 'tydzien') {
  const lista = spotkania || []
  if (!lista.length) {
    return {
      tekst: okres === 'dzien' ? 'wolny cały dzień' : 'wolny cały tydzień',
      wolny: true,
    }
  }
  const umowione = liczbaUmowionych(lista)
  return { tekst: etykietaUmowionych(umowione), wolny: umowione === 0 }
}

/** Pozycja godziny `g` na osi `od..do` w % szerokości (do centrowania etykiet i linii). */
export function pozycjaGodzinyPct(g, od, doGodziny) {
  if (doGodziny <= od) return 0
  return ((g - od) / (doGodziny - od)) * 100
}

/**
 * Godziny z etykietą nad osią poziomą: co `krok` godzin od `od`, zawsze z
 * ostatnią godziną osi (`do`), bez duplikatu.
 */
export function godzinyEtykiet(od, doGodziny, krok = 1) {
  const wynik = []
  for (let g = od; g <= doGodziny; g += krok) wynik.push(g)
  if (wynik[wynik.length - 1] !== doGodziny && doGodziny > od)
    wynik.push(doGodziny)
  return wynik
}

/** Linie pionowe poziomej karty: co `krok` godzin, tylko wewnątrz osi (bez krawędzi). */
export function liniePionowe(od, doGodziny, krok = 2) {
  const wynik = []
  for (let g = od + krok; g < doGodziny; g += krok) wynik.push(g)
  return wynik
}

/**
 * Styl paska poziomego: początek i szerokość w % z minimalną szerokością
 * `minPx`; `left` ograniczony tak, by pasek z minimalną szerokością nie wyszedł
 * poza prawy brzeg ścieżki.
 */
export function stylPaskaPoziomo(
  termin,
  od,
  doGodziny,
  minPx = MIN_SZEROKOSC_PASKA_PX,
) {
  const p = pozycjaPaska(termin, od, doGodziny)
  return {
    left: `min(${p.leftPct}%, calc(100% - ${minPx}px))`,
    width: `${p.widthPct}%`,
    minWidth: `${minPx}px`,
  }
}

/** Pozycja bloku w widoku pionowym w pikselach, w układzie współrzędnych siatki godzin. */
export const pozycjaBlokuPx = pozycjaBlokuPion

/** Wysokość siatki godzin w widoku pionowym (px); nagłówek dni NIE jest jej częścią. */
export function wysokoscSiatkiPion(od, doGodziny, pxNaH) {
  return Math.max(0, (doGodziny - od) * pxNaH)
}

/** Trzy linie dymka: czas i data, klient i miasto, status i telefon. */
export function opisDymka(s) {
  const godzina = godzinaTekst(s.termin)
  const dzien = dataTerminu(s.termin)
  const linia1 = [godzina, dzien ? etykietaDnia(dzien).replace(', ', ' ') : '']
    .filter(Boolean)
    .join(', ')
  const linia2 = [s.lead_name, s.miasto].filter(Boolean).join(', ')
  const linia3 = [s.status, s.telefon].filter(Boolean).join(', ')
  return { linia1, linia2, linia3 }
}

// ---------------------------------------------------------------------------
// Proporcje karty pionowej: wysokość = szerokość * 9/16 (ops#318).
// ---------------------------------------------------------------------------

export const PROPORCJA_KARTY = 9 / 16
export const MIN_PX_NA_GODZINE = 14
export const MAX_PX_NA_GODZINE = 36
/** Poniżej tej skali blok spotkania pokazuje jedną linię "HH:MM Nazwisko". */
export const PROG_JEDNA_LINIA_PX = 24
/** Poniżej tej skali etykiety godzin tylko co 2 h (żeby się nie nakładały). */
export const PROG_ETYKIETY_CO_2H_PX = 20
/** Stałe wysokości karty pionowej poza skalą godzin (px). */
export const STALE_KARTY_PIONOWEJ = {
  narzut: 30, // padding 2 x 14 i obramowanie 2 x 1
  naglowekKarty: 0, // wysokość nagłówka karty z marginesem (0 = brak nagłówka)
  naglowekDni: WYSOKOSC_NAGLOWKA_DNI_PX,
  dolny: 8, // pb-2 na wystającą etykietę ostatniej godziny
  min: MIN_PX_NA_GODZINE,
  max: MAX_PX_NA_GODZINE,
}

/**
 * Skala px/h tak, by karta miała proporcje ok. 16:9: wysokość docelowa =
 * szerokość * 9/16, z niej odejmowane stałe (padding, nagłówek karty, nagłówek
 * dni, dolny margines), reszta dzielona przez liczbę godzin osi i obcięta do
 * `min..max`. Niepoprawne wejście daje `max`.
 */
export function pxNaGodzineZSzerokosci(szerokosc, liczbaGodzin, stale = {}) {
  const s = { ...STALE_KARTY_PIONOWEJ, ...stale }
  if (
    !Number.isFinite(szerokosc) ||
    szerokosc <= 0 ||
    !Number.isFinite(liczbaGodzin) ||
    liczbaGodzin <= 0
  ) {
    return s.max
  }
  const wysokoscDocelowa = szerokosc * PROPORCJA_KARTY
  const naSkale =
    wysokoscDocelowa - s.narzut - s.naglowekKarty - s.naglowekDni - s.dolny
  return Math.min(s.max, Math.max(s.min, Math.floor(naSkale / liczbaGodzin)))
}

/** Czy blok przy tej skali ma pokazać jedną linię "HH:MM Nazwisko" (bez miasta). */
export function czyJednaLinia(pxNaH) {
  return pxNaH < PROG_JEDNA_LINIA_PX
}

/** Godziny z etykietą w widoku pionowym: wszystkie, a przy małej skali co 2 h. */
export function godzinyEtykietPion(od, doGodziny, pxNaH) {
  const krok = pxNaH < PROG_ETYKIETY_CO_2H_PX ? 2 : 1
  return godzinyOsi(od, doGodziny).filter((_, i) => i % krok === 0)
}

// ---------------------------------------------------------------------------
// Nakładające się spotkania tego samego handlowca (ops#318).
// ---------------------------------------------------------------------------

/** Najkrótszy blok pionowy po skróceniu do początku następnego spotkania (godz.). */
export const MIN_DLUGOSC_BLOKU_H = 0.5
/** Poniżej tej wysokości (px) blok pionowy pokazuje jedną linię tekstu. */
export const PROG_WYSOKOSC_DWIE_LINIE_PX = 30

/**
 * Długości bloków pionowych dla spotkań JEDNEGO handlowca w JEDNYM dniu: pełna
 * `dlugoscH`, ale wcześniejszy blok jest skracany do początku następnego
 * spotkania (nie mniej niż `MIN_DLUGOSC_BLOKU_H`). Zwraca obiekt
 * { [spotkanie.name]: długość w godzinach }.
 */
export function dlugosciBlokowPion(listaDnia, dlugoscH = DLUGOSC_SPOTKANIA_H) {
  const posortowane = [...(listaDnia || [])]
    .filter((s) => poczatekWGodzinach(s.termin) !== null)
    .sort((a, b) => poczatekWGodzinach(a.termin) - poczatekWGodzinach(b.termin))
  const wynik = {}
  posortowane.forEach((s, i) => {
    let h = dlugoscH
    const nastepny = posortowane[i + 1]
    if (nastepny) {
      const odstep =
        poczatekWGodzinach(nastepny.termin) - poczatekWGodzinach(s.termin)
      if (odstep < h) h = Math.max(MIN_DLUGOSC_BLOKU_H, odstep)
    }
    wynik[s.name] = h
  })
  return wynik
}

/** Czy blok o takiej skali i długości ma pokazać jedną linię (bez miasta). */
export function czyJednaLiniaBloku(pxNaH, dlugoscH) {
  return czyJednaLinia(pxNaH) || pxNaH * dlugoscH < PROG_WYSOKOSC_DWIE_LINIE_PX
}

// ---------------------------------------------------------------------------
// Grafik dostępności handlowców (b82). Dane z crm.api.kalendarz.spotkania:
// `dostepnosc[user]` to { 'RRRR-MM-DD': [[od, do], ...] } (pełne godziny,
// pusta lista = wolne, null dnia = brak wzoru na ten dzień) albo null (brak
// grafiku). Brak grafiku = cały dzień dostępny (decyzja 3).
// ---------------------------------------------------------------------------

/** Szablony edytora grafiku (pełne godziny). "Cały dzień" to cała doba. */
export const SZABLONY_GRAFIKU = {
  caly: [[0, 24]],
  rano: [[8, 14]],
  popoludnie: [[14, 22]],
  wolne: [],
}

/** Okna dnia z mapy dostępności handlowca; null, gdy brak grafiku (dnia lub całości). */
export function oknaDnia(dostepnoscHandlowca, dataIso) {
  if (!dostepnoscHandlowca || typeof dostepnoscHandlowca !== 'object')
    return null
  const okna = dostepnoscHandlowca[dataIso]
  return Array.isArray(okna) ? okna : null
}

/**
 * Czy przedział `startH`..`startH + dlugoscH` mieści się w jednym oknie.
 * Brak grafiku (okna null) = dostępny.
 */
export function czyDostepnyW(okna, startH, dlugoscH = DLUGOSC_SPOTKANIA_H) {
  if (!Array.isArray(okna)) return true
  if (typeof startH !== 'number' || Number.isNaN(startH)) return true
  const koniec = startH + dlugoscH
  return okna.some(([od, doH]) => od <= startH && koniec <= doH)
}

/**
 * Niedostępne odcinki [od, do] na osi `od`..`doGodziny` (dopełnienie okien).
 * Brak grafiku = brak odcinków (cały dzień jasny).
 */
export function odcinkiNiedostepne(okna, od = OS_OD, doGodziny = OS_DO) {
  if (!Array.isArray(okna)) return []
  const wynik = []
  let kursor = od
  const posortowane = [...okna].sort((a, b) => a[0] - b[0])
  for (const [a, b] of posortowane) {
    if (kursor >= doGodziny) break
    if (b <= kursor) continue
    if (a > kursor) wynik.push([kursor, Math.min(a, doGodziny)])
    kursor = Math.max(kursor, b)
  }
  if (kursor < doGodziny) wynik.push([kursor, doGodziny])
  return wynik.filter(([a, b]) => b > a)
}

/** Styl poziomego odcinka (left, width w %) na osi `od`..`doGodziny`. */
export function stylOdcinkaPoziomo(a, b, od, doGodziny) {
  const left = pozycjaGodzinyPct(a, od, doGodziny)
  return {
    left: `${left}%`,
    width: `${pozycjaGodzinyPct(b, od, doGodziny) - left}%`,
  }
}

/** Styl pionowego odcinka (top, height w px) w siatce od godziny `od`. */
export function stylOdcinkaPion(a, b, od, pxNaH) {
  return { top: `${(a - od) * pxNaH}px`, height: `${(b - a) * pxNaH}px` }
}

/** Czy spotkanie wypada (choć częściowo) poza grafikiem handlowca (decyzja 9). */
export function czyPozaGrafikiem(spotkanie, dostepnoscHandlowca) {
  const start = poczatekWGodzinach(spotkanie?.termin)
  if (start === null) return false
  const okna = oknaDnia(dostepnoscHandlowca, dataTerminu(spotkanie.termin))
  return !czyDostepnyW(okna, start)
}

/** Opis okien dnia: "brak grafiku", "wolne", "cały dzień", "8 do 12, 14 do 18". */
export function opisOkien(okna) {
  if (!Array.isArray(okna)) return 'brak grafiku'
  if (!okna.length) return 'wolne'
  if (okna.length === 1 && okna[0][0] === 0 && okna[0][1] === 24)
    return 'cały dzień'
  return okna.map(([a, b]) => `${a} do ${b}`).join(', ')
}

/** 24 wartości true/false (pełne godziny) z okien; null = wszystko false. */
export function godzinyZOkien(okna) {
  const wynik = Array(24).fill(false)
  for (const [a, b] of Array.isArray(okna) ? okna : []) {
    for (let h = Math.max(0, a); h < Math.min(24, b); h++) wynik[h] = true
  }
  return wynik
}

/** Okna [od, do] z 24 wartości true/false (sąsiednie godziny łączone). */
export function oknaZGodzin(godziny) {
  const wynik = []
  let start = null
  for (let h = 0; h <= 24; h++) {
    const jest = h < 24 && !!godziny[h]
    if (jest && start === null) start = h
    if (!jest && start !== null) {
      wynik.push([start, h])
      start = null
    }
  }
  return wynik
}

/** "HH:MM" na godziny (10:30 => 10.5); null dla niepoprawnej wartości. */
export function godzinaNaLiczbe(godzina) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(godzina || ''))
  if (!m) return null
  return Number(m[1]) + Number(m[2]) / 60
}

/**
 * Handlowcy z flagą `dostepny` w terminie `dataIso` `godzina`, dostępni na
 * górze listy (decyzja 10), kolejność w grupach bez zmian. Bez danych
 * grafiku (`dostepnosc` null/undefined) wszyscy są dostępni.
 */
export function posortujWgDostepnosci(handlowcy, dostepnosc, dataIso, godzina) {
  const start = godzinaNaLiczbe(godzina)
  const z = (handlowcy || []).map((h) => ({
    ...h,
    dostepny:
      !dostepnosc || start === null || !dataIso
        ? true
        : czyDostepnyW(oknaDnia(dostepnosc[h.user], dataIso), start),
  }))
  return [...z.filter((h) => h.dostepny), ...z.filter((h) => !h.dostepny)]
}

/**
 * Ostrzeżenie w "Nowe spotkanie" (decyzja 6: można zapisać mimo to); '' gdy
 * termin mieści się w grafiku albo handlowiec nie ma grafiku.
 */
export function ostrzezenieGrafiku(
  imie,
  dostepnoscHandlowca,
  dataIso,
  godzina,
) {
  const start = godzinaNaLiczbe(godzina)
  if (start === null || !dataIso) return ''
  const okna = oknaDnia(dostepnoscHandlowca, dataIso)
  if (czyDostepnyW(okna, start)) return ''
  const stan = okna.length ? `jest dostępny ${opisOkien(okna)}` : 'ma wolne'
  return `Termin poza grafikiem: ${imie} w tym dniu ${stan}. Umów tylko, jeśli handlowiec to potwierdził.`
}
