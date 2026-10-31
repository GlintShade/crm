import { mozeZmieniacStatusCC } from '@/utils/statusCC'

describe('mozeZmieniacStatusCC', () => {
  it('blokuje czystego handlowca', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales', 'Sales User'])).toBe(false)
  })

  it('flaga uzytkownika zdejmuje blokade z handlowca', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales'], false, true)).toBe(true)
  })

  it('admin zawsze moze, bez flagi', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales'], true, false)).toBe(true)
  })

  it('role uprzywilejowane moga bez flagi', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales', 'Volteo Call Center'], false, false)).toBe(true)
  })

  it('brak rol i brak flagi: moze (regula dotyczy tylko D2D)', () => {
    expect(mozeZmieniacStatusCC(null)).toBe(true)
  })
})
