// VOLTEO (ops#329): lookup kodu pocztowego w panelu leada. Czyste funkcje
// (testy: kodPocztowy.test.js) plus fabryka lookupu z pamiecia per kod;
// samo wywolanie API jest wstrzykiwane, domyslne siedzi w
// data/kodPocztowy.js (pobierzDaneKodu, uzupelnijAdresLeadaZKodu).
//
// API: crm.api.kod_pocztowy.wyszukaj -> { found, wojewodztwo, powiat, gmina,
// miejscowosc, cities } (ten sam ksztalt co dawny Server Script volteo_postal_lookup;
// od ops#329 wolaja to tez ContactModal.vue i DaneKlientaTab.vue).

export const WZOR_KODU_POCZTOWEGO = /^\d{2}-\d{3}$/

export const POLE_KODU = 'custom_install_postal_code'
export const POLE_MIEJSCOWOSCI = 'custom_install_city'
export const POLE_GMINY = 'custom_gmina'

function tekst(v) {
  return v === null || v === undefined ? '' : String(v).trim()
}

export function czyKodPocztowy(v) {
  return WZOR_KODU_POCZTOWEGO.test(tekst(v))
}

// Lista miejscowosci dla kodu: tylko `cities` (bez duplikatow i pustych).
// Bez zgadywania z `miejscowosc`: GeoNames trzyma jedna na kod, czesto nie
// ta (ops#306), wiec bez listy nie ma czego podpowiadac.
export function listaMiejscowosci(wynik) {
  if (!wynik?.found || !Array.isArray(wynik.cities)) return []
  const lista = []
  for (const c of wynik.cities) {
    const t = tekst(c)
    if (t && !lista.includes(t)) lista.push(t)
  }
  return lista
}

// Czy pokazac rozwijana liste: jest z czego wybrac poza obecna wartoscia.
export function czyPokazacListe(lista, wartosc) {
  if (!lista?.length) return false
  return !(lista.length === 1 && lista[0] === tekst(wartosc))
}

// Zmiany pol leada po lookupie kodu. Wojewodztwo, powiat i gmina zawsze z
// kodu (gmina tylko, gdy dokument ma takie pole). Miejscowosc tylko, gdy
// kod ma DOKLADNIE jedna, a pole jest puste: recznie wpisanej (albo
// wybranej) wartosci nie nadpisujemy. Zwraca tylko pola, ktore sie zmieniaja.
export function latkaAdresuZKodu(doc, wynik) {
  if (!doc || !wynik?.found) return {}
  const latka = {}
  const ustaw = (pole, wartosc) => {
    const t = tekst(wartosc)
    if (t && t !== tekst(doc[pole])) latka[pole] = t
  }
  ustaw('custom_voivodeship', wynik.wojewodztwo)
  ustaw('custom_powiat', wynik.powiat)
  if (Object.hasOwn(doc, POLE_GMINY)) ustaw(POLE_GMINY, wynik.gmina)
  const lista = listaMiejscowosci(wynik)
  if (lista.length === 1 && !tekst(doc[POLE_MIEJSCOWOSCI])) {
    latka[POLE_MIEJSCOWOSCI] = lista[0]
  }
  return latka
}

// "Ukryj puste pola" (ops#329): pusta, edytowalna Miejscowosc leada zostaje
// widoczna, gdy kod leada ma liste miejscowosci do wyboru (wtedy jest
// najbardziej potrzebna). Bez listy ukrywa sie jak kazde puste pole.
// `listaDlaKodu` to funkcja: wolana dopiero dla pola Miejscowosc leada, zeby
// inne puste pola nie uruchamialy lookupu.
export function czyPokazacPustaMiejscowosc(doctype, field, listaDlaKodu) {
  if (doctype !== 'CRM Lead' || field?.fieldname !== POLE_MIEJSCOWOSCI) {
    return false
  }
  if (field.read_only) return false
  const lista = listaDlaKodu()
  return Array.isArray(lista) && lista.length > 0
}

export const BRAK_WYNIKU = Object.freeze({ found: false, cities: [] })

// Lookup z pamiecia per kod: wspolna obietnica dla wszystkich instancji
// panelu (Lead.vue renderuje dwa SidePanelLayout na tym samym leadzie).
// Blad API nie zostaje w pamieci (kolejna proba pyta ponownie) i nigdy nie
// wychodzi na zewnatrz: wynik to BRAK_WYNIKU. `poWyniku(kod, wynik)` (opcja)
// dostaje kazdy udany wynik, raz na kod (np. do reaktywnej pamieci list).
export function utworzLookup(wywolaj, poWyniku = null) {
  const pamiec = new Map()
  return function pobierz(kod) {
    const k = tekst(kod)
    if (!czyKodPocztowy(k)) return Promise.resolve(BRAK_WYNIKU)
    if (!pamiec.has(k)) {
      const obietnica = Promise.resolve()
        .then(() => wywolaj(k))
        .then((w) => {
          const wynik = w || BRAK_WYNIKU
          if (poWyniku) poWyniku(k, wynik)
          return wynik
        })
        .catch(() => {
          pamiec.delete(k)
          return BRAK_WYNIKU
        })
      pamiec.set(k, obietnica)
    }
    return pamiec.get(k)
  }
}

// Po zmianie kodu w panelu: lookup i uzupelnienie dokumentu w miejscu (zapis
// robi wolajacy). Gdy kod zmienil sie w trakcie zapytania, nic nie zmienia.
export async function uzupelnijAdresZKodu(doc, pobierz) {
  const kod = tekst(doc?.[POLE_KODU])
  if (!czyKodPocztowy(kod)) return {}
  const wynik = await pobierz(kod)
  if (tekst(doc[POLE_KODU]) !== kod) return {}
  const latka = latkaAdresuZKodu(doc, wynik)
  Object.assign(doc, latka)
  return latka
}
