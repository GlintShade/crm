// Sizing/selection helpers for the PV/storage quote builder (KalkulatorTab.vue).
// Pure, frappe-free display-level heuristics — no pricing math here, that
// stays server-side. Mirrors the style of cpForm.js.

export const VARIANT_PV = 'Fotowoltaika'
export const VARIANT_PV_BAT = 'Fotowoltaika + Magazyn'
export const VARIANT_BAT = 'Magazyn energii'
export const VARIANTS = [VARIANT_PV, VARIANT_PV_BAT, VARIANT_BAT]

export const PV_OVERSIZE_RATIO = 1.4 // sama PV: produkcja celowa = 140% zużycia
export const KWH_PER_KWP = 1000 // przyjęty roczny uzysk z 1 kWp
export const MOC_MIN_KW = 3
export const MOC_MAX_KW = 20
// Minimalna liczba paneli w instalacji (ops#292). Lustro literalu 6 w Server
// Scripcie `volteo_quote_calc` (`ops/crm-kalkulator-bom.py`).
export const MIN_PANELI = 6
export const MOC_STEP_KW = 0.5

/**
 * Zaokrągla wartość do najbliższej połówki (siatka mocy PV co 0,5 kW).
 *
 * @param {number} x - wartość wejściowa
 * @returns {number} wartość zaokrąglona do 0,5
 */
export function roundHalf(x) {
  return Math.round(x * 2) / 2
}

/**
 * Ogranicza wartość do przedziału [lo, hi].
 *
 * @param {number} v - wartość wejściowa
 * @param {number} lo - dolna granica
 * @param {number} hi - górna granica
 * @returns {number} wartość ograniczona do przedziału
 */
export function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

/**
 * Sprawdza, czy dany wariant obejmuje instalację fotowoltaiczną.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy wariant zawiera PV
 */
export function variantHasPv(variant) {
  return variant === VARIANT_PV || variant === VARIANT_PV_BAT
}

/**
 * Sprawdza, czy dany wariant obejmuje magazyn energii.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy wariant zawiera magazyn
 */
export function variantHasBattery(variant) {
  return variant === VARIANT_PV_BAT || variant === VARIANT_BAT
}

// Zestawy OZE dla wariantów z magazynem (ops#291). Jedno źródło prawdy po
// stronie frontu: zestaw wyznacza producenta falownika i magazynu. Lustro w
// Server Scripcie `ops/crm-kalkulator-bom.py` (literal dict ZESTAWY_PRODUCENT,
// Server Script nie importuje), w `Volteo Komponent.zestaw_typ` i w
// `CRM Deal.custom_zestaw_typ`. `opis` to wyłącznie tekst pod przyciskiem:
// "gwarancja rachunku 49 zł/mies." to gwarancja handlowa, NIE koszt, żadnej
// stałej ani pozycji kosztowej za nią nie ma. Dodanie czwartego wyboru (np.
// Deye) to jedna pozycja tutaj plus jedna w literalu serwera.
export const ZESTAWY = [
  { kod: 'COMFORT', producent: 'Hoymiles', opis: 'Hoymiles' },
  { kod: 'COMFORT PREMIUM', producent: 'Solax', opis: 'Solax, gwarancja rachunku 49 zł/mies.' },
  { kod: 'COMFORT +', producent: 'Sigenergy', opis: 'Sigenergy' },
]
export const DOMYSLNY_ZESTAW = 'COMFORT +'
export const PRODUCENT_PV = 'FoxESS'

/**
 * Producent przypisany do zestawu; pusty string dla nieznanego zestawu.
 *
 * @param {string} zestaw - kod zestawu (COMFORT / COMFORT PREMIUM / COMFORT +)
 * @returns {string} nazwa producenta albo ''
 */
export function zestawProducent(zestaw) {
  return ZESTAWY.find((z) => z.kod === zestaw)?.producent || ''
}

/**
 * Zwraca listę dostępnych producentów dla danego wariantu i zestawu.
 * Sama fotowoltaika wymusza FoxESS; warianty z magazynem oferują wyłącznie
 * producenta wybranego zestawu (domyślnie zestawu domyślnego).
 *
 * @param {string} variant - wybrany wariant instalacji
 * @param {string} [zestaw] - wybrany zestaw (dla wariantów z magazynem)
 * @returns {string[]} dostępni producenci
 */
export function producentOptionsFor(variant, zestaw) {
  if (variant === VARIANT_PV) return [PRODUCENT_PV]
  return [zestawProducent(zestaw) || zestawProducent(DOMYSLNY_ZESTAW)]
}

