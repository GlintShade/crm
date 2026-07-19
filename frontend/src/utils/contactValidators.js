// VOLTEO: framework-agnostic validators for the Contact ("Klient") create
// form — no Vue imports so these stay unit-testable in isolation. Every
// validator returns a Polish error string, or `null` when the value is valid.
// Required-ness is NOT enforced here (the caller decides whether an empty
// value is acceptable) — an empty/blank value always validates as `null`.

const NAME_CHARS_RE = /^[\p{L} .'-]+$/u
const DIGIT_RE = /\d/
// Deliberately permissive (format sanity, not full RFC 5322) — matches the
// level of strictness used elsewhere in the app for email fields.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isBlank(v) {
  return v === null || v === undefined || String(v).trim() === ''
}

/**
 * Shared implementation behind validateFirstName/validateLastName.
 * @param {string} v
 * @param {{ noDigits: string, invalid: string }} messages
 */
function validatePersonName(v, messages) {
  if (isBlank(v)) return null
  const value = String(v)

  if (DIGIT_RE.test(value)) return messages.noDigits
  if (!NAME_CHARS_RE.test(value)) return messages.invalid

  return null
}

export function validateFirstName(v) {
  return validatePersonName(v, {
    noDigits: 'Imię nie może zawierać cyfr.',
    invalid: 'Imię zawiera niedozwolone znaki.',
  })
}

export function validateLastName(v) {
  return validatePersonName(v, {
    noDigits: 'Nazwisko nie może zawierać cyfr.',
    invalid: 'Nazwisko zawiera niedozwolone znaki.',
  })
}

/** Strip everything but digits — the canonical PESEL form used for checksum + duplicate-check payloads. */
export function normalizePesel(v) {
  return String(v ?? '').replace(/\s+/g, '')
}

/**
 * PESEL checksum — MUST match the backend implementation.
 * Weights = [1,3,7,9,1,3,7,9,1,3] applied to digits[0..9];
 * control = (10 - (total % 10)) % 10; valid iff control === digits[10].
 */
const PESEL_WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]

export function validatePesel(v) {
  if (isBlank(v)) return null
  const value = normalizePesel(v)

  if (value.length !== 11 || !/^\d{11}$/.test(value)) {
    return 'Numer PESEL musi składać się z 11 cyfr.'
  }

  const digits = value.split('').map(Number)
  const total = PESEL_WEIGHTS.reduce((sum, w, i) => sum + digits[i] * w, 0)
  const control = (10 - (total % 10)) % 10

  if (control !== digits[10]) {
    return 'Nieprawidłowy numer PESEL (błędna suma kontrolna).'
  }

  return null
}

export function validateEmail(v) {
  if (isBlank(v)) return null
  if (!EMAIL_RE.test(String(v).trim())) return 'Nieprawidłowy adres e-mail.'
  return null
}

/** Digits-only phone number, with a leading "48" country code stripped when present as an 11-digit string. */
export function normalizePhone(v) {
  const digitsOnly = String(v ?? '').replace(/\D/g, '')
  if (digitsOnly.length === 11 && digitsOnly.startsWith('48')) {
    return digitsOnly.slice(2)
  }
  return digitsOnly
}

export function validatePhone(v) {
  if (isBlank(v)) return null
  const value = normalizePhone(v)
  if (value.length !== 9) return 'Numer telefonu musi zawierać 9 cyfr.'
  return null
}
