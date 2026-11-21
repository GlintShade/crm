import { KATEGORIE, kolorKategorii } from '@/utils/kategorieHandlowcow'

describe('kategorieHandlowcow', () => {
  it('każda kategoria ma kolor', () => {
    KATEGORIE.forEach((k) => expect(kolorKategorii(k)).not.toBeNull())
  })
  it('Priorytet jest złoty, Standard biały z ciemną obwódką', () => {
    expect(kolorKategorii('Priorytet').wypelnienie).toBe('#e2ab12')
    expect(kolorKategorii('Standard')).toEqual({ wypelnienie: '#ffffff', obwodka: '#3b4252' })
  })
  it('brak lub nieznana kategoria daje null', () => {
    expect(kolorKategorii('')).toBeNull()
    expect(kolorKategorii('x')).toBeNull()
  })
})
