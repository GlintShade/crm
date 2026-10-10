// Helpery formularza kalkulatora OZE dla czterech nowych rodzajow instalacji
// (Rozbudowa PV/ME, Klimatyzacja, Pompa ciepla, Kociol; b68, "Wielki update
// kalkulatora OZE", chunk F3) -- uzywane przez KalkulatorOzeRozszerzony.vue.
//
// ZERO matematyki cenowej tutaj (ten sam komentarz-naglowek co
// KalkulatorTab.vue) -- wycena jest zawsze liczona od nowa na serwerze przez
// `crm.api.kalkulator_oze.volteo_oze_calc`/`volteo_oze_create_deal`. Ten
// plik jest wylacznie: (1) ksztaltowaniem payloadu wejscia zgodnie z
// kontraktem backend<->frontend (plan b68, sekcja 5), (2) kaskadowym
// wyborem pozycji katalogowych (klimatyzacja, pompa ciepla, grzejniki),
// (3) podgladem doboru mocy pompy ciepla (serwer pozostaje autorytatywny --
// `dobierzMocPc` ponizej jest WYLACZNIE prezentacyjnym lustrem
// `crm.volteo_kalkulator_oze.dobierz_moc_pompy`, uzywanym do pokazania
// stanu "Brak doboru" BEZ czekania na debounce 350ms kalkulacji serwera),
// (4) grupowaniem panelu admina `wewnetrzne` do wyswietlenia.
//
// Stale PC_PRODUCENCI/PC_OGRZEWANIE/GRZEJNIKI_ROZMIARY/ZAPOTRZEBOWANIE sa
// CELOWYM duplikatem analogicznych stalych w `crm/volteo_kalkulator_oze.py`
// -- ten modul jest frappe-free i nie eksportuje swoich stalych prywatnych
// (ten sam wzorzec co `PROG_PPOZ_KW` zduplikowany w trzech miejscach, patrz
// `pvForm.js`): kazda zmiana tych wartosci w backendzie wymaga identycznej
// zmiany tutaj.

import { VARIANTS } from './pvForm'

// --- Rodzaje instalacji ----------------------------------------------------

export const OZE_ROZBUDOWA = 'Rozbudowa PV/ME'
export const OZE_KLIMATYZACJA = 'Klimatyzacja'
export const OZE_POMPA_CIEPLA = 'Pompa ciepła'
export const OZE_KOCIOL = 'Kocioł'

// Kolejnosc musi zgadzac sie z `RODZAJE_OZE_NOWE` w `utils/rodzajUmowy.js`
// (kolejnosc wstawiania do Set) i z kafelkami rodzaju w planie b68.
export const RODZAJE_NOWE = [OZE_ROZBUDOWA, OZE_KLIMATYZACJA, OZE_POMPA_CIEPLA, OZE_KOCIOL]

/**
 * Czy `rodzaj` jest jednym z czterech nowych rodzajow instalacji OZE
 * obslugiwanych przez ten kalkulator (w odroznieniu od trzech "starych"
 * rodzajow PV/PV+ME/ME, ktore nadal obsluguje KalkulatorTab.vue).
 *
 * @param {string|null|undefined} rodzaj
 * @returns {boolean}
 */
export function czyNowyRodzaj(rodzaj) {
  return RODZAJE_NOWE.includes(rodzaj)
}

/**
 * Siedem kafelkow "Rodzaj instalacji" -- trzy stare warianty PV/magazynu
 * (`VARIANTS` z pvForm.js) plus cztery nowe rodzaje OZE. Wspolna lista dla
 * KalkulatorTab.vue (karta 1, rzad kafelkow) i KalkulatorOzeRozszerzony.vue
 * (wlasna kopia tego samego rzedu), zeby kolejnosc/etykiety nigdy sie nie
 * rozjechaly miedzy rodzicem a dzieckiem.
 *
 * @returns {string[]} dokladnie siedem wartosci `custom_rodzaj_umowy`
 */
