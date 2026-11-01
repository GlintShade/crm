// Grafik dyzurow SMS (ops#313): czysty JS, lustro crm/volteo_dyzury.py.

export const DNI_TYGODNIA = [
  'Poniedziałek',
  'Wtorek',
  'Środa',
  'Czwartek',
  'Piątek',
  'Sobota',
  'Niedziela',
]

// "08:00:00" -> "08:00", "8:5" -> "08:05"; wartosc nieczytelna wraca bez zmian
export function formatujGodzine(wartosc) {
  const m = /^(\d{1,2}):(\d{1,2})(?::\d{1,2})?$/.exec(String(wartosc ?? '').trim())
  if (!m) return String(wartosc ?? '')
  return `${m[1].padStart(2, '0')}:${m[2].padStart(2, '0')}`
}

// "08:00" -> "08:00:00"; wartosc nieczytelna wraca bez zmian
export function naSekundy(wartosc) {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(String(wartosc ?? '').trim())
  if (!m) return String(wartosc ?? '')
  return `${m[1].padStart(2, '0')}:${m[2]}:${m[3] ?? '00'}`
}

function minuty(wartosc) {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(String(wartosc ?? '').trim())
  if (!m) return null
  const g = Number(m[1])
  const min = Number(m[2])
  const s = Number(m[3] ?? 0)
  if (g > 23 || min > 59 || s > 59) return null
  return g * 3600 + min * 60 + s
}

// Komunikat bledu po polsku albo null; lustro waliduj_wiersz z Pythona
export function walidujWiersz(dzien, od, do_) {
  if (!DNI_TYGODNIA.includes(dzien)) {
    return `Dzień tygodnia musi być jednym z: ${DNI_TYGODNIA.join(', ')}.`
  }
  const a = minuty(od)
  const b = minuty(do_)
  if (a === null || b === null) return 'Godziny dyżuru muszą mieć format GG:MM.'
  if (a >= b) return 'Godzina początku dyżuru musi być wcześniejsza niż godzina końca.'
  return null
}

// { 'Poniedziałek': [...], ... } wszystkie 7 dni, wiersze posortowane po godzinie od i uzytkowniku
export function grupujPoDniach(wiersze) {
  const wynik = Object.fromEntries(DNI_TYGODNIA.map((d) => [d, []]))
  for (const w of wiersze || []) {
    if (w.data) continue // wyjatki od grafiku maja wlasna liste
    if (wynik[w.dzien_tygodnia]) wynik[w.dzien_tygodnia].push(w)
  }
  for (const dzien of DNI_TYGODNIA) {
    wynik[dzien].sort((x, y) => {
      const d = (minuty(x.od) ?? 0) - (minuty(y.od) ?? 0)
      return d !== 0 ? d : String(x.uzytkownik).localeCompare(String(y.uzytkownik))
    })
  }
  return wynik
}

export const PLACEHOLDERY_DYZUR = ['klient', 'telefon', 'kod', 'miejscowosc', 'link']
export const LIMIT_DYZUR_MAX = 1000

// Komunikat bledu po polsku albo null; lustro waliduj_tresc_dyzur z Pythona
export function walidujTresc(tresc) {
  if (!String(tresc ?? '').trim()) return 'Treść SMS nie może być pusta.'
  for (const m of String(tresc).matchAll(/\{(\w+)\}/g)) {
    if (!PLACEHOLDERY_DYZUR.includes(m[1])) {
      const dozwolone = PLACEHOLDERY_DYZUR.map((p) => `{${p}}`).join(', ')
      return `Nieznany placeholder {${m[1]}}. Dozwolone: ${dozwolone}.`
    }
  }
  return null
}

// Komunikat bledu albo null; limit 0..1000 (0 blokuje wysylke)
export function walidujLimit(limit) {
  const n = Number(limit)
  if (String(limit ?? '').trim() === '' || !Number.isInteger(n) || n < 0 || n > LIMIT_DYZUR_MAX) {
    return `Limit dzienny musi być liczbą od 0 do ${LIMIT_DYZUR_MAX} (0 blokuje wysyłkę).`
  }
  return null
}

const SKROTY_DNI = ['nd', 'pn', 'wt', 'śr', 'czw', 'pt', 'sob']

function rozbijDate(data) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(data ?? '').trim())
  if (!m) return null
  const [r, mi, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const dt = new Date(Date.UTC(r, mi - 1, d))
  if (dt.getUTCFullYear() !== r || dt.getUTCMonth() !== mi - 1 || dt.getUTCDate() !== d) return null
  return { r, mi, d, dzienNr: dt.getUTCDay() }
}

// "2026-11-03" -> "wt 03.11.2026"; wartosc nieczytelna wraca bez zmian
export function formatujDate(data) {
  const p = rozbijDate(data)
  if (!p) return String(data ?? '')
  const dd = String(p.d).padStart(2, '0')
  const mm = String(p.mi).padStart(2, '0')
  return `${SKROTY_DNI[p.dzienNr]} ${dd}.${mm}.${p.r}`
}

// "2026-11-03" -> "Wtorek" (nazwa z DNI_TYGODNIA) albo null
export function dzienZDaty(data) {
  const p = rozbijDate(data)
  return p ? DNI_TYGODNIA[(p.dzienNr + 6) % 7] : null
}

// Tylko wiersze z data, rosnaco po dacie, potem po godzinie od
export function sortujWyjatki(wiersze) {
  return (wiersze || [])
    .filter((w) => w.data)
    .sort((x, y) => {
      const d = String(x.data).localeCompare(String(y.data))
      return d !== 0 ? d : (minuty(x.od) ?? 0) - (minuty(y.od) ?? 0)
    })
}

// Komunikat bledu po polsku albo null; lustro waliduj_wiersz (wyjatek) z Pythona
export function walidujWyjatek(data, od, do_, bezDyzuru, uzytkownik) {
  if (!String(data ?? '').trim()) return 'Wybierz datę wyjątku.'
  if (!rozbijDate(data)) return 'Data wyjątku musi mieć format RRRR-MM-DD.'
  if (bezDyzuru) return null
  const a = minuty(od)
  const b = minuty(do_)
  if (a === null || b === null) return 'Godziny dyżuru muszą mieć format GG:MM.'
  if (a >= b) return 'Godzina początku dyżuru musi być wcześniejsza niż godzina końca.'
  if (!uzytkownik) return 'Wybierz użytkownika.'
  return null
}
