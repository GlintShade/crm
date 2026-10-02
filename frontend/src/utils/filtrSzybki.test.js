import {
  czyFiltrSzybkiZablokowany,
  czyWielokrotnyFiltrSzybki,
  etykietaChipaFiltraSzybkiego,
  grupyOpcjiFiltraSzybkiego,
  opcjeDodaniaFiltraSzybkiego,
  przelaczWartoscWielokrotna,
  rozpakujWartoscFiltraSzybkiego,
  spakujWartoscFiltraSzybkiego,
  ustawWartoscWielokrotna,
  zaleznaWartoscFiltraSerwera,
} from './filtrSzybki'
import { opcjeEtapu } from './etapFiltr'
import { OPERATOR_TAGOW } from './tagiProduktow'

describe('rozpakujWartoscFiltraSzybkiego', () => {
  it('skalar (dotychczasowy kształt jednej wartości) -> tablica jednoelementowa', () => {
    expect(rozpakujWartoscFiltraSzybkiego('Nowy')).toEqual(['Nowy'])
  })

  it('["in", [...]] -> tablica wartości, operator bez względu na wielkość liter', () => {
    expect(
      rozpakujWartoscFiltraSzybkiego(['in', ['Nowy', 'Próba kontaktu']]),
    ).toEqual(['Nowy', 'Próba kontaktu'])
    expect(
      rozpakujWartoscFiltraSzybkiego(['IN', ['Nowy', 'Odłożony']]),
    ).toEqual(['Nowy', 'Odłożony'])
  })

  it('inny kształt tablicowy (np. like z rozwiniętego filtra) -> pusta tablica', () => {
    expect(rozpakujWartoscFiltraSzybkiego(['like', '%Jan%'])).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego(['not in', ['Nowy']])).toEqual([])
  })

  it('brak wartości -> pusta tablica', () => {
    expect(rozpakujWartoscFiltraSzybkiego(undefined)).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego(null)).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego('')).toEqual([])
  })

  it('issue #214: skalar "@me" (zapisany widok sprzed wielokrotnego wyboru pól osób, np. custom_cc: "@me") -> jedno zaznaczenie "@me"', () => {
    expect(rozpakujWartoscFiltraSzybkiego('@me')).toEqual(['@me'])
  })

  it('issue ops#173: kształt złożony -> strona "ma"', () => {
    expect(
      rozpakujWartoscFiltraSzybkiego([
        OPERATOR_TAGOW,
        { ma: ['PV', 'PC'], nie_ma: ['AUDYT'] },
      ]),
    ).toEqual(['PV', 'PC'])
    expect(rozpakujWartoscFiltraSzybkiego([OPERATOR_TAGOW, { nie_ma: ['AUDYT'] }])).toEqual(
      [],
    )
  })
})

describe('spakujWartoscFiltraSzybkiego', () => {
  it('0 wartości -> undefined (klucz do usunięcia)', () => {
    expect(spakujWartoscFiltraSzybkiego([])).toBeUndefined()
    expect(spakujWartoscFiltraSzybkiego(null)).toBeUndefined()
  })

  it('1 wartość -> sam string, dotychczasowy kształt', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy'])).toBe('Nowy')
  })

  it('N wartości -> ["in", [...]]', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy', 'Odłożony'])).toEqual([
      'in',
      ['Nowy', 'Odłożony'],
    ])
  })

  it('odrzuca puste/białoznakowe wpisy przed zliczeniem', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy', '', '  '])).toBe('Nowy')
    expect(spakujWartoscFiltraSzybkiego(['', '  '])).toBeUndefined()
  })
})

describe('etykietaChipaFiltraSzybkiego', () => {
  it('brak zaznaczeń -> sama etykieta pola', () => {
    expect(etykietaChipaFiltraSzybkiego('Status CC', [])).toBe('Status CC')
    expect(etykietaChipaFiltraSzybkiego('Status CC', null)).toBe('Status CC')
  })

  it('jedna wartość -> "Etykieta: Wartość"', () => {
    expect(etykietaChipaFiltraSzybkiego('Status CC', ['Nowy'])).toBe(
      'Status CC: Nowy',
    )
  })

  it('dwie wartości -> "Etykieta: Pierwsza +1"', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', ['Nowy', 'Próba kontaktu']),
    ).toBe('Status CC: Nowy +1')
  })

  it('trzy wartości -> "Etykieta: Pierwsza +2"', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', [
        'Nowy',
        'Próba kontaktu',
        'Odłożony',
      ]),
    ).toBe('Status CC: Nowy +2')
  })

  it('puste/nullowe wpisy w liście etykiet są pomijane przy liczeniu', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', ['Nowy', '', null]),
    ).toBe('Status CC: Nowy')
  })
})