export function kafelkiRodzaju() {
  return [...VARIANTS, ...RODZAJE_NOWE]
}

// Rodzaje, dla ktorych ulga termomodernizacyjna nigdy nie ma zastosowania
// (decyzja CEO 2026-10-04) -- lustro `RODZAJE_BEZ_ULGI` w
// `crm/volteo_kalkulator_oze.py`.
const RODZAJE_BEZ_ULGI = new Set([OZE_KLIMATYZACJA])

/**
 * Czy ulga termomodernizacyjna moze dotyczyc danego rodzaju (niezaleznie od
 * typu klienta -- biznesowy i tak nigdy nie dostaje ulgi, ale to sprawdza
 * sam komponent przy typ_klienta, nie ta funkcja).
 *
 * @param {string} rodzaj
 * @returns {boolean}
 */
export function ulgaDotyczy(rodzaj) {
  return !RODZAJE_BEZ_ULGI.has(rodzaj)
}

// --- Pusty formularz ---------------------------------------------------------

const PUSTE_GRZEJNIKI = Object.freeze({
  '600x600': 0,
  '600x800': 0,
  '600x1000': 0,
  '600x1200': 0,
  '600x1600': 0,
})

/**
 * Zwraca swiezy, pusty stan formularza kalkulatora OZE (nowe rodzaje).
 * Kazde wywolanie zwraca NOWY obiekt (nigdy wspoldzielony) -- bezpieczne do
 * `reactive(pustyFormularzOze())` w komponencie.
 *
 * @param {string} [rodzajPoczatkowy] - rodzaj startowy (domyslnie Rozbudowa PV/ME)
 * @returns {object} pusty ksztalt formularza
 */
export function pustyFormularzOze(rodzajPoczatkowy = OZE_ROZBUDOWA) {
  return {
    rodzaj: rodzajPoczatkowy,
    typKlienta: 'indywidualny',
    narzut: 0,
    ulgaPct: 12,
    okresLat: 10,
    wplataWlasna: 0,
    rozbudowa: {
      panele: 0,
      paneleMikro: 0,
      bateria: 0,
      istniejacaPv: 'Nie',
      istniejacaPvMocKwp: null,
      ppozRecznie: 'Nie',
    },
    klimatyzacja: {
      grupa: '',
      klucz: '',
      kod: '',
    },
    pompa: {
      zapotrzebowanie: '',
      producent: '',
      typ: '',
      ogrzewanie: '',
      cwu: '',
      grzejniki: { ...PUSTE_GRZEJNIKI },
    },
    kociol: {
      typ: '',
      kod: '',
      cwu: '',
    },
  }
}

// --- Katalog: pomocnicze filtrowanie -----------------------------------------

/**
 * Filtruje pozycje katalogu (odpowiedz `volteo_oze_pozycje`) wg pola
 * `grupa`, posortowane wg `sort` (a przy remisie wg `moc_kw`).
 *
 * @param {Array<object>} pozycje - lista pozycji z `volteo_oze_pozycje`
 * @param {string} grupa - wartosc pola `grupa` do odfiltrowania
 * @returns {Array<object>} pozycje nalezace do `grupa`, posortowane
 */
export function pozycjeGrupy(pozycje, grupa) {
  return (pozycje || [])
    .filter((p) => p.grupa === grupa)
    .slice()
    .sort((a, b) => (Number(a.sort) || 0) - (Number(b.sort) || 0) || (Number(a.moc_kw) || 0) - (Number(b.moc_kw) || 0))
}

/**
 * Polska odmiana rzeczownika "panel" wg liczby (0/5+ -> "paneli", 1 ->
 * "panel", 2-4 -> "panele") -- uzywana przy etykietach typu "3 panele PV".
 *
 * @param {number} ilosc
 * @returns {'panel'|'panele'|'paneli'}
 */
export function odmianaPaneli(ilosc) {
  const n = Number(ilosc) || 0
  if (n === 1) return 'panel'
  if (n >= 2 && n <= 4) return 'panele'
  return 'paneli'
}

