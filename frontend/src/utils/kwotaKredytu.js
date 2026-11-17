// Podgląd kwoty kredytu w zakładce Umowa (ops#369).
//
// Lustro reguły serwera `crm/volteo_umowa.py::kwota_kredytu`; serwer i PDF zostają
// źródłem prawdy, to jest wyłącznie podpowiedź na ekranie podczas wpisywania.
//   "Kredyt 100%"      -> cała cena brutto
//   "Kredyt + gotówka" -> brutto minus wpłata własna, nie mniej niż 0
//   inaczej            -> 0

function liczba(wartosc) {
  const n = Number(wartosc)
  return Number.isFinite(n) ? n : 0
}

/**
 * @param {*} brutto - cena brutto szansy
 * @param {*} wklad - wpłata własna z formularza umowy
 * @param {*} finansowanie - wybrany sposób finansowania (literał zapisany w bazie)
 * @returns {number} kwota kredytu w zł
 */
export function kwotaKredytuPodglad(brutto, wklad, finansowanie) {
  if (finansowanie === 'Kredyt 100%') return Math.max(0, liczba(brutto))
  if (finansowanie === 'Kredyt + gotówka') return Math.max(0, liczba(brutto) - liczba(wklad))
  return 0
}
