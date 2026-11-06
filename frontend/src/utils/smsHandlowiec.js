// Panel "SMS do handlowcow" (PLAN-SMS-HANDLOWIEC.md, sekcja 9): czysty JS bez frappe-ui,
// lustro czesci crm/volteo_sms_handlowiec.py i kontraktu crm/api/sms_handlowiec_panel.py.

// Trzy szablony: typ = parametr `typ` SMS testowego, pole = klucz w STAN i w zapisie
export const SZABLONY = [
  { typ: 'nowe', pole: 'tresc_handlowiec_nowe', etykieta: 'Nowe spotkanie' },
  {
    typ: 'zmiana',
    pole: 'tresc_handlowiec_zmiana',
    etykieta: 'Zmiana terminu',
  },
  {
    typ: 'odwolanie',
    pole: 'tresc_handlowiec_odwolanie',
    etykieta: 'Odwołanie albo przekazanie innej osobie',
  },
]

export const POLA_SZABLONOW = SZABLONY.map((s) => s.pole)
export const POLE_LIMITU = 'limit_dzienny_handlowiec'
export const POLA_FLAG = [
  'handlowiec_wlaczone',
  'handlowiec_odwolanie_wlaczone',
]
export const LIMIT_MAX = 1000

// Formularz (tylko pola zapisywane przyciskiem) ze STAN zwroconego przez API
export function formularzZeStanu(stan) {
  const wynik = {}
  for (const pole of POLA_SZABLONOW) wynik[pole] = String(stan?.[pole] ?? '')
  wynik[POLE_LIMITU] = stan?.[POLE_LIMITU] ?? 0
  return wynik
}

function flaga(wartosc) {
  return Number(wartosc) ? 1 : 0
}

// Ladunek dla volteo_sms_handlowiec_zapisz: tylko pola rozne od zapisanych.
// Flagi jako 0/1, limit jako liczba, szablony jako tekst; pusty obiekt = nic do zapisu.
export function zmienionePola(formularz, zapisane) {
  const wynik = {}
  for (const pole of POLA_FLAG) {
    if (formularz?.[pole] === undefined) continue
    if (flaga(formularz[pole]) !== flaga(zapisane?.[pole]))
      wynik[pole] = flaga(formularz[pole])
  }
  for (const pole of POLA_SZABLONOW) {
    if (formularz?.[pole] === undefined) continue
    const tresc = String(formularz[pole] ?? '')
    if (tresc !== String(zapisane?.[pole] ?? '')) wynik[pole] = tresc
  }
  if (formularz?.[POLE_LIMITU] !== undefined) {
    const nowy = String(formularz[POLE_LIMITU] ?? '').trim()
    if (nowy !== String(zapisane?.[POLE_LIMITU] ?? '').trim())
      wynik[POLE_LIMITU] = Number(nowy)
  }
  return wynik
}

export function czySaZmiany(formularz, zapisane) {
  return Object.keys(zmienionePola(formularz, zapisane)).length > 0
}

// Komunikat bledu po polsku albo null; lustro waliduj_szablon z crm/volteo_sms.py
export function walidujSzablon(tresc, placeholdery) {
  if (!String(tresc ?? '').trim()) return 'Treść SMS nie może być pusta.'
  const znane = placeholdery || []
  for (const m of String(tresc).matchAll(/\{(\w+)\}/g)) {
    if (!znane.includes(m[1])) {
      const dozwolone = znane.map((p) => `{${p}}`).join(', ')
      return `Nieznany placeholder {${m[1]}}. Dozwolone: ${dozwolone}.`
    }
  }
  return null
}

// Komunikat bledu albo null; limit 0..1000 (0 blokuje wysylke), lustro waliduj_limit_handlowiec
export function walidujLimit(limit) {
  const n = Number(limit)
  if (
    String(limit ?? '').trim() === '' ||
    !Number.isInteger(n) ||
    n < 0 ||
    n > LIMIT_MAX
  ) {
    return `Limit dzienny musi być liczbą od 0 do ${LIMIT_MAX} (0 blokuje wysyłkę).`
  }
  return null
}

