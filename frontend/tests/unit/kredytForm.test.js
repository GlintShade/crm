import {
  TAK_NIE_OPCJE,
  WYKSZTALCENIE_OPCJE,
  RODZAJ_DOKUMENTU_OPCJE,
  STAN_CYWILNY_OPCJE,
  PRACA_FORMA_OPCJE,
  PRACA_OKRES_OPCJE,
  DZIALALNOSC_FORMA_OPCJE,
  PREFILL_KEYS,
  BASE_FIELDS,
  GRUPY,
  WARUNKI_WIDOCZNOSCI,
  defaultForm,
  buildDane,
  hydrateFrom,
  normalizujKwote,
  formatujNumerRachunku,
  formatujNumerRachunkuZKursorem,
  poleWidoczne,
  widocznePola,
  BAZA_WYMAGANE,
  brakujacePola,
  brakujaceDaneKlienta,
} from '@/utils/kredytForm'

function deepFreeze(value) {
  Object.freeze(value)
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object' && !Object.isFrozen(child)) {
      deepFreeze(child)
    }
  }
  return value
}

// Mirror of crm/test_volteo_kredyt_pdf.py's `_kredyt()` fixture, same
// field-for-field values, so overrides in the tests below reproduce the
// backend TestBrakujacePola* case matrix 1:1. Every income-group toggle
// starts off; tests that want to check a specific group turn it on
// explicitly via `nadpisania`.
function kredytKompletny(nadpisania = {}) {
  const baza = {
    miejsce_urodzenia: 'Warszawa',
    rodzaj_dokumentu: 'Dowód osobisty',
    seria_numer_dokumentu: 'ABC123456',
    data_wydania_dokumentu: '2020-01-15',
    data_waznosci_dokumentu: '2030-01-15',
    adres_zameldowania_taki_sam: 'Tak',
    adres_zameldowania: '',
    adres_korespondencji_taki_sam: 'Tak',
    adres_korespondencji: '',
    wyksztalcenie: 'wyższe',
    stan_cywilny: 'Kawaler/panna',
    liczba_osob_na_utrzymaniu: '0',
    kwota_800_plus: '0',
    dochod_wspolmalzonka: '0',
    zrodlo_dochodu_malzonka: 'Emerytura',
    oplaty_miesieczne: '500',
    suma_zobowiazan: '0',
    numer_rachunku: 'PL61109010140000071219812874',
    praca_wlaczone: false,
    praca_forma: '',
    praca_data_zatrudnienia: '',
    praca_okres: '',
    praca_okres_od: '',
    praca_okres_do: '',
    praca_nip: '',
    praca_nazwa_zakladu: '',
    praca_adres_telefon: '',
    praca_kwota_dochodu: '',
    emerytura_wlaczone: false,
    emerytura_numer_swiadczenia: '',
    emerytura_od_kiedy: '',
    emerytura_kwota_dochodu: '',
    renta_wlaczone: false,
    renta_numer_swiadczenia: '',
    renta_od_kiedy: '',
    renta_kwota_dochodu: '',
    dzialalnosc_wlaczone: false,
    dzialalnosc_forma_opodatkowania: '',
    dzialalnosc_forma_inna: '',
    dzialalnosc_nip: '',
    dzialalnosc_nazwa: '',
    dzialalnosc_adres: '',
    dzialalnosc_telefon: '',
    dzialalnosc_od_kiedy: '',
    dzialalnosc_kwota_dochodu: '',
    gospodarstwo_wlaczone: false,
    gospodarstwo_nip: '',
    gospodarstwo_od_kiedy: '',
    gospodarstwo_kwota_dochodu: '',
    inne_wlaczone: false,
    inne_1_typ: '',
    inne_1_kwota: '',
    inne_2_typ: '',
    inne_2_kwota: '',
  }
  return { ...baza, ...nadpisania }
}

