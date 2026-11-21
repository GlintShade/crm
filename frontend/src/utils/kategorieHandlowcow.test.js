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

import { stylRamki } from '@/utils/kategorieHandlowcow'
import { describe as d2, it as i2, expect as e2 } from 'vitest'

d2('stylRamki', () => {
  i2('brak kategorii daje null', () => {
    e2(stylRamki('')).toBeNull()
    e2(stylRamki(undefined)).toBeNull()
  })
  i2('Priorytet i Nie umawiać: sam kolor obwódki', () => {
    e2(stylRamki('Priorytet')).toEqual({ borderColor: '#e2ab12' })
    e2(stylRamki('Nie umawiać')).toEqual({ borderColor: '#6f7783' })
  })
  i2('Standard: biała ramka z ciemnym pierścieniem', () => {
    e2(stylRamki('Standard')).toEqual({ borderColor: '#ffffff', boxShadow: '0 0 0 1px #3b4252' })
  })
})
