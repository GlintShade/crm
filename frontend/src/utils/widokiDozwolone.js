// Logika czysta (bez importu frappe-ui / @, bez __()) do ukrywania
// zapisanych widokow, ktorych filtry odwoluja sie do pola spoza
// permlevel biezacego uzytkownika (headless G5, klik-test wlasciciela
// 2026-09-10). Handlowiec (`Volteo D2D Sales`) nie ma odczytu
// `custom_cc` (permlevel 2, patrz WORKSHOP.md "Leady dla CC") - widok
// publiczny "Do obdzwonienia" filtrujacy po tym polu wywolywal 403 z
// `crm.api.doc.get_data` po kliknieciu, z pusta tabela i bez komunikatu
// (backend odrzuca poprawnie, ale front pokazywal chip prowadzacy w
// slepy zaulek).
//
// `dozwolonePola` to lista nazw pol z `crm.api.doc.pola_dozwolone(doctype)`
// (ten sam endpoint co `ColumnSettings.vue` uzywa dla okna "Kolumny") -
// wywolujacy (ViewControls.vue, WidokiLeadowPasek.vue) laduje ja RAZ per
// doctype (`createResource` z `cache: ['PolaDozwolone', doctype]`) i
// przekazuje tutaj. Brak listy (jeszcze nie zaladowana, `null`/`undefined`)
// oznacza "nie ukrywaj" - to jest wylacznie kosmetyczny filtr UI, prawdziwe
// bezpieczenstwo egzekwuje serwer (`_pola_dozwolone` w `crm/api/doc.py`),
// wiec przy braku danych lepiej pokazac widok niz falszywie go schowac.
//
// Frappe-free, testowalne bezposrednio przez vitest.

import { wydzielGrupy } from './grupyFiltrow'

/**
 * Parsuje `view.filters` do zwyklego obiektu. Akceptuje string JSON
 * (ksztalt sieciowy `CRM View Settings.filters`) lub juz sparsowany
 * obiekt (ViewControls.vue mutuje `view.filters` w miejscu przy
 * pierwszym uzyciu `viewsDropdownOptions` - kolejnosc niepewna, wiec ta
 * funkcja akceptuje oba ksztalty). JSON niepoprawny lub wartosc nie
 * bedaca obiektem zwraca pusty obiekt (brak kluczy do sprawdzenia =
 * widok przechodzi) - to NIE jest bezpiecznik bezpieczenstwa, wiec
 * blad parsowania nie ma prawa ukryc widoku, ktory moze byc calkiem
 * poprawny.
 */
function sparsujFiltry(filtry) {
  if (!filtry) return {}
  if (typeof filtry === 'object') return filtry
  if (typeof filtry !== 'string') return {}
  try {
    const sparsowane = JSON.parse(filtry)
    return sparsowane && typeof sparsowane === 'object' ? sparsowane : {}
  } catch (e) {
    return {}
  }
}

/**
 * Czy `view` (zapisany widok, ksztalt `CRM View Settings`) wolno
 * zaoferowac biezacemu uzytkownikowi - czy wszystkie klucze filtrow
 * (gorny poziom ORAZ klucze wewnatrz kazdej grupy `volteo_grupy`, patrz
 * `wydzielGrupy` w `grupyFiltrow.js`) miesza sie w `dozwolonePola`.
 *
 * `dozwolonePola` brakujace/puste (jeszcze niezaladowane z serwera) =
 * zawsze dozwolony, patrz naglowek modulu.
 */
export function czyWidokDozwolony(view, dozwolonePola) {
  if (!Array.isArray(dozwolonePola) || dozwolonePola.length === 0) return true

  const dozwolone = new Set(dozwolonePola)
  const filtry = sparsujFiltry(view?.filters)
  const { filtryWspolne, grupy } = wydzielGrupy(filtry)

  const klucze = [
    ...Object.keys(filtryWspolne || {}),
    ...(grupy || []).flatMap((grupa) => Object.keys(grupa || {})),
  ]

  return klucze.every((klucz) => dozwolone.has(klucz))
}
