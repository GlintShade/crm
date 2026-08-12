// Wspólny moduł formatowania kwot w złotówkach.
//
// Powód istnienia: cztery komponenty (KalkulatorTab.vue, KalkulatorCPTab.vue,
// deal/ZestawTab.vue, deal/FakturyTab.vue) niosły własną kopię funkcji
// `plnFmt`, każda przez `Math.round()` zaokrąglającą do pełnych złotych —
// co po cichu niszczyło grosze zamiast je wyświetlać. Ten moduł je zastępuje.
//
// Serwer jest jedynym źródłem prawdy o kwotach (liczy je jako `Decimal`);
// ten plik wyłącznie zaokrągla i formatuje wartości do wyświetlenia na
// ekranie, nic tu nie jest zapisywane ani wysyłane z powrotem.

// Twarda spacja (U+00A0) jako separator tysięcy — zapisana przez escape
// ` `, nie jako niewidoczny znak wprost w źródle, żeby edytor/diff jej
// przez pomyłkę nie zamienił na zwykłą spację. Zwykła spacja pozwoliłaby
// przeglądarce złamać kwotę w środku liczby przy zawijaniu wiersza.
const NBSP = '\u00A0'

/**
 * Parse an arbitrary input into a finite number, treating anything
 * non-numeric (including empty string, null, undefined, NaN, Infinity)
 * as zero. Mirrors the "puste = 0" convention used across the calculator
 * utils (see cpMarza.js's parsujStawke).
 *
 * @param {*} value - raw input value
 * @returns {number} finite number, or 0 when unparsable
 */
function parseFiniteOrZero(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Round a monetary amount to 2 decimal places, half-away-from-zero — the
 * same rule the server applies via Python's
 * `Decimal(...).quantize(Decimal("0.01"), ROUND_HALF_UP)`.
 *
 * Nie używać gołego `Math.round`: w JS `Math.round(-0.5)` daje `-0`
 * (zaokrągla połówki w stronę +∞), więc wartości ujemne rozjechałyby się
 * z serwerem. Zamiast tego mnożymy przez znak i zaokrąglamy wartość
 * bezwzględną — to gwarantuje, że `roundPln(-x) === -roundPln(x)`.
 *
 * Przesunięcie o dwa miejsca dziesiętne NIE dzieje się przez zwykłe
 * mnożenie `× 100` — dla wejść typu `1.005` to zawodzi mimo doklejonego
 * `Number.EPSILON`: `1.005` jest w IEEE-754 przechowywane jako
 * `1.00499999999999989…`, więc `1.005 * 100` daje `100.49999999999999`,
 * a odległość do `100.5` (~1.4e-14) jest o rzędy wielkości większa niż
 * `Number.EPSILON` (~2.2e-16) — dodanie epsilona tego nie naprawia i wynik
 * po cichu zaokrągla się w dół zamiast w górę. Zamiast tego dokładamy `'e2'`
 * do zapisu tekstowego liczby i pozwalamy silnikowi JS sparsować wynikowy
 * napis wprost do najbliższej liczby double (`"1.005e2"` → `100.5`,
 * dokładnie) — to omija błąd zaokrąglenia, który wprowadza pośrednie
 * mnożenie zmiennoprzecinkowe.
 *
 * Przesunięcie przez tekst zawodzi, gdy `String(abs)` sam użyje notacji
 * wykładniczej — dzieje się tak dla `|x| < 1e-6` oraz `|x| >= 1e21`. Wtedy
 * doklejenie `'e2'` tworzy zniekształcony literał w rodzaju `"1e-7e2"`, a
 * `Number(...)` z takiego napisu daje `NaN`. Ten przypadek nie jest
 * teoretyczny — `cpMarza.js` liczy `zysk`/`pula` odejmowaniem bliskich
 * sobie kwot (`netto - koszt - prowizja`), co regularnie zostawia resztki
 * rzędu `1e-17`; bez zabezpieczenia poniżej `roundPln` zwracał `NaN`, a
 * `formatPlnAmount` renderował dosłowny napis `"NaN,undefined"` na ekranie.
 *
 * Dwa podzakresy tego przypadku traktujemy osobno, bo zwykłe mnożenie
 * `× 100 ÷ 100` zachowuje się różnie na ich krańcach:
 * — `|x| < 1e-6`: wynik i tak zaokrągla się do 0 groszy, więc zwracamy 0
 *   wprost, bez okrężnej arytmetyki.
 * — `|x| >= 1e21`: druga cyfra po przecinku dawno nie jest reprezentowalna
 *   w double na tę skalę, więc zaokrąglanie do groszy jest bez znaczenia —
 *   a próba `× 100 ÷ 100` (np. dla `1e21`) po cichu *psuje* wartość przez
 *   zaokrąglenie pośredniego iloczynu (`1e21 × 100 = 1e23`, którego double
 *   już nie odda dokładnie), mimo że wejście było dokładne. Zwracamy więc
 *   liczbę niezmienioną zamiast przepuszczać ją przez zbędne mnożenie.
 *
 * Wynik `0` jest normalizowany z `-0` do `0` (`result === 0 ? 0 : result`)
 * — inaczej ujemne mikroskopijne wejście (np. `-1e-7`) dawałoby `-0`, co
 * `Object.is`/`toBe` w testach odróżnia od `0`, choć w formatowaniu obie
 * wartości i tak wyglądają identycznie.
 *
 * @param {*} value - amount to round (Number or numeric String)
 * @returns {number} amount rounded to 2 decimals, half-away-from-zero
 */
export function roundPln(value) {
  const n = parseFiniteOrZero(value)
  const sign = n < 0 ? -1 : 1
  const abs = Math.abs(n)
  const shifted = Number(`${abs}e2`)

  let result
  if (Number.isFinite(shifted)) {
    result = (sign * Math.round(shifted)) / 100
  } else if (abs < 1e-6) {
    result = 0
  } else {
    result = sign * abs
  }

  return result === 0 ? 0 : result
}

/**
 * Format a non-negative amount as a "digits.digits" string with exactly
 * two decimals, guaranteed to never fall back to exponential notation.
 *
 * `Number.prototype.toFixed` itself switches to exponential notation for
 * `|x| >= 1e21` (e.g. `(1e21).toFixed(2) === '1e+21'`) — a string with no
 * `.` in it. Left unguarded, splitting that on `.` in {@link groupDigits}
 * yields an `undefined` decimal part, which is exactly how the
 * `"NaN,undefined"` defect happened in the first place, just one range
 * higher. For that range we build the whole-number digits via
 * `toLocaleString` (which does not have the same 1e21 cutoff) and treat
 * the amount as having no fractional part — money at that magnitude has
 * no meaningful grosze digit anyway.
 *
 * @param {number} nonNegative - non-negative, finite amount
 * @returns {string} amount with exactly two decimals, never exponential
 */
function toFixedSafe(nonNegative) {
  const fixed = nonNegative.toFixed(2)
  if (fixed.includes('e') || fixed.includes('E')) {
    const whole = nonNegative.toLocaleString('en-US', {
      useGrouping: false,
      maximumFractionDigits: 0,
    })
    return `${whole}.00`
  }
  return fixed
}

/**
 * Group the digits of a non-negative, fixed-two-decimal amount string
 * ("52018.20") into Polish thousands groups separated by a non-breaking
 * space, with a comma as the decimal separator ("52 018,20").
 *
 * @param {string} fixed - amount already formatted by {@link toFixedSafe}
 * @returns {string} grouped Polish-formatted digits, without sign or suffix
 */
function groupDigits(fixed) {
  const [wholePart, decimalPart] = fixed.split('.')
  const grouped = wholePart.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP)
  return `${grouped},${decimalPart}`
}

