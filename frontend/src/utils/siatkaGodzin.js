// Zakres i krok siatki godzin spotkan (decyzja wlasciciela 2026-09-24):
// przyciski od 08:00 do 22:00 WLACZNIE co 30 min. Siatka tylko ukrywa
// godziny; reczny wpis dowolnej godziny zostaje. Zmiana wymaga nowego obrazu.
export const SIATKA_GODZIN = { od: '08:00', do: '22:00', krokMin: 30 }

export const pad = (n) => String(n).padStart(2, '0')

function naMinuty(hhmm) {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}

export function generujSiatke(cfg = SIATKA_GODZIN) {
  if (!(cfg.krokMin > 0)) throw new Error('krokMin musi byc dodatni')
  const pola = []
  for (let t = naMinuty(cfg.od); t <= naMinuty(cfg.do); t += cfg.krokMin) {
    const hh = pad(Math.floor(t / 60))
    const mm = pad(t % 60)
    pola.push({ wartosc: `${hh}:${mm}:00`, etykieta: `${hh}:${mm}` })
  }
  return pola
}

export function czyWybrane(pole, time) {
  return Boolean(time) && time.slice(0, 5) === pole.etykieta
}
