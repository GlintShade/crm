// VOLTEO (ops#329): wspolny lookup kodu pocztowego dla panelu leada.
// Logika i testy: utils/kodPocztowy.js. Front woła API pelna sciezka.
import { call } from 'frappe-ui'
import { utworzLookup, uzupelnijAdresZKodu } from '@/utils/kodPocztowy'

export const pobierzDaneKodu = utworzLookup((kod) =>
  call('crm.api.kod_pocztowy.wyszukaj', { kod }),
)

export function uzupelnijAdresLeadaZKodu(doc) {
  return uzupelnijAdresZKodu(doc, pobierzDaneKodu)
}
