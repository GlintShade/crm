// Kod rodzaju umowy (custom_rodzaj_umowy) dla kolumny "Rodzaj" listy Umowy
// (wariant B, b65) - krotki kod tekstowy w komorce, pelna nazwa w atrybucie
// title. Frappe-free, testowalne bezposrednio przez vitest, ten sam wzorzec
// co dealPipeline.js/etapFiltr.js.
//
// LUSTRO crm.volteo_naming.UMOWA_CODES (crm/volteo_naming.py) - ten sam
// mapping rodzaju na kod, ale kod UI dla "Fotowoltaika + Magazyn" to
// "PV+ME" (czytelniejsze w waskiej kolumnie listy), podczas gdy nazwa
// dokumentu (PRO/<KOD>/...) uzywa "PVME" bez znaku "+" (plus w nazwie
// dokumentu bylby mylacy). Przy kazdej zmianie UMOWA_CODES w forku
// zaktualizuj tez KODY_RODZAJU_UMOWY nizej.
//
// Od b68 (Wielki update kalkulatora OZE): cztery nowe rodzaje OZE dzielaja
// kody 1:1 z UMOWA_CODES (ROZ/KL/PC/PP), bez rozjazdu "+" jak przy PV+ME,
// bo zadna z czterech nowych nazw nie niesie znaku "+".
//
// Ten plik jest JEDYNYM zrodlem prawdy po stronie frontu dla calego
// podzialu "ktory rodzaj umowy jest OZE" i "ktore zakladki szansy widac dla
// ktorego rodzaju" - RODZAJE_OZE/czyOze/zakladkiSzansy nizej zastepuja
// lokalne kopie, ktore do b68 zyly w dealPipeline.js, etapFiltr.js,
// notatki.js, Deal.vue, MobileDeal.vue i PlikiTab.vue (kazdy plik mial
// wlasny Set 'Fotowoltaika'/'Fotowoltaika + Magazyn'/'Magazyn energii' -
// przy kazdym nowym rodzaju trzeba bylo pamietac o uaktualnieniu wszystkich
// naraz). Lustro `crm/volteo_pipeline.py::OZE_RODZAJE`.

export const KODY_RODZAJU_UMOWY = {
  Fotowoltaika: 'PV',
  'Fotowoltaika + Magazyn': 'PV+ME',
  'Magazyn energii': 'ME',
  'Czyste Powietrze': 'CP',
  'Rozbudowa PV/ME': 'ROZ',
  Klimatyzacja: 'KL',
  'Pompa ciepła': 'PC',
  Kocioł: 'PP',
}

export const KOD_NIEZNANY = 'XX'

// Trzy "stare" rodzaje OZE (fotowoltaika / magazyn energii) - mialy wlasny
// kalkulator i wlasne zakladki szansy od zawsze. Nazwa PV zachowana dla
// zgodnosci z historycznymi komentarzami w innych plikach ("PV_RODZAJE",
// "RODZAJE_UMOWY_OZE") mimo ze zbior obejmuje takze "Magazyn energii" (ME),
// nie tylko czysta fotowoltaike.
export const RODZAJE_OZE_PV = new Set([
  'Fotowoltaika',
  'Fotowoltaika + Magazyn',
  'Magazyn energii',
])

// Cztery nowe rodzaje OZE (b68, "Wielki update kalkulatora OZE"): wlasny
// kalkulator (KalkulatorOzeRozszerzony.vue, chunk F3), ale ten sam proces
// (etapy) i ten sam gate dostepu (custom_linia_oze) co trzy stare rodzaje -
// patrz `zakladkiSzansy` nizej dla tego, ktore zakladki szansy odrozniaja
// nowe rodzaje od starych.
export const RODZAJE_OZE_NOWE = new Set([
  'Rozbudowa PV/ME',
  'Klimatyzacja',
  'Pompa ciepła',
  'Kocioł',
])

// Wszystkie siedem rodzajow OZE razem - lustro `crm.volteo_pipeline.OZE_RODZAJE`
// (ten sam proces/etapy dla kazdego z siedmiu), uzywane wszedzie, gdzie do
// b68 zyl lokalny `RODZAJE_UMOWY_OZE`/`OZE_RODZAJE` ograniczony do trzech
// starych rodzajow (Kredyt/Notatki/Montaz OZE/Pliki OZE sa teraz dostepne
// dla wszystkich siedmiu, nie tylko dla PV/PV+ME/ME).
export const RODZAJE_OZE = new Set([...RODZAJE_OZE_PV, ...RODZAJE_OZE_NOWE])

/**
 * Czy `rodzaj` jest jednym z siedmiu rodzajow OZE (stare trzy plus nowe
 * cztery) - `false` dla Czyste Powietrze i dla pustej/nieznanej wartosci.
 *
 * @param {string|null|undefined} rodzaj
 * @returns {boolean}
 */
export function czyOze(rodzaj) {
  return RODZAJE_OZE.has(rodzaj)
}