// --- Klimatyzacja: kaskada typ -> model -> moc -------------------------------

// Kolejnosc musi zgadzac sie z backendowym `_KLIMA_RODZAJ_LABEL` w
// `crm/api/kalkulator_oze.py`.
export const GRUPY_KLIMY = ['klima_chlodzenie', 'klima_dogrzewanie', 'klima_grzanie']

export const ETYKIETA_GRUPY_KLIMY = {
  klima_chlodzenie: 'Chłodzenie',
  klima_dogrzewanie: 'Chłodzenie + dogrzewanie',
  klima_grzanie: 'Chłodzenie + grzanie',
}

/**
 * Buduje klucz modelu klimatyzacji (producent+model, bez koloru -- kolor
 * jest tylko wizualnym oznaczeniem tej samej linii produktowej, np. Elis X
 * Czarny vs Roni X Bialy to DWA rozne modele mimo wspolnej mocy/ceny) z
 * pojedynczej pozycji katalogowej.
 *
 * @param {object} pozycja
 * @returns {string}
 */
function kluczModeluKlimy(pozycja) {
  return `${pozycja.producent}|${pozycja.model}`
}

/**
 * Zwraca liste unikalnych modeli klimatyzacji (producent+model+kolor)
 * dostepnych w danej grupie (rodzaju chlodzenia/dogrzewania/grzania) --
 * jeden wpis na kazda rozna kombinacje producenta i modelu, niezaleznie od
 * tego, ile wariantow mocy ta kombinacja ma w katalogu.
 *
 * @param {Array<object>} pozycje - lista pozycji z `volteo_oze_pozycje`
 * @param {string} grupa - jedna z GRUPY_KLIMY
 * @returns {Array<{klucz: string, producent: string, model: string, kolor: string}>}
 */
export function modeleKlimy(pozycje, grupa) {
  const widziane = new Map()
  for (const pozycja of pozycjeGrupy(pozycje, grupa)) {
    const klucz = kluczModeluKlimy(pozycja)
    if (!widziane.has(klucz)) {
      widziane.set(klucz, {
        klucz,
        producent: pozycja.producent,
        model: pozycja.model,
        kolor: pozycja.kolor,
      })
    }
  }
  return [...widziane.values()]
}

/**
 * Zwraca warianty mocy dla wybranej grupy+modelu klimatyzacji, posortowane
 * rosnaco wg mocy -- kazdy wpis niesie `kod` (do wyslania w `wejscie`) i
 * `opis` (np. powierzchnia "do 25 m2") do etykiety selecta.
 *
 * @param {Array<object>} pozycje - lista pozycji z `volteo_oze_pozycje`
 * @param {string} grupa - jedna z GRUPY_KLIMY
 * @param {string} klucz - klucz modelu zwrocony przez `modeleKlimy`
 * @returns {Array<{kod: string, moc_kw: number, opis: string, nazwa: string}>}
 */
export function moceKlimy(pozycje, grupa, klucz) {
  return pozycjeGrupy(pozycje, grupa)
    .filter((p) => kluczModeluKlimy(p) === klucz)
    .map((p) => ({ kod: p.kod, moc_kw: Number(p.moc_kw) || 0, opis: p.opis || '', nazwa: p.nazwa }))
}

/**
 * Sanityzuje wybor klimatyzacji po zmianie katalogu/grupy/modelu -- resetuje
 * wylacznie te pola ponizej wybranego poziomu, ktore przestaly byc zgodne z
 * katalogiem (nigdy niczego nie wlacza, analogicznie do `sanitizujDodatki`
 * w pvForm.js). Czysta funkcja: zwraca NOWY obiekt, nigdy nie mutuje
 * argumentu `wybor`.
 *
 * @param {Array<object>} pozycje - lista pozycji z `volteo_oze_pozycje`
 * @param {{grupa: string, klucz: string, kod: string}} wybor - biezacy wybor klimatyzacji
 * @returns {{grupa: string, klucz: string, kod: string}} sanityzowany wybor
 */
