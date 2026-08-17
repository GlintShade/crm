// WYŁĄCZNIE prezentacyjne grupowanie i sumowanie liczb już policzonych przez
// serwer — świadomy, wąski wyjątek od reguły „ZERO pricing math" w
// `KalkulatorTab.vue`, analogicznie do `cpMarza.js`. Nic nie jest zapisywane.

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
    ],
  },
  {
    klucz: 'marze',
    etykieta: 'Marże + bonus liderski',
    pozycje: [
      ['marza_proenergy', 'Marża ProEnergy'],
      ['marza_sps', 'Marża SPS'],
      ['bonus_liderki', 'Bonus liderki'],
    ],
  },
]

// Kilometrowka serwerowo NIE wchodzi do `net_base` (siedzi w warstwie marż
// silnika BOM). Grupowanie jest czysto prezentacyjne, dlatego wiersz
// `net_base` został usunięty z panelu; suma trzech grup = `netto − narzut`.

/**
 * Group and sum server-computed PV cost breakdown values for presentation.
 *
 * @param {Object<string, *> | null | undefined} breakdown - flat server map
 * @returns {Array<object>} three stable presentation groups
 */
export function grupujBreakdown(breakdown) {
  return DEFINICJA_GRUP.map((grupa) => {
    const pozycje = grupa.pozycje.map(([klucz, etykieta]) => {
      const wartosc = breakdown?.[klucz]
      const parsed = typeof wartosc === 'number' || typeof wartosc === 'string'
        ? Number(wartosc)
        : 0
      const kwota = Number.isFinite(parsed) ? parsed : 0
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