// Najpierw bez poprawnego numeru, potem z linia Leady, potem po imieniu (jak _handlowcy w API)
export function sortujHandlowcow(lista) {
  return [...(lista || [])].sort((a, b) => {
    const okA = a?.numer_ok ? 1 : 0
    const okB = b?.numer_ok ? 1 : 0
    if (okA !== okB) return okA - okB
    const liniaA = a?.linia_leady ? 0 : 1
    const liniaB = b?.linia_leady ? 0 : 1
    if (liniaA !== liniaB) return liniaA - liniaB
    const nazwaA = String(a?.imie_nazwisko || a?.uzytkownik || '').toLowerCase()
    const nazwaB = String(b?.imie_nazwisko || b?.uzytkownik || '').toLowerCase()
    return nazwaA.localeCompare(nazwaB, 'pl')
  })
}

// Stan numeru handlowca: { kod: 'brak' | 'niepoprawny' | 'ok', etykieta, blad }
export function stanNumeru(handlowiec) {
  const numer = String(handlowiec?.mobile_no ?? '').trim()
  if (!numer) return { kod: 'brak', etykieta: 'Brak numeru', blad: true }
  if (!handlowiec?.numer_ok)
    return { kod: 'niepoprawny', etykieta: 'Niepoprawny numer', blad: true }
  return { kod: 'ok', etykieta: 'Numer poprawny', blad: false }
}

export function liczBezNumeru(lista) {
  return (lista || []).filter((h) => stanNumeru(h).blad).length
}

// "1 część" / "2 części" / "5 części"
export function odmianaCzesci(czesci) {
  return Number(czesci) === 1 ? 'część' : 'części'
}

// "98 znaków GSM-7, 1 część SMS"
export function opisCzesci(dlugosc, czesci) {
  const n = Number(czesci) || 1
  return `${Number(dlugosc) || 0} znaków GSM-7, ${n} ${odmianaCzesci(n)} SMS`
}

// Ostrzezenie przy 2 i wiecej czesciach; serwer daje wlasne, to jest zapas
export function ostrzezenieCzesci(czesci) {
  const n = Number(czesci) || 1
  if (n < 2) return null
  return `Treść zajmie ${n} ${odmianaCzesci(n)} SMS, SMSAPI policzy ją jak ${n} wiadomości.`
}

// "SMS-y wychodzą od 08:00 do 21:00, później czekają do rana."
export function opisCiszyNocnej(ciszaOd, ciszaDo) {
  if (!ciszaOd || !ciszaDo) return null
  return `SMS-y wychodzą od ${ciszaDo} do ${ciszaOd}, później czekają do rana.`
}

// Dzisiejsze zuzycie limitu; wyslane null = Redis niedostepny
export function opisLicznikaDnia(wyslane, limit) {
  const l = Number(limit) || 0
  if (l === 0) return 'Limit 0: wysyłka SMS do handlowców zablokowana.'
  if (wyslane === null || wyslane === undefined) {
    return `Dziś wysłano: brak danych (licznik niedostępny). Limit: ${l}.`
  }
  return `Dziś wysłano ${Number(wyslane) || 0} z ${l}.`
}

// "{termin} (np. pt. 07.11 14:30)" dla kazdego placeholdera
export function listaPlaceholderow(placeholdery, przyklady) {
  return (placeholdery || []).map((p) => {
    const przyklad = przyklady?.[p]
    return przyklad ? `{${p}} (np. ${przyklad})` : `{${p}}`
  })
}

// Wynik SMS testowego z odpowiedzi {ok, powod, tryb_testowy}: { ok, tekst }
export function wynikTestu(data) {
  if (data?.ok) {
    return {
      ok: true,
      tekst: data.tryb_testowy
        ? 'Tryb testowy SMSAPI: treść poprawna, nic nie wysłano.'
        : 'SMS testowy wysłany na Twój numer.',
    }
  }
  return {
    ok: false,
    tekst: data?.powod || 'Nie udało się wysłać SMS testowego.',
  }
}

// Komunikat z rzuconego bledu createResource (frappe.throw) albo domyslny.
// Celowo bez err.message: frappe-ui sklada tam URL i typ wyjatku, nie tekst dla czlowieka.
export function komunikatBledu(err, domyslny) {
  const z = err?.messages?.[0]
  return z ? String(z) : domyslny
}