export function kaskadaKlimy(pozycje, wybor) {
  const grupa = GRUPY_KLIMY.includes(wybor?.grupa) ? wybor.grupa : ''
  if (!grupa) return { grupa: '', klucz: '', kod: '' }

  const modele = modeleKlimy(pozycje, grupa)
  const klucz = modele.some((m) => m.klucz === wybor.klucz) ? wybor.klucz : ''
  if (!klucz) return { grupa, klucz: '', kod: '' }

  const mocy = moceKlimy(pozycje, grupa, klucz)
  const kod = mocy.some((m) => m.kod === wybor.kod) ? wybor.kod : ''
  return { grupa, klucz, kod }
}

// --- Pompa ciepla -------------------------------------------------------------

// Lustro `PC_PRODUCENCI` w `crm/volteo_kalkulator_oze.py` -- Rotenso NIE ma
// wariantu Split (decyzja CEO).
const PC_PRODUCENCI = { Rotenso: ['Monoblok'], Midea: ['Monoblok', 'Split'] }

/**
 * Lista producentow pompy ciepla w ustalonej kolejnosci kafelkow.
 *
 * @returns {string[]}
 */
export function producenciPc() {
  return Object.keys(PC_PRODUCENCI)
}

/**
 * Typy (Monoblok/Split) dostepne dla danego producenta -- Rotenso zwraca
 * wylacznie Monoblok, nigdy Split.
 *
 * @param {string} producent
 * @returns {string[]}
 */
export function typyPcDostepne(producent) {
  return PC_PRODUCENCI[producent] ? [...PC_PRODUCENCI[producent]] : []
}

// Lustro `PC_OGRZEWANIE` w `crm/volteo_kalkulator_oze.py` -- "Mieszane"
// dobiera moc z tabeli Grzejnikow (decyzja CEO).
const PC_OGRZEWANIE_DOBORU = { Grzejniki: 'Grzejniki', Podłogówka: 'Podłogówka', Mieszane: 'Grzejniki' }

/**
 * Mapuje rodzaj ogrzewania wybrany przez klienta na kolumne `ogrzewanie`
 * uzywana w tabeli doboru mocy ("Mieszane" -> "Grzejniki").
 *
 * @param {string} ogrzewanie
 * @returns {string} wartosc kolumny `ogrzewanie` w `dobor`, albo '' gdy nieznana
 */
export function ogrzewanieDoTabeli(ogrzewanie) {
  return PC_OGRZEWANIE_DOBORU[ogrzewanie] || ''
}

// Lustro `ZAPOTRZEBOWANIE` w `crm/volteo_kalkulator_oze.py`.
const WARTOSC_ZAPOTRZEBOWANIA = {
  ponizej_4: 0,
  '4.5': 4.5,
  '5': 5,
  '5.5': 5.5,
  '6': 6,
  '6.5': 6.5,
  '7': 7,
  '7.5': 7.5,
  '8': 8,
  '8.5': 8.5,
  '9': 9,
  '9.5': 9.5,
  '10': 10,
  '10.5': 10.5,
  '11': 11,
  '11.5': 11.5,
  '12': 12,
  '12.5': 12.5,
  '13': 13,
  '13.5': 13.5,
  '14': 14,
}

/**
 * Podglad doboru mocy pompy ciepla (WYLACZNIE prezentacja -- lustro
 * `crm.volteo_kalkulator_oze.dobierz_moc_pompy`; serwer jest zrodlem
 * prawdy przy kazdym `volteo_oze_calc`). Zwraca `null`, gdy brak
 * pasujacego wiersza doboru (odpowiednik `OZEBrakDoboru`) -- uzyj
 * `brakDoboru()` do odczytu tego stanu w szablonie.
 *
 * Przy nakladajacych sie granicach (np. (8.5,9.5,10) i (9.5,10.5,12))
 * wybiera WIEKSZA pompe z pasujacych wierszy, identycznie jak backend.
 *
 * @param {Array<object>} dobor - wiersze z `volteo_oze_pozycje().dobor`
 * @param {string} zapotrzebowanieKod - klucz z listy `zapotrzebowanie` (np. "6.5")
 * @param {string} producent
 * @param {string} typ
 * @param {string} ogrzewanie - rodzaj ogrzewania wybrany przez klienta (Mieszane dozwolone)
 * @returns {number|null} moc w kW, albo null gdy brak doboru
 */
