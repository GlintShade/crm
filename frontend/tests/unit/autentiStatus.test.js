import {
  AUTENTI_BADGE,
  badgeFor,
  canSend,
  groupRecipients,
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

    it('zwraca wpis badge dla znanego statusu (dokument domyślny: umowa)', () => {
      expect(badgeFor('Podpisana')).toEqual({ label: 'Podpisana', theme: 'green' })
      expect(badgeFor('Błąd')).toEqual({ label: 'Błąd wysyłki', theme: 'red' })
    })

    it('zwraca null dla nieznanego statusu zamiast rzucać wyjątek', () => {
      expect(badgeFor('CośNieistniejącego')).toBeNull()
    })

    it('dla dokument="umowa" etykiety pozostają rodzaju żeńskiego (bez zmian)', () => {
      expect(badgeFor('Wysłana', 'umowa')).toEqual({ label: 'Wysłana do podpisu', theme: 'amber' })
      expect(badgeFor('Podpisana', 'umowa')).toEqual({ label: 'Podpisana', theme: 'green' })
      expect(badgeFor('Odrzucona', 'umowa')).toEqual({ label: 'Odrzucona', theme: 'red' })
      expect(badgeFor('Wygasła', 'umowa')).toEqual({ label: 'Wygasła', theme: 'gray' })
      expect(badgeFor('Wycofana', 'umowa')).toEqual({ label: 'Wycofana', theme: 'gray' })
    })

    it('dla dokument="kredyt" etykiety są rodzaju męskiego (formularz kredytowy)', () => {
      expect(badgeFor('Wysłana', 'kredyt')).toEqual({ label: 'Wysłany do podpisu', theme: 'amber' })
      expect(badgeFor('Podpisana', 'kredyt')).toEqual({ label: 'Podpisany', theme: 'green' })
      expect(badgeFor('Odrzucona', 'kredyt')).toEqual({ label: 'Odrzucony', theme: 'red' })
      expect(badgeFor('Wygasła', 'kredyt')).toEqual({ label: 'Wygasły', theme: 'gray' })
      expect(badgeFor('Wycofana', 'kredyt')).toEqual({ label: 'Wycofany', theme: 'gray' })
    })

    it('dla dokument="kredyt" statusy bez rodzajowego rzeczownika zostają bez zmian', () => {
      expect(badgeFor('Wysyłanie', 'kredyt')).toEqual({ label: 'Wysyłanie…', theme: 'blue' })
      expect(badgeFor('Błąd', 'kredyt')).toEqual({ label: 'Błąd wysyłki', theme: 'red' })
    })

    it('nieznany status z dokument="kredyt" nadal zwraca null', () => {
      expect(badgeFor('CośNieistniejącego', 'kredyt')).toBeNull()
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
    ])('sendButtonLabel(%p) === %p (bez dokument, domyślnie umowa)', (status, expected) => {
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

    it.each([
      [null, 'Podpisz umowę'],
      [undefined, 'Podpisz umowę'],
      ['', 'Podpisz umowę'],
      ['Błąd', 'Wyślij ponownie do podpisu'],
      ['Odrzucona', 'Wyślij ponownie do podpisu'],
      ['Wygasła', 'Wyślij ponownie do podpisu'],
      ['Wycofana', 'Wyślij ponownie do podpisu'],
    ])('sendButtonLabel(%p, "umowa") === %p (jawny dokument, bez zmian)', (status, expected) => {
      expect(sendButtonLabel(status, 'umowa')).toBe(expected)
    })

    it.each([
      [null, 'Podpisz wniosek'],
      [undefined, 'Podpisz wniosek'],
      ['', 'Podpisz wniosek'],
      ['Błąd', 'Wyślij ponownie do podpisu'],
      ['Odrzucona', 'Wyślij ponownie do podpisu'],
      ['Wygasła', 'Wyślij ponownie do podpisu'],
      ['Wycofana', 'Wyślij ponownie do podpisu'],
    ])('sendButtonLabel(%p, "kredyt") === %p', (status, expected) => {
      expect(sendButtonLabel(status, 'kredyt')).toBe(expected)
    })
  })

  describe('groupRecipients', () => {
    const klient = { full_name: 'Jan Kowalski', email: 'jan@example.com', role: 'SIGNER' }
    const prezes = { full_name: 'Anna Prezes', email: 'prezes@proenergy.pro', role: 'SIGNER' }
    const handlowiec = {
      full_name: 'Piotr Handlowiec',
      email: 'piotr@proenergy.pro',
      role: 'VIEWER',
    }
    const archiwum = { full_name: 'Archiwum', email: 'archiwum@proenergy.pro', role: 'VIEWER' }

    it('dzieli listę na SIGNER i VIEWER, zachowując kolejność', () => {
      const result = groupRecipients([klient, prezes, handlowiec, archiwum], null)
      expect(result.signers).toEqual([klient, prezes])
      expect(result.viewers).toEqual([handlowiec, archiwum])
    })

    it('działa z samymi podpisującymi (brak VIEWER)', () => {
      const result = groupRecipients([klient], null)
      expect(result.signers).toEqual([klient])
      expect(result.viewers).toEqual([])
    })

    it.each([[null], [undefined], [[]]])(
      'przy braku proposed_recipients (%p) wraca do proposed_signer jako jedynego SIGNER',
      (recipients) => {
        const fallback = { full_name: 'Jan Kowalski', email: 'jan@example.com' }
        const result = groupRecipients(recipients, fallback)
        expect(result.signers).toEqual([
          { full_name: 'Jan Kowalski', email: 'jan@example.com', role: 'SIGNER' },
        ])
        expect(result.viewers).toEqual([])
      },
    )

    it('zwraca puste grupy, gdy brak zarówno proposed_recipients jak i proposed_signer', () => {
      const result = groupRecipients(null, null)
      expect(result.signers).toEqual([])
      expect(result.viewers).toEqual([])
    })
  })
})
