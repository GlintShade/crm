// Zakładki "OSD" i "Dotacja" na szansie OZE (ops#202). Lustro czystego
// kanonu backendu `crm/volteo_osd_dotacja.py`: STATUSY, KOLORY i ETYKIETY
// tutaj muszą pozostać bajt w bajt zgodne z tamtym plikiem (i z opcjami pól
// Select na CRM Deal w ops/crm-osd-dotacja.py) -- trzy miejsca, jedna zmiana
// naraz w każdym.
//
// Frappe-free (zero importów `@/utils`/`frappe-ui`), dokładnie jak
// utils/notatki.js i utils/aktualizacje.js -- ten sam powód: testowalność
// bez mocka Vue i bez wciągania grafu modułów przez barrel `@/utils`.
//
// Pusta/nieustawiona wartość pola renderuje się jak "Nie rozpoczęto" (gray)
// bez żadnego zapisu -- "Nie rozpoczęto" jest też PRAWDZIWĄ wartością w
// STATUSY (backoffice może ją jawnie wybrać, np. żeby cofnąć omyłkowy
// status), tylko domyślny (nieustawiony) stan renderuje się identycznie.

export const STATUSY = {
  OSD: [
    'Nie rozpoczęto',
    'Zgłoszenie wysłane',
    'Uwagi OSD',
    'Umowa przyłączeniowa',
    'Licznik wymieniony',
    'Zakończone',
  ],
  Dotacja: [
    'Nie rozpoczęto',
    'Wniosek złożony',
    'Uzupełnienie',
    'Decyzja pozytywna',
    'Wypłacona',
    'Odrzucona',
  ],
}

// Kolor (klucz COLOR_BUTTON_CLASS_MAP w utils/statusColors.js) dla każdej
// wartości STATUSY. Decyzja właściciela 2026-09-28: statusy "w trakcie" są
// zawsze niebieskie, tylko stany terminalne dostają inny kolor. "Decyzja
// pozytywna" jest jasnozielona ("lime", klucz dopisany do
// COLOR_BUTTON_CLASS_MAP przez ten issue).
export const KOLORY = {
  OSD: {
    'Nie rozpoczęto': 'gray',
    'Zgłoszenie wysłane': 'blue',
    'Uwagi OSD': 'blue',
    'Umowa przyłączeniowa': 'blue',
    'Licznik wymieniony': 'blue',
    Zakończone: 'green',
  },
  Dotacja: {
    'Nie rozpoczęto': 'gray',
    'Wniosek złożony': 'blue',
    Uzupełnienie: 'blue',
    'Decyzja pozytywna': 'lime',
    Wypłacona: 'green',
    Odrzucona: 'red',
  },
}

// Etykieta karty statusu wyświetlana nad strumieniem notatek każdej
// zakładki (StatusZakladki.vue).
export const ETYKIETY = {
  OSD: 'Status OSD',
  Dotacja: 'Status dotacji',
}

// Kolor (klucz KOLORY[zakladka]) dla wartości `wartosc` pola statusu danej
// zakładki. Pusta/nieznana wartość ('' albo undefined/null, oraz każda
// wartość spoza STATUSY[zakladka]) wraca jako kolor "Nie rozpoczęto" (gray)
// -- nigdy `undefined`, żeby wołający zawsze dostał bezpieczny klucz koloru.
export function kolorStatusu(zakladka, wartosc) {
  const kolory = KOLORY[zakladka] || {}
  return kolory[wartosc] || kolory['Nie rozpoczęto'] || 'gray'
}

// Etykieta wyświetlana w przycisku/plakietce dla wartości `wartosc` pola
// statusu danej zakładki -- pusta/nieznana wartość wraca jako "Nie
// rozpoczęto", surowy polski tekst (tłumaczenie przez __() dzieje się w
// komponencie, jak wszędzie indziej w tym pliku).
export function etykietaStatusu(zakladka, wartosc) {
  const statusy = STATUSY[zakladka] || []
  return statusy.includes(wartosc) ? wartosc : 'Nie rozpoczęto'
}