export function dobierzMocPc(dobor, zapotrzebowanieKod, producent, typ, ogrzewanie) {
  const zapotrzebowanie = WARTOSC_ZAPOTRZEBOWANIA[zapotrzebowanieKod]
  if (zapotrzebowanie === undefined || !producent || !typ || !ogrzewanie) return null

  const ogrzewanieDoboru = ogrzewanieDoTabeli(ogrzewanie)
  if (!ogrzewanieDoboru) return null

  const kandydaci = (dobor || [])
    .filter(
      (w) =>
        w.producent === producent &&
        w.typ === typ &&
        w.ogrzewanie === ogrzewanieDoboru &&
        zapotrzebowanie >= Number(w.od_kw) &&
        zapotrzebowanie <= Number(w.do_kw),
    )
    .map((w) => Number(w.moc_kw))

  return kandydaci.length ? Math.max(...kandydaci) : null
}

/**
 * Czy wynik `dobierzMocPc` oznacza brak doboru (pompa poza najwyzszym
 * przedzialem tabeli -- np. 13-14 kW dla Rotenso).
 *
 * @param {number|null} mocKw - wynik `dobierzMocPc`
 * @returns {boolean}
 */
export function brakDoboru(mocKw) {
  return mocKw === null || mocKw === undefined
}

// --- Grzejniki niskotemperaturowe ---------------------------------------------

// Lustro `GRZEJNIKI_MAX`/`GRZEJNIKI_ROZMIARY` w `crm/volteo_kalkulator_oze.py`.
export const GRZEJNIKI_MAX = 15
const GRZEJNIKI_ROZMIARY = ['600x600', '600x800', '600x1000', '600x1200', '600x1600']

/**
 * Zwraca katalogowe pozycje grzejnikow niskotemperaturowych (grupa
 * `grzejnik`), posortowane wg `sort`, z wyekstrahowanym kluczem `rozmiar`
 * (np. "600x600") do powiazania z `form.pompa.grzejniki`.
 *
 * @param {Array<object>} pozycje - lista pozycji z `volteo_oze_pozycje`
 * @returns {Array<{kod: string, rozmiar: string, nazwa: string, opis: string}>}
 */
export function rozmiaryGrzejnikow(pozycje) {
  return pozycjeGrupy(pozycje, 'grzejnik').map((p) => ({
    kod: p.kod,
    rozmiar: p.kod.replace(/^grzejnik_/, ''),
    nazwa: p.nazwa,
    opis: p.opis || '',
  }))
}

/**
 * Suma wszystkich wybranych grzejnikow (wszystkie rozmiary razem).
 *
 * @param {Object<string, number>} grzejniki - `{rozmiar: ilosc}`
 * @returns {number}
 */
export function sumaGrzejnikow(grzejniki) {
  return Object.values(grzejniki || {}).reduce((suma, ilosc) => suma + (Number(ilosc) || 0), 0)
}

/**
 * Czy wybor grzejnikow jest poprawny -- same nieujemne liczby calkowite,
 * suma lacznie nie przekracza GRZEJNIKI_MAX (lustro walidacji
 * `_pozycje_grzejnikow` w backendzie).
 *
 * @param {Object<string, number>} grzejniki
 * @returns {boolean}
 */
export function grzejnikiPoprawne(grzejniki) {
  for (const rozmiar of GRZEJNIKI_ROZMIARY) {
    const ilosc = (grzejniki || {})[rozmiar]
    if (ilosc === undefined) continue
    const n = Number(ilosc)
    if (!Number.isInteger(n) || n < 0) return false
  }
  return sumaGrzejnikow(grzejniki) <= GRZEJNIKI_MAX
}