describe('czyWielokrotnyFiltrSzybki', () => {
  it('Select → true', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_status_handlowy',
        fieldtype: 'Select',
        options: 'A\nB',
      }),
    ).toBe(true)
  })

  it('Link poza User → true', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Lead Status',
      }),
    ).toBe(true)
  })

  it('issue #214: Link options===User (custom_cc, lead_owner) → true, checkboxy z zakresem Sales Hierarchy w QuickFilterCheckList', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_cc',
        fieldtype: 'Link',
        options: 'User',
      }),
    ).toBe(true)
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'lead_owner',
        fieldtype: 'Link',
        options: 'User',
      }),
    ).toBe(true)
  })

  it('Date/Datetime → false', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_kolejny_kontakt',
        fieldtype: 'Date',
      }),
    ).toBe(false)
  })

  it('owner remark #37 (2026-09-28): CRM Deal status (Etap) → true jak każdy Link poza User, lista opcji procesu żyje w QuickFilterField', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Deal', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Deal Status',
      }),
    ).toBe(true)
  })

  it('ops#150: pole tagów (Data + volteo_tagi) → true, dostaje QuickFilterCheckList', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_posiadane_produkty',
        fieldtype: 'Data',
        options: 'PV\nME\nPC',
        volteo_tagi: 1,
      }),
    ).toBe(true)
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_produkt_procesu',
        fieldtype: 'Data',
        options: 'PV\nPVME\nME\nPC\nCP',
        volteo_tagi: 1,
      }),
    ).toBe(true)
  })

  it('status na innym doctype niż CRM Deal (np. CRM Lead) → true', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Lead Status',
      }),
    ).toBe(true)
  })
})

