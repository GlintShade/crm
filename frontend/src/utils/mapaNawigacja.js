// Nawigacja z szybkiego podglądu leada na mapie: link do trasy Google Maps
// liczonej do WSPÓŁRZĘDNYCH leada (nie do tekstu adresu), więc Google pokazuje
// dokładnie ten punkt, który widać na pinie. Na telefonie ten sam URL otwiera
// aplikację Google Maps z trasą od bieżącej lokalizacji. Frappe-free i bez Vue,
// żeby dało się przetestować samym vitestem.

function czytajLiczbe(wartosc) {
  if (wartosc === null || wartosc === undefined) return NaN
  if (typeof wartosc === 'string' && wartosc.trim() === '') return NaN
  if (typeof wartosc !== 'number' && typeof wartosc !== 'string') return NaN
  return Number(wartosc)
}

// Maksymalnie 6 miejsc po przecinku, zawsze z kropką (bez formatowania
// lokalnego); Number() zjada końcowe zera.
function formatujWspolrzedna(n) {
  return String(Number(n.toFixed(6)))
}

/**
 * Link do trasy w Google Maps do punktu (lat, lng). Zwraca null, gdy
 * współrzędne są brak, nieliczbowe, nieskończone, 0/0 albo poza zakresem.
 * Bez dir_action=navigate: widok trasy, nie natychmiastowy start nawigacji.
 *
 * @param {unknown} lat
 * @param {unknown} lng
 * @returns {string | null}
 */
export function linkTrasyGoogle(lat, lng) {
  const a = czytajLiczbe(lat)
  const b = czytajLiczbe(lng)
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null
  if (a === 0 && b === 0) return null
  if (a < -90 || a > 90 || b < -180 || b > 180) return null
  const cel = `${formatujWspolrzedna(a)},${formatujWspolrzedna(b)}`
  return `https://www.google.com/maps/dir/?api=1&destination=${cel}&travelmode=driving`
}

/**
 * Czy punkt leada to tylko środek miejscowości lub kodu pocztowego (a nie
 * konkretny dom). Wartości z `custom_geo_dokladnosc`.
 *
 * @param {unknown} dokladnosc
 * @returns {boolean}
 */
export function czyLokalizacjaPrzyblizona(dokladnosc) {
  return dokladnosc === 'miejscowosc' || dokladnosc === 'kod'
}
