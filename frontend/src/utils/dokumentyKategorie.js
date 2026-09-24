// Logika czysta (bez importu z barrela @/utils, bez frappe-ui, bez __() na
// poziomie modułu -- ten sam powód co w utils/aktualizacje.js: __() wolno
// wywoływać tylko wewnątrz komponentu) grupowania dokumentów biblioteki OZE
// (`DokumentyLista.vue`) po kategorii (`Volteo Dokument.kategoria`, ops#179
// Faza 2).
//
// Kontrakt: serwer (`crm.api.dokumenty.dokumenty_lista`) już sortuje wiersze
// po `kolejnosc, tytul` -- ten moduł tylko GRUPUJE gotowo posortowaną listę,
// nie sortuje jej ponownie ani nie zmienia kolejności wewnątrz grupy.

/**
 * Grupuje dokumenty po kategorii, w kolejności podanej listy `kategorie`
 * (NIE w kolejności pierwszego wystąpienia w `dokumenty`). Puste grupy
 * (kategoria z listy, do której nie trafił żaden dokument) są pomijane.
 * Dokumenty z pustą albo nieznaną kategorią (spoza `kategorie`) trafiają do
 * jednej dodatkowej grupy `{ kategoria: '' }`, zawsze na końcu wyniku, i
 * tylko wtedy, gdy taki dokument w ogóle istnieje.
 *
 * Nie mutuje `dokumenty` ani `kategorie`. `kategorie`/`dokumenty` puste albo
 * `undefined`/`null` traktowane są jak `[]`.
 *
 * @param {Array<object>} dokumenty - wiersze dokumentów (kształt z serwera),
 *   każdy z polem `kategoria` (string, może być puste).
 * @param {Array<string>} kategorie - opcje kategorii w pożądanej kolejności
 *   wyświetlania (z `kategorie_opcje` odpowiedzi listy).
 * @returns {Array<{ kategoria: string, dokumenty: Array<object> }>}
 */
export function grupujDokumenty(dokumenty, kategorie) {
  const listaDokumentow = dokumenty || []
  const listaKategorii = kategorie || []

  const wgKategorii = new Map()
  const pozostale = []

  for (const dokument of listaDokumentow) {
    const kategoria = dokument.kategoria || ''
    if (kategoria && listaKategorii.includes(kategoria)) {
      if (!wgKategorii.has(kategoria)) wgKategorii.set(kategoria, [])
      wgKategorii.get(kategoria).push(dokument)
    } else {
      pozostale.push(dokument)
    }
  }

  const grupy = []
  for (const kategoria of listaKategorii) {
    const wDokumenty = wgKategorii.get(kategoria)
    if (wDokumenty && wDokumenty.length) {
      grupy.push({ kategoria, dokumenty: wDokumenty })
    }
  }

  if (pozostale.length) {
    grupy.push({ kategoria: '', dokumenty: pozostale })
  }

  return grupy
}