/**
 * Opcje selecta ilosci dla danego rozmiaru grzejnika -- ograniczone tak,
 * zeby suma WSZYSTKICH rozmiarow nigdy nie mogla przekroczyc GRZEJNIKI_MAX
 * (uwzglednia juz wybrane ilosci pozostalych rozmiarow).
 *
 * @param {Object<string, number>} grzejniki - biezacy wybor `{rozmiar: ilosc}`
 * @param {string} rozmiar - rozmiar, dla ktorego budujemy opcje
 * @param {number} [max] - limit laczny (domyslnie GRZEJNIKI_MAX)
 * @returns {number[]} opcje 0..N
 */
export function opcjeIlosciGrzejnika(grzejniki, rozmiar, max = GRZEJNIKI_MAX) {
  const aktualna = Number((grzejniki || {})[rozmiar]) || 0
  const innychSuma = sumaGrzejnikow(grzejniki) - aktualna
  const dostepne = Math.max(0, max - innychSuma)
  const opcje = []
  for (let i = 0; i <= dostepne; i += 1) opcje.push(i)
  return opcje
}

// --- Kompletnosc formularza (czy mozna policzyc/wygenerowac ofertę) ---------

/**
 * Czy sekcja Rozbudowy ma wybrany co najmniej jeden element (panele,
 * panele z mikrofalownikiem, moduly baterii) ORAZ nie wybrano naraz obu
 * typow paneli (lustro walidacji `_pozycje_rozbudowa` w backendzie).
 *
 * @param {{panele: number, paneleMikro: number, bateria: number}} rozbudowa
 * @returns {boolean}
 */
export function kompletnyRozbudowa(rozbudowa) {
  const panele = Number(rozbudowa?.panele) || 0
  const paneleMikro = Number(rozbudowa?.paneleMikro) || 0
  const bateria = Number(rozbudowa?.bateria) || 0
  if (panele > 0 && paneleMikro > 0) return false
  return panele > 0 || paneleMikro > 0 || bateria > 0
}

/**
 * Przelacza element Rozbudowy (1 po wlaczeniu, 0 po wylaczeniu) z
 * wykluczeniem: wlaczenie "panele" zeruje "paneleMikro" i odwrotnie.
 * Bateria jest niezalezna. Zwraca NOWY obiekt, nie mutuje wejscia.
 *
 * @param {object} rozbudowa
 * @param {'panele'|'paneleMikro'|'bateria'} klucz
 * @returns {object}
 */
export function przelaczElementRozbudowy(rozbudowa, klucz) {
  const wlaczony = (Number(rozbudowa?.[klucz]) || 0) > 0
  const nowy = { ...rozbudowa, [klucz]: wlaczony ? 0 : 1 }
  if (!wlaczony && klucz === 'panele') nowy.paneleMikro = 0
  if (!wlaczony && klucz === 'paneleMikro') nowy.panele = 0
  return nowy
}

/**
 * Czy dany element Rozbudowy jest zablokowany przez wybor drugiego typu paneli
 * (tylko gdy sam jest wylaczony; w stanie konfliktowym oba da sie wylaczyc).
 *
 * @param {object} rozbudowa
 * @param {string} klucz
 * @returns {boolean}
 */
export function elementRozbudowyZablokowany(rozbudowa, klucz) {
  if ((Number(rozbudowa?.[klucz]) || 0) > 0) return false
  if (klucz === 'panele') return (Number(rozbudowa?.paneleMikro) || 0) > 0
  if (klucz === 'paneleMikro') return (Number(rozbudowa?.panele) || 0) > 0
  return false
}

/**
 * Czy wybrano model klimatyzacji (kazdy wybor jest zawsze dokladnie jedna
 * pozycja katalogowa).
 *
 * @param {{kod: string}} klimatyzacja
 * @returns {boolean}
 */
export function kompletnyKlimatyzacja(klimatyzacja) {
  return Boolean(klimatyzacja?.kod)
}

