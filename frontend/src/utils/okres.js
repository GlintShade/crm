// Okres rozliczen prowizji (ops#283): presety liczy front, serwer dostaje
// { wg, od, do } (daty RRRR-MM-DD, oba konce wlacznie). Czysty JS bez zaleznosci
// od DOM poza localStorage (zawsze w try/catch), testowalny przez vitest.

export const PRESETY = [
  { klucz: 'dzisiaj', etykieta: 'Dzisiaj' },
  { klucz: 'ten_tydzien', etykieta: 'Ten tydzień' },
  { klucz: 'poprzedni_tydzien', etykieta: 'Poprzedni tydzień' },
  { klucz: 'ten_miesiac', etykieta: 'Ten miesiąc' },
  { klucz: 'poprzedni_miesiac', etykieta: 'Poprzedni miesiąc' },
  { klucz: 'ten_kwartal', etykieta: 'Ten kwartał' },
  { klucz: 'poprzedni_kwartal', etykieta: 'Poprzedni kwartał' },
  { klucz: 'ten_rok', etykieta: 'Ten rok' },
  { klucz: 'ostatnie_30_dni', etykieta: 'Ostatnie 30 dni' },
  { klucz: 'ostatnie_90_dni', etykieta: 'Ostatnie 90 dni' },
  { klucz: 'wlasny', etykieta: 'Własny zakres' },
]

export const OPCJE_WG = [
  { klucz: 'podpisanie', etykieta: 'Data podpisania umowy' },
  { klucz: 'wyplata', etykieta: 'Data wypłaty' },
  { klucz: 'utworzenie', etykieta: 'Data utworzenia szansy' },
  { klucz: 'oznaczenie', etykieta: 'Data oznaczenia' },
]

export const KLUCZ_STORAGE = 'volteo_rozliczenia_okres'
export const DOMYSLNY_WYBOR = { wg: 'podpisanie', preset: 'ten_miesiac' }

const RE_DATA = /^\d{4}-\d{2}-\d{2}$/

function dwa(n) {
  return String(n).padStart(2, '0')
}

// Data lokalna jako RRRR-MM-DD (bez przesuniec strefy czasowej).
export function formatujDate(d) {
  return `${d.getFullYear()}-${dwa(d.getMonth() + 1)}-${dwa(d.getDate())}`
}

// Parsuje RRRR-MM-DD do lokalnej polnocy; null dla niepoprawnej daty.
export function parsujDate(tekst) {
  if (typeof tekst !== 'string' || !RE_DATA.test(tekst)) return null
  const [r, m, d] = tekst.split('-').map(Number)
  const data = new Date(r, m - 1, d)
  if (data.getFullYear() !== r || data.getMonth() !== m - 1 || data.getDate() !== d) return null
  return data
}

function przesun(d, dni) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + dni)
}

function poczatekTygodnia(d) {
  const dzien = (d.getDay() + 6) % 7 // poniedzialek = 0
  return przesun(d, -dzien)
}

function zakresKwartalu(rok, kwartal) {
  // kwartal 0..3, moze byc ujemny/ponad 3 (przechodzi na sasiedni rok)
  const miesiac = kwartal * 3
  return [new Date(rok, miesiac, 1), new Date(rok, miesiac + 3, 0)]
}

export function jestPoprawnymPresetem(klucz) {
  return PRESETY.some((p) => p.klucz === klucz)
}

// Zwraca { od, do } (RRRR-MM-DD) albo null, gdy zakres jest niepoprawny
// (nieznany preset, "wlasny" bez dat albo od > do).
export function zakresOkresu(preset, dzis = new Date(), od, doDaty) {
  const t = new Date(dzis.getFullYear(), dzis.getMonth(), dzis.getDate())
  let a
  let b
  switch (preset) {
    case 'dzisiaj':
      a = b = t
      break
    case 'ten_tydzien':
      a = poczatekTygodnia(t)
      b = przesun(a, 6)
      break
    case 'poprzedni_tydzien':
      a = przesun(poczatekTygodnia(t), -7)
      b = przesun(a, 6)
      break
    case 'ten_miesiac':
      a = new Date(t.getFullYear(), t.getMonth(), 1)
      b = new Date(t.getFullYear(), t.getMonth() + 1, 0)
      break
    case 'poprzedni_miesiac':
      a = new Date(t.getFullYear(), t.getMonth() - 1, 1)
      b = new Date(t.getFullYear(), t.getMonth(), 0)
      break
    case 'ten_kwartal':
      ;[a, b] = zakresKwartalu(t.getFullYear(), Math.floor(t.getMonth() / 3))
      break
    case 'poprzedni_kwartal':
      ;[a, b] = zakresKwartalu(t.getFullYear(), Math.floor(t.getMonth() / 3) - 1)
      break
    case 'ten_rok':
      a = new Date(t.getFullYear(), 0, 1)
      b = new Date(t.getFullYear(), 11, 31)
      break
    case 'ostatnie_30_dni':
      a = przesun(t, -29)
      b = t
      break
    case 'ostatnie_90_dni':
      a = przesun(t, -89)
      b = t
      break
    case 'wlasny': {
      const pa = parsujDate(od)
      const pb = parsujDate(doDaty)
      if (!pa || !pb || pa > pb) return null
      a = pa
      b = pb
      break
    }
    default:
      return null
  }
  return { od: formatujDate(a), do: formatujDate(b) }
}

export function etykietaZakresu(od, doDaty) {
  return `od ${od} do ${doDaty}`
}

// Wybor ({ wg, preset, od, do }) -> okres dla API ({ wg, od, do }) albo null.
export function okresDlaApi(wybor, dzis = new Date()) {
  if (!wybor) return null
  const zakres = zakresOkresu(wybor.preset, dzis, wybor.od, wybor.do)
  if (!zakres) return null
  return { wg: wybor.wg, od: zakres.od, do: zakres.do }
}

export function zapiszWybor(wybor) {
  try {
    localStorage.setItem(KLUCZ_STORAGE, JSON.stringify(wybor))
  } catch {
    // brak localStorage (tryb prywatny): wybor zyje tylko w pamieci
  }
}

export function odczytajWybor() {
  try {
    const surowy = localStorage.getItem(KLUCZ_STORAGE)
    if (!surowy) return { ...DOMYSLNY_WYBOR }
    const w = JSON.parse(surowy)
    if (!w || typeof w !== 'object') return { ...DOMYSLNY_WYBOR }
    if (!OPCJE_WG.some((o) => o.klucz === w.wg)) return { ...DOMYSLNY_WYBOR }
    if (!jestPoprawnymPresetem(w.preset)) return { ...DOMYSLNY_WYBOR }
    if (w.preset === 'wlasny') {
      if (!zakresOkresu('wlasny', new Date(), w.od, w.do)) return { ...DOMYSLNY_WYBOR }
      return { wg: w.wg, preset: 'wlasny', od: w.od, do: w.do }
    }
    return { wg: w.wg, preset: w.preset }
  } catch {
    return { ...DOMYSLNY_WYBOR }
  }
}