/**
 * Sprawdza, czy dla danego producenta dostępny jest dodatek "Dodatkowy
 * licznik" (potrzebny przy zachowaniu starego falownika lub mikrofalowników).
 * Dostępny dla każdego falownika hybrydowego (Sigenergy, Deye, Hoymiles,
 * Solax), nigdy dla FoxESS. Lustro bramki w `volteo_quote_calc`.
 *
 * @param {string} producent - wybrany producent falownika
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function licznikDostepny(producent) {
  return ['Sigenergy', 'Deye', 'Hoymiles', 'Solax'].includes(producent)
}

// Threshold above which PPOZ (fire-protection utility agreements) become
// required: sum of the new installation's PV power plus any existing PV
// power the client already has. Deliberately duplicated in two other places
// that cannot import this module: `crm/volteo_umowa.py::ppoz_wymagane`
// (frappe-free but a separate module, mirrored for the contract tab) and the
// ops Server Script in `ops/crm-kalkulator-bom.py` (safe_exec, no imports
// allowed at all). Change all three together (ops#194).
export const PROG_PPOZ_KW = 6.5

/**
 * Sprawdza, czy sama suma mocy (nowa plus istniejąca) przekracza próg PPOŻ,
 * bez uwzględnienia ręcznego ustawienia ani kalkulatora OZE. Używane do
 * blokowania selecta "Uzgodnienia PPOŻ" na Tak, gdy próg jest przekroczony
 * (ops#194): `ppozWymagane` poniżej jest zbudowane na tej funkcji.
 *
 * @param {object} params
 * @param {number} params.mocNowaKw - moc nowej instalacji PV w kWp (0 dla wariantu bez PV)
 * @param {string} params.istniejacaPv - "Tak"/"Nie", czy klient ma już instalację PV
 * @param {number} params.mocIstniejacaKwp - moc istniejącej instalacji PV w kWp
 * @returns {boolean} czy sama suma mocy przekracza PROG_PPOZ_KW
 */
export function ppozWymuszonyProgiem({ mocNowaKw, istniejacaPv, mocIstniejacaKwp }) {
  const nowa = Number(mocNowaKw) || 0
  const istniejaca = istniejacaPv === 'Tak' ? Number(mocIstniejacaKwp) || 0 : 0
  return nowa + istniejaca > PROG_PPOZ_KW
}

/**
 * Sprawdza, czy uzgodnienia PPOŻ są wymagane dla danej konfiguracji.
 * WYŁĄCZNIE prezentacja: serwer pozostaje autorytatywny (patrz `ppoz` w
 * odpowiedzi `volteo_quote_calc`/`volteo_quote_generate`) i liczy tę samą
 * regułę niezależnie od tego, co pokazuje ten formularz. Lustrzane odbicie
 * `crm/volteo_umowa.py::ppoz_wymagane`, używane zarówno w KalkulatorTab.vue,
 * jak i w UmowaTab.vue (ta sama sygnatura, ops#194).
 *
 * @param {object} params
 * @param {number} params.mocNowaKw - moc nowej instalacji PV w kWp (0 dla wariantu bez PV)
 * @param {string} params.istniejacaPv - "Tak"/"Nie", czy klient ma już instalację PV
 * @param {number} params.mocIstniejacaKwp - moc istniejącej instalacji PV w kWp
 * @param {string} [params.ppozKalkulator] - "Tak"/"Nie", wynik kalkulatora OZE (jeśli już doliczył PPOŻ, umowa go dziedziczy)
 * @param {string} [params.ppozRecznie] - "Tak"/"Nie", ręczne ustawienie handlowca w kalkulatorze OZE; tylko "Tak" podnosi wynik, nigdy nie obniża go poniżej progu (ops#194)
 * @returns {boolean} czy PPOŻ jest wymagane
 */
export function ppozWymagane({ mocNowaKw, istniejacaPv, mocIstniejacaKwp, ppozKalkulator, ppozRecznie }) {
  if (ppozKalkulator === 'Tak') return true
  if (ppozRecznie === 'Tak') return true

  return ppozWymuszonyProgiem({ mocNowaKw, istniejacaPv, mocIstniejacaKwp })
}

/**
 * Buduje listę opcji mocy PV: MOC_MIN_KW–MOC_MAX_KW co MOC_STEP_KW, z etykietą
 * pokazującą szacowaną liczbę paneli (moc * 2). Wyłącznie prezentacja — nie
 * wylicza cen.
 *
 * Krok liczony w dziesiątych kW (liczby całkowite), żeby uniknąć błędów
 * zaokrągleń zmiennoprzecinkowych przy wielokrotnym dodawaniu 0,5 — takich
 * jak 7.000000000000001, które nie przejdą ścisłego porównania z wartością
 * opcji <select> ani z testami.
 *
 * @returns {{value: number, label: string}[]} opcje mocy PV
 */
export function buildMocOptions() {
  const out = []
  const stepTenths = Math.round(MOC_STEP_KW * 10)
  const minTenths = Math.round(MOC_MIN_KW * 10)
  const maxTenths = Math.round(MOC_MAX_KW * 10)
  for (let tenths = minTenths; tenths <= maxTenths; tenths += stepTenths) {
    const kw = tenths / 10
    out.push({ value: kw, label: `${kw} kW (${Math.round(kw * 2)} paneli)` })
  }
  return out
}

/**
 * Sugerowana moc instalacji PV na podstawie rocznego zużycia i wariantu.
 * Przy samej fotowoltaice nadwyżki produkcji idą do sieci, więc instalację
 * się przewymiarowuje (mnożnik 1,4). Przy PV + magazyn nadwyżkę zbiera
 * bateria, więc mnożnik zostaje 1 (bez przewymiarowania).
 *
 * @param {number} consumption - roczne zużycie energii w kWh
 * @param {string} variant - wybrany wariant instalacji
 * @returns {number} sugerowana moc PV w kW (0, gdy nie dotyczy)
 */
