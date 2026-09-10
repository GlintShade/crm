import { zasadyDotacjiBadge } from '@/utils/zasadyDotacji'

describe('zasadyDotacjiBadge', () => {
  it('"Nowe zasady" daje etykietę "Nowe" i kolor green', () => {
    expect(zasadyDotacjiBadge('Nowe zasady')).toEqual({
      etykieta: 'Nowe',
      kolor: 'green',
    })
  })

  it('"Stare zasady" daje etykietę "Stare" i kolor violet', () => {
    expect(zasadyDotacjiBadge('Stare zasady')).toEqual({
      etykieta: 'Stare',
      kolor: 'violet',
    })
  })

  it('pusta wartość daje null', () => {
    expect(zasadyDotacjiBadge('')).toBeNull()
    expect(zasadyDotacjiBadge(null)).toBeNull()
    expect(zasadyDotacjiBadge(undefined)).toBeNull()
  })

  it('nierozpoznana wartość daje null (bez wybuchu)', () => {
    expect(zasadyDotacjiBadge('coś-nieznanego')).toBeNull()
  })
})
