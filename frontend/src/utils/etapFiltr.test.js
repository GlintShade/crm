import { procesDlaFiltraRodzaju, opcjeEtapu } from './etapFiltr'

const PROCES_OZE = [
  'Lead',
  'Umowa Wygenerowana',
  'Umowa Podpisana',
  'Weryfikacja Backoffice',
  'Finansowanie',
  'Wygrana – montaż',
  'Przegrana',
]

const PROCES_CP = [
  'Lead',
  'Dokumentacja',
  'Audyt Energetyczny',
  'Umowa na realizację',
  'Wniosek o dotację',
  'Dyspozycja wypłaty zaliczki',
  'I transza',
  'Finansowanie Trify',
  'Realizacja',
  'Wniosek o płatność końcową',
  '2 transza',
  'Projekt rozliczony',
  'Przegrana',
]

// Kształt `crm.api.pipeline.volteo_pipeline_grupy` — wszystkie trzy warianty
// OZE mapują się na IDENTYCZNĄ tablicę (gwarancja backendu, patrz
// `crm/volteo_pipeline.py::grupa_for` + `PIPELINE_OZE`/`TERMINALE["OZE"]`
// współdzielone przez cały `OZE_RODZAJE`).
const grupy = {
  Fotowoltaika: PROCES_OZE,
  'Fotowoltaika + Magazyn': PROCES_OZE,
  'Magazyn energii': PROCES_OZE,
  'Czyste Powietrze': PROCES_CP,
}

const wszystkieZnane = (nazwy) => (name) => nazwy.includes(name)

describe('procesDlaFiltraRodzaju', () => {
  it('rodzaj jako goły string → grupa tego rodzaju', () => {
    expect(procesDlaFiltraRodzaju(grupy, 'Czyste Powietrze')).toEqual(PROCES_CP)
    expect(procesDlaFiltraRodzaju(grupy, 'Fotowoltaika')).toEqual(PROCES_OZE)
  })

  it('operator "=" → grupa wskazanego rodzaju', () => {
    expect(procesDlaFiltraRodzaju(grupy, ['=', 'Czyste Powietrze'])).toEqual(
      PROCES_CP,
    )
    expect(procesDlaFiltraRodzaju(grupy, ['equals', 'Magazyn energii'])).toEqual(
      PROCES_OZE,
    )
  })

  it('operator "in" z wartościami jednego procesu (OZE) → grupa tego procesu', () => {
    expect(
      procesDlaFiltraRodzaju(grupy, [
        'in',
        ['Fotowoltaika', 'Magazyn energii'],
      ]),
    ).toEqual(PROCES_OZE)
  })

  it('operator "in" z jedną wartością → grupa tego procesu (trywialnie jeden proces)', () => {
    expect(
      procesDlaFiltraRodzaju(grupy, ['in', ['Czyste Powietrze']]),
    ).toEqual(PROCES_CP)
  })

  it('operator "in" z wartościami z RÓŻNYCH procesów (OZE + CP) → null', () => {
    expect(
      procesDlaFiltraRodzaju(grupy, [
        'in',
        ['Fotowoltaika', 'Czyste Powietrze'],
      ]),
    ).toBeNull()
  })

  it('nieznany/nierozpoznany rodzaj → null', () => {
    expect(procesDlaFiltraRodzaju(grupy, 'Widmo')).toBeNull()
    expect(procesDlaFiltraRodzaju(grupy, ['=', 'Widmo'])).toBeNull()
    expect(
      procesDlaFiltraRodzaju(grupy, ['in', ['Fotowoltaika', 'Widmo']]),
    ).toBeNull()
  })

  it.each([
    [undefined],
    [null],
    [''],
    [['=', '']],
    [['in', []]],
    [['not equals', 'Fotowoltaika']],
    [['not in', ['Fotowoltaika']]],
    [['like', 'Foto%']],
  ])('brak/nierozpoznany kształt filtra (%p) → null', (rodzajFilter) => {
    expect(procesDlaFiltraRodzaju(grupy, rodzajFilter)).toBeNull()
  })

  it.each([[null], [undefined]])(
    'grupy=%p (null-safe względem configu) → null',
    (badGrupy) => {
      expect(procesDlaFiltraRodzaju(badGrupy, 'Czyste Powietrze')).toBeNull()
    },
  )
})