/**
 * Format an amount for display, without a currency suffix: two decimals
 * always, comma as decimal separator, non-breaking-space thousands
 * grouping, and a leading ASCII `-` for negative values applied to the
 * whole formatted number (grouping applies only to the digits).
 *
 * Rounding happens through {@link roundPln} first, so this never disagrees
 * with `roundPln` on the boundary cases (half-away-from-zero).
 *
 * Pas i szelki: `roundPln` już nie powinien zwracać nic poza skończoną
 * liczbą, ale to wyjście trafia wprost do DOM, więc dokładamy tu jeszcze
 * jedną osłonę na wypadek, gdyby jakiś przyszły wywołujący ominął
 * `roundPln` i podał tu `NaN`/`Infinity` bezpośrednio — bez tego
 * `Math.abs(NaN).toFixed(2)` daje napis `"NaN"`, którego `groupDigits`
 * nie potrafi rozbić na część dziesiętną, i na ekran trafia dosłowne
 * `"NaN,undefined"`.
 *
 * @param {*} value - amount to format (Number or numeric String)
 * @returns {string} formatted amount, e.g. '52 018,20'
 */
export function formatPlnAmount(value) {
  const roundedRaw = roundPln(value)
  const rounded = Number.isFinite(roundedRaw) ? roundedRaw : 0
  const negative = rounded < 0
  // toFixedSafe na wartości bezwzględnej: liczymy na już zaokrąglonej
  // przez roundPln wartości (żeby nie rozjechać się z jej regułą
  // half-away-from-zero), a samo formatowanie do "digits.digits" idzie
  // przez toFixedSafe, nie goły toFixed — ten drugi przechodzi w zapis
  // wykładniczy dla |x| >= 1e21 i wtedy groupDigits nie miałby czego
  // rozbić na część dziesiętną.
  const fixed = toFixedSafe(Math.abs(rounded))
  const formatted = groupDigits(fixed)
  return negative ? `-${formatted}` : formatted
}

/**
 * Format an amount for display with the ' zł' currency suffix, matching
 * the UI convention already used across the calculator tabs.
 *
 * @param {*} value - amount to format (Number or numeric String)
 * @returns {string} formatted amount with suffix, e.g. '52 018,20 zł'
 */
export function formatPln(value) {
  return `${formatPlnAmount(value)} zł`
}
