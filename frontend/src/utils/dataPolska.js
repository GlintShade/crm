// Formatowanie polskiej daty/godziny dla dymka mapy leadów (MapaLeadow.vue,
// item #31 rundy klik-testu po b63) - "Termin spotkania" ma pokazywać polski
// skrót dnia tygodnia i miesiąca oraz godzinę w formacie 24h, np.
// "pt., 25 wrz 2026, 17:00", zamiast angielskiego 12h domyślnego
// formatDate()/getFormat() z utils/index.js.
//
// Frappe-free (bez importu `@/utils`, `frappe-ui`, dayjs ani `~icons`), ten
// sam wzorzec co mapaKolory.js - testowalne bezpośrednio przez vitest, bez
// rejestrowania globalnej lokalizacji dayjs `pl`.

export const DNI_TYGODNIA_SKROT = ['niedz.', 'pon.', 'wt.', 'śr.', 'czw.', 'pt.', 'sob.']

export const MIESIACE_SKROT = [
  'sty',
  'lut',
  'mar',
  'kwi',
  'maj',
  'cze',
  'lip',
  'sie',
  'wrz',
  'paź',
  'lis',
  'gru',
]

// `YYYY-MM-DD HH:mm` albo `YYYY-MM-DD HH:mm:ss` (surowy Frappe Datetime),
// separator dnia i godziny spacja albo `T`, sekundy opcjonalne.
const WZORZEC_DATY_CZASU = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/

/**
 * Formatuje datę/czas na polski zapis dla dymka mapy: skrót dnia tygodnia,
 * dzień bez zera wiodącego, skrót miesiąca, rok, godzina HH:mm (24h).
 *
 * Celowo NIE używa `new Date(string)` na wejściu tekstowym (interpretacja
 * jako UTC zniekształciłaby godzinę) - string parsowany jest wyłącznie
 * regexem, a dzień tygodnia liczony przez `new Date(y, m - 1, d)` (lokalna
 * północ, bez stref czasowych).
 *
 * @param {string|Date} dataCzas surowy Datetime z Frappe ("YYYY-MM-DD HH:mm[:ss]",
 *   dopuszczalny separator "T") albo obiekt Date
 * @returns {string} np. "pt., 25 wrz 2026, 17:00", albo '' gdy wejście puste/niepoprawne
 */
export function formatujTermin(dataCzas) {
  if (dataCzas === null || dataCzas === undefined || dataCzas === '') return ''

  let rok, miesiac, dzien, godzina, minuta

  if (dataCzas instanceof Date) {
    if (Number.isNaN(dataCzas.getTime())) return ''
    rok = dataCzas.getFullYear()
    miesiac = dataCzas.getMonth() + 1
    dzien = dataCzas.getDate()
    godzina = dataCzas.getHours()
    minuta = dataCzas.getMinutes()
  } else if (typeof dataCzas === 'string') {
    const dopasowanie = WZORZEC_DATY_CZASU.exec(dataCzas)
    if (!dopasowanie) return ''
    rok = Number(dopasowanie[1])
    miesiac = Number(dopasowanie[2])
    dzien = Number(dopasowanie[3])
    godzina = Number(dopasowanie[4])
    minuta = Number(dopasowanie[5])
  } else {
    return ''
  }

  if (miesiac < 1 || miesiac > 12) return ''
  if (dzien < 1 || dzien > 31) return ''
  if (godzina < 0 || godzina > 23) return ''
  if (minuta < 0 || minuta > 59) return ''

  const data = new Date(rok, miesiac - 1, dzien)
  // Odrzuca daty nieistniejące (np. 31 lutego), które JS po cichu przesuwa
  // na kolejny miesiąc zamiast rzucić błąd.
  if (
    data.getFullYear() !== rok ||
    data.getMonth() !== miesiac - 1 ||
    data.getDate() !== dzien
  ) {
    return ''
  }

  const dzienTygodnia = DNI_TYGODNIA_SKROT[data.getDay()]
  const miesiacSkrot = MIESIACE_SKROT[miesiac - 1]
  const godzinaStr = String(godzina).padStart(2, '0')
  const minutaStr = String(minuta).padStart(2, '0')

  return `${dzienTygodnia}, ${dzien} ${miesiacSkrot} ${rok}, ${godzinaStr}:${minutaStr}`
}