describe('opcjeEtapu', () => {
  const isKnown = wszystkieZnane([...PROCES_OZE, ...PROCES_CP])

  it('z rodzajem (OZE): płaska lista w kolejności procesu', () => {
    expect(opcjeEtapu(grupy, 'Fotowoltaika', isKnown)).toEqual(
      PROCES_OZE.map((name) => ({ label: name, value: name })),
    )
  })

  it('z rodzajem (Czyste Powietrze): płaska lista w kolejności procesu', () => {
    expect(opcjeEtapu(grupy, 'Czyste Powietrze', isKnown)).toEqual(
      PROCES_CP.map((name) => ({ label: name, value: name })),
    )
  })

  it('z rodzajem: filterKnown usuwa nazwy nieznane store\'owi', () => {
    const isKnownBezJednego = wszystkieZnane(
      PROCES_OZE.filter((name) => name !== 'Finansowanie'),
    )
    const wynik = opcjeEtapu(grupy, 'Fotowoltaika', isKnownBezJednego)
    expect(wynik.map((o) => o.value)).not.toContain('Finansowanie')
    expect(wynik).toHaveLength(PROCES_OZE.length - 1)
  })

  it('bez rodzaju: pogrupowane OZE / Czyste Powietrze, bez "Inne" gdy brak statusów spoza procesów', () => {
    const wynik = opcjeEtapu(grupy, null, isKnown)
    expect(wynik).toEqual([
      { group: 'OZE', items: PROCES_OZE.map((name) => ({ label: name, value: name })) },
      { group: 'Czyste Powietrze', items: PROCES_CP.map((name) => ({ label: name, value: name })) },
    ])
  })

  it('bez rodzaju: dokłada "Inne" tylko gdy niepuste (znane statusy spoza obu procesów)', () => {
    const wszystkieZBonusowym = [...PROCES_OZE, ...PROCES_CP, 'Widmowy Status']
    const isKnownRozszerzony = wszystkieZnane(wszystkieZBonusowym)

    const wynik = opcjeEtapu(grupy, null, isKnownRozszerzony, wszystkieZBonusowym)

    expect(wynik).toHaveLength(3)
    expect(wynik[2]).toEqual({
      group: 'Inne',
      items: [{ label: 'Widmowy Status', value: 'Widmowy Status' }],
    })
  })

  it('bez wszystkieStatusy (parametr pominięty) nigdy nie dokłada "Inne"', () => {
    const wynik = opcjeEtapu(grupy, undefined, isKnown)
    expect(wynik.map((g) => g.group)).toEqual(['OZE', 'Czyste Powietrze'])
  })

  it('rodzaj mieszany (in z dwóch procesów) traktowany jak brak rodzaju: pogrupowana lista', () => {
    const wynik = opcjeEtapu(
      grupy,
      ['in', ['Fotowoltaika', 'Czyste Powietrze']],
      isKnown,
    )
    expect(wynik.map((g) => g.group)).toEqual(['OZE', 'Czyste Powietrze'])
  })

  it('bez rodzaju: filterKnown stosowany też do grup OZE/CP', () => {
    const isKnownWaskie = wszystkieZnane(['Lead', 'Przegrana'])
    const wynik = opcjeEtapu(grupy, null, isKnownWaskie)
    const oze = wynik.find((g) => g.group === 'OZE')
    const cp = wynik.find((g) => g.group === 'Czyste Powietrze')
    expect(oze.items.map((o) => o.value)).toEqual(['Lead', 'Przegrana'])
    expect(cp.items.map((o) => o.value)).toEqual(['Lead', 'Przegrana'])
  })
})