/**
 * Czy formularz pompy ciepla niesie wszystkie pola WYMAGANE do policzenia
 * doboru mocy (CWU i grzejniki sa opcjonalne) -- NIE sprawdza, czy dobor
 * faktycznie istnieje (patrz `dobierzMocPc`/`brakDoboru` dla tego osobno,
 * bo "Brak doboru" to stan kompletnego, ale niepoliczalnego formularza).
 *
 * @param {{zapotrzebowanie: string, producent: string, typ: string, ogrzewanie: string}} pompa
 * @returns {boolean}
 */
export function kompletnyPompa(pompa) {
  if (!pompa) return false
  return Boolean(pompa.zapotrzebowanie && pompa.producent && pompa.typ && pompa.ogrzewanie)
}

/**
 * Czy wybrano model kotla (kazdy wybor jest zawsze dokladnie jedna pozycja
 * katalogowa).
 *
 * @param {{kod: string}} kociol
 * @returns {boolean}
 */
export function kompletnyKociol(kociol) {
  return Boolean(kociol?.kod)
}

/**
 * Dyspozytor kompletnosci calego formularza wg `form.rodzaj` -- jedyne
 * miejsce, ktore komponent powinien odpytywac, zeby zdecydowac, czy
 * uruchomic debounce'owana kalkulacje.
 *
 * @param {object} form - stan formularza (ksztalt `pustyFormularzOze`)
 * @returns {boolean}
 */
export function kompletnyFormOze(form) {
  if (!form) return false
  if (form.rodzaj === OZE_ROZBUDOWA) return kompletnyRozbudowa(form.rozbudowa)
  if (form.rodzaj === OZE_KLIMATYZACJA) return kompletnyKlimatyzacja(form.klimatyzacja)
  if (form.rodzaj === OZE_POMPA_CIEPLA) return kompletnyPompa(form.pompa)
  if (form.rodzaj === OZE_KOCIOL) return kompletnyKociol(form.kociol)
  return false
}

// --- Payload wejscia dla volteo_oze_calc / volteo_oze_create_deal -----------

/**
 * Buduje zagniezdzony ksztalt `wejscie` zgodny z kontraktem B5 (plan b68,
 * sekcja 5) z biezacego stanu formularza. Wysyla WYLACZNIE pod-slownik
 * pasujacy do `form.rodzaj` -- serwer i tak czyta tylko ten jeden ("Czytany
 * tylko pod-slownik pasujacy do rodzaj"), ale ograniczenie tutaj czyni
 * payload czytelniejszym do debugowania.
 *
 * WAZNE: `ppoz_recznie` jest wysylane jako prawdziwy boolean, NIGDY jako
 * string "Tak"/"Nie" -- `crm.volteo_kalkulator_oze._pozycje_rozbudowa` (a
 * scislej `oblicz_oferte`) robi `bool(rozbudowa.get("ppoz_recznie", False))`
 * po stronie Pythona, a `bool("Nie")` tam jest PRAWDA (kazdy niepusty
 * string jest prawdziwy) -- string "Nie" zostalby wiec odczytany jako
 * recznie wymuszone PPOZ. `form.rozbudowa.ppozRecznie` zostaje
 * "Tak"/"Nie" (ten sam UI-owy format co reszta kalkulatorow), konwersja do
 * boola dzieje sie wylacznie tutaj.
 *
 * @param {object} form - stan formularza (ksztalt `pustyFormularzOze`)
 * @returns {object} `wejscie` gotowe do `volteo_oze_calc`/`volteo_oze_create_deal`
 */