export function suggestedKwp(consumption, variant) {
  const cons = Number(consumption)
  if (!Number.isFinite(cons) || cons <= 0) return 0
  if (!variantHasPv(variant)) return 0

  const ratio = variant === VARIANT_PV ? PV_OVERSIZE_RATIO : 1
  return clamp(roundHalf((cons * ratio) / KWH_PER_KWP), MOC_MIN_KW, MOC_MAX_KW)
}

/**
 * Sugerowana pojemność magazynu energii na podstawie rocznego zużycia i mocy
 * PV. `kwp` jest jawnym argumentem (nie liczone z suggestedKwp wewnątrz), aby
 * przewymiarowanie ×1,4 przy samej fotowoltaice nie przeciekało do doboru
 * magazynu.
 *
 * @param {number} consumption - roczne zużycie energii w kWh
 * @param {number} kwp - moc instalacji PV w kW (bazowa, bez przewymiarowania)
 * @returns {number} sugerowana pojemność magazynu w kWh (0, gdy nie dotyczy)
 */
export function suggestedStorageKwh(consumption, kwp) {
  const cons = Number(consumption) || 0
  const kw = Number(kwp) || 0
  if (cons <= 0 || kw <= 0) return 0

  const daily = cons / 365
  const surplus = Math.max(0, kw * 4.5 - daily * 0.4) // 4.5 godz. słońca, 40% autokonsumpcji dziennej
  const nightNeed = daily * 0.6
  return clamp(Math.ceil(Math.min(surplus, nightNeed) * 1.2), 10, 60) // 1.2 zapasu
}

/**
 * Wybiera z listy komponent o najmniejszej wartości pola >= minValue;
 * jeśli żaden nie spełnia progu, zwraca komponent o największej wartości.
 * Nie mutuje przekazanej listy.
 *
 * @param {object[]} list - lista komponentów
 * @param {string} field - nazwa pola liczbowego do porównania
 * @param {number} minValue - minimalna wymagana wartość
 * @returns {object|undefined} wybrany komponent lub undefined dla pustej listy
 */
export function pickBySpec(list, field, minValue) {
  if (!list || list.length === 0) return undefined

  const sorted = [...list].sort((a, b) => Number(a[field]) - Number(b[field]))
  const match = sorted.find((item) => Number(item[field]) >= minValue)
  return match || sorted[sorted.length - 1]
}

/**
 * Wybiera konstrukcję montażową: preferuje nazwę zawierającą "blacha",
 * w innym wypadku pierwszą dostępną.
 *
 * @param {object[]} list - lista konstrukcji
 * @returns {object|undefined} wybrana konstrukcja lub undefined dla pustej listy
 */
export function pickMounting(list) {
  if (!list || list.length === 0) return undefined

  return (
    list.find((item) => (item.nazwa || '').toLowerCase().includes('blacha')) ||
    list[0]
  )
}

/**
 * Buduje etykietę panelu z nazwą, modelem i mocą.
 * Puste pola pomija, a moc dopisuje tylko dla dodatniej liczby skończonej.
 *
 * @param {object|null} row - dane panelu
 * @returns {string} etykieta panelu
 */
export function panelLabel(row) {
  if (!row) return ''

  const parts = [row.nazwa, row.model].filter(Boolean)
  const power = row.moc_wp
  const suffix = Number.isFinite(power) && power > 0 ? ` (${power} Wp)` : ''
  return `${parts.join(' ')}${suffix}`
}

/**
 * Karty paneli dostępne dla zestawu (ops#292). Zestaw z własnymi kartami
 * (`zestaw_typ` równe kodowi zestawu) widzi wyłącznie je; zestaw bez własnych
 * kart oraz sama fotowoltaika (pusty kod) widzą karty uniwersalne
 * (puste `zestaw_typ`).
 *
 * @param {Array<{zestaw_typ?: string}>} karty - aktywne karty Panel PV
 * @param {string} zestawTyp - kod zestawu albo '' dla samej PV
 * @returns {Array} karty do wyboru
 */
export function paneleDlaZestawu(karty, zestawTyp) {
  const lista = Array.isArray(karty) ? karty : []
  const wlasne = zestawTyp
    ? lista.filter((k) => (k?.zestaw_typ || '') === zestawTyp)
    : []
  if (wlasne.length) return wlasne
  return lista.filter((k) => !(k?.zestaw_typ || ''))
}

/**
 * Buduje listę mocy instalacji dopasowanych do mocy pojedynczego panelu.
 * Liczbę paneli wyznacza z granic MIN_PANELI (dolna) i MOC_MAX_KW (górna).
 *
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {{value: number, label: string, panele: number}[]} opcje mocy PV
 */
export function buildMocOptionsForPanel(wp) {
  if (!Number.isFinite(wp) || wp <= 0) return []

  const out = []
  const minPanels = MIN_PANELI
  const maxPanels = Math.floor((MOC_MAX_KW * 1000) / wp)
  if (
    !Number.isFinite(minPanels) ||
    !Number.isFinite(maxPanels) ||
    minPanels > maxPanels
  ) {
    return []
  }

  for (let panele = minPanels; panele <= maxPanels; panele += 1) {
    const value = (panele * wp) / 1000
    out.push({
      value,
      label: `${panele} paneli, ${value.toFixed(2)} kWp`,
      panele,
    })
  }
  return out
}

/**
 * Wybiera moc panelowej instalacji najbliższą podanej wartości.
 * Przy takiej samej odległości wybiera niższą moc.
 *
 * @param {number} kwp - docelowa moc instalacji w kWp
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {number|null} najbliższa dostępna moc lub null
 */
