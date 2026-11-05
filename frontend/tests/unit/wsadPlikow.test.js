import { rozstrzygnijWsad } from '@/utils/wsadPlikow'

describe('Rozstrzyganie wsadu plików po równoległym uploadzie (wsadPlikow, uwaga 93)', () => {
  it('wszystkie pliki udane: zamyka okno, czyści listę, emituje after ze wszystkimi', () => {
    const wyniki = [{ ok: true, wynik: 'a' }, { ok: true, wynik: 'b' }, { ok: true, wynik: 'c' }]
    const decyzja = rozstrzygnijWsad(3, wyniki)
    expect(decyzja.zamknij).toBe(true)
    expect(decyzja.wyczyscListe).toBe(true)
    expect(decyzja.emitujAfter).toBe(true)
    expect(decyzja.udane).toEqual(['a', 'b', 'c'])
  })

  it('część plików nieudana: okno zostaje otwarte, udane są do emit after, lista nie jest czyszczona w całości', () => {
    const wyniki = [{ ok: true, wynik: 'a' }, { ok: false }, { ok: true, wynik: 'c' }, { ok: false }]
    const decyzja = rozstrzygnijWsad(4, wyniki)
    expect(decyzja.zamknij).toBe(false)
    expect(decyzja.wyczyscListe).toBe(false)
    expect(decyzja.emitujAfter).toBe(true)
    expect(decyzja.udane).toEqual(['a', 'c'])
  })

  it('wszystkie pliki nieudane: okno zostaje otwarte, bez after', () => {
    const wyniki = [{ ok: false }, { ok: false }]
    const decyzja = rozstrzygnijWsad(2, wyniki)
    expect(decyzja.zamknij).toBe(false)
    expect(decyzja.wyczyscListe).toBe(false)
    expect(decyzja.emitujAfter).toBe(false)
    expect(decyzja.udane).toEqual([])
  })

  it('jeden plik udany (ścieżka linku/aparatu, wsad jednoelementowy): zamyka i emituje', () => {
    const decyzja = rozstrzygnijWsad(1, [{ ok: true, wynik: 'jedyny' }])
    expect(decyzja.zamknij).toBe(true)
    expect(decyzja.wyczyscListe).toBe(true)
    expect(decyzja.emitujAfter).toBe(true)
    expect(decyzja.udane).toEqual(['jedyny'])
  })

  it('jeden plik nieudany (wsad jednoelementowy): okno zostaje otwarte, bez after', () => {
    const decyzja = rozstrzygnijWsad(1, [{ ok: false }])
    expect(decyzja.zamknij).toBe(false)
    expect(decyzja.wyczyscListe).toBe(false)
    expect(decyzja.emitujAfter).toBe(false)
    expect(decyzja.udane).toEqual([])
  })

  it('wyniki w odwróconej kolejności (ostatni indeks rozstrzyga się pierwszy): decyzja identyczna jak przy kolejności prostej', () => {
    // To jest dokładnie scenariusz, który gubił pliki w starym kodzie:
    // ten o ostatnim indeksie kończył się jako PIERWSZY, więc zdążył
    // zamknąć okno i wyemitować 'after', zanim reszta się rozstrzygnęła.
    // Funkcja nie powinna w ogóle patrzeć na kolejność.
    const wPorzadkuProstym = rozstrzygnijWsad(3, [
      { ok: true, wynik: 'i0' },
      { ok: true, wynik: 'i1' },
      { ok: true, wynik: 'i2' },
    ])
    const wPorzadkuOdwroconym = rozstrzygnijWsad(3, [
      { ok: true, wynik: 'i2' },
      { ok: true, wynik: 'i1' },
      { ok: true, wynik: 'i0' },
    ])
    expect(wPorzadkuOdwroconym.zamknij).toBe(wPorzadkuProstym.zamknij)
    expect(wPorzadkuOdwroconym.wyczyscListe).toBe(wPorzadkuProstym.wyczyscListe)
    expect(wPorzadkuOdwroconym.emitujAfter).toBe(wPorzadkuProstym.emitujAfter)
    expect(wPorzadkuOdwroconym.udane).toEqual(['i2', 'i1', 'i0'])
  })

  it('wyniki w odwróconej kolejności z błędem na ostatnim indeksie: nadal wykrywa częściowy błąd, bez duplikatów i bez gubienia', () => {
    // Plik o ostatnim indeksie (i2) pada jako PIERWSZY rozstrzygnięty,
    // stary kod zamykał okno właśnie wtedy, co gubiło i0/i1.
    const wyniki = [
      { ok: false }, // i2 rozstrzygnięty jako pierwszy
      { ok: true, wynik: 'i1' },
      { ok: true, wynik: 'i0' },
    ]
    const decyzja = rozstrzygnijWsad(3, wyniki)
    expect(decyzja.zamknij).toBe(false)
    expect(decyzja.emitujAfter).toBe(true)
    expect(decyzja.udane).toEqual(['i1', 'i0'])
    expect(decyzja.udane).toHaveLength(2)
  })

  it('rzuca, gdy liczba wyników nie zgadza się z zadeklarowanym rozmiarem wsadu', () => {
    expect(() => rozstrzygnijWsad(3, [{ ok: true }])).toThrow()
  })
})
