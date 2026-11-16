import { MAX_DODATKOWYCH_OZE, dolaczZdjecia, ileMiejsca, komunikatLimitu } from '@/utils/audytWielePlikow'

describe('audytWielePlikow', () => {
  it('limit zdjęć dodatkowych OZE to 15', () => {
    expect(MAX_DODATKOWYCH_OZE).toBe(15)
    expect(dolaczZdjecia(Array(14).fill('x').map((_, i) => 'a' + i), ['n1', 'n2'], MAX_DODATKOWYCH_OZE).pominiete).toBe(1)
  })
  it('liczy wolne miejsce', () => {
    expect(ileMiejsca(['a', 'b'], 5)).toBe(3)
    expect(ileMiejsca(null, 5)).toBe(5)
    expect(ileMiejsca(['a', 'b', 'c', 'd', 'e', 'f'], 5)).toBe(0)
  })
  it('dokleja wszystkie, gdy się mieszczą', () => {
    const r = dolaczZdjecia(['a'], ['b', 'c'], 5)
    expect(r.lista).toEqual(['a', 'b', 'c'])
    expect(r.dodane).toEqual(['b', 'c'])
    expect(r.pominiete).toBe(0)
  })
  it('ucina nadmiar i liczy pominięte', () => {
    const r = dolaczZdjecia(['a', 'b', 'c'], ['d', 'e', 'f'], 5)
    expect(r.lista).toEqual(['a', 'b', 'c', 'd', 'e'])
    expect(r.pominiete).toBe(1)
  })
  it('pomija puste i duble, nie mutuje wejścia', () => {
    const wej = ['a']
    const r = dolaczZdjecia(wej, ['a', '', null, 'b', 'b'], 5)
    expect(r.lista).toEqual(['a', 'b'])
    expect(r.pominiete).toBe(0)
    expect(wej).toEqual(['a'])
  })
  it('komunikat tylko przy pominiętych', () => {
    expect(komunikatLimitu(0, 5)).toBe('')
    expect(komunikatLimitu(2, 5)).toContain('limit: 5')
  })
})
