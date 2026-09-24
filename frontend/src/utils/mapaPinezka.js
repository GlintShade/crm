// Geometria i styl "pinezki" (teardrop) rysowanej na canvasie mapy leadów
// (MapaLeadow.vue), zastępujące zwykłe kółka (dawne stylZnacznika w
// mapaKolory.js, usunięte w tej samej zmianie). Frappe-free i bez importu
// Leafleta -- L.CircleMarker jest podklasowany bezpośrednio w
// MapaLeadow.vue (potrzebuje `L`), ten moduł dostarcza mu wyłącznie czystą,
// testowalną geometrię i funkcje rysujące ścieżkę na dowolnym 2D
// CanvasRenderingContext2D.
//
// Kolor aktywnej (wybranej) pinezki: fuksja, celowo spoza palety statusów
// (HEX_PO_NAZWIE_KOLORU w MapaLeadow.vue) i palety użytkowników
// (PALETA_UZYTKOWNIKOW w mapaKolory.js), żeby wybrany lead nie zlewał się
// z żadnym statusem ani handlowcem/CC.
export const KOLOR_WYBRANEJ = '#d946ef'
export const KOLOR_OBWODKI = '#ffffff'

export const STYL_PINEZKI = Object.freeze({ radius: 6, weight: 1, fillOpacity: 0.92 })
export const STYL_PINEZKI_WYBRANEJ = Object.freeze({ radius: 11, weight: 2.5, fillOpacity: 1 })

/**
 * Opcje stylu dla warstwy pinezki (konstruktor podklasy L.CircleMarker /
 * setStyle). Zwraca zawsze NOWY obiekt (coding-style.md: nowe obiekty, nie
 * mutacja stałych powyżej). Obwódka zawsze biała -- to ona daje nowoczesny,
 * "wycięty" wygląd pinezki -- a wypełnienie niesie kolor statusu/handlowca/CC,
 * albo KOLOR_WYBRANEJ, gdy pinezka jest aktywna (otwarty panel "Szybki
 * podgląd"). Flaga `wybrany` jedzie w opcjach dalej, bo podklasa Leafleta
 * czyta ją we własnym _updatePath (poświata tylko dla wybranej).
 *
 * @param {string} kolor
 * @param {boolean} wybrany
 * @returns {{radius: number, weight: number, fillOpacity: number, color: string, fillColor: string, wybrany: boolean}}
 */
export function stylPinezki(kolor, wybrany = false) {
  const baza = wybrany ? STYL_PINEZKI_WYBRANEJ : STYL_PINEZKI
  return {
    ...baza,
    color: KOLOR_OBWODKI,
    fillColor: wybrany ? KOLOR_WYBRANEJ : kolor,
    wybrany,
  }
}

/**
 * Geometria kropli o promieniu główki `r` (promień pinezki, jak dotąd
 * `options.radius`), kotwica (współrzędna geograficzna markera) w czubku
 * kropli. Środek główki leży `r*1.9` nad kotwicą, więc cała pinezka ma
 * wysokość ok. `r*2.9` (główka + trzon do czubka) i szerokość `2r` (średnica
 * główki). `kropkaR` to promień białej kropki rysowanej w środku główki.
 * Zawsze NOWY, zamrożony obiekt.
 *
 * @param {number} r
 * @returns {{srodekY: number, wysokosc: number, szerokosc: number, kropkaR: number}}
 */
export function geometriaPinezki(r) {
  return Object.freeze({
    srodekY: -r * 1.9,
    wysokosc: r * 2.9,
    szerokosc: r * 2,
    kropkaR: r * 0.42,
  })
}

// Kąty (w radianach, konwencja canvasu: 0 = w prawo, rosnące = zgodnie z
// ruchem wskazówek, bo oś Y rośnie w dół) wyznaczające lukę na dole główki,
// przez którą wychodzi trzon do czubka. 0.8*PI i 0.2*PI to symetryczne
// punkty ok. 36°/144° -- łuk główki idzie "długą drogą" (przez lewo, górę,
// prawo), zostawiając ok. 108-stopniową lukę na dole na trzon.
const KAT_START = 0.8 * Math.PI
const KAT_KONIEC = 0.2 * Math.PI

/**
 * Rysuje ścieżkę kropli (łuk główki + dwie krzywe zbiegające się w czubku)
 * na podanym kontekście 2D. Nie woła fill()/stroke() -- to robi wołający
 * (na canvasie Leafleta: `renderer._fillStroke(ctx, layer)`, w testach:
 * asercje na wywołaniach fejkowego ctx), żeby ta funkcja pozostała czystą
 * geometrią, testowalną bez żadnego DOM-u/canvasu.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x współrzędna piksela kotwicy (czubek pinezki)
 * @param {number} y współrzędna piksela kotwicy (czubek pinezki)
 * @param {number} r promień główki w pikselach
 */
export function sciezkaPinezki(ctx, x, y, r) {
  const g = geometriaPinezki(r)
  const cx = x
  const cy = y + g.srodekY

  const p1x = cx + r * Math.cos(KAT_START)
  const p1y = cy + r * Math.sin(KAT_START)
  const p2x = cx + r * Math.cos(KAT_KONIEC)
  const p2y = cy + r * Math.sin(KAT_KONIEC)

  ctx.beginPath()
  // Łuk główki: od KAT_START, "długą drogą" (przez lewo/górę/prawo) do
  // KAT_KONIEC -- ctx.arc z anticlockwise=false zaczyna w miejscu p1 (bo
  // to pierwsza operacja na ścieżce, więc jest niejawnym moveTo) i kończy
  // w p2, zostawiając dolną lukę na trzon.
  ctx.arc(cx, cy, r, KAT_START, KAT_KONIEC, false)
  // Trzon: od p2 krzywą do czubka (x, y), potem od czubka krzywą z powrotem
  // do p1 -- ścieżka kończy się dokładnie w czubku pinezki.
  ctx.quadraticCurveTo(p2x, p2y + r * 0.6, x, y)
  ctx.quadraticCurveTo(p1x, p1y + r * 0.6, p1x, p1y)
  ctx.closePath()
}

/**
 * Rysuje ścieżkę białej kropki w środku główki (rysowana PO
 * `_fillStroke(ctx, layer)` w podklasie, osobnym fill() z KOLOR_OBWODKI --
 * ta funkcja tylko buduje ścieżkę, tak jak sciezkaPinezki wyżej).
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x współrzędna piksela kotwicy (czubek pinezki)
 * @param {number} y współrzędna piksela kotwicy (czubek pinezki)
 * @param {number} r promień główki w pikselach
 */
export function kropkaPinezki(ctx, x, y, r) {
  const g = geometriaPinezki(r)
  ctx.beginPath()
  ctx.arc(x, y + g.srodekY, g.kropkaR, 0, Math.PI * 2, false)
  ctx.closePath()
}
