// Dokładanie wielu zdjęć naraz do listy (zdjęcia dodatkowe OZE, galeria CP).
// Czysta logika, bez Vue i bez API: rodzic zapisuje wynik jednym zapisem.

// Ile plików jeszcze się zmieści w liście o limicie `max`.
export function ileMiejsca(lista, max) {
  return Math.max(0, max - (Array.isArray(lista) ? lista.length : 0))
}

// Dokleja `urle` do `lista` nie przekraczając `max`. Puste wartości i duble
// (także względem listy) są pomijane. Zwraca nową listę, dodane adresy i
// liczbę adresów, które się nie zmieściły.
export function dolaczZdjecia(lista, urle, max) {
  const obecne = Array.isArray(lista) ? lista : []
  const wolne = ileMiejsca(obecne, max)
  const widziane = new Set(obecne)
  const kandydaci = []
  for (const u of Array.isArray(urle) ? urle : []) {
    if (typeof u !== 'string' || !u || widziane.has(u)) continue
    widziane.add(u)
    kandydaci.push(u)
  }
  const dodane = kandydaci.slice(0, wolne)
  return {
    lista: [...obecne, ...dodane],
    dodane,
    pominiete: kandydaci.length - dodane.length,
  }
}

// Komunikat o plikach, które nie weszły z powodu limitu (puste, gdy wszystkie weszły).
export function komunikatLimitu(pominiete, max) {
  if (!pominiete) return ''
  return `Dodano tyle plików, ile się zmieściło (limit: ${max}). Pominięto: ${pominiete}.`
}
