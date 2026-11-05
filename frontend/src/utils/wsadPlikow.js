// Decyzja "co zrobić po rozstrzygnięciu wsadu plików" w oknie "Załącz"
// (FilesUploader.vue), wyciągnięta do czystej funkcji bez Vue, żeby dało
// się ją przetestować osobno (uwaga 93).
//
// Dlaczego to w ogóle istnieje: okno wysyła wszystkie wybrane pliki
// RÓWNOLEGLE, a stara wersja kodu zamykała okno i emitowała 'after' gdy
// kończył się plik o OSTATNIM INDEKSIE z forEach, zakładając że to on
// skończy się jako ostatni. Kolejność zakończenia uploadów bywa inna niż
// kolejność ich startu (różne rozmiary plików, różne czasy odpowiedzi
// serwera), więc pliki kończące się PO ostatnim indeksie nie wywoływały
// już nic: znikały bez śladu, okno było już zamknięte, lista wyczyszczona.
// Wywołujący (FilesUploader.vue) ma teraz czekać, aż KAŻDY plik wsadu się
// rozstrzygnie (np. przez Promise.all na obietnicach, które same nigdy nie
// odrzucają, sukces/porażka to tylko pole w wyniku), i dopiero wtedy
// zapytać tę funkcję, co dalej.

/**
 * @typedef {{ ok: boolean, wynik?: unknown }} WynikPliku
 *   Rozstrzygnięcie jednego pliku ze wsadu. `ok` mówi, czy upload się udał;
 *   `wynik` to odpowiedź serwera (tylko gdy `ok === true`).
 */

/**
 * @typedef {object} DecyzjaWsadu
 * @property {boolean} zamknij - czy zamknąć okno dialogowe "Załącz"
 * @property {boolean} wyczyscListe - czy wyczyścić CAŁĄ listę plików
 *   (tylko gdy wszystkie się udały; przy częściowym błędzie wywołujący ma
 *   zostawić na liście tylko pliki nieudane, a udane z niej usunąć)
 * @property {boolean} emitujAfter - czy wyemitować 'after' (raz, gdy
 *   cokolwiek ze wsadu się udało)
 * @property {Array<unknown>} udane - odpowiedzi serwera dla udanych
 *   plików, w kolejności z `wyniki` (dowolnej, patrz niżej), do
 *   przekazania jako payload 'after'
 */

/**
 * Rozstrzyga, co zrobić po zakończeniu CAŁEGO wsadu plików.
 *
 * Kolejność elementów w `wyniki` jest DOWOLNA (nie musi odpowiadać
 * kolejności indeksów w oryginalnej liście plików), funkcja celowo nie
 * zakłada nic o kolejności, żeby nie powtórzyć błędu ze starego kodu.
 *
 * @param {number} liczbaPlikow - rozmiar wsadu (ile plików wysłano razem)
 * @param {WynikPliku[]} wyniki - rozstrzygnięcie KAŻDEGO pliku ze wsadu
 * @returns {DecyzjaWsadu}
 */
export function rozstrzygnijWsad(liczbaPlikow, wyniki) {
  if (!Array.isArray(wyniki) || wyniki.length !== liczbaPlikow) {
    throw new Error('Liczba wyników nie zgadza się z rozmiarem wsadu plików')
  }

  const udane = wyniki.filter((w) => w.ok).map((w) => w.wynik)
  const wszystkieOk = liczbaPlikow > 0 && udane.length === liczbaPlikow

  return {
    zamknij: wszystkieOk,
    wyczyscListe: wszystkieOk,
    emitujAfter: udane.length > 0,
    udane,
  }
}
