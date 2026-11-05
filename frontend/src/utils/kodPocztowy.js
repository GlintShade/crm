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

// Sentinel opcji "Recznie" w liscie miejscowosci (nie moze wystapic jako
// prawdziwa nazwa miejscowosci -- nie trafia nigdy do pola dokumentu).
export const WARTOSC_RECZNIE = '__recznie__'

// Etykieta opcji "Recznie": funkcja (nie stala modulu), bo wola `__()`,
// ktore Vue plugin i18n podpina na `window` dopiero przy starcie aplikacji
// (PULAPKA eager chunk -- patrz etapFiltr.js); wywolanie wewnatrz funkcji
// jest bezpieczne, bo funkcja dziala dopiero w trakcie renderu.
export function etykietaRecznie() {
  return __('Ręcznie')
}

// Opcje pola Miejscowosc/Miasto dla kodu pocztowego: miejscowosci z listy
// kodu (kolejnosc jak w `lista`), do tego biezaca wartosc pola, gdy jest
// niepusta i nie ma jej na liscie (stara albo recznie wpisana wartosc --
// dzieki temu select zawsze ma czym pokazac aktualny wpis, patrz
// ContactModal.vue/DaneKlientaTab.vue, ktore robily to samo osobno przed
// ops#329), a na samym koncu ZAWSZE opcja "Recznie" (decyzja wlasciciela:
// pole nigdy nie wybiera miejscowosci samo, wiec zejscie do wolnego tekstu
// musi byc zawsze dostepne). Pusta `lista` -> pusta lista opcji (kod bez
// listy miejscowosci: wolajacy pokazuje zwykle pole tekstowe, patrz
// `trybPolaMiejscowosci`).
export function opcjeMiejscowosci(lista, wartosc) {
  if (!lista?.length) return []
  const biezaca = tekst(wartosc)
  const miasta = biezaca && !lista.includes(biezaca) ? [...lista, biezaca] : lista
  return [
    ...miasta.map((m) => ({ label: m, value: m })),
    { label: etykietaRecznie(), value: WARTOSC_RECZNIE },
  ]
}

// Tryb renderowania pola: 'lista' (rozwijana lista miejscowosci + "Recznie")
// albo 'tekst' (zwykle pole do wpisania). Bez listy dla kodu zawsze 'tekst'
// (kod nieznany/pusty, "jak dotad"); z lista domyslnie 'lista', chyba ze
// uzytkownik wybral "Recznie" (stan `recznieWybrane`, trzyma go wolajacy --
// to jedyny stan UI w tej funkcji, reszta jest czysto pochodna od `lista`).
export function trybPolaMiejscowosci(lista, recznieWybrane) {
  return lista?.length && !recznieWybrane ? 'lista' : 'tekst'
}

// Zadanie N (ops#329): czy po zmianie kodu miejscowosc powinna zostac
// wyczyszczona. Czysta funkcja, patrzy wylacznie na biezaca wartosc pola i
// liste miejscowosci NOWEGO kodu (juz po listaMiejscowosci, nie surowy
// wynik API) -- zero zaleznosci od ksztaltu `wynik`, wiec ta sama funkcja
// sluzy leadowi (przez latkaAdresuZKodu nizej) i kontaktowi (ContactModal.vue
// / DaneKlientaTab.vue woluja ja wprost, bo tam pole wojewodztwa ma inna
// nazwe niz w leadzie, wiec cala latkaAdresuZKodu nie pasuje). Reguly
// wlasciciela z klik-testu: nowy kod ma liste i biezacej miejscowosci NIE MA
// na niej -> true (czysci); jest na liscie -> false (zostaje); kod bez
// listy -> false (zostaje, nowy kod niczego nie podpowiada, wiec stara
// wartosc zostaje jak przy recznym wpisie); pusta miejscowosc -> false (nie
// ma czego czyscic).
export function czyWyczyscicMiejscowosc(biezaca, listaNowegoKodu) {
  const t = tekst(biezaca)
  if (!t) return false
  const lista = Array.isArray(listaNowegoKodu) ? listaNowegoKodu : []
  return lista.length > 0 && !lista.includes(t)
}

// Zmiany pol leada po lookupie kodu. Wojewodztwo, powiat i gmina zawsze z
// kodu (gmina tylko, gdy dokument ma takie pole). Miejscowosc NIGDY nie jest
// WPISYWANA samemu (decyzja wlasciciela, ops#329): nawet kod z dokladnie
// jedna miejscowoscia na liscie zostawiamy do recznego wyboru w panelu
// (lista + "Recznie"). Zadanie N (ops#329, "czyszczenie po zmianie kodu"):
// gdy wolajacy poda `poleMiejscowosci` (nazwa pola, np. POLE_MIEJSCOWOSCI
// dla leada), a biezaca wartosc tego pola nie pasuje do listy nowego kodu
// (czyWyczyscicMiejscowosc powyzej), latka dostaje to pole wyczyszczone do
// ''. Bez trzeciego argumentu miejscowosc zostaje calkowicie nietknieta
// (zachowanie sprzed Zadania N, dalej uzywane tam, gdzie nazwa pola
// wojewodztwa/powiatu zaszyta ponizej nie pasuje do doctype'u). Zwraca
// tylko pola, ktore sie zmieniaja.
export function latkaAdresuZKodu(doc, wynik, poleMiejscowosci) {
  if (!doc || !wynik?.found) return {}
  const latka = {}
  const ustaw = (pole, wartosc) => {
    const t = tekst(wartosc)
    if (t && t !== tekst(doc[pole])) latka[pole] = t
  }
  ustaw('custom_voivodeship', wynik.wojewodztwo)
  ustaw('custom_powiat', wynik.powiat)
  if (Object.hasOwn(doc, POLE_GMINY)) ustaw(POLE_GMINY, wynik.gmina)
  if (
    poleMiejscowosci &&
    czyWyczyscicMiejscowosc(doc[poleMiejscowosci], listaMiejscowosci(wynik))
  ) {
    latka[poleMiejscowosci] = ''
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
// `poleMiejscowosci` (opcjonalny) przechodzi wprost do latkaAdresuZKodu
// (Zadanie N): podany, wyczysci miejscowosc, gdy nie pasuje do nowej listy.
export async function uzupelnijAdresZKodu(doc, pobierz, poleMiejscowosci) {
  const kod = tekst(doc?.[POLE_KODU])
  if (!czyKodPocztowy(kod)) return {}
  const wynik = await pobierz(kod)
  if (tekst(doc[POLE_KODU]) !== kod) return {}
  const latka = latkaAdresuZKodu(doc, wynik, poleMiejscowosci)
  Object.assign(doc, latka)
  return latka
}
