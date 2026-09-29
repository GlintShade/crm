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
// separator dnia i godziny spacja albo `T`, sekundy opcjonalne, a gdy są -
// opcjonalny ułamek sekundy (Frappe zwraca np. "15:19:56.291762" dla
// `data_zdarzenia`/`creation`; ułamek jest tu tylko dopuszczony w
// dopasowaniu, nigdy nie wchodzi do wyniku). Lustro tego samego tolerancyjnego
// wzorca żyje w `godzinaZTekstu()` w NotatkaKarta.vue.
const WZORZEC_DATY_CZASU = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/

/**
 * Rozbiera surowy Datetime (string albo obiekt Date) na części
 * kalendarzowe, bez interpretacji strefy czasowej (patrz komentarz przy
 * `formatujTermin` - `new Date(string)` na wejściu tekstowym
 * zniekształciłaby godzinę). Wspólny parser dla `formatujTermin` i
 * `terminWzgledny`, żeby tolerancyjny regex i walidacja istniały w jednym
 * miejscu.
 *
 * @param {string|Date} dataCzas
 * @returns {{rok: number, miesiac: number, dzien: number, godzina: number, minuta: number}|null}
 */
function rozbierzDataCzas(dataCzas) {
  if (dataCzas === null || dataCzas === undefined || dataCzas === '') return null

  let rok, miesiac, dzien, godzina, minuta

  if (dataCzas instanceof Date) {
    if (Number.isNaN(dataCzas.getTime())) return null
    rok = dataCzas.getFullYear()
    miesiac = dataCzas.getMonth() + 1
    dzien = dataCzas.getDate()
    godzina = dataCzas.getHours()
    minuta = dataCzas.getMinutes()
  } else if (typeof dataCzas === 'string') {
    const dopasowanie = WZORZEC_DATY_CZASU.exec(dataCzas)
    if (!dopasowanie) return null
    rok = Number(dopasowanie[1])
    miesiac = Number(dopasowanie[2])
    dzien = Number(dopasowanie[3])
    godzina = Number(dopasowanie[4])
    minuta = Number(dopasowanie[5])
  } else {
    return null
  }

  if (miesiac < 1 || miesiac > 12) return null
  if (dzien < 1 || dzien > 31) return null
  if (godzina < 0 || godzina > 23) return null
  if (minuta < 0 || minuta > 59) return null

  const data = new Date(rok, miesiac - 1, dzien)
  // Odrzuca daty nieistniejące (np. 31 lutego), które JS po cichu przesuwa
  // na kolejny miesiąc zamiast rzucić błąd.
  if (
    data.getFullYear() !== rok ||
    data.getMonth() !== miesiac - 1 ||
    data.getDate() !== dzien
  ) {
    return null
  }

  return { rok, miesiac, dzien, godzina, minuta }
}

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
  const czesci = rozbierzDataCzas(dataCzas)
  if (!czesci) return ''

  const { rok, miesiac, dzien, godzina, minuta } = czesci
  const data = new Date(rok, miesiac - 1, dzien)
  const dzienTygodnia = DNI_TYGODNIA_SKROT[data.getDay()]
  const miesiacSkrot = MIESIACE_SKROT[miesiac - 1]
  const godzinaStr = String(godzina).padStart(2, '0')
  const minutaStr = String(minuta).padStart(2, '0')

  return `${dzienTygodnia}, ${dzien} ${miesiacSkrot} ${rok}, ${godzinaStr}:${minutaStr}`
}

/**
 * Tekst względny terminu (panel właściwości TaskModal.vue, issue
 * GlintShade/proenergy-crm-ops#208): "dziś", "jutro", "za N dni" dla
 * terminów w przyszłości, "Termin minął N dni temu" dla przeszłych,
 * porównanie WYŁĄCZNIE po dniu kalendarzowym (godzina/minuta terminu nie
 * wpływają na wynik) względem `teraz`.
 *
 * Frappe-free (bez importu `__`, `frappe-ui` ani dayjs) - zwraca gotowy,
 * surowy polski tekst, dokładnie jak `formatujTermin` powyżej; wołający
 * wyświetla go wprost, bez owijania w `__()`.
 *
 * Różnica dni liczona przez `Date.UTC(rok, miesiac - 1, dzien)` dla obu dat
 * kalendarzowych (nie przez odejmowanie dwóch `Date` z godziną/minutą) -
 * unika przesunięć przy zmianie czasu (DST) i przy różnicy godzin między
 * terminem a `teraz` w tym samym dniu.
 *
 * @param {string|Date} dataCzas surowy Datetime z Frappe albo obiekt Date
 * @param {Date} [teraz] punkt odniesienia "teraz" (domyślnie `new Date()`)
 * @returns {string} np. "dziś", "jutro", "za 5 dni", "Termin minął 3 dni temu",
 *   albo '' gdy `dataCzas` puste/niepoprawne
 */
export function terminWzgledny(dataCzas, teraz = new Date()) {
  const czesci = rozbierzDataCzas(dataCzas)
  if (!czesci) return ''
  if (!(teraz instanceof Date) || Number.isNaN(teraz.getTime())) return ''

  const dzienDocelowy = Date.UTC(czesci.rok, czesci.miesiac - 1, czesci.dzien)
  const dzienDzisiejszy = Date.UTC(teraz.getFullYear(), teraz.getMonth(), teraz.getDate())
  const roznicaDni = Math.round((dzienDocelowy - dzienDzisiejszy) / 86400000)

  if (roznicaDni === 0) return 'dziś'
  if (roznicaDni === 1) return 'jutro'
  if (roznicaDni > 1) return `za ${roznicaDni} dni`
  return `Termin minął ${Math.abs(roznicaDni)} dni temu`
}