export function snapMocToPanel(kwp, wp) {
  if (!Number.isFinite(kwp) || kwp <= 0) return null

  const options = buildMocOptionsForPanel(wp)
  if (options.length === 0) return null

  let nearest = options[0].value
  let distance = Math.abs(nearest - kwp)
  for (const option of options.slice(1)) {
    const optionDistance = Math.abs(option.value - kwp)
    if (optionDistance < distance) {
      nearest = option.value
      distance = optionDistance
    }
  }
  return nearest
}

/**
 * Wybiera najmniejszą moc panelowej instalacji spełniającą cel.
 * Jeśli cel przekracza dostępne moce, zwraca największą dostępną moc.
 *
 * @param {number} targetKwp - docelowa moc instalacji w kWp
 * @param {number} wp - moc pojedynczego panelu w watach
 * @returns {number|null} wybrana moc lub null
 */
export function pickMocForTarget(targetKwp, wp) {
  if (!Number.isFinite(targetKwp) || targetKwp <= 0) return null

  const options = buildMocOptionsForPanel(wp)
  if (options.length === 0) return null

  return (
    options.find((option) => option.value >= targetKwp) ||
    options[options.length - 1]
  ).value
}

// --- Autodobor zestawu COMFORT PREMIUM (ops#295) ---------------------------
// Decyzja wlasciciela 2026-10-21: dla PV + Magazyn w zestawie COMFORT PREMIUM
// moc PV = zuzycie x 1,2 x 0,95 / 1000, magazyn = zuzycie x 2,7 x 0,95 / 1000;
// gdy nie da sie idealnie, pierwsza dostepna opcja POWYZEJ. Wylacznie dobor
// (prezentacja), ceny licza sie po stronie serwera.
export const COMFORT_PREMIUM_PV_MNOZNIK = 1.2
export const COMFORT_PREMIUM_ME_MNOZNIK = 2.7
export const COMFORT_PREMIUM_SPRAWNOSC = 0.95
export const ZESTAW_AUTODOBOR = 'COMFORT PREMIUM'

function zaokraglij2(x) {
  return Math.round((x + 1e-9) * 100) / 100
}

function celZuzycia(consumption, mnoznik) {
  const cons = Number(consumption)
  if (!Number.isFinite(cons) || cons <= 0) return 0
  return zaokraglij2((cons * mnoznik * COMFORT_PREMIUM_SPRAWNOSC) / 1000)
}

/** @returns {boolean} czy dla wariantu i zestawu kalkulator sam dobiera moc, magazyn i falownik */
export function czyAutodobor({ variant, zestaw } = {}) {
  return variant === VARIANT_PV_BAT && zestaw === ZESTAW_AUTODOBOR
}

/** Cel mocy PV w kWp (2 miejsca), 0 dla braku zuzycia. */
export function celKwpComfortPremium(consumption) {
  return celZuzycia(consumption, COMFORT_PREMIUM_PV_MNOZNIK)
}

/** Cel pojemnosci magazynu w kWh (2 miejsca), 0 dla braku zuzycia. */
export function celKwhComfortPremium(consumption) {
  return celZuzycia(consumption, COMFORT_PREMIUM_ME_MNOZNIK)
}

/**
 * Najmniejsza moc z opcji panelu o wartosci >= cel; ponizej minimum pierwsza,
 * powyzej maksimum ostatnia. null bez zuzycia albo bez opcji.
 */
export function dobierzMocComfortPremium(consumption, wp) {
  const cel = celKwpComfortPremium(consumption)
  if (cel <= 0) return null
  const opcje = buildMocOptionsForPanel(wp)
  if (!opcje.length) return null
  return (opcje.find((o) => zaokraglij2(o.value) >= cel) || opcje[opcje.length - 1]).value
}

/**
 * Magazyn o najmniejszej pojemnosc_kwh >= cel, a gdy zaden, najwiekszy.
 * Pusta lista albo brak zuzycia: undefined. Nie mutuje listy.
 */
export function dobierzMagazynComfortPremium(consumption, magazyny) {
  const cel = celKwhComfortPremium(consumption)
  if (cel <= 0 || !magazyny || magazyny.length === 0) return undefined
  return pickBySpec(magazyny, 'pojemnosc_kwh', cel)
}

// --- Opcje dodatkowe do istniejacych zestawow PV / PV+ME / ME (ops#225) ----
// Katalog ("Volteo Cennik Pozycja", rodzaj="Dodatek OZE") przychodzi z
// volteo_quote_components jako data.dodatki[] = {kod, nazwa, grupa,
// producent, model, kolor, moc_kw, ilosc, parametr, opis, cena}. "cena" to
// juz gotowa cena klienta netto calego dodatku (suma skladowych) - ten plik
// wylacznie prezentuje/filtruje te pozycje, zero wlasnej matematyki cenowej.
//
// Stopniowe odslanianie (decyzja wlasciciela 2026-10-05): wszystkie dodatki
// startuja WYLACZONE, wlacznie z EMS Zeronest (kod ems_breeze, mimo wczesniejszego zapisu CEO
// "TAK domyslna"). Decyzja Jana 2026-10-09 (b69, #237): EMS startuje
// na "Tak", gdy jest dostepny (domyslnyStanEms nizej, stosowany przez
// KalkulatorTab). sanitizujDodatki ponizej TYLKO zeruje wybory, ktore
// przestaly byc dostepne dla biezacej konfiguracji (wariant/producent/typ
// falownika) - nigdy niczego nie wlacza samoistnie.

