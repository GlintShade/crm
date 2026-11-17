// Karta "Handlowiec" (ops#366): czy da sie pobrac dane kontaktowe wlasciciela.
// Endpoint odrzuca Administrator, Guest i wartosci niebedace adresem e-mail.
export function czyPobracKontakt(wlasciciel) {
  if (typeof wlasciciel !== 'string') return false
  const w = wlasciciel.trim()
  if (!w || w === 'Administrator' || w === 'Guest') return false
  const czesci = w.split('@')
  return czesci.length === 2 && czesci[0].length > 0 && czesci[1].length > 0
}
