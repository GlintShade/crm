// Czysta logika grupowania list (ops#413): stan wyboru (pole, "pokaz puste",
// zwiniete grupy), stan starych widokow "group_by", laczenie licznikow z serwera
// z wierszami zaladowanymi per grupa. Bez frappe-ui i bez `@/`, testowalne
// bezposrednio przez vitest (wzorzec utils/widokLeady.js). Wszystkie funkcje
// zwracaja nowe obiekty, nigdy nie mutuja argumentow.

// Prefiks klucza wiersza-grupy: ListRows rozpoznaje grupe po prawdziwym `group`,
// a klucz pustej wartosci to "" (falsy).
export const PREFIKS_GRUPY = 'g:'

// Odmowa serwera dla leadow powyzej progu (crm.volteo_grupowanie.LIMIT_LEADOW).
export const ODMOWA_LIMIT = 'limit'

export const STAN_PUSTY = Object.freeze({
  pole: null,
  pokazPuste: false,
  zwiniete: Object.freeze([]),
})

function nowyStan(pole, pokazPuste, zwiniete) {
  return { pole: pole || null, pokazPuste: !!pokazPuste, zwiniete: [...zwiniete] }
}

/**
 * Wczytuje stan z zapisanego widoku (JSON w `volteo_grupowanie`) albo obiektu.
 * Zle dane i pole spoza `dozwolonePola` (lista nazw; brak listy = bez sprawdzania)
 * daja stan pusty, nigdy wyjatek.
 */
export function parsujStan(surowy, dozwolonePola = null) {
  let obj = surowy
  if (typeof surowy === 'string') {
    if (!surowy.trim()) return nowyStan(null, false, [])
    try {
      obj = JSON.parse(surowy)
    } catch (e) {
      return nowyStan(null, false, [])
    }
  }
  if (!obj || typeof obj !== 'object' || typeof obj.pole !== 'string') {
    return nowyStan(null, false, [])
  }
  if (dozwolonePola && !dozwolonePola.includes(obj.pole)) {
    return nowyStan(null, false, [])
  }
  const zwiniete = Array.isArray(obj.zwiniete)
    ? obj.zwiniete.filter((k) => typeof k === 'string')
    : []
  return nowyStan(obj.pole, obj.pokazPuste, zwiniete)
}

/** JSON do zapisu w widoku; pusty string gdy grupowanie wylaczone. */
export function serializujStan(stan) {
  if (!stan?.pole) return ''
  return JSON.stringify({
    pole: stan.pole,
    pokazPuste: !!stan.pokazPuste,
    zwiniete: [...(stan.zwiniete || [])],
  })
}

/**
 * Stan poczatkowy listy. Pierwszenstwo: zapisany `volteo_grupowanie`; potem stary
 * widok typu `group_by` (jego `group_by_field`, o ile jest na liscie dozwolonych);
 * potem pole z parametru `grupuj` (przekierowanie starej trasy /view/group_by).
 */
export function stanZWidoku(widok, dozwolonePola, poleZPrzekierowania = null) {
  if (widok?.volteo_grupowanie) {
    return parsujStan(widok.volteo_grupowanie, dozwolonePola)
  }
  if (
    widok?.type === 'group_by' &&
    widok.group_by_field &&
    dozwolonePola.includes(widok.group_by_field)
  ) {
    return nowyStan(widok.group_by_field, false, [])
  }
  if (poleZPrzekierowania && dozwolonePola.includes(poleZPrzekierowania)) {
    return nowyStan(poleZPrzekierowania, false, [])
  }
  return nowyStan(null, false, [])
}

/** Zmiana pola zeruje zwiniete grupy (klucze nalezaly do poprzedniego pola). */
export function ustawPole(stan, pole) {
  return nowyStan(pole, stan.pokazPuste, [])
}

export function ustawPokazPuste(stan, wartosc) {
  return nowyStan(stan.pole, wartosc, stan.zwiniete)
}

