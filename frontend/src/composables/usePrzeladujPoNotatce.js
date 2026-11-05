// Zadanie J: "Czas do pierwszego kontaktu" ma sie zaktualizowac na zywo po
// dodaniu notatki, bez odswiezania strony -- u autora notatki, nawet zanim
// dotrze sygnal realtime z backendu.
//
// Backend (crm/api/czas_kontaktu.py, Comment.after_insert) zapisuje
// CRM Lead.custom_czas_do_kontaktu przez frappe.db.set_value w tym samym
// requeście co dodanie notatki, wiec zanim ten request sie skonczy, pole
// jest juz zapisane. Ten composable przeladowuje dokument leada ~1 s po
// wspolnym sygnale `wersjaKomentarzy` (utils/notatkiLeada.js) -- tym samym,
// ktory juz odpala sie z sekcji Notatki zakladki Szczegoly, karty Notatki w
// prawym panelu, popupu komentarzy i zakladki Aktywnosc, niezaleznie od
// tego, ktore z tych miejsc dodalo notatke.
//
// Dla innych osob patrzacych na tego samego leada w tym samym momencie
// odswieza go sygnal realtime backendu (`_powiadom_realtime` w
// crm/api/czas_kontaktu.py) -- obsluguje go juz `useDocument()` z
// frontend/src/data/document.js (`createDocumentResource` z `frappe-ui`,
// `realtime: true` nasluchuje `list_update` i samo dociaga dokument, gdy
// `{doctype, name}` pasuje do otwartego), wiec nie trzeba tu duplikowac
// nasluchiwania na socket.
//
// Seria notatek w krotkim odstepie (np. dwie notatki pod rzad) daje jedno
// przeladowanie, nie jedno na notatke -- kazdy kolejny sygnal przesuwa
// odliczanie.
import { onBeforeUnmount, watch } from 'vue'
import { wersjaKomentarzy } from '@/utils/notatkiLeada'

export const OPOZNIENIE_PRZELADOWANIA_MS = 1000

/**
 * @param {object} opcje
 * @param {string} [opcje.doctype] - domyslnie 'CRM Lead'.
 * @param {() => string} opcje.docname - getter, bo leadId moze sie zmienic
 *   (np. inny lead w tym samym komponencie przy cache'owanym useDocument()).
 * @param {() => void} opcje.reload - wywolywane po opoznieniu, np.
 *   `() => document.reload()` z useDocument().
 * @param {number} [opcje.opoznienieMs] - domyslnie OPOZNIENIE_PRZELADOWANIA_MS.
 */
export function usePrzeladujPoNotatce({
  doctype = 'CRM Lead',
  docname,
  reload,
  opoznienieMs = OPOZNIENIE_PRZELADOWANIA_MS,
}) {
  let timer = null

  function posprzataj() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  // flush: 'sync' -- bez tego Vue odpala watcher dopiero w kolejnym
  // mikrozadaniu (kolejka reaktywnosci), tu bez znaczenia dla UI, za to
  // dzieki temu dzialanie jest deterministyczne (testy bez oczekiwania na
  // nextTick/flushPromises).
  const zatrzymajObserwator = watch(
    () => wersjaKomentarzy(doctype, docname()),
    (nowa, stara) => {
      if (nowa === stara) return
      posprzataj()
      timer = setTimeout(() => {
        timer = null
        reload?.()
      }, opoznienieMs)
    },
    { flush: 'sync' },
  )

  onBeforeUnmount(() => {
    posprzataj()
    zatrzymajObserwator()
  })
}
