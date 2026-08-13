import {
  AUTENTI_BADGE,
  badgeFor,
  canSend,
  isInFlight,
  sendButtonLabel,
} from '@/utils/autentiStatus'

describe('Autenti — status umowy (autentiStatus)', () => {
  describe('AUTENTI_BADGE', () => {
    it('zawiera wpis dla każdego znanego statusu z poprawnym theme Badge', () => {
      const validThemes = new Set(['gray', 'blue', 'green', 'amber', 'red', 'violet'])
      const statuses = [
        'Wysyłanie',
        'Wysłana',
        'Podpisana',
        'Odrzucona',
        'Wygasła',
        'Wycofana',
        'Błąd',
      ]
      for (const status of statuses) {
        expect(AUTENTI_BADGE[status]).toBeDefined()
        expect(typeof AUTENTI_BADGE[status].label).toBe('string')
        expect(AUTENTI_BADGE[status].label.length).toBeGreaterThan(0)
        expect(validThemes.has(AUTENTI_BADGE[status].theme)).toBe(true)
      }
    })
  })

  describe('badgeFor', () => {
    it.each([[null], [undefined], ['']])(
      'zwraca null dla nigdy niewysłanej umowy (%p)',
      (status) => {
        expect(badgeFor(status)).toBeNull()
      },
    )

    it('zwraca wpis badge dla znanego statusu', () => {
      expect(badgeFor('Podpisana')).toEqual({ label: 'Podpisana', theme: 'green' })
      expect(badgeFor('Błąd')).toEqual({ label: 'Błąd wysyłki', theme: 'red' })
    })

    it('zwraca null dla nieznanego statusu zamiast rzucać wyjątek', () => {
      expect(badgeFor('CośNieistniejącego')).toBeNull()
    })
  })

  describe('canSend', () => {
    it.each([
      [null, true],
      [undefined, true],
      ['', true],
      ['Błąd', true],
      ['Odrzucona', true],
      ['Wygasła', true],
      ['Wycofana', true],
      ['Wysyłanie', false],
      ['Wysłana', false],
      ['Podpisana', false],
    ])('canSend(%p) === %p', (status, expected) => {
      expect(canSend(status)).toBe(expected)
    })
  })

  describe('isInFlight', () => {
    it.each([
      ['Wysyłanie', true],
      ['Wysłana', true],
      [null, false],
      [undefined, false],
      ['', false],
      ['Podpisana', false],
      ['Odrzucona', false],
      ['Wygasła', false],
      ['Wycofana', false],
      ['Błąd', false],
    ])('isInFlight(%p) === %p', (status, expected) => {
      expect(isInFlight(status)).toBe(expected)
    })
  })

  describe('sendButtonLabel', () => {
    it.each([
      [null, 'Podpisz umowę'],
      [undefined, 'Podpisz umowę'],
      ['', 'Podpisz umowę'],
      ['Błąd', 'Wyślij ponownie do podpisu'],
      ['Odrzucona', 'Wyślij ponownie do podpisu'],
      ['Wygasła', 'Wyślij ponownie do podpisu'],
      ['Wycofana', 'Wyślij ponownie do podpisu'],
    ])('sendButtonLabel(%p) === %p', (status, expected) => {
      expect(sendButtonLabel(status)).toBe(expected)
    })

    // Statuses that block sending (in flight / already signed) never reach
    // the button in the UI (it's not rendered — see canSend), but the
    // function itself should still degrade sanely rather than throw.
    it.each([
      ['Wysyłanie', 'Podpisz umowę'],
      ['Wysłana', 'Podpisz umowę'],
      ['Podpisana', 'Podpisz umowę'],
    ])('sendButtonLabel(%p) === %p (nieużywane w UI, ale bez wyjątku)', (status, expected) => {
      expect(sendButtonLabel(status)).toBe(expected)
    })
  })
})