// Producenci, dla których EMS Zeronest jest dostępny (lustro Server Scriptu).
const PRODUCENCI_EMS = ['Deye', 'Hoymiles', 'Solax']

// Trzy rodzaje dodatku "Klimatyzacja". Od b69 (#237) rodzaj NIE ma stalego
// modelu: lista modeli rodzaju wynika z danych (modeleDodatkuKlimy nizej),
// bo rodzaj to grupa pozycji SAMODZIELNEJ klimatyzacji ("klima_*"), a
// pozycje dodatku ("dod_klima") rodzaju nie niosa.
export const RODZAJ_KLIMY_CHLODZENIE = 'chlodzenie'
export const RODZAJ_KLIMY_DOGRZEWANIE = 'dogrzewanie'
export const RODZAJ_KLIMY_GRZANIE = 'grzanie'
export const RODZAJE_KLIMY_DODATKU = [
  { value: RODZAJ_KLIMY_CHLODZENIE, label: 'Chłodzenie', grupa: 'klima_chlodzenie' },
  { value: RODZAJ_KLIMY_DOGRZEWANIE, label: 'Chłodzenie + dogrzewanie', grupa: 'klima_dogrzewanie' },
  { value: RODZAJ_KLIMY_GRZANIE, label: 'Chłodzenie + grzanie', grupa: 'klima_grzanie' },
]

// Opisowa powierzchnia pokoju per moc jednostki klimatyzacji (prezentacja
// wylacznie), kluczowana stringiem mocy z jedna cyfra po przecinku (zgodnie
// z katalogiem: 2.6/3.5/5.1/6.8 kW).
export const POWIERZCHNIA_KLIMY = {
  '2.6': 'do 25 m2',
  '3.5': '25-40 m2',
  '5.1': '40-55 m2',
  '6.8': '55-75 m2',
}

/**
 * Buduje listę modeli dodatku klimatyzacji dla rodzaju: modele pozycji
 * samodzielnych grupy rodzaju (np. klima_chlodzenie), które mają też
 * wyceniane pozycje dodatku ("dod_klima"). Model bez pozycji dodatku nie
 * jest oferowany (nie da się go wycenić jako dodatek). Wyłącznie
 * prezentacja, bez matematyki cenowej.
 *
 * @param {object[]} dodatki - katalog dodatków (data.dodatki)
 * @param {object[]} pozycjeKlimy - pozycje katalogu klimatyzacji samodzielnej (z volteo_oze_pozycje), z polami grupa/model
 * @param {string} rodzajKlimy - wartość rodzaju (RODZAJE_KLIMY_DODATKU[].value)
 * @returns {{model: string, kolor: string, label: string}[]} modele w kolejności katalogu
 */
export function modeleDodatkuKlimy(dodatki, pozycjeKlimy, rodzajKlimy) {
  const rodzaj = RODZAJE_KLIMY_DODATKU.find((r) => r.value === rodzajKlimy)
  if (!rodzaj || !Array.isArray(dodatki) || !Array.isArray(pozycjeKlimy)) return []

  const modeleGrupy = new Set(
    pozycjeKlimy.filter((p) => p && p.grupa === rodzaj.grupa && p.model).map((p) => p.model),
  )
  const wynik = []
  const widziane = new Set()
  for (const d of dodatki) {
    if (!d || d.grupa !== 'dod_klima' || !modeleGrupy.has(d.model) || widziane.has(d.model)) continue
    widziane.add(d.model)
    const kolor = d.kolor || ''
    wynik.push({ model: d.model, kolor, label: kolor ? `${d.model} (${kolor})` : d.model })
  }
  return wynik
}

/**
 * Domyślny stan przełącznika EMS Zeronest (kod `ems_breeze`, nazwa handlowa
 * od b73): "Nie", gdy dodatek niedostępny; "Tak" bezwarunkowo, gdy wymuszony
 * (Solax z magazynem, wyborReczny ignorowany); w przeciwnym razie zapamiętany
 * wybór użytkownika (wyborReczny true/false), a bez wyboru "Tak". Wybór ręczny jest trwały przez całe życie formularza
 * (decyzja właściciela 2026-10-10): niedostępność go nie kasuje, więc po
 * powrocie do konfiguracji z EMS przełącznik wraca do wyboru użytkownika.
 *
 * @param {object} params
 * @param {string} params.producent
 * @param {string} params.variant
 * @param {boolean|null} params.wyborReczny - null: brak wyboru; true/false: wybór użytkownika
 * @returns {boolean} docelowy stan przełącznika
 */
export function domyslnyStanEms({ producent, variant, wyborReczny = null } = {}) {
  if (!emsDostepny({ producent, variant })) return false
  if (emsWymuszony({ producent, variant })) return true
  return wyborReczny === null ? true : Boolean(wyborReczny)
}