export function czyZwinieta(stan, klucz) {
  return stan.zwiniete.includes(klucz)
}

export function przelaczZwiniecie(stan, klucz) {
  const zwiniete = czyZwinieta(stan, klucz)
    ? stan.zwiniete.filter((k) => k !== klucz)
    : [...stan.zwiniete, klucz]
  return nowyStan(stan.pole, stan.pokazPuste, zwiniete)
}

/** "Zwin wszystkie grupy": wszystkie biezace klucze trafiaja do zwinietych. */
export function zwinWszystkie(stan, klucze) {
  return nowyStan(stan.pole, stan.pokazPuste, klucze)
}

export function rozwinWszystkie(stan) {
  return nowyStan(stan.pole, stan.pokazPuste, [])
}

/** Dlugosc strony grupy: wpis per grupa albo rozmiar strony z paska ("na grupe"). */
export function dlugoscStrony(strony, klucz, rozmiar) {
  return strony?.[klucz] || rozmiar
}

/** "Pokaz kolejne": o jeden rozmiar strony wiecej niz dotychczas. */
export function powiekszStrone(strony, klucz, rozmiar) {
  return { ...strony, [klucz]: dlugoscStrony(strony, klucz, rozmiar) + rozmiar }
}

/**
 * Laczy grupy z serwera (`{klucz, etykieta, licznik, pusta}`) ze stanem i danymi
 * wierszy (`dane[klucz] = {wiersze, wczytuje}`). Zwinieta grupa nie niesie wierszy.
 */
export function zbudujGrupy(grupy, stan, dane, rodzaj = 'select') {
  return (grupy || []).map((g) => {
    const zwinieta = czyZwinieta(stan, g.klucz)
    const wiersze = zwinieta ? [] : dane?.[g.klucz]?.wiersze || []
    return {
      klucz: g.klucz,
      etykieta: g.etykieta,
      licznik: g.licznik,
      pusta: !!g.pusta,
      rodzaj,
      zwinieta,
      wiersze,
      wczytuje: !zwinieta && !!dane?.[g.klucz]?.wczytuje,
      maWiecej: !zwinieta && wiersze.length < g.licznik,
    }
  })
}

/**
 * Wiersze dla ListRows/frappe-ui ListView: obiekty z `group`/`rows` plus dane
 * naglowka. `parsuj` przeksztalca surowe wiersze na komorki strony (parseRows).
 */
export function wierszeGrup(zbudowane, parsuj, akcje = {}) {
  return zbudowane.map((g) => ({
    group: PREFIKS_GRUPY + g.klucz,
    klucz: g.klucz,
    label: g.etykieta,
    count: g.licznik,
    kind: g.rodzaj,
    empty: g.pusta,
    collapsed: g.zwinieta,
    loading: g.wczytuje,
    hasMore: g.maWiecej,
    loaded: g.wiersze.length,
    rows: parsuj(g.wiersze),
    onToggle: () => akcje.przelacz?.(g.klucz),
    onMore: () => akcje.wiecej?.(g.klucz),
  }))
}

/** Suma rekordow i liczba grup do stopki. */
export function podsumowanie(grupy) {
  const lista = grupy || []
  return {
    razem: lista.reduce((suma, g) => suma + (g.licznik || 0), 0),
    liczbaGrup: lista.length,
  }
}

/** Inicjaly do awatara grupy uzytkownika (nazwa wyswietlana albo e-mail). */
export function inicjaly(nazwa) {
  const czesci = String(nazwa || '')
    .split(/[\s@._-]+/)
    .filter(Boolean)
  return (czesci[0]?.[0] || '?').toUpperCase() + (czesci[1]?.[0] || '').toUpperCase()
}

/** Typ trasy widoku: stary `group_by` otwiera sie jako zwykla lista. */
export function typTrasyWidoku(typ) {
  return typ === 'group_by' ? 'list' : typ
}