export function zbudujPayloadOze(form) {
  const bazowe = {
    rodzaj: form.rodzaj,
    typ_klienta: form.typKlienta,
    narzut: Number(form.narzut) || 0,
    ulga_pct: ulgaDotyczy(form.rodzaj) ? Number(form.ulgaPct) || 0 : 0,
    okres_lat: Number(form.okresLat) || 10,
    wplata_wlasna: Number(form.wplataWlasna) || 0,
  }

  if (form.rodzaj === OZE_ROZBUDOWA) {
    const r = form.rozbudowa || {}
    return {
      ...bazowe,
      rozbudowa: {
        panele: Number(r.panele) || 0,
        panele_mikro: Number(r.paneleMikro) || 0,
        bateria: Number(r.bateria) || 0,
        istniejaca_pv_moc_kwp: r.istniejacaPv === 'Tak' ? Number(r.istniejacaPvMocKwp) || 0 : 0,
        ppoz_recznie: r.ppozRecznie === 'Tak',
      },
    }
  }

  if (form.rodzaj === OZE_KLIMATYZACJA) {
    return { ...bazowe, klimatyzacja: { kod: form.klimatyzacja?.kod || '' } }
  }

  if (form.rodzaj === OZE_POMPA_CIEPLA) {
    const p = form.pompa || {}
    return {
      ...bazowe,
      pompa: {
        zapotrzebowanie: p.zapotrzebowanie || '',
        producent: p.producent || '',
        typ: p.typ || '',
        ogrzewanie: p.ogrzewanie || '',
        cwu: p.cwu || '',
        grzejniki: { ...(p.grzejniki || {}) },
      },
    }
  }

  if (form.rodzaj === OZE_KOCIOL) {
    return { ...bazowe, kociol: { kod: form.kociol?.kod || '', cwu: form.kociol?.cwu || '' } }
  }

  return bazowe
}

// --- Panel administratora (wewnetrzne) ---------------------------------------

const ETYKIETY_TYPU_SKLADOWEJ = {
  Koszt: 'Koszt',
  'Marża Proenergy': 'Marża Proenergy',
  'Bonus liderski': 'Bonus liderski',
}

/**
 * Grupuje `wynik.wewnetrzne` (kontrakt B5, widoczne wylacznie dla
 * System Manager / Volteo Core Admin) do prezentacji w panelu admina --
 * linie pogrupowane wg `typ` (Koszt / Marza Proenergy / Bonus liderski),
 * kazda grupa z suma. Czysto prezentacyjne, nic tu nie jest zapisywane.
 *
 * @param {object|null} wewnetrzne - blok `wewnetrzne` z odpowiedzi `volteo_oze_calc`
 * @returns {{koszt_calkowity: number, marza_proenergy: number, bonus_liderski: number, narzut: number, marza: number, zysk: number, grupy: Array<object>, pozycje: Array<object>}}
 */
export function grupujWewnetrzneOze(wewnetrzne) {
  const puste = {
    koszt_calkowity: 0,
    marza_proenergy: 0,
    bonus_liderski: 0,
    narzut: 0,
    marza: 0,
    zysk: 0,
    grupy: [],
    pozycje: [],
  }
  if (!wewnetrzne) return puste

  const linie = Array.isArray(wewnetrzne.linie) ? wewnetrzne.linie : []
  const grupy = Object.keys(ETYKIETY_TYPU_SKLADOWEJ)
    .map((typ) => {
      const pozycjeGrupy = linie.filter((l) => l.typ === typ)
      const suma = pozycjeGrupy.reduce((s, l) => s + (Number(l.kwota) || 0), 0)
      return { klucz: typ, etykieta: ETYKIETY_TYPU_SKLADOWEJ[typ], pozycje: pozycjeGrupy, suma }
    })
    .filter((g) => g.pozycje.length > 0)

  return {
    koszt_calkowity: Number(wewnetrzne.koszt_calkowity) || 0,
    marza_proenergy: Number(wewnetrzne.marza_proenergy) || 0,
    bonus_liderski: Number(wewnetrzne.bonus_liderski) || 0,
    narzut: Number(wewnetrzne.narzut) || 0,
    marza: Number(wewnetrzne.marza) || 0,
    zysk: Number(wewnetrzne.zysk) || 0,
    grupy,
    pozycje: Array.isArray(wewnetrzne.pozycje) ? wewnetrzne.pozycje : [],
  }
}
