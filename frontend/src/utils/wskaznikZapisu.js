// Opcje toastu sukcesu po zapisie pojedynczego pola dokumentu (setValue w
// useDocument, frontend/src/data/document.js).
//
// Powod: uwaga 6 z klik-testu wlasciciela (2026-09-24). Domyslny toast
// frappe-ui/vue-sonner ("Dokument zaktualizowany pomyslnie", pasek 360 px,
// 4 s, prawy dolny rog, z przyciskiem X) zaslanial przycisk "Komentarze" na
// dole panelu "Szybki podglad" (frontend/src/components/LeadSzybkiPodglad.vue,
// szerokosc 340 px) na mapie leadow, wiec szybko klikajaca osoba musiala
// zamykac komunikat albo czekac. Decyzja wlasciciela: zamiast paska z
// tekstem, mala ikonka sukcesu (sam checkmark), znikajaca szybko, ktora nie
// blokuje klikania pod soba.
//
// Opcje ponizej trafiaja do vue-sonner 1:1 przez toast.success(msg, data) z
// frappe-ui (node_modules/frappe-ui/src/components/Toast/toast.ts, funkcja
// dispatch) -- bez zadnego patcha. vue-sonner honoruje per-toast: duration,
// closeButton, dismissible, classes (scalane z klasami providera) oraz
// inline style.

export const WSKAZNIK_ZAPISU_MS = 800

/**
 * Zwraca nowy obiekt opcji dla toast.success() przy kazdym wywolaniu
 * (niemutowalnosc, zgodnie z konwencja projektu).
 */
export function opcjeWskaznikaZapisu() {
  return {
    duration: WSKAZNIK_ZAPISU_MS,
    closeButton: false,
    dismissible: false,
    // Inline style nadpisuje w-[360px] py-2.5 px-4 z ToastProvider.vue bez
    // polegania na kolejnosci CSS. pointer-events: none dziedziczy sie w
    // glab wszystkich dzieci, wiec klik przechodzi na to, co lezy pod spodem
    // (np. przycisk "Komentarze" w LeadSzybkiPodglad.vue).
    style: { width: 'auto', minWidth: 0, padding: '6px 8px', pointerEvents: 'none' },
    classes: { icon: '!mr-0' },
  }
}
