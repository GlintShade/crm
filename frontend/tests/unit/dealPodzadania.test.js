import {
  STANY_PODZADAN,
  STAN_META,
  parsePodzadania,
  stanFor,
  dozwoloneStany,
  tasksForStage,
  stageSummary,
  buildPodzadaniePayload,
  entryFromPayload,
  applyOptimistic,
} from '@/utils/dealPodzadania'

describe('Podzadania rurociągu CP — czysta logika (dealPodzadania)', () => {
  describe('parsePodzadania — śmieci na wejściu', () => {
    it.each([
      [null, 'null'],
      [undefined, 'undefined'],
      ['', 'pusty string'],
      ['nie json', 'nieparsowalny string'],
      [42, 'liczba'],
      [true, 'bool'],
      [[], 'tablica'],
      ['[]', 'JSON tablicy jako string'],
    ])('zwraca {} dla raw=%p (%s)', (raw) => {
      expect(parsePodzadania(raw)).toEqual({})
    })

    it('toleruje podwójnie zakodowany JSON', () => {
      const wpis = { 'dok:x': { stan: 'accepted' } }
      const razPodwojnie = JSON.stringify(JSON.stringify(wpis))
      expect(parsePodzadania(razPodwojnie)).toEqual(wpis)
    })

    it('parsuje zwykły JSON string tak samo jak obiekt', () => {
      const wpis = { 'dok:x': { stan: 'waiting' } }
      expect(parsePodzadania(JSON.stringify(wpis))).toEqual(wpis)
    })

    it('odrzuca wpisy nie-dict (string/liczba/tablica/null jako wartość klucza)', () => {
      const raw = {
        'dok:a': 'accepted',
        'dok:b': 42,
        'dok:c': ['accepted'],
        'dok:d': null,
        'dok:e': { stan: 'accepted' },
      }
      expect(parsePodzadania(raw)).toEqual({ 'dok:e': { stan: 'accepted' } })
    })

    it('odrzuca wpisy, których stan nie jest w STANY_PODZADAN', () => {
      const raw = {
        'dok:a': { stan: 'zrobione' },
        'dok:b': { stan: '' },
        'dok:c': { stan: undefined },
        'dok:d': { inne_pole: 1 },
        'dok:e': { stan: 'error' },
      }
      expect(parsePodzadania(raw)).toEqual({ 'dok:e': { stan: 'error' } })
    })

    it.each(STANY_PODZADAN)('akceptuje każdy prawidłowy stan: %s', (stan) => {
      expect(parsePodzadania({ 'dok:x': { stan } })).toEqual({ 'dok:x': { stan } })
    })

    it('zwraca NOWY obiekt — nie mutuje raw, ani nie dzieli referencji wpisów', () => {
      const wpis = { stan: 'accepted', note: 'coś' }
      const raw = { 'dok:x': wpis }
      const wynik = parsePodzadania(raw)
      expect(wynik).not.toBe(raw)
      expect(wynik['dok:x']).not.toBe(wpis)
      expect(wynik['dok:x']).toEqual(wpis)
    })

    it('nie mutuje przekazanego raw', () => {
      const raw = { 'dok:x': { stan: 'accepted' }, 'dok:y': { stan: 'zły stan' } }
      const kopia = JSON.parse(JSON.stringify(raw))
      parsePodzadania(raw)
      expect(raw).toEqual(kopia)
    })
  })

  describe('stanFor — domyślny stan', () => {
    it.each([
      [null, 'null'],
      [undefined, 'undefined'],
      [{}, 'pusta mapa'],
    ])('zwraca "brak" dla mapy=%p (%s), niezależnie od klucza', (mapa) => {
      expect(stanFor(mapa, 'dok:x')).toBe('brak')
    })

    it.each([[null], [undefined], ['']])(
      'zwraca "brak" dla klucz=%p, niezależnie od mapy',
      (klucz) => {
        expect(stanFor({ 'dok:x': { stan: 'accepted' } }, klucz)).toBe('brak')
      },
    )

    it('zwraca "brak", gdy klucz nie istnieje w mapie', () => {
      expect(stanFor({ 'dok:a': { stan: 'accepted' } }, 'dok:nieistniejacy')).toBe('brak')
    })

    it('zwraca stan wpisu, gdy klucz istnieje i stan jest prawidłowy', () => {
      const mapa = { 'dok:a': { stan: 'waiting' }, 'dok:b': { stan: 'error' } }
      expect(stanFor(mapa, 'dok:a')).toBe('waiting')
      expect(stanFor(mapa, 'dok:b')).toBe('error')
    })

    it('zwraca "brak", gdy wpis istnieje ale ma nieprawidłowy/brakujący stan', () => {
      expect(stanFor({ 'dok:a': { stan: 'coś dziwnego' } }, 'dok:a')).toBe('brak')
      expect(stanFor({ 'dok:a': {} }, 'dok:a')).toBe('brak')
      expect(stanFor({ 'dok:a': 'accepted' }, 'dok:a')).toBe('brak')
    })

    it('czyta przez zwykły dostęp do właściwości (bezpieczne na reactive() — bez hasOwnProperty)', () => {
      // Regresja: żadna implementacja stanFor() nie powinna wołać
      // hasOwnProperty/Object.hasOwn na mapie — to jedyny sposób, by ta sama
      // funkcja bezpiecznie działała, gdy wołający owinie mapę w reactive().
      const mapa = { 'dok:a': { stan: 'accepted' } }
      const hasOwnSpy = vi.spyOn(Object.prototype, 'hasOwnProperty')
      const hasOwnStaticSpy = vi.spyOn(Object, 'hasOwn')
      stanFor(mapa, 'dok:a')
      expect(hasOwnSpy).not.toHaveBeenCalled()
      expect(hasOwnStaticSpy).not.toHaveBeenCalled()
      hasOwnSpy.mockRestore()
      hasOwnStaticSpy.mockRestore()
    })
  })

  describe('dozwoloneStany — macierz typ × nd_dozwolone (lustro dozwolone_stany z crm/volteo_pipeline.py)', () => {
    it.each([
      [{ typ: 'weryfikacja', nd_dozwolone: false }, ['waiting', 'accepted', 'error', 'brak']],
      [
        { typ: 'weryfikacja', nd_dozwolone: true },
        ['waiting', 'accepted', 'error', 'nd', 'brak'],
      ],
      [{ typ: 'odhaczenie', nd_dozwolone: false }, ['accepted', 'brak']],
      [{ typ: 'odhaczenie', nd_dozwolone: true }, ['accepted', 'nd', 'brak']],
      // typ nieznany/brak traktowany jak 'odhaczenie' (baza = tylko accepted) — mirror Pythona (else-gałąź)
      [{ typ: 'coś innego', nd_dozwolone: false }, ['accepted', 'brak']],
      [{}, ['accepted', 'brak']],
    ])('dozwoloneStany(%p) === %p', (def, expected) => {
      expect(dozwoloneStany(def)).toEqual(expected)
    })

    it('null/undefined definicja nie rzuca — traktowana jak odhaczenie bez nd', () => {
      expect(dozwoloneStany(null)).toEqual(['accepted', 'brak'])
      expect(dozwoloneStany(undefined)).toEqual(['accepted', 'brak'])
    })

    it('"brak" jest zawsze ostatnim elementem (wyczyść dostępne zawsze)', () => {
      expect(dozwoloneStany({ typ: 'weryfikacja', nd_dozwolone: true }).at(-1)).toBe('brak')
      expect(dozwoloneStany({ typ: 'odhaczenie' }).at(-1)).toBe('brak')
    })
  })

  describe('tasksForStage', () => {
    const subtasks = {
      Dokumentacja: [{ klucz: 'dok:a' }, { klucz: 'dok:b' }],
      'Audyt Energetyczny': [{ klucz: 'audyt:a' }],
    }

    it('zwraca definicje dla etapu, który je ma', () => {
      expect(tasksForStage(subtasks, 'Dokumentacja')).toEqual([
        { klucz: 'dok:a' },
        { klucz: 'dok:b' },
      ])
    })

    it.each([
      [subtasks, 'Lead', 'etap bez podzadań w katalogu'],
      [subtasks, 'Nieznany etap', 'etap spoza katalogu'],
      [subtasks, null, 'status=null'],
      [subtasks, undefined, 'status=undefined'],
      [subtasks, '', 'status pusty string'],
      [null, 'Dokumentacja', 'subtasks=null'],
      [undefined, 'Dokumentacja', 'subtasks=undefined'],
      [{}, 'Dokumentacja', 'subtasks={} (np. OZE — brak katalogu)'],
    ])('zwraca [] dla subtasks=%p, status=%p (%s)', (s, status) => {
      expect(tasksForStage(s, status)).toEqual([])
    })
  })

  describe('stageSummary — nd liczone jako załatwione', () => {
    const defs = [
      { klucz: 'dok:a' },
      { klucz: 'dok:b' },
      { klucz: 'dok:c' },
      { klucz: 'dok:d' },
      { klucz: 'dok:e' },
    ]

    it('accepted i nd oba liczą się jako zrobione, waiting/error/brak nie', () => {
      const mapa = {
        'dok:a': { stan: 'accepted' },
        'dok:b': { stan: 'nd' },
        'dok:c': { stan: 'waiting' },
        'dok:d': { stan: 'error' },
        // dok:e brak wpisu → 'brak'
      }
      expect(stageSummary(defs, mapa)).toEqual({ zrobione: 2, wszystkie: 5 })
    })

    it('wszystko zaakceptowane → zrobione === wszystkie', () => {
      const mapa = Object.fromEntries(defs.map((d) => [d.klucz, { stan: 'accepted' }]))
      expect(stageSummary(defs, mapa)).toEqual({ zrobione: 5, wszystkie: 5 })
    })

    it('pusta mapa → zrobione 0, wszystkie === liczba definicji', () => {
      expect(stageSummary(defs, {})).toEqual({ zrobione: 0, wszystkie: 5 })
    })

    it.each([[null], [undefined], [[]]])(
      'defs=%p → {zrobione: 0, wszystkie: 0} (null-safe)',
      (badDefs) => {
        expect(stageSummary(badDefs, { 'dok:a': { stan: 'accepted' } })).toEqual({
          zrobione: 0,
          wszystkie: 0,
        })
      },
    )

    it('mapa=null/undefined nie rzuca, wszystkie liczone jako "brak"', () => {
      expect(stageSummary(defs, null)).toEqual({ zrobione: 0, wszystkie: 5 })
      expect(stageSummary(defs, undefined)).toEqual({ zrobione: 0, wszystkie: 5 })
    })
  })

  describe('STAN_META — kompletność', () => {
    it('ma wpis dla każdego stanu w STANY_PODZADAN plus "brak"', () => {
      const oczekiwaneKlucze = [...STANY_PODZADAN, 'brak'].sort()
      expect(Object.keys(STAN_META).sort()).toEqual(oczekiwaneKlucze)
    })

    it.each(Object.keys(STAN_META))('%s ma theme i label niepuste', (klucz) => {
      const meta = STAN_META[klucz]
      expect(typeof meta.theme).toBe('string')
      expect(meta.theme.length).toBeGreaterThan(0)
      expect(typeof meta.label).toBe('string')
      expect(meta.label.length).toBeGreaterThan(0)
    })

    it('theme używa wyłącznie nazw motywów frappe-ui Badge (bez surowych hexów)', () => {
      const dozwoloneThemes = ['gray', 'blue', 'green', 'amber', 'red', 'violet']
      Object.values(STAN_META).forEach((meta) => {
        expect(dozwoloneThemes).toContain(meta.theme)
        expect(meta.theme).not.toMatch(/^#/)
      })
    })

    it('"nd" jest oznaczone jako muted, "brak" nie', () => {
      expect(STAN_META.nd.muted).toBe(true)
      expect(STAN_META.brak.muted).toBeUndefined()
    })

    it('"nd" i "brak" współdzielą theme "gray", ale pozostają rozróżnialne przez "muted"', () => {
      expect(STAN_META.nd.theme).toBe('gray')
      expect(STAN_META.brak.theme).toBe('gray')
      expect(STAN_META.nd.muted).not.toBe(STAN_META.brak.muted)
    })
  })

  describe('buildPodzadaniePayload — kształt żądania do volteo_podzadania_set (b49 F3)', () => {
    it('stan="brak" nigdy nie niesie data/note, nawet gdy podane', () => {
      expect(
        buildPodzadaniePayload({
          zadanie: 'dok:a',
          stan: 'brak',
          data: '2026-08-20',
          note: 'coś',
          zData: true,
        }),
      ).toEqual({ zadanie: 'dok:a', stan: 'brak' })
    })

    it('pomija data, gdy zData=false, nawet jeśli wartość podana', () => {
      expect(
        buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', data: '2026-08-20', zData: false }),
      ).toEqual({ zadanie: 'dok:a', stan: 'accepted' })
    })

    it('pomija data, gdy zData=true ale wartość pusta/undefined', () => {
      expect(buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', data: '', zData: true })).toEqual({
        zadanie: 'dok:a',
        stan: 'accepted',
      })
      expect(
        buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', data: undefined, zData: true }),
      ).toEqual({ zadanie: 'dok:a', stan: 'accepted' })
    })

    it('dołącza data, gdy zData=true i wartość podana', () => {
      expect(
        buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', data: '2026-08-20', zData: true }),
      ).toEqual({ zadanie: 'dok:a', stan: 'accepted', data: '2026-08-20' })
    })

    it('przycina notatkę do 500 znaków klientowsko', () => {
      const dluga = 'x'.repeat(600)
      const wynik = buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', note: dluga })
      expect(wynik.note).toHaveLength(500)
      expect(wynik.note).toBe('x'.repeat(500))
    })

    it('przycina białe znaki i pomija notatkę, gdy po przycięciu jest pusta', () => {
      expect(buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', note: '   ' })).toEqual({
        zadanie: 'dok:a',
        stan: 'accepted',
      })
      expect(
        buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', note: '  ważne  ' }),
      ).toEqual({ zadanie: 'dok:a', stan: 'accepted', note: 'ważne' })
    })

    it('note nie-string (np. undefined) nie rzuca i jest pomijane', () => {
      expect(buildPodzadaniePayload({ zadanie: 'dok:a', stan: 'accepted', note: undefined })).toEqual({
        zadanie: 'dok:a',
        stan: 'accepted',
      })
    })

    it('nie mutuje przekazanych argumentów (nie zwraca referencji na nie)', () => {
      const input = { zadanie: 'dok:a', stan: 'accepted', data: '2026-08-20', note: 'x', zData: true }
      const kopia = { ...input }
      buildPodzadaniePayload(input)
      expect(input).toEqual(kopia)
    })
  })

  describe('entryFromPayload — payload wysłany → wpis optymistyczny w mapie', () => {
    it('stan="brak" daje null (wpis usunięty)', () => {
      expect(entryFromPayload({ zadanie: 'dok:a', stan: 'brak' })).toBeNull()
    })

    it('null/undefined payload daje null', () => {
      expect(entryFromPayload(null)).toBeNull()
      expect(entryFromPayload(undefined)).toBeNull()
    })

    it('zachowuje tylko stan, gdy payload nie ma data/note', () => {
      expect(entryFromPayload({ zadanie: 'dok:a', stan: 'accepted' })).toEqual({ stan: 'accepted' })
    })

    it('przenosi data i note, gdy obecne w payloadzie', () => {
      expect(
        entryFromPayload({ zadanie: 'audyt:umowiony', stan: 'waiting', data: '2026-08-25', note: 'ok' }),
      ).toEqual({ stan: 'waiting', data: '2026-08-25', note: 'ok' })
    })

    it('pomija `zadanie` z wpisu — to klucz mapy, nie pole wpisu', () => {
      const wynik = entryFromPayload({ zadanie: 'dok:a', stan: 'accepted' })
      expect(wynik).not.toHaveProperty('zadanie')
    })
  })

  describe('applyOptimistic — zapis/rollback bez mutacji', () => {
    it('dodaje/nadpisuje wpis pod kluczem, zwraca NOWY obiekt', () => {
      const mapa = { 'dok:a': { stan: 'waiting' } }
      const wynik = applyOptimistic(mapa, 'dok:b', { stan: 'accepted' })
      expect(wynik).not.toBe(mapa)
      expect(wynik).toEqual({ 'dok:a': { stan: 'waiting' }, 'dok:b': { stan: 'accepted' } })
      expect(mapa).toEqual({ 'dok:a': { stan: 'waiting' } }) // niezmutowane
    })

    it('wpis=null usuwa klucz (mirror stan="brak")', () => {
      const mapa = { 'dok:a': { stan: 'waiting' }, 'dok:b': { stan: 'accepted' } }
      const wynik = applyOptimistic(mapa, 'dok:a', null)
      expect(wynik).toEqual({ 'dok:b': { stan: 'accepted' } })
      expect(mapa).toHaveProperty('dok:a') // źródło niezmutowane
    })

    it('wpis=undefined też usuwa klucz', () => {
      const mapa = { 'dok:a': { stan: 'waiting' } }
      expect(applyOptimistic(mapa, 'dok:a', undefined)).toEqual({})
    })

    it('usuwanie nieistniejącego klucza jest no-opem (zwraca kopię bez rzucania)', () => {
      const mapa = { 'dok:a': { stan: 'waiting' } }
      expect(applyOptimistic(mapa, 'dok:nieznany', null)).toEqual(mapa)
    })

    it('mapa=null/undefined traktowane jak pusta mapa', () => {
      expect(applyOptimistic(null, 'dok:a', { stan: 'accepted' })).toEqual({ 'dok:a': { stan: 'accepted' } })
      expect(applyOptimistic(undefined, 'dok:a', { stan: 'accepted' })).toEqual({
        'dok:a': { stan: 'accepted' },
      })
    })

    it('kopiuje wpis płytko — mutacja zwróconego wpisu nie rusza oryginału podanego jako wpis', () => {
      const wpis = { stan: 'accepted', note: 'x' }
      const wynik = applyOptimistic({}, 'dok:a', wpis)
      wynik['dok:a'].note = 'zmienione'
      expect(wpis.note).toBe('x')
    })

    it('kompozycja z buildPodzadaniePayload/entryFromPayload — rollback do snapshotu na błędzie', () => {
      const before = { 'dok:a': { stan: 'waiting' } }
      const payload = buildPodzadaniePayload({
        zadanie: 'dok:a',
        stan: 'accepted',
        note: 'zaakceptowane',
      })
      const optimistic = applyOptimistic(before, 'dok:a', entryFromPayload(payload))
      expect(optimistic).toEqual({ 'dok:a': { stan: 'accepted', note: 'zaakceptowane' } })
      // Na błędzie serwera wołający po prostu wraca do `before` — sam `before`
      // pozostał niezmutowany przez cały czas.
      expect(before).toEqual({ 'dok:a': { stan: 'waiting' } })
    })
  })
})
