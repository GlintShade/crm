import { widocznyLead } from '@/utils/mapaFiltry'

const BRAK_STATUSU = '(brak)'

function lead(overrides) {
  return {
    status: 'Nowy',
    lead_owner: 'rep@proenergy.pro',
    custom_install_city: 'Warszawa',
    ...overrides,
  }
}

describe('widocznyLead', () => {
  it('lead jest widoczny, gdy nic nie jest wyłączone', () => {
    expect(widocznyLead(lead(), { wylaczone: new Set() }, BRAK_STATUSU)).toBe(true)
  })

  it('status spoza początkowego zbioru jest widoczny (ops#113)', () => {
    // Symuluje edycję statusu na coś, co nie istniało w zbiorze przy
    // starcie mapy (np. CC ma same leady "Nowy" i zmienia jeden na
    // "Umówiony") -- pusty zbiór wyłączonych nie blokuje niczego nowego.
    const zmienionyLead = lead({ status: 'Umówiony' })
    expect(widocznyLead(zmienionyLead, { wylaczone: new Set() }, BRAK_STATUSU)).toBe(true)
  })

  it('status wyłączony jest ukryty', () => {
    const wylaczone = new Set(['Nowy'])
    expect(widocznyLead(lead(), { wylaczone }, BRAK_STATUSU)).toBe(false)
  })

  it('lead bez statusu używa etykiety brakStatusu do sprawdzenia wyłączenia', () => {
    const bezStatusu = lead({ status: '' })
    const wylaczone = new Set([BRAK_STATUSU])
    expect(widocznyLead(bezStatusu, { wylaczone }, BRAK_STATUSU)).toBe(false)
  })

  it('filtr handlowca odrzuca leada innego właściciela', () => {
    const filtry = { wylaczone: new Set(), handlowiec: 'inny@proenergy.pro' }
    expect(widocznyLead(lead(), filtry, BRAK_STATUSU)).toBe(false)
  })

  it('pusty filtr handlowca (string) nie zawęża wyniku', () => {
    const filtry = { wylaczone: new Set(), handlowiec: '' }
    expect(widocznyLead(lead(), filtry, BRAK_STATUSU)).toBe(true)
  })

  it('filtr miasta dopasowuje bez uwzględniania wielkości liter', () => {
    const filtry = { wylaczone: new Set(), miasto: 'WARSZ' }
    expect(widocznyLead(lead(), filtry, BRAK_STATUSU)).toBe(true)
  })

  it('filtr miasta odrzuca leada z innego miasta', () => {
    const filtry = { wylaczone: new Set(), miasto: 'Kraków' }
    expect(widocznyLead(lead(), filtry, BRAK_STATUSU)).toBe(false)
  })

  it('lead bez custom_install_city nie pasuje do niepustego filtra miasta', () => {
    const filtry = { wylaczone: new Set(), miasto: 'Warszawa' }
    expect(widocznyLead(lead({ custom_install_city: '' }), filtry, BRAK_STATUSU)).toBe(false)
  })

  it('kombinacja filtrów: status wyłączony wygrywa niezależnie od reszty', () => {
    const filtry = {
      wylaczone: new Set(['Nowy']),
      handlowiec: 'rep@proenergy.pro',
      miasto: 'Warszawa',
    }
    expect(widocznyLead(lead(), filtry, BRAK_STATUSU)).toBe(false)
  })
})
