import { PALETA_UZYTKOWNIKOW } from '@/utils/mapaKolory'
import {
  KOLOR_OBWODKI,
  KOLOR_WYBRANEJ,
  STYL_PINEZKI,
  STYL_PINEZKI_WYBRANEJ,
  geometriaPinezki,
  kropkaPinezki,
  sciezkaPinezki,
  stylPinezki,
} from '@/utils/mapaPinezka'

// Ten sam 13-elementowy słownik co HEX_PO_NAZWIE_KOLORU w MapaLeadow.vue --
// przepisany literalnie, bo to <script setup>, nie da się go zaimportować.
const HEXY_STATUSOW = [
  '#18181b',
  '#374151',
  '#2563eb',
  '#15803d',
  '#dc2626',
  '#db2777',
  '#ea580c',
  '#d97706',
  '#ca8a04',
  '#0891b2',
  '#0d9488',
  '#7c3aed',
  '#9333ea',
]

describe('stylPinezki', () => {
  it('domyślnie zwraca promień 6, obwódkę 1, wypełnienie 0.92, białą obwódkę, kolor leada w fillColor', () => {
    const styl = stylPinezki('#dc2626')
    expect(styl.radius).toBe(6)
    expect(styl.weight).toBe(1)
    expect(styl.fillOpacity).toBe(0.92)
    expect(styl.color).toBe(KOLOR_OBWODKI)
    expect(styl.fillColor).toBe('#dc2626')
    expect(styl.wybrany).toBe(false)
  })

  it('dla wybrany=true zwraca promień 11, obwódkę 2.5, pełne wypełnienie, fillColor = KOLOR_WYBRANEJ (fuksja)', () => {
    const styl = stylPinezki('#2563eb', true)
    expect(styl.radius).toBe(11)
    expect(styl.weight).toBe(2.5)
    expect(styl.fillOpacity).toBe(1)
    expect(styl.color).toBe(KOLOR_OBWODKI)
    expect(styl.fillColor).toBe(KOLOR_WYBRANEJ)
    expect(styl.fillColor).toBe('#d946ef')
    expect(styl.wybrany).toBe(true)
  })

  it('zwraca nowy obiekt przy każdym wywołaniu i nie mutuje stałych', () => {
    const a = stylPinezki('#111111')
    const b = stylPinezki('#111111')
    expect(a).not.toBe(b)
    expect(Object.isFrozen(STYL_PINEZKI)).toBe(true)
    expect(Object.isFrozen(STYL_PINEZKI_WYBRANEJ)).toBe(true)
    expect(STYL_PINEZKI).toEqual({ radius: 6, weight: 1, fillOpacity: 0.92 })
    expect(STYL_PINEZKI_WYBRANEJ).toEqual({ radius: 11, weight: 2.5, fillOpacity: 1 })
  })

  it('styl wybranej jest zawsze większy niż domyślny (promień i obwódka)', () => {
    const domyslny = stylPinezki('#000000', false)
    const wybrany = stylPinezki('#000000', true)
    expect(wybrany.radius).toBeGreaterThan(domyslny.radius)
    expect(wybrany.weight).toBeGreaterThan(domyslny.weight)
  })
})

describe('KOLOR_WYBRANEJ', () => {
  it('nie koliduje z paletą kolorów użytkowników (mapaKolory.js)', () => {
    expect(PALETA_UZYTKOWNIKOW).not.toContain(KOLOR_WYBRANEJ)
  })

  it('nie koliduje z paletą hexów statusów (HEX_PO_NAZWIE_KOLORU w MapaLeadow.vue)', () => {
    expect(HEXY_STATUSOW).not.toContain(KOLOR_WYBRANEJ)
  })
})

describe('geometriaPinezki', () => {
  it('dla promienia 6 daje oczekiwaną geometrię', () => {
    const g = geometriaPinezki(6)
    expect(g.srodekY).toBeCloseTo(-11.4)
    expect(g.wysokosc).toBeCloseTo(17.4)
    expect(g.szerokosc).toBeCloseTo(12)
    expect(g.poswiataR).toBeCloseTo(11.4)
  })

  it('zwraca zamrożony obiekt', () => {
    expect(Object.isFrozen(geometriaPinezki(6))).toBe(true)
  })

  it('skaluje się liniowo z promieniem', () => {
    const mala = geometriaPinezki(3)
    const duza = geometriaPinezki(6)
    expect(duza.srodekY).toBeCloseTo(mala.srodekY * 2)
    expect(duza.wysokosc).toBeCloseTo(mala.wysokosc * 2)
  })
})

// Fejkowy CanvasRenderingContext2D nagrywający wszystkie wywołania metod
// (wzorzec z code-review.md: małe, czytelne testy zamiast prawdziwego DOM-u).
function fakeCtx() {
  const wywolania = []
  const rejestruj =
    (nazwa) =>
    (...args) =>
      wywolania.push({ metoda: nazwa, args })
  return {
    wywolania,
    beginPath: rejestruj('beginPath'),
    closePath: rejestruj('closePath'),
    arc: rejestruj('arc'),
    quadraticCurveTo: rejestruj('quadraticCurveTo'),
  }
}

describe('sciezkaPinezki', () => {
  it('woła beginPath, potem arc na środku główki z promieniem r, kończy w czubku, woła closePath', () => {
    const ctx = fakeCtx()
    sciezkaPinezki(ctx, 100, 200, 6)

    expect(ctx.wywolania[0].metoda).toBe('beginPath')
    expect(ctx.wywolania.at(-1).metoda).toBe('closePath')

    const arcCall = ctx.wywolania.find((w) => w.metoda === 'arc')
    expect(arcCall).toBeDefined()
    const [cx, cy, r] = arcCall.args
    expect(cx).toBeCloseTo(100)
    expect(cy).toBeCloseTo(200 + geometriaPinezki(6).srodekY)
    expect(r).toBe(6)

    // Ostatnia krzywa (quadraticCurveTo) przed closePath musi kończyć się
    // W CZUBKU pinezki (kotwica (x, y)) -- pierwsza krzywa idzie do czubka,
    // druga wraca do początku łuku, więc szukamy wywołania z args kończącymi
    // się dokładnie na (100, 200).
    const krzyweDoCzubka = ctx.wywolania.filter(
      (w) => w.metoda === 'quadraticCurveTo' && w.args[2] === 100 && w.args[3] === 200,
    )
    expect(krzyweDoCzubka.length).toBe(1)
  })

  it('nie woła fill()/stroke() -- to robi wołający', () => {
    const ctx = fakeCtx()
    ctx.fill = vi.fn()
    ctx.stroke = vi.fn()
    sciezkaPinezki(ctx, 0, 0, 6)
    expect(ctx.fill).not.toHaveBeenCalled()
    expect(ctx.stroke).not.toHaveBeenCalled()
  })
})

describe('kropkaPinezki', () => {
  it('rysuje kółko w środku główki o promieniu kropkaR', () => {
    const ctx = fakeCtx()
    kropkaPinezki(ctx, 100, 200, 6)

    expect(ctx.wywolania[0].metoda).toBe('beginPath')
    expect(ctx.wywolania.at(-1).metoda).toBe('closePath')

    const arcCall = ctx.wywolania.find((w) => w.metoda === 'arc')
    const [cx, cy, r] = arcCall.args
    expect(cx).toBeCloseTo(100)
    expect(cy).toBeCloseTo(200 + geometriaPinezki(6).srodekY)
    expect(r).toBeCloseTo(geometriaPinezki(6).kropkaR)
  })
})