/**
 * Sprawdza, czy dodatek "Klimatyzacja" jest dostępny dla danego wariantu.
 * Dostępny dla każdego z trzech wariantów (PV / PV+ME / ME), niezależnie od
 * producenta.
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function klimaDodatekDostepna(variant) {
  return VARIANTS.includes(variant)
}

/**
 * Sprawdza, czy dodatki "Panele PV" / "Panele PV + mikro" są dostępne.
 * Wyłącznie w wariancie "Magazyn energii" (zestaw bez własnej PV).
 *
 * @param {string} variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function dodatekPaneleDostepny(variant) {
  return variant === VARIANT_BAT
}

/**
 * Sprawdza, czy dodatek "EMS Zeronest" (kod `ems_breeze`, nazwa historyczna)
 * jest dostępny: producent Hoymiles, Solax lub Deye z magazynem energii
 * (PV+ME lub ME). Deye zostaje dla konfiguracji historycznych; Sigenergy ma
 * własny EMS, więc nie.
 *
 * @param {object} params
 * @param {string} params.producent - wybrany producent falownika
 * @param {string} params.variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function emsDostepny({ producent, variant } = {}) {
  return PRODUCENCI_EMS.includes(producent) && variantHasBattery(variant)
}

/**
 * EMS Zeronest jest na sztywno "Tak" (bez możliwości odkliknięcia) dla
 * Solax z magazynem (zestaw COMFORT PREMIUM). Lustro reguły serwera.
 *
 * @param {object} params
 * @param {string} params.producent - wybrany producent falownika
 * @param {string} params.variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest wymuszony
 */
export function emsWymuszony({ producent, variant } = {}) {
  return producent === 'Solax' && variantHasBattery(variant)
}

/**
 * Sprawdza, czy dodatek "Licznik Pstryk" jest dostępny: wyłącznie producent
 * Sigenergy z magazynem energii (PV+ME lub ME).
 *
 * @param {object} params
 * @param {string} params.producent - wybrany producent falownika
 * @param {string} params.variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function pstrykDostepny({ producent, variant } = {}) {
  return producent === 'Sigenergy' && variantHasBattery(variant)
}

/**
 * Sprawdza, czy dodatek "Ładowarka EV" jest dostępny: wyłącznie producent
 * Sigenergy z magazynem energii (PV+ME lub ME). Rodzaj ładowarki (AC/DC)
 * jest dalej ograniczany przez evOpcje() poniżej (DC tylko z falownikiem
 * Sigenergy AIO).
 *
 * @param {object} params
 * @param {string} params.producent - wybrany producent falownika
 * @param {string} params.variant - wybrany wariant instalacji
 * @returns {boolean} czy dodatek jest dostępny do wyboru
 */
export function evDostepne({ producent, variant } = {}) {
  return producent === 'Sigenergy' && variantHasBattery(variant)
}

/**
 * Buduje listę opcji mocy dla dodatku "Klimatyzacja" dla wybranego
 * modelu (rodzaj -> model -> moc), posortowaną rosnąco po
 * mocy. Wyłącznie prezentacja: "cena" przychodzi gotowa z katalogu
 * (data.dodatki), żadnej matematyki tutaj.
 *
 * @param {object[]} dodatki - katalog dodatków z volteo_quote_components (data.dodatki)
 * @param {string} model - wybrany model (z modeleDodatkuKlimy), np. "Elis X"
 * @returns {{kod: string, moc_kw: number, label: string, cena: number}[]} opcje mocy
 */
export function moceDodatkuKlimy(dodatki, model) {
  if (!model || !Array.isArray(dodatki)) return []

  return dodatki
    .filter((d) => d && d.grupa === 'dod_klima' && d.model === model)
    .map((d) => {
      const mocKw = Number(d.moc_kw) || 0
      const klucz = mocKw.toFixed(1)
      const opis = POWIERZCHNIA_KLIMY[klucz]
      const mocLabel = String(mocKw).replace('.', ',')
      return {
        kod: d.kod,
        moc_kw: mocKw,
        label: opis ? `${mocLabel} kW (${opis})` : `${mocLabel} kW`,
        cena: Number(d.cena) || 0,
      }
    })
    .sort((a, b) => a.moc_kw - b.moc_kw)
}

/**
 * Buduje listę opcji ładowarki EV (AC zawsze, DC wyłącznie z falownikiem
 * Sigenergy AIO), posortowaną AC przed DC i rosnąco po mocy w każdej grupie.
 *
 * @param {object[]} dodatki - katalog dodatków z volteo_quote_components (data.dodatki)
 * @param {object} kontekst
 * @param {string} kontekst.producent - wybrany producent falownika
 * @param {string} kontekst.variant - wybrany wariant instalacji
 * @param {string} [kontekst.sigenTyp] - typ falownika Sigenergy ("TP2"/"AIO"), gdy dotyczy
 * @returns {{kod: string, nazwa: string, moc_kw: number, cena: number, grupa: string}[]} opcje ładowarki
 */
export function evOpcje(dodatki, { producent, variant, sigenTyp } = {}) {
  if (!evDostepne({ producent, variant }) || !Array.isArray(dodatki)) return []

  return dodatki
    .filter((d) => {
      if (!d) return false
      if (d.grupa === 'ev_ac') return true
      if (d.grupa === 'ev_dc') return sigenTyp === 'AIO'
      return false
    })
    .map((d) => ({
      kod: d.kod,
      nazwa: d.nazwa,
      moc_kw: Number(d.moc_kw) || 0,
      cena: Number(d.cena) || 0,
      grupa: d.grupa,
    }))
    .sort((a, b) => {
      if (a.grupa !== b.grupa) return a.grupa === 'ev_ac' ? -1 : 1
      return a.moc_kw - b.moc_kw
    })
}

