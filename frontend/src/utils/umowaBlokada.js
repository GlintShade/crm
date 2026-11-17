// Stan blokady formularza umowy (ops#371). Czysta funkcja: z obiektu `blokada`
// zwracanego przez crm.api.umowa.* wylicza stan interfejsu. Brak `blokada`
// (stary backend) oznacza zachowanie jak dotychczas, czyli wszystko false.

// Serwer wysyła czas lokalny jako "YYYY-MM-DD HH:MM:SS". Parsujemy napis,
// bez Date, żeby nie przesuwać stref czasowych.
export function formatujCzasBlokady(wartosc) {
  if (!wartosc) return ''
  const m = String(wartosc).match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/)
  if (!m) return ''
  const data = `${m[3]}.${m[2]}.${m[1]}`
  return m[4] !== undefined ? `${data} ${m[4]}:${m[5]}` : data
}

export function stanBlokady(blokada) {
  const pusty = {
    zablokowany: false,
    odblokowanyPoPodpisie: false,
    tekstBanera: '',
    pokazOdblokuj: false,
    pokazZablokuj: false,
  }
  if (!blokada || typeof blokada !== 'object') return pusty

  const zablokowany = !!blokada.zablokowany
  const odblokowany = !!blokada.odblokowany
  const mozeOdblokowac = !!blokada.moze_odblokowac
  const dataPodpisu = formatujCzasBlokady(blokada.pierwszy_podpis)

  let tekstBanera = ''
  if (zablokowany) {
    const czesc =
      blokada.powod === 'podpisana' && !dataPodpisu
        ? 'Umowa została podpisana w Autenti.'
        : `Umowa została podpisana w Autenti (pierwszy podpis: ${dataPodpisu}).`
    tekstBanera = `Formularz zablokowany. ${czesc} Zmiany może odblokować administrator.`
  } else if (odblokowany) {
    const kto = blokada.odblokowal || 'administratora'
    const kiedy = formatujCzasBlokady(blokada.odblokowano_dnia)
    tekstBanera =
      `Formularz odblokowany przez ${kto}` +
      (kiedy ? ` dnia ${kiedy}` : '') +
      '. Podpisany dokument w Autenti się nie zmienia.'
  }

  return {
    zablokowany,
    odblokowanyPoPodpisie: !zablokowany && odblokowany,
    tekstBanera,
    pokazOdblokuj: zablokowany && mozeOdblokowac,
    pokazZablokuj: !zablokowany && odblokowany && mozeOdblokowac,
  }
}
