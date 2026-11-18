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
  FORMY_FINANSOWANIA,
  STAN_META_OZE,
  metaStanu,
  pozycjeDlaFormy,
  podsumowanieEtapu,
  tekstLicznika,
  wyczyscPoZmianieFormy,
} from '@/utils/dealPodzadania'

describe('Podzadania procesu CP — czysta logika (dealPodzadania)', () => {
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

describe('Podzadania OZE (ops#381)', () => {
  const GOT = '100% Gotówka'
  const KRE = '100% Kredyt'
  const MIX = 'Gotówka + Kredyt'
  const fin = [
    { klucz: 'oze_fin:formularz_kredytowy', formy: [KRE, MIX] },
    { klucz: 'oze_fin:kredyt_procesowany', formy: [KRE, MIX] },
    { klucz: 'oze_fin:kredyt_odrzucony', formy: [KRE, MIX] },
    { klucz: 'oze_fin:kredyt_podpisany', formy: [KRE, MIX] },
    { klucz: 'oze_fin:proforma', formy: [GOT, MIX] },
    { klucz: 'oze_fin:platnosc_klienta', formy: [GOT, MIX] },
  ]
  const klucze = (lista) => lista.map((d) => d.klucz)

  it('FORMY_FINANSOWANIA: trzy wartości z kontraktu', () => {
    expect(FORMY_FINANSOWANIA).toEqual([GOT, KRE, MIX])
  })

  describe('pozycjeDlaFormy', () => {
    it('gotówka: 2 pozycje', () => {
      expect(klucze(pozycjeDlaFormy(fin, GOT))).toEqual(['oze_fin:proforma', 'oze_fin:platnosc_klienta'])
    })
    it('kredyt: 4 pozycje', () => {
      expect(pozycjeDlaFormy(fin, KRE)).toHaveLength(4)
    })
    it('gotówka + kredyt: 6 pozycji', () => {
      expect(pozycjeDlaFormy(fin, MIX)).toHaveLength(6)
    })
    it('pusta lub nieznana forma: 0 pozycji z `formy`', () => {
      expect(pozycjeDlaFormy(fin, '')).toHaveLength(0)
      expect(pozycjeDlaFormy(fin, null)).toHaveLength(0)
      expect(pozycjeDlaFormy(fin, 'Inna')).toHaveLength(0)
    })
    it('brak pola `formy` = zawsze widoczna, także przy pustej formie', () => {
      const lista = [{ klucz: 'a' }, { klucz: 'b', formy: [GOT] }]
      expect(klucze(pozycjeDlaFormy(lista, ''))).toEqual(['a'])
      expect(klucze(pozycjeDlaFormy(lista, GOT))).toEqual(['a', 'b'])
    })
    it('nie mutuje wejścia i toleruje nie-tablicę', () => {
      const kopia = JSON.stringify(fin)
      pozycjeDlaFormy(fin, GOT)
      expect(JSON.stringify(fin)).toBe(kopia)
      expect(pozycjeDlaFormy(null, GOT)).toEqual([])
    })
  })

  describe('podsumowanieEtapu (wektory z Pythona)', () => {
    const def = (n) => Array.from({ length: n }, (_, i) => ({ klucz: `k${i}` }))
    it('(a) 3 pozycje, 2 accepted, 1 bez wpisu', () => {
      const mapa = { k0: { stan: 'accepted' }, k1: { stan: 'accepted' } }
      expect(podsumowanieEtapu(def(3), mapa)).toEqual({ ok: 2, err: 0, razem: 3 })
    })
    it('(b) 8 pozycji, 4 accepted, 1 nd, 1 waiting', () => {
      const mapa = {
        k0: { stan: 'accepted' },
        k1: { stan: 'accepted' },
        k2: { stan: 'accepted' },
        k3: { stan: 'accepted' },
        k4: { stan: 'nd' },
        k5: { stan: 'waiting' },
      }
      expect(podsumowanieEtapu(def(8), mapa)).toEqual({ ok: 4, err: 0, razem: 7 })
    })
    it('(c) 4 pozycje, 1 accepted, 1 error', () => {
      const mapa = { k0: { stan: 'accepted' }, k1: { stan: 'error' } }
      expect(podsumowanieEtapu(def(4), mapa)).toEqual({ ok: 1, err: 1, razem: 4 })
    })
    it('pusta lista i brak mapy', () => {
      expect(podsumowanieEtapu([], {})).toEqual({ ok: 0, err: 0, razem: 0 })
      expect(podsumowanieEtapu(null, null)).toEqual({ ok: 0, err: 0, razem: 0 })
    })
  })

  describe('tekstLicznika', () => {
    it('bez błędów', () => {
      expect(tekstLicznika({ ok: 3, err: 0, razem: 7 })).toBe('3/7 zaakceptowane')
    })
    it('z błędami', () => {
      expect(tekstLicznika({ ok: 3, err: 1, razem: 7 })).toBe('3/7 zaakceptowane \u00b7 błędy: 1')
    })
    it('null daje pusty tekst', () => {
      expect(tekstLicznika(null)).toBe('')
      expect(tekstLicznika(undefined)).toBe('')
    })
  })

  describe('STAN_META_OZE i metaStanu', () => {
    it('te same klucze i motywy co STAN_META, etykiety OZE', () => {
      expect(Object.keys(STAN_META_OZE)).toEqual(Object.keys(STAN_META))
      Object.keys(STAN_META).forEach((k) => expect(STAN_META_OZE[k].theme).toBe(STAN_META[k].theme))
      expect(STAN_META_OZE.nd.muted).toBe(true)
      expect(Object.fromEntries(Object.entries(STAN_META_OZE).map(([k, v]) => [k, v.label]))).toEqual({
        brak: 'Brak statusu',
        waiting: 'Oczekuje',
        accepted: 'Zaakceptowano',
        error: 'Błąd',
        nd: 'Nie dotyczy',
      })
    })
    it('metaStanu: OZE z tabeli OZE, inaczej CP bez zmian', () => {
      expect(metaStanu('OZE', 'accepted').label).toBe('Zaakceptowano')
      expect(metaStanu('CP', 'accepted').label).toBe('Załatwione')
      expect(metaStanu(null, 'accepted')).toBe(STAN_META.accepted)
      expect(metaStanu('OZE', 'cos')).toBe(STAN_META_OZE.brak)
      expect(STAN_META.accepted.label).toBe('Załatwione')
    })
  })

  describe('wyczyscPoZmianieFormy', () => {
    const mapa = {
      'oze_fin:formularz_kredytowy': { stan: 'accepted' },
      'oze_fin:proforma': { stan: 'waiting' },
      'oze_up:akceptacja_klienta': { stan: 'accepted' },
    }
    it('usuwa wpisy pozycji spoza nowej formy, reszta zostaje, bez mutacji', () => {
      const kopia = JSON.stringify(mapa)
      const wynik = wyczyscPoZmianieFormy(mapa, fin, GOT)
      expect(Object.keys(wynik)).toEqual(['oze_fin:proforma', 'oze_up:akceptacja_klienta'])
      expect(JSON.stringify(mapa)).toBe(kopia)
      expect(wynik).not.toBe(mapa)
    })
    it('pusta forma usuwa wszystkie pozycje z `formy`', () => {
      expect(Object.keys(wyczyscPoZmianieFormy(mapa, fin, ''))).toEqual(['oze_up:akceptacja_klienta'])
    })
    it('forma mieszana nie usuwa nic', () => {
      expect(Object.keys(wyczyscPoZmianieFormy(mapa, fin, MIX))).toHaveLength(3)
    })
    it('null-safe', () => {
      expect(wyczyscPoZmianieFormy(null, null, GOT)).toEqual({})
    })
  })
})
