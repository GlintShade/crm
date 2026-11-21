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

import { klasaWiersza, przelacz, slugKategorii } from '@/utils/kategorieHandlowcow'

describe('kategorieHandlowcow: pasek i pigułka', () => {
  it('klasaWiersza daje klasę per kategoria, brak kategorii bez klasy', () => {
    expect(klasaWiersza('Priorytet')).toBe('kat-priorytet')
    expect(klasaWiersza('Standard')).toBe('kat-standard')
    expect(klasaWiersza('Nie umawiać')).toBe('kat-nie-umawiac')
    expect(klasaWiersza('')).toBe('')
    expect(klasaWiersza(undefined)).toBe('')
  })
  it('slugKategorii', () => {
    expect(slugKategorii('Nie umawiać')).toBe('nie-umawiac')
    expect(slugKategorii('x')).toBe('')
  })
  it('przelacz: klik w aktywną wyłącza, inaczej wybiera', () => {
    expect(przelacz('Priorytet', 'Priorytet')).toBeNull()
    expect(przelacz(null, 'Standard')).toBe('Standard')
    expect(przelacz('Priorytet', 'Standard')).toBe('Standard')
  })
})