/**
 * Zeruje wyłącznie te wybory dodatków, które przestały być dostępne dla
 * bieżącej konfiguracji (wariant/producent/typ falownika Sigenergy).
 * Nigdy niczego nie włącza ani nie zmienia na wartość inną niż "wyłączone" -
 * zwraca NOWY obiekt (niemutujące), nie modyfikuje przekazanego `wybor`.
 *
 * Specjalny przypadek: ładowarka DC wybrana wcześniej z falownikiem AIO,
 * gdy falownik zmienia się na coś innego niż AIO, jest tu czyszczona z
 * selecta (żeby nie zostawiać martwego wyboru w zamkniętym dropdownie) -
 * serwer i tak odrzuca taką kombinację rzucając błąd, nigdy nie zeruje jej
 * po cichu (ops#225); to czyszczenie po stronie frontu jest wyłącznie
 * higieną UI, nie próbą obejścia tej reguły.
 *
 * @param {object} wybor - bieżący sel.dodatki ({klimaKod, panele, paneleMikro, emsBreeze, pstryk, evKod})
 * @param {object} kontekst
 * @param {string} kontekst.variant - wybrany wariant instalacji
 * @param {string} kontekst.producent - wybrany producent falownika
 * @param {string} [kontekst.sigenTyp] - typ falownika Sigenergy ("TP2"/"AIO"), gdy dotyczy
 * @returns {object} nowy obiekt wyboru dodatków, z niedostępnymi polami wyzerowanymi
 */
export function sanitizujDodatki(wybor, kontekst = {}) {
  const { variant, producent, sigenTyp } = kontekst
  const next = { ...(wybor || {}) }

  if (!klimaDodatekDostepna(variant)) {
    next.klimaKod = ''
  }
  if (!dodatekPaneleDostepny(variant)) {
    next.panele = 0
    next.paneleMikro = 0
  }
  if (!emsDostepny({ producent, variant })) {
    next.emsBreeze = 'Nie'
  } else if (emsWymuszony({ producent, variant })) {
    next.emsBreeze = 'Tak'
  }
  if (!pstrykDostepny({ producent, variant })) {
    next.pstryk = 'Nie'
  }
  if (!evDostepne({ producent, variant })) {
    next.evKod = ''
  } else if (sigenTyp !== 'AIO' && typeof next.evKod === 'string' && next.evKod.startsWith('ev_dc')) {
    next.evKod = ''
  }

  return next
}

// --- Prezentacja kalkulatora OZE (wariant A, kokpit z paragonem) -------------
// Wylacznie czyste helpery prezentacji: grupowanie list, proporcje paska i
// podsumowania zwiniętych sekcji. Zadnej matematyki cenowej: kwoty zawsze
// przychodza z serwera (summary), tu tylko formatowane lub dzielone na procenty
// do narysowania paska.

/**
 * Grupuje opcje mocy PV na "do progu PPOŻ" i "powyzej progu". Opcja trafia do
 * grupy "powyzej", gdy moc nowa + istniejaca > prog (ostro, jak
 * ppozWymuszonyProgiem). Zwraca tylko niepuste grupy, w kolejnosci wejscia.
 *
 * @param {{value: number, label: string}[]} opcje - opcje mocy (buildMocOptionsForPanel)
 * @param {object} [params]
 * @param {number} [params.progKw] - prog w kWp (domyslnie PROG_PPOZ_KW)
 * @param {number} [params.istniejacaKwp] - moc istniejacej instalacji PV w kWp
 * @param {string} [params.etykietaPowyzej] - naglowek grupy powyzej progu
 * @returns {{naglowek: string, opcje: object[]}[]} niepuste grupy
 */
export function grupujMocePv(opcje, { progKw = PROG_PPOZ_KW, istniejacaKwp = 0, etykietaPowyzej = 'Powyżej 6,5 kW' } = {}) {
  const lista = Array.isArray(opcje) ? opcje : []
  const istn = Number(istniejacaKwp) || 0
  const doProgu = []
  const powyzej = []
  for (const o of lista) {
    if ((Number(o?.value) || 0) + istn > progKw) powyzej.push(o)
    else doProgu.push(o)
  }
  const progTekst = String(progKw).replace('.', ',')
  const grupy = [
    { naglowek: `Do ${progTekst} kW`, opcje: doProgu },
    { naglowek: etykietaPowyzej, opcje: powyzej },
  ]
  return grupy.filter((g) => g.opcje.length > 0)
}

const PROGI_MAGAZYNU = [
  { max: 30, naglowek: 'Do 30 kWh' },
  { max: 50, naglowek: '30 do 50 kWh' },
  { max: 70, naglowek: '50 do 70 kWh' },
  { max: Infinity, naglowek: '70 kWh i więcej' },
]

/**
 * Grupuje magazyny energii po pojemnosc_kwh: <30, 30..<50, 50..<70, >=70.
 * Brak lub 0 pojemnosci laduje w "Do 30 kWh". Tylko niepuste grupy; naglowki
 * nie wspominaja o marzach ani kosztach.
 *
 * @param {{pojemnosc_kwh?: number}[]} opcje - komponenty magazynu
 * @returns {{naglowek: string, opcje: object[]}[]} niepuste grupy
 */
