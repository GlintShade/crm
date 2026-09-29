// Segmenty paska postepu procesu pod odznaka statusu na liscie szans
// (kolumna "Etap procesu", wariant B listy Umowy, b65). Frappe-free -
// testowalne bezposrednio przez vitest, ten sam wzorzec co dealPipeline.js.
//
// Mianownik (liczba segmentow) i licznik (ile wypelnionych) liczone sa
// WYLACZNIE z danych juz pobranych przez wolajacego (DealsListView.vue):
// grupa statusow per rodzaj z crm.api.pipeline.volteo_pipeline_grupy (ten
// sam zasob, cache 'volteo-pipeline-grupy', ktory Filter.vue/
// QuickFilterField.vue juz odpytuja - patrz utils/etapFiltr.js, wiec
// zwykle jest juz cieply w cache przy wejsciu na liste szans) i typ
// statusu (Won/Lost) ze store'u statusow (dealStatusesByName[...].type) -
// NIGDY hardkodowane liczby krokow (5 dla OZE, 12 dla CP).
//
// Grupa zwrocona przez volteo_pipeline_grupy to proces PLUS statusy
// terminalne, w tej kolejnosci (crm.volteo_pipeline.grupa_for =
// pipeline_for(rodzaj) + TERMINALE[klucz]) - pipelineOnly() nizej odcina z
// KONCA te wpisy, ktore sa nazwami terminalnymi (NAZWY_TERMINALNE), zeby
// zostac z sama kolejnoscia procesu. Nazwy terminalne sa tu zduplikowane
// jako stale literaly (TERMINALE w crm/volteo_pipeline.py nie jest
// wystawione zadnym API) - ten sam, zaakceptowany w tym repo wzorzec co
// PROG_PPOZ_KW (crm/volteo_umowa.py / pvForm.js), zamiast dodawac nowy
// endpoint backendu tylko po liczby.

const NAZWY_TERMINALNE = new Set(['Wygrana – montaż', 'Przegrana'])

/**
 * Odcina z KONCA tablicy nazwy statusow terminalnych, zostawiajac sama
 * kolejnosc procesu. Bezpieczne dla pustej/nie-tablicowej wartosci.
 *
 * @param {string[]|null|undefined} grupa
 * @returns {string[]}
 */
export function pipelineOnly(grupa) {
  if (!Array.isArray(grupa)) return []
  const wynik = [...grupa]
  while (wynik.length && NAZWY_TERMINALNE.has(wynik[wynik.length - 1])) {
    wynik.pop()
  }
  return wynik
}

/**
 * Liczba segmentow paska (mianownik) dla danego rodzaju umowy. Zero dla
 * brakujacej/nieznanej grupy albo pustego/nieznanego rodzaju (np. "XX") -
 * wolajacy ma to czytac jako "nie renderuj paska w ogole".
 *
 * @param {Object<string, string[]>|null|undefined} grupy - ksztalt crm.api.pipeline.volteo_pipeline_grupy
 * @param {string|null|undefined} rodzaj
 * @returns {number}
 */
export function liczbaSegmentow(grupy, rodzaj) {
  if (!grupy || !rodzaj) return 0
  return pipelineOnly(grupy[rodzaj]).length
}

/**
 * Liczba wypelnionych segmentow (licznik) dla statusu biezacej szansy.
 *
 * Status W procesie -> jego pozycja (1-based, `indexOf + 1`). Status POZA
 * procesem typu Won -> pelny pasek (np. OZE "Wygrana – montaż"; dla CP
 * "Projekt rozliczony" jest natomiast W PROCESIE - ostatni krok, wiec
 * trafia w pierwsza galaz, nie w te). Typu Lost albo nieznany -> pusty
 * pasek (0). Rodzaj bez procesu (pusty/nieznany, "XX") -> 0 (wolajacy i
 * tak nie renderuje paska wtedy, patrz `liczbaSegmentow` zwracajace 0 dla
 * tego samego wejscia).
 *
 * @param {Object<string, string[]>|null|undefined} grupy
 * @param {string|null|undefined} rodzaj
 * @param {string|null|undefined} status
 * @param {string|null|undefined} typStatusu - 'Open'|'Ongoing'|'Won'|'Lost'|undefined
 * @returns {number}
 */
export function segmentyWypelnione(grupy, rodzaj, status, typStatusu) {
  const proces = grupy && rodzaj ? pipelineOnly(grupy[rodzaj]) : []
  if (proces.length === 0) return 0
  const indeks = proces.indexOf(status)
  if (indeks >= 0) return indeks + 1
  return typStatusu === 'Won' ? proces.length : 0
}