describe('przelaczWartoscWielokrotna', () => {
  it('wartości nie ma -> dodana na końcu', () => {
    expect(przelaczWartoscWielokrotna(['Nowy'], 'Odłożony')).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('wartość już jest -> usunięta', () => {
    expect(
      przelaczWartoscWielokrotna(['Nowy', 'Odłożony'], 'Nowy'),
    ).toEqual(['Odłożony'])
  })

  it('pusta lista wejściowa -> tablica jednoelementowa', () => {
    expect(przelaczWartoscWielokrotna([], 'Nowy')).toEqual(['Nowy'])
    expect(przelaczWartoscWielokrotna(null, 'Nowy')).toEqual(['Nowy'])
  })

  it('nie mutuje wejściowej tablicy (immutability)', () => {
    const wejscie = ['Nowy']
    const wynik = przelaczWartoscWielokrotna(wejscie, 'Odłożony')
    expect(wejscie).toEqual(['Nowy'])
    expect(wynik).not.toBe(wejscie)
  })
})

// Regresja 2026-09-11 (issue #127 follow-up): frappe-ui's Checkbox.vue
// emituje update:modelValue dwa razy na jedno kliknięcie z tym samym
// argumentem. ustawWartoscWielokrotna (w przeciwieństwie do
// przelaczWartoscWielokrotna) musi być idempotentna wobec tego -- ta sama
// para (wartość, zaznaczona) wywołana dwukrotnie musi dać ten sam wynik co
// raz, patrz komentarz przy funkcji w filtrSzybki.js.
describe('ustawWartoscWielokrotna', () => {
  it('zaznaczona=true, wartości nie ma -> dodana na końcu', () => {
    expect(ustawWartoscWielokrotna(['Nowy'], 'Odłożony', true)).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('zaznaczona=false, wartość jest -> usunięta', () => {
    expect(
      ustawWartoscWielokrotna(['Nowy', 'Odłożony'], 'Nowy', false),
    ).toEqual(['Odłożony'])
  })

  it('idempotentność: dwa wywołania zaznaczona=true z tą samą wartością dają ten sam wynik co jedno', () => {
    let wynik = ustawWartoscWielokrotna([], 'Nowy', true)
    wynik = ustawWartoscWielokrotna(wynik, 'Nowy', true)
    expect(wynik).toEqual(['Nowy'])
  })

  it('idempotentność: dwa wywołania zaznaczona=false z tą samą wartością dają ten sam wynik co jedno', () => {
    let wynik = ustawWartoscWielokrotna(['Nowy'], 'Nowy', false)
    wynik = ustawWartoscWielokrotna(wynik, 'Nowy', false)
    expect(wynik).toEqual([])
  })

  it('pusta lista wejściowa -> tablica jednoelementowa (zaznaczona=true)', () => {
    expect(ustawWartoscWielokrotna([], 'Nowy', true)).toEqual(['Nowy'])
    expect(ustawWartoscWielokrotna(null, 'Nowy', true)).toEqual(['Nowy'])
  })

  it('zaznaczona=false, wartości nie ma -> lista bez zmian', () => {
    expect(ustawWartoscWielokrotna(['Odłożony'], 'Nowy', false)).toEqual([
      'Odłożony',
    ])
  })

  it('nie mutuje wejściowej tablicy (immutability)', () => {
    const wejscie = ['Nowy']
    const wynik = ustawWartoscWielokrotna(wejscie, 'Odłożony', true)
    expect(wejscie).toEqual(['Nowy'])
    expect(wynik).not.toBe(wejscie)
  })
})

describe('czyFiltrSzybkiZablokowany', () => {
  it('true dla kształtu złożonego', () => {
    expect(
      czyFiltrSzybkiZablokowany([OPERATOR_TAGOW, { ma: ['PV'], nie_ma: ['AUDYT'] }]),
    ).toBe(true)
  })

  it('true dla "not in"', () => {
    expect(czyFiltrSzybkiZablokowany(['not in', ['PV']])).toBe(true)
  })

  it('false dla "in", skalara, braku wartości', () => {
    expect(czyFiltrSzybkiZablokowany(['in', ['PV']])).toBe(false)
    expect(czyFiltrSzybkiZablokowany('PV')).toBe(false)
    expect(czyFiltrSzybkiZablokowany(undefined)).toBe(false)
    expect(czyFiltrSzybkiZablokowany(null)).toBe(false)
  })
})

// Owner remark #37 (2026-09-28): Etap (status na CRM Deal) dostał
// wielokrotny wybór z checkboxami, ale zostaje przy własnej, zawężonej do
// procesu liście opcji z utils/etapFiltr.js::opcjeEtapu -- płaskiej albo
// pogrupowanej OZE/Czyste Powietrze/Inne. grupyOpcjiFiltraSzybkiego
// normalizuje oba kształty do jednej postaci, którą renderuje
// QuickFilterCheckList.vue.
describe('grupyOpcjiFiltraSzybkiego', () => {
  it('płaska lista → jedna grupa z group: null i tymi samymi opcjami', () => {
    expect(
      grupyOpcjiFiltraSzybkiego([
        { label: 'Nowy', value: 'Nowy' },
        { label: 'Odłożony', value: 'Odłożony' },
      ]),
    ).toEqual([
      {
        group: null,
        items: [
          { label: 'Nowy', value: 'Nowy' },
          { label: 'Odłożony', value: 'Odłożony' },
        ],
      },
    ])
  })

  it('lista pogrupowana OZE/Czyste Powietrze/Inne → ta sama kolejność, etykiety i opcje', () => {
    const wejscie = [
      {
        group: 'OZE',
        items: [{ label: 'Lead', value: 'Lead' }],
      },
      {
        group: 'Czyste Powietrze',
        items: [{ label: 'Audyt', value: 'Audyt' }],
      },
      {
        group: 'Inne',
        items: [{ label: 'Ręczny', value: 'Ręczny' }],
      },
    ]
    expect(grupyOpcjiFiltraSzybkiego(wejscie)).toEqual(wejscie)
  })

  it('wpisy z value: "" i value: null odrzucone wewnątrz grupy i w liście płaskiej', () => {
    expect(
      grupyOpcjiFiltraSzybkiego([
        { label: '', value: '' },
        { label: 'Nowy', value: 'Nowy' },
        { label: 'Brak', value: null },
      ]),
    ).toEqual([{ group: null, items: [{ label: 'Nowy', value: 'Nowy' }] }])

    expect(
      grupyOpcjiFiltraSzybkiego([
        {
          group: 'OZE',
          items: [
            { label: '', value: '' },
            { label: 'Lead', value: 'Lead' },
            { label: 'Brak', value: null },
          ],
        },
      ]),
    ).toEqual([{ group: 'OZE', items: [{ label: 'Lead', value: 'Lead' }] }])
  })

  it('puste grupy (przypadek zimnego ładowania) są odrzucane', () => {
    expect(
      grupyOpcjiFiltraSzybkiego([
        { group: 'OZE', items: [] },
        { group: 'Czyste Powietrze', items: [] },
      ]),
    ).toEqual([])
  })

  it('undefined, null, string → pusta tablica', () => {
    expect(grupyOpcjiFiltraSzybkiego(undefined)).toEqual([])
    expect(grupyOpcjiFiltraSzybkiego(null)).toEqual([])
    expect(grupyOpcjiFiltraSzybkiego('CRM Deal Status')).toEqual([])
  })

  it('grupa z pustym group (\'\') nadal rozpoznana jako pogrupowana przez items', () => {
    expect(
      grupyOpcjiFiltraSzybkiego([
        { group: '', items: [{ label: 'Nowy', value: 'Nowy' }] },
      ]),
    ).toEqual([{ group: null, items: [{ label: 'Nowy', value: 'Nowy' }] }])
  })

  it('nie mutuje wejścia', () => {
    const wejscie = [
      { group: 'OZE', items: [{ label: 'Lead', value: 'Lead' }] },
    ]
    const kopiaWejscia = JSON.parse(JSON.stringify(wejscie))
    grupyOpcjiFiltraSzybkiego(wejscie)
    expect(wejscie).toEqual(kopiaWejscia)
  })

  it('end-to-end z opcjeEtapu (etapFiltr.js): bez zawężenia rodzaju → OZE/Czyste Powietrze/Inne', () => {
    const grupy = {
      Fotowoltaika: ['Lead', 'Umowa Wygenerowana', 'Wygrana'],
      'Czyste Powietrze': ['Lead', 'Audyt', 'Wygrana'],
    }
    const isKnown = () => true
    const wszystkieStatusy = [
      'Lead',
      'Umowa Wygenerowana',
      'Wygrana',
      'Audyt',
      'Ręczny',
    ]

    const wynik = grupyOpcjiFiltraSzybkiego(
      opcjeEtapu(grupy, null, isKnown, wszystkieStatusy),
    )

    expect(wynik).toEqual([
      {
        group: 'OZE',
        items: [
          { label: 'Lead', value: 'Lead' },
          { label: 'Umowa Wygenerowana', value: 'Umowa Wygenerowana' },
          { label: 'Wygrana', value: 'Wygrana' },
        ],
      },
      {
        group: 'Czyste Powietrze',
        items: [
          { label: 'Lead', value: 'Lead' },
          { label: 'Audyt', value: 'Audyt' },
          { label: 'Wygrana', value: 'Wygrana' },
        ],
      },
      {
        group: 'Inne',
        items: [{ label: 'Ręczny', value: 'Ręczny' }],
      },
    ])
  })
})

describe('zaleznaWartoscFiltraSerwera', () => {
  const konfiguracjaPowiatu = {
    url: 'crm.api.volteo_leady.powiaty_filtra',
    zalezy_od: 'custom_voivodeship',
    parametr: 'wojewodztwa',
  }

  it('pole bez volteo_wartosci -> pusta tablica', () => {
    expect(zaleznaWartoscFiltraSerwera({ fieldtype: 'Data' }, {})).toEqual([])
    expect(zaleznaWartoscFiltraSerwera(null, {})).toEqual([])
    expect(zaleznaWartoscFiltraSerwera(undefined, { custom_voivodeship: 'mazowieckie' })).toEqual(
      [],
    )
  })

  it('zalezny filtr nieustawiony -> pusta tablica (serwer nie zaweza)', () => {
    const field = { fieldtype: 'Data', volteo_wartosci: konfiguracjaPowiatu }
    expect(zaleznaWartoscFiltraSerwera(field, {})).toEqual([])
    expect(zaleznaWartoscFiltraSerwera(field, undefined)).toEqual([])
  })

  it('zalezny filtr skalarem (jedno wojewodztwo) -> tablica jednoelementowa', () => {
    const field = { fieldtype: 'Data', volteo_wartosci: konfiguracjaPowiatu }
    expect(
      zaleznaWartoscFiltraSerwera(field, { custom_voivodeship: 'mazowieckie' }),
    ).toEqual(['mazowieckie'])
  })

  it('zalezny filtr ["in", [...]] (kilka wojewodztw) -> tablica wartosci', () => {
    const field = { fieldtype: 'Data', volteo_wartosci: konfiguracjaPowiatu }
    expect(
      zaleznaWartoscFiltraSerwera(field, {
        custom_voivodeship: ['in', ['mazowieckie', 'slaskie']],
      }),
    ).toEqual(['mazowieckie', 'slaskie'])
  })

  it('zalezny filtr nierozpoznanym ksztaltem (np. like) -> pusta tablica', () => {
    const field = { fieldtype: 'Data', volteo_wartosci: konfiguracjaPowiatu }
    expect(
      zaleznaWartoscFiltraSerwera(field, { custom_voivodeship: ['like', '%maz%'] }),
    ).toEqual([])
  })

  it('czyta klucz zalezny_od z konfiguracji pola, nie nazwe pola samego', () => {
    const field = {
      fieldtype: 'Data',
      volteo_wartosci: { url: 'x', zalezy_od: 'inny_klucz', parametr: 'p' },
    }
    expect(
      zaleznaWartoscFiltraSerwera(field, {
        custom_voivodeship: 'mazowieckie',
        inny_klucz: 'wartosc',
      }),
    ).toEqual(['wartosc'])
  })
})

describe('opcjeDodaniaFiltraSzybkiego', () => {
  const polaDoctype = [
    { fieldname: 'status', label: 'Etap', fieldtype: 'Link' },
    { fieldname: 'lead_name', label: 'Klient', fieldtype: 'Data' },
    { fieldname: 'custom_koszty_zysk_plan', label: 'Zysk (plan)', fieldtype: 'Currency', permlevel: 2 },
    { fieldname: 'bez_etykiety', label: '', fieldtype: 'Data' },
  ]

  it('dozwolonePola=null (jeszcze się ładuje) -> ostrożny fallback do pól permlevel 0', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(polaDoctype, null, [])
    expect(wynik.map((o) => o.value)).toEqual(['status', 'lead_name'])
  })

  it('dozwolonePola=undefined -> ten sam fallback jak null', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(polaDoctype, undefined, [])
    expect(wynik.map((o) => o.value)).toEqual(['status', 'lead_name'])
  })

  it('dozwolonePola jako tablica -> zwęża do tych nazw, nawet gdy permlevel > 0', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(
      polaDoctype,
      ['status', 'custom_koszty_zysk_plan'],
      [],
    )
    expect(wynik.map((o) => o.value)).toEqual(['status', 'custom_koszty_zysk_plan'])
  })

  it('dozwolonePola jako pusta tablica -> brak opcji', () => {
    expect(opcjeDodaniaFiltraSzybkiego(polaDoctype, [], [])).toEqual([])
  })

  it('pole bez etykiety jest wykluczone niezależnie od dozwolonePola', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(
      polaDoctype,
      ['status', 'bez_etykiety'],
      [],
    )
    expect(wynik.map((o) => o.value)).toEqual(['status'])
  })

  it('pole już na pasku (istniejaceNaPasku) jest wykluczone', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(polaDoctype, null, ['lead_name'])
    expect(wynik.map((o) => o.value)).toEqual(['status'])
  })

  it('istniejaceNaPasku=undefined traktowane jak pusta tablica', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(polaDoctype, null, undefined)
    expect(wynik.map((o) => o.value)).toEqual(['status', 'lead_name'])
  })

  it('polaDoctype niepoprawne (nie-tablica) -> pusta tablica opcji', () => {
    expect(opcjeDodaniaFiltraSzybkiego(null, null, [])).toEqual([])
    expect(opcjeDodaniaFiltraSzybkiego(undefined, null, [])).toEqual([])
  })

  it('zwraca kształt {label, value, fieldtype}, nigdy {fieldname}', () => {
    const wynik = opcjeDodaniaFiltraSzybkiego(polaDoctype, null, [])
    expect(wynik[0]).toEqual({ label: 'Etap', value: 'status', fieldtype: 'Link' })
    expect(wynik[0].fieldname).toBeUndefined()
  })

  it('nie mutuje polaDoctype/istniejaceNaPasku (immutability)', () => {
    const pola = [...polaDoctype]
    const istniejace = ['lead_name']
    opcjeDodaniaFiltraSzybkiego(pola, null, istniejace)
    expect(pola).toEqual(polaDoctype)
    expect(istniejace).toEqual(['lead_name'])
  })
})