/**
 * Czy `rodzaj` jest jednym z TRZECH starych rodzajow OZE (Fotowoltaika /
 * Fotowoltaika + Magazyn / Magazyn energii) - np. dla zakladki "Dotacja"
 * (dotacja Moj Prad istnieje tylko dla tych trzech, nie dla nowych
 * rodzajow, gdzie `custom_dotacja` jest zawsze 0).
 *
 * @param {string|null|undefined} rodzaj
 * @returns {boolean}
 */
export function czyOzePv(rodzaj) {
  return RODZAJE_OZE_PV.has(rodzaj)
}

/**
 * Czy `rodzaj` jest jednym z CZTERECH nowych rodzajow OZE wprowadzonych w
 * b68 (Rozbudowa PV/ME, Klimatyzacja, Pompa ciepła, Kocioł) - np. do
 * ukrycia przycisku generowania PDF umowy, dla ktorego wzor jest jeszcze w
 * przygotowaniu (patrz `umowaWPrzygotowaniu` nizej).
 *
 * @param {string|null|undefined} rodzaj
 * @returns {boolean}
 */
export function czyOzeNowy(rodzaj) {
  return RODZAJE_OZE_NOWE.has(rodzaj)
}

/**
 * Widocznosc zakladek szansy zaleznych od `custom_rodzaj_umowy` - jedyne
 * miejsce, ktore wie, ktora zakladka nalezy do ktorego rodzaju. Wywolujacy
 * (Deal.vue, MobileDeal.vue, PlikiTab.vue, NotatkiStrumien.vue,
 * StatusZakladki.vue, MontazTabOze.vue) czyta z wyniku tylko te klucze,
 * ktore go dotycza - np. PlikiTab.vue potrzebuje wylacznie `plikiOze`.
 *
 * Tabela (patrz plan b68, sekcja 3 "Tabela zakladek"):
 *   - `osd`: PV/PV+ME/ME oraz Rozbudowa PV/ME (nie Klimatyzacja/Pompa
 *     ciepła/Kocioł, nie Czyste Powietrze).
 *   - `dotacja`: wylacznie PV/PV+ME/ME (dotacja Moj Prad nie istnieje dla
 *     zadnego z czterech nowych rodzajow).
 *   - `kredyt`, `notatki`, `montazOze`, `plikiOze`: wszystkie siedem
 *     rodzajow OZE (nigdy Czyste Powietrze, ktora ma wlasne odpowiedniki -
 *     Trify, Notatki/Montaz wspolny komponent z innym `konfig`, UmowaCP).
 *   - `umowaOze`, `audytOze`: kazdy rodzaj POZA Czyste Powietrze, w tym
 *     rodzaj pusty/nierozpoznany (fail-open - zachowuje dotychczasowe
 *     zachowanie Deal.vue/MobileDeal.vue dla szansy bez ustawionego
 *     rodzaju, zanim dokument w ogole sie zaladuje).
 *
 * @param {string|null|undefined} rodzaj
 * @returns {{osd: boolean, dotacja: boolean, kredyt: boolean, notatki: boolean, montazOze: boolean, plikiOze: boolean, umowaOze: boolean, audytOze: boolean}}
 */
export function zakladkiSzansy(rodzaj) {
  const oze = czyOze(rodzaj)
  const pv = czyOzePv(rodzaj)
  const rozbudowa = rodzaj === 'Rozbudowa PV/ME'
  const cp = rodzaj === 'Czyste Powietrze'
  return {
    osd: pv || rozbudowa,
    dotacja: pv,
    kredyt: oze,
    notatki: oze,
    montazOze: oze,
    plikiOze: oze,
    umowaOze: !cp,
    audytOze: !cp,
  }
}

/**
 * Czy wzor umowy PDF dla `rodzaj` jest jeszcze w przygotowaniu (b68: cztery
 * nowe rodzaje OZE nie maja jeszcze wzoru umowy, faza 2, prawnik). Gdy
 * `true`, przycisk generowania PDF na zakladce Umowa jest wylaczony i
 * pokazuje sie baner info (chunk F4, `UmowaTab.vue`); formularz szansy
 * mozna nadal wypelnic.
 *
 * @param {string|null|undefined} rodzaj
 * @returns {boolean}
 */
export function umowaWPrzygotowaniu(rodzaj) {
  return czyOzeNowy(rodzaj)
}

/**
 * Kod i pelna nazwa rodzaju umowy do komorki "Rodzaj" (kod widoczny w
 * kolumnie, pelna nazwa w atrybucie `title`).
 *
 * @param {string|null|undefined} rodzaj - surowa wartosc `custom_rodzaj_umowy`
 * @returns {{kod: string, pelnaNazwa: string}}
 */
export function opisRodzajuUmowy(rodzaj) {
  if (!rodzaj) {
    return { kod: KOD_NIEZNANY, pelnaNazwa: 'Brak rodzaju umowy' }
  }
  const kod = KODY_RODZAJU_UMOWY[rodzaj]
  if (!kod) {
    return { kod: KOD_NIEZNANY, pelnaNazwa: `Nieznany rodzaj umowy (${rodzaj})` }
  }
  return { kod, pelnaNazwa: rodzaj }
}
