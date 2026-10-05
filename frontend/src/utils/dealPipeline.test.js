import { describe, it, expect } from 'vitest'
import { filtrujOpcjeRodzajuUmowy } from './dealPipeline'
import { RODZAJE_OZE } from './rodzajUmowy'

// b68 ("Wielki update kalkulatora OZE"): filtrujOpcjeRodzajuUmowy przeszedl
// z wlasnego, lokalnego zbioru trzech starych rodzajow OZE na import
// RODZAJE_OZE z rodzajUmowy.js (siedem rodzajow - trzy stare plus cztery
// nowe). Ten plik sprawdza wylacznie, ze ten import dziala i obejmuje
// wszystkie siedem rodzajow; zachowanie samej funkcji (operator fail-open,
// obsluga Czyste Powietrze) nie zmienia sie i nie jest tu powtarzane.

const WSZYSTKIE_RODZAJE = [
  '',
  'Fotowoltaika',
  'Fotowoltaika + Magazyn',
  'Magazyn energii',
  'Rozbudowa PV/ME',
  'Klimatyzacja',
  'Pompa ciepła',
  'Kocioł',
  'Czyste Powietrze',
]

describe('filtrujOpcjeRodzajuUmowy (siedem rodzajow OZE, b68)', () => {
  it('RODZAJE_OZE (uzywane wewnatrz) ma dokladnie siedem wartosci', () => {
    expect(RODZAJE_OZE.size).toBe(7)
  })

  it('oze=false usuwa wszystkie siedem rodzajow OZE, zostawia Czyste Powietrze i pusta opcje', () => {
    const wynik = filtrujOpcjeRodzajuUmowy(WSZYSTKIE_RODZAJE.join('\n'), { oze: false })
    expect(wynik).toBe(['', 'Czyste Powietrze'].join('\n'))
  })

  it('cp=false usuwa wylacznie Czyste Powietrze, wszystkie siedem rodzajow OZE zostaja', () => {
    const wynik = filtrujOpcjeRodzajuUmowy(WSZYSTKIE_RODZAJE.join('\n'), { cp: false })
    expect(wynik).toBe(
      [
        '',
        'Fotowoltaika',
        'Fotowoltaika + Magazyn',
        'Magazyn energii',
        'Rozbudowa PV/ME',
        'Klimatyzacja',
        'Pompa ciepła',
        'Kocioł',
      ].join('\n'),
    )
  })

  it('bez flag (fail-open) zostawia wszystkie dziewiec opcji bez zmian', () => {
    const options = WSZYSTKIE_RODZAJE.join('\n')
    expect(filtrujOpcjeRodzajuUmowy(options)).toBe(options)
  })

  it('kazdy z czterech nowych rodzajow (b68) jest traktowany jak OZE, nie jak "inny"', () => {
    for (const rodzaj of ['Rozbudowa PV/ME', 'Klimatyzacja', 'Pompa ciepła', 'Kocioł']) {
      const wynik = filtrujOpcjeRodzajuUmowy(rodzaj, { oze: false })
      expect(wynik, rodzaj).toBe('')
    }
  })
})
