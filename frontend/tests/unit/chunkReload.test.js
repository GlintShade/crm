import { isStaleChunkError, shouldReload } from '@/utils/chunkReload'

describe('Stale-chunk detection (chunkReload)', () => {
  describe('isStaleChunkError — matches known stale-chunk wordings', () => {
    it.each([
      ['Chrome/Vite', 'Failed to fetch dynamically imported module'],
      ['Safari', 'Importing a module script failed'],
      ['Firefox', 'error loading dynamically imported module'],
    ])('matches %s wording', (_browser, message) => {
      expect(isStaleChunkError(new Error(message))).toBe(true)
    })

    it('matches regardless of case', () => {
      expect(
        isStaleChunkError(new Error('IMPORTING A MODULE SCRIPT FAILED')),
      ).toBe(true)
      expect(
        isStaleChunkError({ message: 'FAILED TO FETCH DYNAMICALLY IMPORTED MODULE: foo.js' }),
      ).toBe(true)
    })

    it('matches when the pattern is a substring of a longer message', () => {
      expect(
        isStaleChunkError(
          new Error(
            'TypeError: Failed to fetch dynamically imported module: https://crm.proenergy.pro/assets/crm/frontend/GlobalModals-Bo_1Lx7A.js',
          ),
        ),
      ).toBe(true)
    })
  })

  describe('isStaleChunkError — does not match unrelated errors', () => {
    it('does not match a plain TypeError unrelated to imports', () => {
      expect(isStaleChunkError(new TypeError('Cannot read properties of undefined'))).toBe(
        false,
      )
    })

    it('does not match a network/server error', () => {
      expect(isStaleChunkError(new Error('Request failed with status code 500'))).toBe(false)
    })

    it.each([
      ['undefined', undefined],
      ['null', null],
      ['a string instead of an error object', 'Importing a module script failed'],
      ['an object with no message', { code: 'ERR_MODULE' }],
      ['an object with a non-string message', { message: 42 }],
      ['an object with an empty message', { message: '' }],
    ])('does not throw and returns false for %s', (_label, value) => {
      expect(isStaleChunkError(value)).toBe(false)
    })
  })
})

describe('Reload cooldown (chunkReload)', () => {
  const NOW = 1_000_000
  const COOLDOWN_MS = 60_000

  describe('shouldReload — allows reload when there is no valid recent timestamp', () => {
    it.each([
      ['no stored value (fresh tab)', null],
      ['undefined', undefined],
      ['empty string', ''],
      ['non-numeric garbage', 'not-a-timestamp'],
      ['NaN as a string', 'NaN'],
    ])('returns true for %s', (_label, storedValue) => {
      expect(shouldReload(storedValue, NOW, COOLDOWN_MS)).toBe(true)
    })
  })

  describe('shouldReload — cooldown window', () => {
    it('returns false when the last reload was inside the cooldown window', () => {
      const lastReloadAt = NOW - (COOLDOWN_MS - 1)
      expect(shouldReload(String(lastReloadAt), NOW, COOLDOWN_MS)).toBe(false)
    })

    it('returns false right at the moment of a previous reload (elapsed 0)', () => {
      expect(shouldReload(String(NOW), NOW, COOLDOWN_MS)).toBe(false)
    })

    it('returns true once the cooldown has fully elapsed', () => {
      const lastReloadAt = NOW - COOLDOWN_MS
      expect(shouldReload(String(lastReloadAt), NOW, COOLDOWN_MS)).toBe(true)
    })

    it('returns true well after the cooldown window (e.g. a later, unrelated deploy)', () => {
      const lastReloadAt = NOW - COOLDOWN_MS * 100
      expect(shouldReload(String(lastReloadAt), NOW, COOLDOWN_MS)).toBe(true)
    })
  })

  describe('shouldReload — clock skew', () => {
    it('treats a stored timestamp in the future as recent and withholds reload', () => {
      const lastReloadAt = NOW + 5_000
      expect(shouldReload(String(lastReloadAt), NOW, COOLDOWN_MS)).toBe(false)
    })
  })
})