export function grupujMagazyny(opcje) {
  const lista = Array.isArray(opcje) ? opcje : []
  const grupy = PROGI_MAGAZYNU.map((p) => ({ naglowek: p.naglowek, opcje: [] }))
  for (const o of lista) {
    const kwh = Number(o?.pojemnosc_kwh) || 0
    const idx = PROGI_MAGAZYNU.findIndex((p) => kwh < p.max)
    grupy[idx].opcje.push(o)
  }
  return grupy.filter((g) => g.opcje.length > 0)
}

/**
 * Procentowe udzialy ceny brutto: klient / dotacja / ulga. WYLACZNIE do
 * narysowania paska proporcji (wyswietlanie), nie wartosci rozliczeniowe.
 * Dotacja i ulga zaokraglane do calosci, klient = reszta (>= 0); wszystko 0
 * przy brutto <= 0.
 *
 * @param {{brutto?: number, dotacja?: number, ulga?: number}} summary
 * @returns {{klient: number, dotacja: number, ulga: number}} procenty calkowite
 */
export function udzialyCeny(summary) {
  const brutto = Number(summary?.brutto) || 0
  if (brutto <= 0) return { klient: 0, dotacja: 0, ulga: 0 }
  const proc = (x) => clamp(Math.round(((Number(x) || 0) / brutto) * 100), 0, 100)
  const dotacja = proc(summary.dotacja)
  const ulga = Math.min(proc(summary.ulga), 100 - dotacja)
  return { klient: Math.max(0, 100 - dotacja - ulga), dotacja, ulga }
}

/**
 * Jednolinijkowe podsumowanie zwinietej sekcji "Montaz i przylacze".
 *
 * @param {object} sel - stan formularza (kabelM, spoldzielnia, licznik, operator, kierunek)
 * @param {object} ctx
 * @param {boolean} ctx.licznikDostepny - czy pole licznika jest widoczne dla producenta
 * @param {boolean} ctx.ppozWymagane - czy PPOŻ jest wymagane
 * @param {number} [ctx.ppozCena] - cena PPOŻ do wyswietlenia (0 = bez kwoty)
 * @param {boolean} [ctx.hasPv] - czy wariant ma PV (kierunek montazu tylko wtedy)
 * @param {(n: number) => string} ctx.formatPln
 * @returns {string} podsumowanie
 */
export function podsumowanieMontazu(sel, { licznikDostepny: licznikOk = false, ppozWymagane: ppoz = false, ppozCena = 0, hasPv = true, formatPln } = {}) {
  const fmt = typeof formatPln === 'function' ? formatPln : (n) => String(n)
  const s = sel || {}
  const kabel = Number(s.kabelM) || 0
  const czesci = [`Kabel ${kabel} m`, s.spoldzielnia === 'Tak' ? 'spółdzielnia' : 'bez spółdzielni']
  if (licznikOk) czesci.push(`licznik: ${s.licznik === 'Tak' ? 'tak' : 'nie'}`)
  czesci.push(ppoz ? `PPOŻ: wymagane${Number(ppozCena) > 0 ? ` (+${fmt(ppozCena)})` : ''}` : 'PPOŻ: niewymagane')
  czesci.push(`operator: ${s.operator || 'brak'}`)
  if (hasPv) czesci.push(`kierunek: ${s.kierunek || 'brak'}`)
  return czesci.join(' · ')
}

/**
 * Jednolinijkowe podsumowanie zwinietej sekcji "Finansowanie".
 *
 * @param {object} sel - stan formularza (ulgaPct, okresLat, wplataWlasna)
 * @param {object} ctx
 * @param {(n: number) => string} ctx.formatPln
 * @returns {string} podsumowanie
 */
export function podsumowanieFinansowania(sel, { formatPln } = {}) {
  const fmt = typeof formatPln === 'function' ? formatPln : (n) => String(n)
  const s = sel || {}
  return `Ulga ${Number(s.ulgaPct) || 0}% · ${Number(s.okresLat) || 0} lat · wpłata własna ${fmt(Number(s.wplataWlasna) || 0)}`
}

/**
 * Jednolinijkowe podsumowanie zwinietej sekcji "Opcje dodatkowe". Kwota
 * (dodatkiNetto) pochodzi z serwera, nigdy nie jest sumowana tutaj.
 *
 * @param {object} params
 * @param {string[]} params.dostepne - nazwy dostepnych dodatkow
 * @param {string[]} params.wybrane - nazwy wybranych dodatkow
 * @param {number} params.dodatkiNetto - summary.dodatki_netto
 * @param {(n: number) => string} params.formatPln
 * @returns {string} podsumowanie
 */
export function podsumowanieDodatkow({ dostepne = [], wybrane = [], dodatkiNetto = 0, formatPln } = {}) {
  const fmt = typeof formatPln === 'function' ? formatPln : (n) => String(n)
  if (!wybrane.length) {
    return dostepne.length ? `Brak wybranych · dostępne: ${dostepne.join(', ')}` : 'Brak wybranych'
  }
  const kwota = Number(dodatkiNetto) > 0 ? ` · +${fmt(dodatkiNetto)} netto` : ''
  return `Wybrane: ${wybrane.join(', ')}${kwota}`
}
