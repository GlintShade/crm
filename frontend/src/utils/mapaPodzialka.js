// Podzialka liniowa (skala) na mapach Leaflet. Discord 130, ops#382.
// Tylko km i metry (bez mil), lewy dolny rog, zeby nie kolidowala z atrybucja
// OpenStreetMap w prawym dolnym rogu (wymagana licencja, zostaje bez zmian).
export const OPCJE_PODZIALKI = Object.freeze({
  position: 'bottomleft',
  metric: true,
  imperial: false,
  maxWidth: 150,
})

export function dodajPodzialke(L, mapa) {
  if (!L || !L.control || typeof L.control.scale !== 'function' || !mapa) {
    return null
  }
  return L.control.scale({ ...OPCJE_PODZIALKI }).addTo(mapa)
}