describe('Kredyt form logic', () => {
  describe('option constants', () => {
    it('pins the authoritative option wording (PDF transcription, except STAN_CYWILNY_OPCJE which is an owner override)', () => {
      expect(TAK_NIE_OPCJE).toEqual(['', 'Tak', 'Nie'])
      expect(WYKSZTALCENIE_OPCJE).toEqual([
        '',
        'wyższe',
        'średnie',
        'zawodowe',
        'podstawowe/gimnazjalne',
      ])
      expect(RODZAJ_DOKUMENTU_OPCJE).toEqual(['', 'Dowód osobisty', 'Paszport', 'Karta pobytu'])
      expect(STAN_CYWILNY_OPCJE).toEqual([
        '',
        'Kawaler/panna',
        'Rozwiedziony/a',
        'Małżeństwo - rozdzielność majątkowa',
        'Małżeństwo - wspólnota majątkowa',
        'Wdowiec/wdowa',
        'Separacja',
      ])
      expect(PRACA_FORMA_OPCJE).toEqual(['', 'Umowa o pracę', 'Umowa zlecenie', 'Umowa o dzieło'])
      expect(PRACA_OKRES_OPCJE).toEqual(['', 'Czas określony', 'Czas nieokreślony'])
      expect(DZIALALNOSC_FORMA_OPCJE).toEqual([
        '',
        'ryczałt',
        'księga przychodów i rozchodów (KPiR)',
        'inne',
      ])
    })

    it('uses the lowercase "inne" value, not "Inne"', () => {
      expect(DZIALALNOSC_FORMA_OPCJE).toContain('inne')
      expect(DZIALALNOSC_FORMA_OPCJE).not.toContain('Inne')
    })

    it('exports the 10 read-only prefill keys', () => {
      expect(PREFILL_KEYS).toEqual([
        'pesel',
        'imiona',
        'nazwisko',
        'telefon',
        'email',
        'kod_pocztowy',
        'miejscowosc',
        'ulica',
        'nr_domu',
        'nr_lokalu',
      ])
    })
  })

  describe('GRUPY', () => {
    it('declares six income groups', () => {
      expect(GRUPY).toHaveLength(6)
      expect(GRUPY.map((g) => g.key)).toEqual([
        'praca',
        'emerytura',
        'renta',
        'dzialalnosc',
        'gospodarstwo',
        'inne',
      ])
    })

    it('every group fieldname (toggle + fields) exists as a key in defaultForm()', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        expect(form).toHaveProperty(grupa.wlaczone)
        grupa.fields.forEach((fn) => {
          expect(form).toHaveProperty(fn)
        })
      })
    })

    it('every base field exists as a key in defaultForm()', () => {
      const form = defaultForm()
      BASE_FIELDS.forEach((fn) => {
        expect(form).toHaveProperty(fn)
      })
    })
  })

  describe('defaultForm', () => {
    it('sets every toggle to false and every other field to the empty string', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        expect(form[grupa.wlaczone]).toBe(false)
        grupa.fields.forEach((fn) => {
          expect(form[fn]).toBe('')
        })
      })
      BASE_FIELDS.forEach((fn) => {
        expect(form[fn]).toBe('')
      })
    })

    it('returns independent copies on each call', () => {
      const first = defaultForm()
      const second = defaultForm()
      first.miejsce_urodzenia = 'Warszawa'
      first.praca_wlaczone = true
      expect(second.miejsce_urodzenia).toBe('')
      expect(second.praca_wlaczone).toBe(false)
      expect(first).not.toBe(second)
    })
  })

  describe('buildDane', () => {
    it('passes base fields through unchanged', () => {
      const form = defaultForm()
      form.miejsce_urodzenia = 'Kraków'
      form.wyksztalcenie = 'wyższe'
      form.liczba_osob_na_utrzymaniu = '2'

      const dane = buildDane(form)
      expect(dane.miejsce_urodzenia).toBe('Kraków')
      expect(dane.wyksztalcenie).toBe('wyższe')
      expect(dane.liczba_osob_na_utrzymaniu).toBe('2')
    })

    it('never mutates a deeply frozen form', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      form.praca_forma = 'Umowa o pracę'
      form.praca_kwota_dochodu = '5000'
      form.miejsce_urodzenia = 'Poznań'
      const before = JSON.parse(JSON.stringify(form))

      deepFreeze(form)
      buildDane(form)

      expect(form).toEqual(before)
    })

    it('sends null for every field of a group whose toggle is off', () => {
      const form = defaultForm()
      form.praca_forma = 'Umowa zlecenie'
      form.praca_kwota_dochodu = '4200'
      form.praca_wlaczone = false

      const dane = buildDane(form)
      expect(dane.praca_wlaczone).toBe(false)
      expect(dane.praca_forma).toBeNull()
      expect(dane.praca_data_zatrudnienia).toBeNull()
      expect(dane.praca_okres).toBeNull()
      expect(dane.praca_okres_od).toBeNull()
      expect(dane.praca_okres_do).toBeNull()
      expect(dane.praca_nip).toBeNull()
      expect(dane.praca_nazwa_zakladu).toBeNull()
      expect(dane.praca_adres_telefon).toBeNull()
      expect(dane.praca_kwota_dochodu).toBeNull()
    })

    it('passes through every field of a group whose toggle is on', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      form.praca_forma = 'Umowa o pracę'
      form.praca_data_zatrudnienia = '2020-01-15'
      form.praca_okres = 'Czas określony'
      form.praca_okres_od = '2020-01-15'
      form.praca_okres_do = '2028-01-15'
      form.praca_nip = '1234567890'
      form.praca_nazwa_zakladu = 'ACME sp. z o.o.'
      form.praca_adres_telefon = 'ul. Testowa 1, 500600700'
      form.praca_kwota_dochodu = '6500'

      const dane = buildDane(form)
      expect(dane).toMatchObject({
        praca_wlaczone: true,
        praca_forma: 'Umowa o pracę',
        praca_data_zatrudnienia: '2020-01-15',
        praca_okres: 'Czas określony',
        praca_okres_od: '2020-01-15',
        praca_okres_do: '2028-01-15',
        praca_nip: '1234567890',
        praca_nazwa_zakladu: 'ACME sp. z o.o.',
        praca_adres_telefon: 'ul. Testowa 1, 500600700',
        praca_kwota_dochodu: '6500',
      })
    })

    it('all-off toggle matrix: every group nulled, every toggle false', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        grupa.fields.forEach((fn, i) => {
          form[fn] = `wartosc-${i}`
        })
      })

      const dane = buildDane(form)
      GRUPY.forEach((grupa) => {
        expect(dane[grupa.wlaczone]).toBe(false)
        grupa.fields.forEach((fn) => {
          expect(dane[fn]).toBeNull()
        })
      })
    })

    it('all-on toggle matrix: every group passed through, every toggle true', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        form[grupa.wlaczone] = true
        grupa.fields.forEach((fn, i) => {
          form[fn] = `wartosc-${i}`
        })
      })

      const dane = buildDane(form)
      GRUPY.forEach((grupa) => {
        expect(dane[grupa.wlaczone]).toBe(true)
        grupa.fields.forEach((fn, i) => {
          expect(dane[fn]).toBe(`wartosc-${i}`)
        })
      })
    })

    it('mixed matrix: only the toggled-off groups are nulled', () => {
      const form = defaultForm()
      form.emerytura_wlaczone = true
      form.emerytura_numer_swiadczenia = 'EMR-1'
      form.emerytura_od_kiedy = '2018-05-01'
      form.emerytura_kwota_dochodu = '3200'

      form.dzialalnosc_wlaczone = true
      form.dzialalnosc_forma_opodatkowania = 'ryczałt'
      form.dzialalnosc_nip = '9998887776'
      form.dzialalnosc_nazwa = 'Firma X'
      form.dzialalnosc_kwota_dochodu = '9000'

      // renta and inne stay off
      form.renta_numer_swiadczenia = 'stale'
      form.inne_1_typ = 'stypendium'
      form.inne_1_kwota = '400'

      const dane = buildDane(form)

      expect(dane.emerytura_wlaczone).toBe(true)
      expect(dane.emerytura_numer_swiadczenia).toBe('EMR-1')
      expect(dane.emerytura_od_kiedy).toBe('2018-05-01')
      expect(dane.emerytura_kwota_dochodu).toBe('3200')

      expect(dane.dzialalnosc_wlaczone).toBe(true)
      expect(dane.dzialalnosc_forma_opodatkowania).toBe('ryczałt')
      expect(dane.dzialalnosc_nip).toBe('9998887776')
      expect(dane.dzialalnosc_nazwa).toBe('Firma X')
      expect(dane.dzialalnosc_kwota_dochodu).toBe('9000')
      // Group is ON but this field was never typed — passed through as the
      // untouched default '', NOT nulled (nulling only happens when the
      // group's own toggle is off).
      expect(dane.dzialalnosc_forma_inna).toBe('')

      expect(dane.renta_wlaczone).toBe(false)
      expect(dane.renta_numer_swiadczenia).toBeNull()

      expect(dane.inne_wlaczone).toBe(false)
      expect(dane.inne_1_typ).toBeNull()
      expect(dane.inne_1_kwota).toBeNull()
    })

    it('returns a fresh object every call', () => {
      const form = defaultForm()
      const first = buildDane(form)
      const second = buildDane(form)
      first.miejsce_urodzenia = 'zmienione'
      expect(second.miejsce_urodzenia).toBe('')
      expect(first).not.toBe(second)
    })
  })

  describe('hydrateFrom', () => {
    it('coerces every toggle to a real boolean', () => {
      const record = {
        praca_wlaczone: 1,
        emerytura_wlaczone: 0,
        renta_wlaczone: null,
        dzialalnosc_wlaczone: true,
        gospodarstwo_wlaczone: false,
        inne_wlaczone: undefined,
      }
      const form = hydrateFrom(record)
      expect(form.praca_wlaczone).toBe(true)
      expect(form.emerytura_wlaczone).toBe(false)
      expect(form.renta_wlaczone).toBe(false)
      expect(form.dzialalnosc_wlaczone).toBe(true)
      expect(form.gospodarstwo_wlaczone).toBe(false)
      expect(form.inne_wlaczone).toBe(false)
    })

    it('coerces null/undefined non-toggle fields to the empty string', () => {
      const record = {
        miejsce_urodzenia: null,
        wyksztalcenie: undefined,
        praca_forma: null,
      }
      const form = hydrateFrom(record)
      expect(form.miejsce_urodzenia).toBe('')
      expect(form.wyksztalcenie).toBe('')
      expect(form.praca_forma).toBe('')
    })

    it('preserves real values, including falsy-but-meaningful strings and numbers', () => {
      const record = {
        miejsce_urodzenia: 'Gdańsk',
        liczba_osob_na_utrzymaniu: 0,
        praca_wlaczone: true,
        praca_kwota_dochodu: '0',
      }
      const form = hydrateFrom(record)
      expect(form.miejsce_urodzenia).toBe('Gdańsk')
      expect(form.liczba_osob_na_utrzymaniu).toBe(0)
      expect(form.praca_wlaczone).toBe(true)
      expect(form.praca_kwota_dochodu).toBe('0')
    })

    it('treats a null record like an empty one, returning defaultForm()', () => {
      expect(hydrateFrom(null)).toEqual(defaultForm())
      expect(hydrateFrom(undefined)).toEqual(defaultForm())
    })

    it('never mutates the source record', () => {
      const record = deepFreeze({ praca_wlaczone: true, praca_forma: 'Umowa o pracę' })
      expect(() => hydrateFrom(record)).not.toThrow()
      expect(record.praca_wlaczone).toBe(true)
    })

    it('returns a fresh object every call', () => {
      const record = { miejsce_urodzenia: 'Łódź' }
      const first = hydrateFrom(record)
      const second = hydrateFrom(record)
      first.miejsce_urodzenia = 'zmienione'
      expect(second.miejsce_urodzenia).toBe('Łódź')
      expect(first).not.toBe(second)
    })
  })

  describe('normalizujKwote', () => {
    it('appends ",00" to a bare integer', () => {
      expect(normalizujKwote('123')).toBe('123,00')
    })

    it('pads a single decimal digit to two', () => {
      expect(normalizujKwote('123,4')).toBe('123,40')
    })

    it('leaves an already-two-decimal-digit amount unchanged', () => {
      expect(normalizujKwote('123,90')).toBe('123,90')
    })

    it('treats a trailing comma with no digits as zero decimals', () => {
      expect(normalizujKwote('123,')).toBe('123,00')
    })

    it('converts a dot decimal separator to a comma and pads it', () => {
      expect(normalizujKwote('123.4')).toBe('123,40')
    })

    it('treats a trailing dot with no digits as zero decimals', () => {
      expect(normalizujKwote('123.')).toBe('123,00')
    })

    it('preserves user-typed thousands-space grouping, touching only the decimal part', () => {
      expect(normalizujKwote('12 300')).toBe('12 300,00')
      expect(normalizujKwote('12 300,5')).toBe('12 300,50')
      expect(normalizujKwote('1 234 567')).toBe('1 234 567,00')
    })

    it('returns empty or whitespace-only text unchanged', () => {
      expect(normalizujKwote('')).toBe('')
      expect(normalizujKwote('   ')).toBe('   ')
    })

    it('returns text unchanged when it fails a Decimal-like parse', () => {
      expect(normalizujKwote('abc')).toBe('abc')
      expect(normalizujKwote('1,2,3')).toBe('1,2,3')
      expect(normalizujKwote(',123')).toBe(',123')
      expect(normalizujKwote('1.2.3')).toBe('1.2.3')
    })

    it('leaves more than 2 decimal digits unchanged rather than rounding', () => {
      expect(normalizujKwote('123,456')).toBe('123,456')
      expect(normalizujKwote('123.4567')).toBe('123.4567')
    })

    it('never mutates its argument and never throws on non-string input', () => {
      const tekst = '123'
      const wynik = normalizujKwote(tekst)
      expect(tekst).toBe('123')
      expect(wynik).toBe('123,00')
      expect(() => normalizujKwote(null)).not.toThrow()
      expect(() => normalizujKwote(undefined)).not.toThrow()
    })
  })

  describe('formatujNumerRachunku', () => {
    it('groups a full 26-digit NRB as 2 digits then groups of 4', () => {
      expect(formatujNumerRachunku('61109010140000071219812874')).toBe(
        '61 1090 1014 0000 0712 1981 2874',
      )
    })

    it('formats progressively as digits accumulate (partial input)', () => {
      expect(formatujNumerRachunku('6')).toBe('6')
      expect(formatujNumerRachunku('61')).toBe('61')
      expect(formatujNumerRachunku('611')).toBe('61 1')
      expect(formatujNumerRachunku('611090')).toBe('61 1090')
    })

    it('is idempotent — formatting an already-formatted value is a no-op', () => {
      const raz = formatujNumerRachunku('61109010140000071219812874')
      expect(formatujNumerRachunku(raz)).toBe(raz)
    })

    it('regroups a value with misplaced spaces, keying only off the digits', () => {
      expect(formatujNumerRachunku('61 10 9010')).toBe('61 1090 10')
    })

    it('strips a non-breaking space and regroups from the digits underneath', () => {
      expect(formatujNumerRachunku('61 1090')).toBe('61 1090')
    })

    it('returns empty and whitespace-only input as empty string', () => {
      expect(formatujNumerRachunku('')).toBe('')
      expect(formatujNumerRachunku('   ')).toBe('')
    })

    it('returns non-digit content verbatim — server has no format validation for this field', () => {
      expect(formatujNumerRachunku('PL61109010140000071219812874')).toBe(
        'PL61109010140000071219812874',
      )
      expect(formatujNumerRachunku('61-1090')).toBe('61-1090')
      expect(formatujNumerRachunku('abc')).toBe('abc')
    })

    it('groups more than 26 digits too — this is a display mask, not a length validator', () => {
      expect(formatujNumerRachunku('6110901014000007121981287499')).toBe(
        '61 1090 1014 0000 0712 1981 2874 99',
      )
    })

    it('returns non-string input unchanged and never throws', () => {
      expect(formatujNumerRachunku(null)).toBeNull()
      expect(formatujNumerRachunku(undefined)).toBeUndefined()
      expect(formatujNumerRachunku(123)).toBe(123)
    })
  })

  describe('formatujNumerRachunkuZKursorem', () => {
    it('keeps the caret at the end when it starts at the end', () => {
      // '611090' (6 digits) -> '61 1090' (7 chars); caret was after all 6
      // digits, so it lands after all digits in the formatted string too.
      expect(formatujNumerRachunkuZKursorem('611090', 6)).toEqual({
        tekst: '61 1090',
        kursor: 7,
      })
    })

    it('lands the caret right after a digit just typed mid-string', () => {
      // Rep had '61 1090' and typed '5' after '61 1', producing raw
      // '61 15090' with the caret at index 5 (right after the new '5').
      // That's the 4th digit in the raw text (6,1,1,5); the formatted
      // string '61 1509 0' has its 4th digit ('5') at index 4, so the
      // caret goes to index 5 — still immediately after that same '5'.
      expect(formatujNumerRachunkuZKursorem('61 15090', 5)).toEqual({
        tekst: '61 1509 0',
        kursor: 5,
      })
    })

    it('keeps caret 0 at 0', () => {
      expect(formatujNumerRachunkuZKursorem('611090', 0)).toEqual({
        tekst: '61 1090',
        kursor: 0,
      })
    })

    it('deleting a digit just after a space keeps the caret stable', () => {
      // Raw '6110914' (7 digits) with the caret at index 5 — 5 digits
      // precede it (6,1,1,0,9). The formatted string '61 1091 4' has its
      // 5th digit ('9') at index 5, so the caret goes to index 6,
      // immediately after that digit rather than jumping to the end.
      expect(formatujNumerRachunkuZKursorem('6110914', 5)).toEqual({
        tekst: '61 1091 4',
        kursor: 6,
      })
    })

    it('pasting a full 26-digit number with the caret at the end lands the caret at the end', () => {
      const surowy = '61109010140000071219812874'
      const sformatowany = '61 1090 1014 0000 0712 1981 2874'
      expect(formatujNumerRachunkuZKursorem(surowy, surowy.length)).toEqual({
        tekst: sformatowany,
        kursor: sformatowany.length,
      })
    })

    it('keeps the original caret untouched for verbatim (non-digit) passthrough', () => {
      expect(formatujNumerRachunkuZKursorem('61-1090', 3)).toEqual({
        tekst: '61-1090',
        kursor: 3,
      })
      expect(formatujNumerRachunkuZKursorem('abc', 2)).toEqual({ tekst: 'abc', kursor: 2 })
    })
  })

  describe('poleWidoczne', () => {
    it('is visible when the field has no rule in WARUNKI_WIDOCZNOSCI', () => {
      const form = defaultForm()
      expect(poleWidoczne(form, 'miejsce_urodzenia')).toBe(true)
    })

    it('a "value" rule matches on equality', () => {
      const form = defaultForm()
      form.adres_zameldowania_taki_sam = 'Nie'
      expect(poleWidoczne(form, 'adres_zameldowania')).toBe(true)
    })

    it('a "value" rule hides the field when the value does not match', () => {
      const form = defaultForm()
      form.adres_zameldowania_taki_sam = 'Tak'
      expect(poleWidoczne(form, 'adres_zameldowania')).toBe(false)
    })

    it('a "values" rule shows the field for every non-empty PRACA_OKRES_OPCJE value', () => {
      PRACA_OKRES_OPCJE.filter((v) => v !== '').forEach((wartosc) => {
        const form = defaultForm()
        form.praca_okres = wartosc
        expect(poleWidoczne(form, 'praca_okres_od')).toBe(true)
      })
    })

    it('a "values" rule hides the field for the empty PRACA_OKRES_OPCJE value', () => {
      const form = defaultForm()
      form.praca_okres = ''
      expect(poleWidoczne(form, 'praca_okres_od')).toBe(false)
    })

    it('never mutates the form it inspects', () => {
      const form = deepFreeze(defaultForm())
      expect(() => poleWidoczne(form, 'praca_okres_od')).not.toThrow()
    })
  })

  describe('WARUNKI_WIDOCZNOSCI (contract mirrored against crm/volteo_kredyt.py brakujace_pola)', () => {
    it('praca_okres_od is visible for every non-empty PRACA_OKRES_OPCJE value (backend requires it whenever "praca" is on, regardless of period type)', () => {
      PRACA_OKRES_OPCJE.filter((v) => v !== '').forEach((wartosc) => {
        const form = defaultForm()
        form.praca_okres = wartosc
        expect(poleWidoczne(form, 'praca_okres_od')).toBe(true)
      })
    })

    it('praca_okres_do is visible only for "Czas określony"', () => {
      const form1 = defaultForm()
      form1.praca_okres = 'Czas określony'
      expect(poleWidoczne(form1, 'praca_okres_do')).toBe(true)

      const form2 = defaultForm()
      form2.praca_okres = 'Czas nieokreślony'
      expect(poleWidoczne(form2, 'praca_okres_do')).toBe(false)

      const form3 = defaultForm()
      form3.praca_okres = ''
      expect(poleWidoczne(form3, 'praca_okres_do')).toBe(false)
    })

    it('dzialalnosc_forma_inna is visible only for the lowercase "inne"', () => {
      const form1 = defaultForm()
      form1.dzialalnosc_forma_opodatkowania = 'inne'
      expect(poleWidoczne(form1, 'dzialalnosc_forma_inna')).toBe(true)

      const form2 = defaultForm()
      form2.dzialalnosc_forma_opodatkowania = 'ryczałt'
      expect(poleWidoczne(form2, 'dzialalnosc_forma_inna')).toBe(false)
    })

    it('adres_zameldowania is visible only for "Nie"', () => {
      const form1 = defaultForm()
      form1.adres_zameldowania_taki_sam = 'Nie'
      expect(poleWidoczne(form1, 'adres_zameldowania')).toBe(true)

      const form2 = defaultForm()
      form2.adres_zameldowania_taki_sam = 'Tak'
      expect(poleWidoczne(form2, 'adres_zameldowania')).toBe(false)
    })

    it('adres_korespondencji is visible only for "Nie"', () => {
      const form1 = defaultForm()
      form1.adres_korespondencji_taki_sam = 'Nie'
      expect(poleWidoczne(form1, 'adres_korespondencji')).toBe(true)

      const form2 = defaultForm()
      form2.adres_korespondencji_taki_sam = 'Tak'
      expect(poleWidoczne(form2, 'adres_korespondencji')).toBe(false)
    })
  })

  describe('widocznePola', () => {
    it('includes a field hidden by rule when its fieldname is present in brakujace (safety net)', () => {
      const form = defaultForm()
      form.praca_okres = 'Czas nieokreślony'
      const fields = [
        { fieldname: 'praca_okres_do', label: 'Okres zatrudnienia do' },
      ]
      const wynik = widocznePola(fields, form, ['praca_okres_do'])
      expect(wynik.map((f) => f.fieldname)).toEqual(['praca_okres_do'])
    })

    it('excludes a field hidden by rule and absent from brakujace', () => {
      const form = defaultForm()
      form.praca_okres = 'Czas nieokreślony'
      const fields = [
        { fieldname: 'praca_okres_do', label: 'Okres zatrudnienia do' },
      ]
      const wynik = widocznePola(fields, form, [])
      expect(wynik).toEqual([])
    })

    it('preserves field order', () => {
      const form = defaultForm()
      form.praca_okres = 'Czas określony'
      const fields = [
        { fieldname: 'praca_forma', label: 'a' },
        { fieldname: 'praca_okres', label: 'b' },
        { fieldname: 'praca_okres_od', label: 'c' },
        { fieldname: 'praca_okres_do', label: 'd' },
        { fieldname: 'praca_nip', label: 'e' },
      ]
      const wynik = widocznePola(fields, form, [])
      expect(wynik.map((f) => f.fieldname)).toEqual([
        'praca_forma',
        'praca_okres',
        'praca_okres_od',
        'praca_okres_do',
        'praca_nip',
      ])
    })

    it('defaults brakujace to an empty list when omitted', () => {
      const form = defaultForm()
      form.praca_okres = 'Czas nieokreślony'
      const fields = [{ fieldname: 'praca_okres_do', label: 'Okres zatrudnienia do' }]
      expect(widocznePola(fields, form)).toEqual([])
    })

    it('never mutates its inputs (deep-compare before/after)', () => {
      const form = defaultForm()
      form.praca_okres = 'Czas nieokreślony'
      const fields = [
        { fieldname: 'praca_okres_od', label: 'Okres zatrudnienia od' },
        { fieldname: 'praca_okres_do', label: 'Okres zatrudnienia do' },
      ]
      const brakujace = ['praca_okres_do']

      const formPrzed = JSON.parse(JSON.stringify(form))
      const fieldsPrzed = JSON.parse(JSON.stringify(fields))
      const brakujacePrzed = JSON.parse(JSON.stringify(brakujace))

      widocznePola(fields, form, brakujace)

      expect(form).toEqual(formPrzed)
      expect(fields).toEqual(fieldsPrzed)
      expect(brakujace).toEqual(brakujacePrzed)
    })

    it('regression (ops#139): praca_okres = "Czas nieokreślony" shows praca_okres_od and hides praca_okres_do', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      form.praca_okres = 'Czas nieokreślony'
      const pracaFields = GRUPY.find((g) => g.key === 'praca').fields.map((fn) => ({
        fieldname: fn,
        label: fn,
      }))

      const wynik = widocznePola(pracaFields, form, [])
      const nazwy = wynik.map((f) => f.fieldname)

      expect(nazwy).toContain('praca_okres_od')
      expect(nazwy).not.toContain('praca_okres_do')
    })
  })

  describe('BAZA_WYMAGANE', () => {
    it('is the 15-field list mirrored from crm/volteo_kredyt.py _BAZA_WYMAGANE, numer_rachunku absent', () => {
      expect(BAZA_WYMAGANE).toEqual([
        'miejsce_urodzenia',
        'rodzaj_dokumentu',
        'seria_numer_dokumentu',
        'data_wydania_dokumentu',
        'data_waznosci_dokumentu',
        'adres_zameldowania_taki_sam',
        'adres_korespondencji_taki_sam',
        'wyksztalcenie',
        'stan_cywilny',
        'liczba_osob_na_utrzymaniu',
        'kwota_800_plus',
        'dochod_wspolmalzonka',
        'zrodlo_dochodu_malzonka',
        'oplaty_miesieczne',
        'suma_zobowiazan',
      ])
      expect(BAZA_WYMAGANE).not.toContain('numer_rachunku')
    })
  })

  describe('brakujacePola (mirror of crm/volteo_kredyt.py brakujace_pola, case matrix from crm/test_volteo_kredyt_pdf.py TestBrakujacePola*)', () => {
    describe('pola bazowe (TestBrakujacePolaBazowe)', () => {
      it('a: pusty rekord daje liste bazowa', () => {
        expect(brakujacePola({})).toEqual(BAZA_WYMAGANE)
      })

      it('b: kompletny rekord bez grup dochodu nic nie brakuje', () => {
        expect(brakujacePola(kredytKompletny())).toEqual([])
      })

      it('c: zero amount liczy sie jako wypelnione', () => {
        const dane = kredytKompletny({
          kwota_800_plus: '0',
          dochod_wspolmalzonka: '0',
          suma_zobowiazan: '0',
        })
        const wynik = brakujacePola(dane)
        expect(wynik).not.toContain('kwota_800_plus')
        expect(wynik).not.toContain('dochod_wspolmalzonka')
        expect(wynik).not.toContain('suma_zobowiazan')
      })

      it('d: bialy znak jest brakujacy', () => {
        const dane = kredytKompletny({ miejsce_urodzenia: '   ' })
        expect(brakujacePola(dane)).toContain('miejsce_urodzenia')
      })

      it('e: nie mutuje wejscia', () => {
        const dane = deepFreeze(kredytKompletny())
        expect(() => brakujacePola(dane)).not.toThrow()
      })

      it('f: numer_rachunku pusty nie jest brakujacy', () => {
        const dane = kredytKompletny({ numer_rachunku: '' })
        expect(brakujacePola(dane)).not.toContain('numer_rachunku')
      })
    })

    describe('pola warunkowe adresy (TestBrakujacePolaWarunkoweAdresy)', () => {
      it('a: adres_zameldowania wymagany gdy Nie', () => {
        const dane = kredytKompletny({ adres_zameldowania_taki_sam: 'Nie', adres_zameldowania: '' })
        expect(brakujacePola(dane)).toContain('adres_zameldowania')
      })

      it('b: adres_zameldowania niewymagany gdy Tak', () => {
        const dane = kredytKompletny({ adres_zameldowania_taki_sam: 'Tak', adres_zameldowania: '' })
        expect(brakujacePola(dane)).not.toContain('adres_zameldowania')
      })

      it('c: adres_zameldowania wypelniony wystarcza', () => {
        const dane = kredytKompletny({
          adres_zameldowania_taki_sam: 'Nie',
          adres_zameldowania: 'ul. Polna 10',
        })
        expect(brakujacePola(dane)).not.toContain('adres_zameldowania')
      })

      it('d: adres_korespondencji analogicznie', () => {
        const dane1 = kredytKompletny({ adres_korespondencji_taki_sam: 'Nie', adres_korespondencji: '' })
        expect(brakujacePola(dane1)).toContain('adres_korespondencji')

        const dane2 = kredytKompletny({
          adres_korespondencji_taki_sam: 'Nie',
          adres_korespondencji: 'ul. Inna 3',
        })
        expect(brakujacePola(dane2)).not.toContain('adres_korespondencji')
      })
    })

    describe('grupy dochodu (TestBrakujacePolaGrupyDochodu)', () => {
      it('a: zero grup wlaczonych kompletne', () => {
        expect(brakujacePola(kredytKompletny())).toEqual([])
      })

      it('b: praca wlaczona dodaje jej pola', () => {
        const dane = kredytKompletny({ praca_wlaczone: 1 })
        const wynik = brakujacePola(dane)
        ;['praca_forma', 'praca_data_zatrudnienia', 'praca_okres', 'praca_okres_od'].forEach((pole) => {
          expect(wynik).toContain(pole)
        })
        // praca_okres_do NIE jest wymagane, bo praca_okres nie jest "Czas określony".
        expect(wynik).not.toContain('praca_okres_do')
      })

      it('c: praca_okres_do wymagany tylko dla Czas okreslony', () => {
        const daneOkreslony = kredytKompletny({
          praca_wlaczone: 1,
          praca_forma: 'Umowa o pracę',
          praca_data_zatrudnienia: '2020-01-01',
          praca_okres: 'Czas określony',
          praca_okres_od: '2020-01-01',
          praca_nip: '123',
          praca_nazwa_zakladu: 'Firma',
          praca_adres_telefon: 'tel',
          praca_kwota_dochodu: '5000',
        })
        expect(brakujacePola(daneOkreslony)).toContain('praca_okres_do')

        const daneNieokreslony = { ...daneOkreslony, praca_okres: 'Czas nieokreślony' }
        expect(brakujacePola(daneNieokreslony)).not.toContain('praca_okres_do')
      })

      it('d: praca_okres_od zawsze wymagany gdy praca wlaczona', () => {
        const dane = kredytKompletny({
          praca_wlaczone: 1,
          praca_okres: 'Czas nieokreślony',
          praca_okres_od: '',
        })
        expect(brakujacePola(dane)).toContain('praca_okres_od')
      })

      it('e: emerytura wlaczona dodaje jej pola', () => {
        const dane = kredytKompletny({ emerytura_wlaczone: 1 })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('emerytura_numer_swiadczenia')
        expect(wynik).toContain('emerytura_od_kiedy')
        expect(wynik).toContain('emerytura_kwota_dochodu')
      })

      it('f: renta wlaczona dodaje jej pola', () => {
        const dane = kredytKompletny({ renta_wlaczone: 1 })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('renta_numer_swiadczenia')
        expect(wynik).toContain('renta_od_kiedy')
        expect(wynik).toContain('renta_kwota_dochodu')
      })

      it('g: gospodarstwo wlaczone dodaje jego pola', () => {
        const dane = kredytKompletny({ gospodarstwo_wlaczone: 1 })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('gospodarstwo_nip')
        expect(wynik).toContain('gospodarstwo_od_kiedy')
        expect(wynik).toContain('gospodarstwo_kwota_dochodu')
      })

      it('h: dzialalnosc wlaczona bez formy inna nie wymaga opisu', () => {
        const dane = kredytKompletny({
          dzialalnosc_wlaczone: 1,
          dzialalnosc_forma_opodatkowania: 'ryczałt',
          dzialalnosc_nip: '123',
          dzialalnosc_nazwa: 'Firma',
          dzialalnosc_adres: 'adres',
          dzialalnosc_telefon: 'tel',
          dzialalnosc_od_kiedy: '2020-01-01',
          dzialalnosc_kwota_dochodu: '5000',
        })
        expect(brakujacePola(dane)).toEqual([])
      })

      it('i: dzialalnosc forma inne wymaga opisu', () => {
        const dane = kredytKompletny({
          dzialalnosc_wlaczone: 1,
          dzialalnosc_forma_opodatkowania: 'inne',
          dzialalnosc_forma_inna: '',
          dzialalnosc_nip: '123',
          dzialalnosc_nazwa: 'Firma',
          dzialalnosc_adres: 'adres',
          dzialalnosc_telefon: 'tel',
          dzialalnosc_od_kiedy: '2020-01-01',
          dzialalnosc_kwota_dochodu: '5000',
        })
        expect(brakujacePola(dane)).toContain('dzialalnosc_forma_inna')
      })

      it('test_e_wielka_litera_inne_nie_pasuje: "Inne" (wielka litera) nie pasuje, forma_inna nie jest wymagana', () => {
        const dane = kredytKompletny({
          dzialalnosc_wlaczone: 1,
          dzialalnosc_forma_opodatkowania: 'Inne',
          dzialalnosc_forma_inna: '',
          dzialalnosc_nip: '123',
          dzialalnosc_nazwa: 'Firma',
          dzialalnosc_adres: 'adres',
          dzialalnosc_telefon: 'tel',
          dzialalnosc_od_kiedy: '2020-01-01',
          dzialalnosc_kwota_dochodu: '5000',
        })
        expect(brakujacePola(dane)).not.toContain('dzialalnosc_forma_inna')
      })

      it('j: inne druga para opcjonalna', () => {
        const dane = kredytKompletny({ inne_wlaczone: 1, inne_1_typ: 'Alimenty', inne_1_kwota: '1000' })
        expect(brakujacePola(dane)).toEqual([])
      })

      it('k: inne pierwsza para wymagana', () => {
        const dane = kredytKompletny({ inne_wlaczone: 1, inne_1_typ: '', inne_1_kwota: '' })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('inne_1_typ')
        expect(wynik).toContain('inne_1_kwota')
        expect(wynik).not.toContain('inne_2_typ')
        expect(wynik).not.toContain('inne_2_kwota')
      })

      it('l: wiele grup naraz', () => {
        const dane = kredytKompletny({ praca_wlaczone: 1, gospodarstwo_wlaczone: 1 })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('praca_forma')
        expect(wynik).toContain('gospodarstwo_nip')
        expect(wynik).not.toContain('emerytura_numer_swiadczenia')
        expect(wynik).not.toContain('renta_numer_swiadczenia')
      })
    })

    describe('nowe nazwy pol, rozbicie dokumentu i adresu firmy (TestBrakujacePolaNoweNazwyPol)', () => {
      it('a: rodzaj_dokumentu i seria_numer puste sa brakujace', () => {
        const dane = kredytKompletny({ rodzaj_dokumentu: '', seria_numer_dokumentu: '' })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('rodzaj_dokumentu')
        expect(wynik).toContain('seria_numer_dokumentu')
      })

      it('b: rodzaj_dokumentu i seria_numer wypelnione wystarcza', () => {
        const dane = kredytKompletny({
          rodzaj_dokumentu: 'Dowód osobisty',
          seria_numer_dokumentu: 'ABC123456',
        })
        const wynik = brakujacePola(dane)
        expect(wynik).not.toContain('rodzaj_dokumentu')
        expect(wynik).not.toContain('seria_numer_dokumentu')
      })

      it('c: jedno z pary puste nadal brakujace', () => {
        const dane = kredytKompletny({ rodzaj_dokumentu: 'Dowód osobisty', seria_numer_dokumentu: '' })
        const wynik = brakujacePola(dane)
        expect(wynik).not.toContain('rodzaj_dokumentu')
        expect(wynik).toContain('seria_numer_dokumentu')
      })

      it('d: dzialalnosc adres i telefon wymagane gdy grupa wlaczona', () => {
        const dane = kredytKompletny({
          dzialalnosc_wlaczone: 1,
          dzialalnosc_forma_opodatkowania: 'ryczałt',
          dzialalnosc_nip: '123',
          dzialalnosc_nazwa: 'Firma',
          dzialalnosc_adres: '',
          dzialalnosc_telefon: '',
          dzialalnosc_od_kiedy: '2020-01-01',
          dzialalnosc_kwota_dochodu: '5000',
        })
        const wynik = brakujacePola(dane)
        expect(wynik).toContain('dzialalnosc_adres')
        expect(wynik).toContain('dzialalnosc_telefon')
      })

      it('e: dzialalnosc adres i telefon wypelnione wystarcza', () => {
        const dane = kredytKompletny({
          dzialalnosc_wlaczone: 1,
          dzialalnosc_forma_opodatkowania: 'ryczałt',
          dzialalnosc_nip: '123',
          dzialalnosc_nazwa: 'Firma',
          dzialalnosc_adres: 'ul. Firmowa 1',
          dzialalnosc_telefon: '500600700',
          dzialalnosc_od_kiedy: '2020-01-01',
          dzialalnosc_kwota_dochodu: '5000',
        })
        expect(brakujacePola(dane)).toEqual([])
      })

      it('f: dzialalnosc wylaczona nie wymaga adresu ani telefonu', () => {
        const dane = kredytKompletny({ dzialalnosc_wlaczone: 0, dzialalnosc_adres: '', dzialalnosc_telefon: '' })
        const wynik = brakujacePola(dane)
        expect(wynik).not.toContain('dzialalnosc_adres')
        expect(wynik).not.toContain('dzialalnosc_telefon')
      })
    })
  })

  describe('brakujaceDaneKlienta (mirror of crm/api/kredyt.py _PREFILL_ETYKIETY)', () => {
    const kompletnyPrefill = {
      pesel: '90010112345',
      imiona: 'Jan',
      nazwisko: 'Kowalski',
      telefon: '500600700',
      email: 'jan@example.com',
      kod_pocztowy: '00-001',
      miejscowosc: 'Warszawa',
      ulica: 'Kwiatowa',
      nr_domu: '5',
      nr_lokalu: '12',
    }

    it('returns an empty list when all 9 required keys are filled', () => {
      expect(brakujaceDaneKlienta(kompletnyPrefill)).toEqual([])
    })

    it('returns the PL label, not the fieldname, for a missing key', () => {
      const prefill = { ...kompletnyPrefill, pesel: '' }
      expect(brakujaceDaneKlienta(prefill)).toEqual(['PESEL'])
    })

    it('nr_lokalu is never checked, missing it alone blocks nothing', () => {
      const prefill = { ...kompletnyPrefill, nr_lokalu: '' }
      expect(brakujaceDaneKlienta(prefill)).toEqual([])
    })

    it('an empty/undefined prefill reports all 9 labels in the mirrored order', () => {
      const oczekiwane = [
        'PESEL',
        'Imię/imiona',
        'Nazwisko',
        'Telefon',
        'E-mail',
        'Kod pocztowy',
        'Miejscowość',
        'Ulica',
        'Nr domu',
      ]
      expect(brakujaceDaneKlienta({})).toEqual(oczekiwane)
      expect(brakujaceDaneKlienta(undefined)).toEqual(oczekiwane)
    })

    it('uses a falsy check like the backend, not a whitespace trim: a whitespace-only value counts as filled', () => {
      const prefill = { ...kompletnyPrefill, ulica: '   ' }
      expect(brakujaceDaneKlienta(prefill)).toEqual([])
    })

    it('never mutates its argument', () => {
      const prefill = deepFreeze({ ...kompletnyPrefill })
      expect(() => brakujaceDaneKlienta(prefill)).not.toThrow()
    })
  })

  describe('ops#147 regression: praca_okres_od transient state (documents why the widocznePola safety net exists)', () => {
    it('the instant "praca" is switched on, before praca_okres has a value, praca_okres_od is required but hidden by the pure rule; the safety net (brakujacePola fed back into widocznePola) is what actually shows it', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      const pracaFields = GRUPY.find((g) => g.key === 'praca').fields.map((fn) => ({
        fieldname: fn,
        label: fn,
      }))

      const braki = brakujacePola(form)
      expect(braki).toContain('praca_okres_od')

      // Pure rule visibility (no safety net) still hides it in this
      // transient state, exactly the class of mismatch the `brakujace`
      // safety-net parameter of widocznePola() exists to absorb. KredytTab.vue
      // always calls widocznePola() with the live brakujacePola(form) result
      // as that third argument, never `[]`, so this transient state never
      // actually reproduces the ops#139 banner deadlock in the running app.
      const bezSiatki = widocznePola(pracaFields, form, [])
      expect(bezSiatki.map((f) => f.fieldname)).not.toContain('praca_okres_od')

      const zSiatka = widocznePola(pracaFields, form, braki)
      expect(zSiatka.map((f) => f.fieldname)).toContain('praca_okres_od')
    })
  })

  describe('invariant (ops#147): required fields are visible via WARUNKI_WIDOCZNOSCI alone, for every "settled" state', () => {
    // "Settled" = every conditional discriminator (praca_okres,
    // dzialalnosc_forma_opodatkowania, adres_*_taki_sam) already carries a
    // concrete value, i.e. every state actually reachable once the rep has
    // interacted with the group's own discriminator field. The one
    // deliberately excluded transient state (a group just switched on, its
    // own discriminator still blank) is covered separately above: that is
    // exactly what the widocznePola `brakujace` safety-net parameter exists
    // to absorb at runtime, so it is not expected to hold under the "pure
    // rule, no safety net" check here.
    const wszystkiePola = [...BASE_FIELDS, ...GRUPY.flatMap((g) => g.fields)].map((fn) => ({
      fieldname: fn,
    }))

    const matrix = [
      kredytKompletny(),
      kredytKompletny({ adres_zameldowania_taki_sam: 'Nie', adres_zameldowania: '' }),
      kredytKompletny({ adres_korespondencji_taki_sam: 'Nie', adres_korespondencji: '' }),
      kredytKompletny({
        praca_wlaczone: true,
        praca_okres: 'Czas określony',
        praca_forma: 'Umowa o pracę',
        praca_data_zatrudnienia: '2020-01-01',
        praca_okres_od: '',
        praca_okres_do: '',
        praca_nip: '123',
        praca_nazwa_zakladu: 'Firma',
        praca_adres_telefon: 'tel',
        praca_kwota_dochodu: '5000',
      }),
      kredytKompletny({
        praca_wlaczone: true,
        praca_okres: 'Czas nieokreślony',
        praca_forma: 'Umowa o pracę',
        praca_data_zatrudnienia: '2020-01-01',
        praca_okres_od: '',
        praca_nip: '123',
        praca_nazwa_zakladu: 'Firma',
        praca_adres_telefon: 'tel',
        praca_kwota_dochodu: '5000',
      }),
      kredytKompletny({
        dzialalnosc_wlaczone: true,
        dzialalnosc_forma_opodatkowania: 'inne',
        dzialalnosc_forma_inna: '',
        dzialalnosc_nip: '123',
        dzialalnosc_nazwa: 'Firma',
        dzialalnosc_adres: 'adres',
        dzialalnosc_telefon: 'tel',
        dzialalnosc_od_kiedy: '2020-01-01',
        dzialalnosc_kwota_dochodu: '5000',
      }),
      kredytKompletny({ emerytura_wlaczone: true }),
      kredytKompletny({ renta_wlaczone: true }),
      kredytKompletny({ gospodarstwo_wlaczone: true }),
      kredytKompletny({ inne_wlaczone: true }),
      kredytKompletny({
        praca_wlaczone: true,
        praca_okres: 'Czas nieokreślony',
        praca_forma: 'Umowa o pracę',
        praca_data_zatrudnienia: '2020-01-01',
        praca_okres_od: '2020-01-01',
        praca_nip: '123',
        praca_nazwa_zakladu: 'Firma',
        praca_adres_telefon: 'tel',
        praca_kwota_dochodu: '5000',
        gospodarstwo_wlaczone: true,
      }),
    ]

    it('every fieldname brakujacePola(form) returns is present in widocznePola(wszystkiePola, form, [])', () => {
      matrix.forEach((form) => {
        const braki = brakujacePola(form)
        const widoczneNazwy = widocznePola(wszystkiePola, form, []).map((f) => f.fieldname)
        braki.forEach((pole) => {
          expect(widoczneNazwy).toContain(pole)
        })
      })
    })
  })
})
