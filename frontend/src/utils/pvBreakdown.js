// WYŁĄCZNIE prezentacyjne grupowanie i sumowanie liczb już policzonych przez
// serwer — świadomy, wąski wyjątek od reguły „ZERO pricing math" w
// `KalkulatorTab.vue`, analogicznie do `cpMarza.js`. Nic nie jest zapisywane.
//
// Etykiety pozycji PV (klucz -> etykieta) w DEFINICJA_GRUP poniżej są
// CELOWO zduplikowane w `ops/crm-kalkulator-bom.py` (mapowanie etykiet przy
// budowie snapshotu `custom_koszty_json` — GENERATE_PERSIST) — zmieniaj oba
// miejsca razem, inaczej etykiety w panelu kosztów rzeczywistych (b49,
// `MontazKosztyPanel.vue`, zamontowany na dole zakładki Zestaw) rozjadą się
// z etykietami w tym pliku.

const DEFINICJA_GRUP = [
  {
    klucz: 'hurtownia',
    etykieta: 'Hurtownia (części)',
    pozycje: [
      ['k_falownik', 'Falownik'],
      ['k_bateria', 'Bateria'],
      ['k_panele', 'Panele'],
      ['k_konstrukcja', 'Konstrukcja'],
      ['k_sterownik', 'Sterownik'],
      // To dopłata rozliczeniowa („Doplata — spoldzielnia energetyczna"),
      // umieszczona tu świadomą decyzją właściciela — nie „poprawiać".
      ['k_spoldzielnia', 'Spółdzielnia'],
    ],
  },
  {
    klucz: 'montaz',
    etykieta: 'Montaż',
    pozycje: [
      ['kilometrowka', 'Kilometrówka'],
      ['k_montaz_pv', 'Montaż PV'],
      ['k_montaz_mag', 'Montaż magazynu'],
      ['k_akcesoria', 'Akcesoria'],
      ['k_kabel', 'Kabel'],
      // Etykieta "Dodatkowy licznik" jest CELOWO zduplikowana w
      // `koszty_linie` silnika ops (patrz komentarz u góry pliku): zmieniaj
      // oba miejsca razem.
      ['k_licznik', 'Dodatkowy licznik'],
      // Etykieta "Uzgodnienia PPOŻ" jest CELOWO zduplikowana w
      // `koszty_linie` silnika ops (patrz komentarz u góry pliku): zmieniaj
      // oba miejsca razem (ops#194).
      ['k_ppoz', 'Uzgodnienia PPOŻ'],
    ],
  },
  // ops#225: koszty dodatkow PV/PV+ME/ME (klimatyzacja, panele, panele +
  // mikro, EMS Breeze, ladowarka EV) - tylko koszt (k_dod_*), tak samo jak
  // hurtownia/montaz powyzej. Marza tych dodatkow (m_dod_*) NIE jest tu
  // osobna pozycja - jest sumowana w jedna pozycje "marza_dodatki" w grupie
  // "marze" ponizej (admin breakdown nie wysyla gotowego pola marza_dodatki,
  // wiec grupujBreakdown liczy te sume sam, patrz MARZA_DODATKI_SKLADNIKI).
  // Licznik Pstryk celowo pominiety: jego koszt jest zawsze 0 (cennik ma
  // tylko pozycje "Koszt" = 0, bez marzy), wiec silnik BOM w ogole nie
  // wysyla k_pstryk/m_pstryk w breakdown - nie ma czego tu pokazywac.
  {
    klucz: 'dodatki',
    etykieta: 'Opcje dodatkowe',
    pozycje: [
      ['k_dod_klima', 'Dodatek: klimatyzacja'],
      ['k_dod_panele', 'Dodatek: panele PV'],
      ['k_dod_panele_mikro', 'Dodatek: panele PV + mikro'],
      ['k_ems_breeze', 'EMS Breeze'],
      ['k_ev', 'Ładowarka EV'],
    ],
  },
  {
    klucz: 'marze',
    etykieta: 'Marże + bonus liderski',
    pozycje: [
      ['marza_proenergy', 'Marża ProEnergy'],
      ['marza_sps', 'Marża SPS'],
      ['bonus_liderki', 'Bonus liderki'],
      // ops#225: suma marz wszystkich wybranych dodatkow (m_dod_klima +
      // m_dod_panele + m_dod_panele_mikro + m_ems_breeze + m_ev) - jedna
      // zbiorcza pozycja, zeby nie mnozyc wierszy w panelu o piec kolejnych
      // linii o zerowej wartosci przy braku wybranych dodatkow.
      ['marza_dodatki', 'Marża - dodatki'],
    ],
  },
]

// Skladowe sumowane w jedna pozycje "marza_dodatki" (patrz komentarz przy
// definicji grupy "marze" powyzej) - jedyny klucz w DEFINICJA_GRUP, ktory nie
// czyta wartosci wprost z `breakdown`, tylko sumuje kilka jego pol naraz.
const MARZA_DODATKI_SKLADNIKI = [
  'm_dod_klima',
  'm_dod_panele',
  'm_dod_panele_mikro',
  'm_ems_breeze',
  'm_ev',
]

// Kilometrowka serwerowo NIE wchodzi do `net_base` (siedzi w warstwie marż
// silnika BOM). Grupowanie jest czysto prezentacyjne, dlatego wiersz
// `net_base` został usunięty z panelu; suma czterech grup = `netto − narzut`.

function parsujKwote(wartosc) {
  const parsed = typeof wartosc === 'number' || typeof wartosc === 'string'
    ? Number(wartosc)
    : 0
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Group and sum server-computed PV cost breakdown values for presentation.
 *
 * @param {Object<string, *> | null | undefined} breakdown - flat server map
 * @returns {Array<object>} four stable presentation groups
 */
export function grupujBreakdown(breakdown) {
  return DEFINICJA_GRUP.map((grupa) => {
    const pozycje = grupa.pozycje.map(([klucz, etykieta]) => {
      const kwota = klucz === 'marza_dodatki'
        ? MARZA_DODATKI_SKLADNIKI.reduce((suma, sklad) => suma + parsujKwote(breakdown?.[sklad]), 0)
        : parsujKwote(breakdown?.[klucz])
      return { klucz, etykieta, kwota }
    })

    const suma = pozycje.reduce((razem, pozycja) => razem + pozycja.kwota, 0)

    return {
      klucz: grupa.klucz,
      etykieta: grupa.etykieta,
      pozycje,
      suma: Number.isFinite(suma) ? suma : 0,
    }
  })
}
