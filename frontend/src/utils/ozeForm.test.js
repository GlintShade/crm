import { describe, expect, it } from 'vitest'
import {
  GRUPY_KLIMY,
  GRZEJNIKI_MAX,
  OZE_KLIMATYZACJA,
  OZE_KOCIOL,
  OZE_POMPA_CIEPLA,
  OZE_ROZBUDOWA,
  RODZAJE_NOWE,
  brakDoboru,
  czyNowyRodzaj,
  dobierzMocPc,
  grupujWewnetrzneOze,
  grzejnikiPoprawne,
  kafelkiRodzaju,
  kaskadaKlimy,
  kompletnyFormOze,
  kompletnyKlimatyzacja,
  kompletnyKociol,
  kompletnyPompa,
  kompletnyRozbudowa,
  modeleKlimy,
  moceKlimy,
  odmianaPaneli,
  ogrzewanieDoTabeli,
  opcjeIlosciGrzejnika,
  pozycjeGrupy,
  producenciPc,
  pustyFormularzOze,
  rozmiaryGrzejnikow,
  sumaGrzejnikow,
  typyPcDostepne,
  ulgaDotyczy,
  zbudujPayloadOze,
} from './ozeForm'

// Minimalny wycinek katalogu uzywany przez wiele testow ponizej -- lustro
// ksztaltu `volteo_oze_pozycje().pozycje` (bez `aktywny`/`skladowe`,
// zgodnie z kontraktem B5).
const KLIMA_POZYCJE = [
  { kod: 'klima_elis_x_2_6', nazwa: 'Rotenso Elis X Czarny 2,6 kW', rodzaj: 'Klimatyzacja', grupa: 'klima_chlodzenie', producent: 'Rotenso', model: 'Elis X', kolor: 'Czarny', moc_kw: 2.6, ilosc: 1, parametr: '', opis: 'do 25 m2', sort: 1 },
  { kod: 'klima_elis_x_3_5', nazwa: 'Rotenso Elis X Czarny 3,5 kW', rodzaj: 'Klimatyzacja', grupa: 'klima_chlodzenie', producent: 'Rotenso', model: 'Elis X', kolor: 'Czarny', moc_kw: 3.5, ilosc: 1, parametr: '', opis: '25-40 m2', sort: 2 },
  { kod: 'klima_roni_x_2_6', nazwa: 'Rotenso Roni X Bialy 2,6 kW', rodzaj: 'Klimatyzacja', grupa: 'klima_chlodzenie', producent: 'Rotenso', model: 'Roni X', kolor: 'Bialy', moc_kw: 2.6, ilosc: 1, parametr: '', opis: 'do 25 m2', sort: 3 },
  { kod: 'klima_teta_mirror_x_3_5', nazwa: 'Rotenso Teta Mirror X Czarny 3,5 kW', rodzaj: 'Klimatyzacja', grupa: 'klima_dogrzewanie', producent: 'Rotenso', model: 'Teta Mirror X', kolor: 'Czarny', moc_kw: 3.5, ilosc: 1, parametr: '', opis: '', sort: 4 },
  { kod: 'klima_mira_x_3_5', nazwa: 'Rotenso Mira X Bialy 3,5 kW', rodzaj: 'Klimatyzacja', grupa: 'klima_grzanie', producent: 'Rotenso', model: 'Mira X', kolor: 'Bialy', moc_kw: 3.5, ilosc: 1, parametr: '', opis: '', sort: 5 },
]

const GRZEJNIK_POZYCJE = [
  { kod: 'grzejnik_600x600', nazwa: 'Grzejnik 600x600', rodzaj: 'Dodatek grzewczy', grupa: 'grzejnik', producent: '', model: '', kolor: '', moc_kw: 0, ilosc: 1, parametr: '', opis: '', sort: 1 },
  { kod: 'grzejnik_600x1600', nazwa: 'Grzejnik 600x1600', rodzaj: 'Dodatek grzewczy', grupa: 'grzejnik', producent: '', model: '', kolor: '', moc_kw: 0, ilosc: 1, parametr: '', opis: '', sort: 5 },
]

const DOBOR_ROTENSO_PODLOGOWKA = [
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 0, do_kw: 6, moc_kw: 6 },
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 6.5, do_kw: 8, moc_kw: 8 },
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 8.5, do_kw: 9.5, moc_kw: 10 },
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 9.5, do_kw: 10.5, moc_kw: 12 },
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 10.5, do_kw: 12, moc_kw: 14 },
  { producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka', od_kw: 12, do_kw: 13.5, moc_kw: 16 },
]

describe('RODZAJE_NOWE / czyNowyRodzaj / kafelkiRodzaju', () => {
  it('niesie dokladnie cztery nowe rodzaje w ustalonej kolejnosci', () => {
    expect(RODZAJE_NOWE).toEqual([OZE_ROZBUDOWA, OZE_KLIMATYZACJA, OZE_POMPA_CIEPLA, OZE_KOCIOL])
  })

  it('czyNowyRodzaj rozpoznaje wylacznie cztery nowe rodzaje', () => {
    expect(czyNowyRodzaj(OZE_ROZBUDOWA)).toBe(true)
    expect(czyNowyRodzaj(OZE_KOCIOL)).toBe(true)
    expect(czyNowyRodzaj('Fotowoltaika')).toBe(false)
    expect(czyNowyRodzaj('Czyste Powietrze')).toBe(false)
    expect(czyNowyRodzaj('')).toBe(false)
    expect(czyNowyRodzaj(null)).toBe(false)
  })

  it('kafelkiRodzaju zwraca dokladnie siedem wartosci: trzy stare + cztery nowe', () => {
    const kafelki = kafelkiRodzaju()
    expect(kafelki).toHaveLength(7)
    expect(kafelki.slice(0, 3)).toEqual(['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii'])
    expect(kafelki.slice(3)).toEqual(RODZAJE_NOWE)
  })
})

describe('ulgaDotyczy', () => {
  it('Klimatyzacja nigdy nie ma ulgi', () => {
    expect(ulgaDotyczy(OZE_KLIMATYZACJA)).toBe(false)
  })

  it('Rozbudowa, Pompa ciepla, Kociol moga miec ulge', () => {
    expect(ulgaDotyczy(OZE_ROZBUDOWA)).toBe(true)
    expect(ulgaDotyczy(OZE_POMPA_CIEPLA)).toBe(true)
    expect(ulgaDotyczy(OZE_KOCIOL)).toBe(true)
  })
})

describe('pustyFormularzOze', () => {
  it('zwraca kompletny ksztalt z domyslnym rodzajem Rozbudowa', () => {
    const form = pustyFormularzOze()
    expect(form.rodzaj).toBe(OZE_ROZBUDOWA)
    expect(form.typKlienta).toBe('indywidualny')
    expect(form.rozbudowa).toEqual({
      panele: 0,
      paneleMikro: 0,
      bateria: 0,
      istniejacaPv: 'Nie',
      istniejacaPvMocKwp: null,
      ppozRecznie: 'Nie',
    })
    expect(form.klimatyzacja).toEqual({ grupa: '', klucz: '', kod: '' })
    expect(form.pompa.grzejniki).toEqual({
      '600x600': 0,
      '600x800': 0,
      '600x1000': 0,
      '600x1200': 0,
      '600x1600': 0,
    })
    expect(form.kociol).toEqual({ typ: '', kod: '', cwu: '' })
  })

  it('przyjmuje rodzaj startowy', () => {
    expect(pustyFormularzOze(OZE_KOCIOL).rodzaj).toBe(OZE_KOCIOL)
  })

  it('kazde wywolanie zwraca niezalezny obiekt (zero wspoldzielenia)', () => {
    const a = pustyFormularzOze()
    const b = pustyFormularzOze()
    a.rozbudowa.panele = 3
    a.pompa.grzejniki['600x600'] = 5
    expect(b.rozbudowa.panele).toBe(0)
    expect(b.pompa.grzejniki['600x600']).toBe(0)
  })
})

describe('pozycjeGrupy / odmianaPaneli', () => {
  it('filtruje i sortuje wg sort, potem moc_kw', () => {
    const wynik = pozycjeGrupy(KLIMA_POZYCJE, 'klima_chlodzenie')
    expect(wynik.map((p) => p.kod)).toEqual(['klima_elis_x_2_6', 'klima_elis_x_3_5', 'klima_roni_x_2_6'])
  })

  it('zwraca pusta liste dla nieznanej grupy albo pustego katalogu', () => {
    expect(pozycjeGrupy(KLIMA_POZYCJE, 'brak_takiej_grupy')).toEqual([])
    expect(pozycjeGrupy(null, 'klima_chlodzenie')).toEqual([])
  })

  it('odmianaPaneli stosuje polska odmiane 1/2-4/5+', () => {
    expect(odmianaPaneli(0)).toBe('paneli')
    expect(odmianaPaneli(1)).toBe('panel')
    expect(odmianaPaneli(2)).toBe('panele')
    expect(odmianaPaneli(3)).toBe('panele')
    expect(odmianaPaneli(4)).toBe('panele')
    expect(odmianaPaneli(5)).toBe('paneli')
  })
})

describe('GRUPY_KLIMY / modeleKlimy / moceKlimy / kaskadaKlimy', () => {
  it('GRUPY_KLIMY niesie dokladnie trzy grupy w ustalonej kolejnosci', () => {
    expect(GRUPY_KLIMY).toEqual(['klima_chlodzenie', 'klima_dogrzewanie', 'klima_grzanie'])
  })

  it('modeleKlimy zwraca jeden wpis na kazda rozna kombinacje producent+model', () => {
    const modele = modeleKlimy(KLIMA_POZYCJE, 'klima_chlodzenie')
    expect(modele).toEqual([
      { klucz: 'Rotenso|Elis X', producent: 'Rotenso', model: 'Elis X', kolor: 'Czarny' },
      { klucz: 'Rotenso|Roni X', producent: 'Rotenso', model: 'Roni X', kolor: 'Bialy' },
    ])
  })

  it('moceKlimy zwraca warianty mocy wylacznie dla wybranego modelu, posortowane', () => {
    const mocy = moceKlimy(KLIMA_POZYCJE, 'klima_chlodzenie', 'Rotenso|Elis X')
    expect(mocy).toEqual([
      { kod: 'klima_elis_x_2_6', moc_kw: 2.6, opis: 'do 25 m2', nazwa: 'Rotenso Elis X Czarny 2,6 kW' },
      { kod: 'klima_elis_x_3_5', moc_kw: 3.5, opis: '25-40 m2', nazwa: 'Rotenso Elis X Czarny 3,5 kW' },
    ])
  })

  it('kaskadaKlimy resetuje wszystko, gdy grupa jest nieznana', () => {
    expect(kaskadaKlimy(KLIMA_POZYCJE, { grupa: 'cos_innego', klucz: 'x', kod: 'y' })).toEqual({
      grupa: '',
      klucz: '',
      kod: '',
    })
  })

  it('kaskadaKlimy czysci klucz+kod, gdy model przestal pasowac do grupy', () => {
    const wynik = kaskadaKlimy(KLIMA_POZYCJE, {
      grupa: 'klima_dogrzewanie',
      klucz: 'Rotenso|Elis X', // ten model nalezy do klima_chlodzenie, nie dogrzewanie
      kod: 'klima_elis_x_2_6',
    })
    expect(wynik).toEqual({ grupa: 'klima_dogrzewanie', klucz: '', kod: '' })
  })

  it('kaskadaKlimy czysci tylko kod, gdy kod przestal pasowac do modelu', () => {
    const wynik = kaskadaKlimy(KLIMA_POZYCJE, {
      grupa: 'klima_chlodzenie',
      klucz: 'Rotenso|Elis X',
      kod: 'klima_roni_x_2_6', // nalezy do innego modelu w tej samej grupie
    })
    expect(wynik).toEqual({ grupa: 'klima_chlodzenie', klucz: 'Rotenso|Elis X', kod: '' })
  })

  it('kaskadaKlimy zachowuje kompletny, poprawny wybor bez zmian', () => {
    const wybor = { grupa: 'klima_chlodzenie', klucz: 'Rotenso|Elis X', kod: 'klima_elis_x_3_5' }
    expect(kaskadaKlimy(KLIMA_POZYCJE, wybor)).toEqual(wybor)
  })

  it('kaskadaKlimy nigdy nie mutuje wejsciowy obiekt wyboru', () => {
    const wybor = { grupa: 'klima_chlodzenie', klucz: 'Rotenso|Elis X', kod: 'klima_elis_x_3_5' }
    const kopia = { ...wybor }
    kaskadaKlimy(KLIMA_POZYCJE, wybor)
    expect(wybor).toEqual(kopia)
  })
})

describe('producenciPc / typyPcDostepne / ogrzewanieDoTabeli', () => {
  it('producenciPc zwraca Rotenso i Midea w tej kolejnosci', () => {
    expect(producenciPc()).toEqual(['Rotenso', 'Midea'])
  })

  it('Rotenso ma wylacznie Monoblok, Midea ma Monoblok i Split', () => {
    expect(typyPcDostepne('Rotenso')).toEqual(['Monoblok'])
    expect(typyPcDostepne('Midea')).toEqual(['Monoblok', 'Split'])
    expect(typyPcDostepne('Nieznany')).toEqual([])
  })

  it('ogrzewanieDoTabeli mapuje Mieszane na Grzejniki, reszte zostawia', () => {
    expect(ogrzewanieDoTabeli('Mieszane')).toBe('Grzejniki')
    expect(ogrzewanieDoTabeli('Grzejniki')).toBe('Grzejniki')
    expect(ogrzewanieDoTabeli('Podłogówka')).toBe('Podłogówka')
    expect(ogrzewanieDoTabeli('cos innego')).toBe('')
  })
})

describe('dobierzMocPc / brakDoboru (zloty test z kontraktu)', () => {
  it('dobiera 6 kW dla zapotrzebowania "5" (Rotenso Monoblok Podlogowka)', () => {
    const moc = dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '5', 'Rotenso', 'Monoblok', 'Podłogówka')
    expect(moc).toBe(6)
    expect(brakDoboru(moc)).toBe(false)
  })

  it('na granicy nakladajacych sie przedzialow wybiera WIEKSZA pompe', () => {
    expect(dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '9.5', 'Rotenso', 'Monoblok', 'Podłogówka')).toBe(12)
    expect(dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '10.5', 'Rotenso', 'Monoblok', 'Podłogówka')).toBe(14)
    expect(dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '12', 'Rotenso', 'Monoblok', 'Podłogówka')).toBe(16)
  })

  it('poza najwyzszym przedzialem (14 kW) zwraca null -- brak doboru', () => {
    const moc = dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '14', 'Rotenso', 'Monoblok', 'Podłogówka')
    expect(moc).toBeNull()
    expect(brakDoboru(moc)).toBe(true)
  })

  it('niekompletne dane wejsciowe daja null (brak rzutu na serwer bez powodu)', () => {
    expect(dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, '5', '', 'Monoblok', 'Podłogówka')).toBeNull()
    expect(dobierzMocPc(DOBOR_ROTENSO_PODLOGOWKA, 'nieznany_kod', 'Rotenso', 'Monoblok', 'Podłogówka')).toBeNull()
  })

  it('brakDoboru traktuje undefined tak samo jak null', () => {
    expect(brakDoboru(undefined)).toBe(true)
    expect(brakDoboru(6)).toBe(false)
    expect(brakDoboru(0)).toBe(false)
  })
})

describe('GRZEJNIKI_MAX / rozmiaryGrzejnikow / sumaGrzejnikow / grzejnikiPoprawne / opcjeIlosciGrzejnika', () => {
  it('GRZEJNIKI_MAX wynosi 15', () => {
    expect(GRZEJNIKI_MAX).toBe(15)
  })

  it('rozmiaryGrzejnikow ekstrahuje rozmiar z kodu pozycji', () => {
    expect(rozmiaryGrzejnikow(GRZEJNIK_POZYCJE)).toEqual([
      { kod: 'grzejnik_600x600', rozmiar: '600x600', nazwa: 'Grzejnik 600x600', opis: '' },
      { kod: 'grzejnik_600x1600', rozmiar: '600x1600', nazwa: 'Grzejnik 600x1600', opis: '' },
    ])
  })

  it('sumaGrzejnikow sumuje wszystkie rozmiary', () => {
    expect(sumaGrzejnikow({ '600x600': 2, '600x800': 0, '600x1000': 3 })).toBe(5)
    expect(sumaGrzejnikow({})).toBe(0)
    expect(sumaGrzejnikow(null)).toBe(0)
  })

  it('grzejnikiPoprawne odrzuca sume ponad limit', () => {
    expect(grzejnikiPoprawne({ '600x600': 15 })).toBe(true)
    expect(grzejnikiPoprawne({ '600x600': 10, '600x800': 6 })).toBe(false)
  })

  it('grzejnikiPoprawne odrzuca liczby ujemne i niecalkowite', () => {
    expect(grzejnikiPoprawne({ '600x600': -1 })).toBe(false)
    expect(grzejnikiPoprawne({ '600x600': 1.5 })).toBe(false)
  })

  it('opcjeIlosciGrzejnika ogranicza dostepne opcje do pozostalego limitu', () => {
    const grzejniki = { '600x600': 10, '600x800': 0 }
    expect(opcjeIlosciGrzejnika(grzejniki, '600x800')).toEqual([0, 1, 2, 3, 4, 5])
    // Wlasna, juz wybrana wartosc nie ogranicza sama siebie.
    const pelne = { '600x600': 15 }
    expect(opcjeIlosciGrzejnika(pelne, '600x600')).toEqual(Array.from({ length: 16 }, (_, i) => i))
  })
})

describe('kompletny*', () => {
  it('kompletnyRozbudowa wymaga co najmniej jednego wybranego elementu', () => {
    expect(kompletnyRozbudowa({ panele: 0, paneleMikro: 0, bateria: 0 })).toBe(false)
    expect(kompletnyRozbudowa({ panele: 1, paneleMikro: 0, bateria: 0 })).toBe(true)
    expect(kompletnyRozbudowa({ panele: 0, paneleMikro: 0, bateria: 2 })).toBe(true)
  })

  it('kompletnyKlimatyzacja/kompletnyKociol wymagaja wybranego kodu', () => {
    expect(kompletnyKlimatyzacja({ kod: '' })).toBe(false)
    expect(kompletnyKlimatyzacja({ kod: 'klima_elis_x_2_6' })).toBe(true)
    expect(kompletnyKociol({ kod: '' })).toBe(false)
    expect(kompletnyKociol({ kod: 'kociol_pellet_8' })).toBe(true)
  })

  it('kompletnyPompa wymaga czterech pol, CWU i grzejniki sa opcjonalne', () => {
    expect(kompletnyPompa({ zapotrzebowanie: '5', producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: '' })).toBe(false)
    expect(
      kompletnyPompa({ zapotrzebowanie: '5', producent: 'Rotenso', typ: 'Monoblok', ogrzewanie: 'Podłogówka' }),
    ).toBe(true)
  })

  it('kompletnyFormOze deleguje do wlasciwej funkcji wg form.rodzaj', () => {
    const rozbudowa = pustyFormularzOze(OZE_ROZBUDOWA)
    expect(kompletnyFormOze(rozbudowa)).toBe(false)
    rozbudowa.rozbudowa.bateria = 1
    expect(kompletnyFormOze(rozbudowa)).toBe(true)

    const kociol = pustyFormularzOze(OZE_KOCIOL)
    expect(kompletnyFormOze(kociol)).toBe(false)
    kociol.kociol.kod = 'kociol_duo_12'
    expect(kompletnyFormOze(kociol)).toBe(true)
  })

  it('kompletnyFormOze zwraca false dla nieznanego/pustego rodzaju', () => {
    expect(kompletnyFormOze({ rodzaj: '' })).toBe(false)
    expect(kompletnyFormOze(null)).toBe(false)
  })
})

describe('zbudujPayloadOze', () => {
  it('Rozbudowa: wysyla boolean dla ppoz_recznie, nigdy string "Tak"/"Nie"', () => {
    const form = pustyFormularzOze(OZE_ROZBUDOWA)
    form.rozbudowa.panele = 2
    form.rozbudowa.bateria = 1
    form.rozbudowa.ppozRecznie = 'Tak'
    const payload = zbudujPayloadOze(form)
    expect(payload.rodzaj).toBe(OZE_ROZBUDOWA)
    expect(payload.rozbudowa).toEqual({
      panele: 2,
      panele_mikro: 0,
      bateria: 1,
      istniejaca_pv_moc_kwp: 0,
      ppoz_recznie: true,
    })
    expect(payload.rozbudowa.ppoz_recznie).not.toBe('Tak')
    expect(payload.klimatyzacja).toBeUndefined()
  })

  it('Rozbudowa: ppozRecznie "Nie" daje boolean false', () => {
    const form = pustyFormularzOze(OZE_ROZBUDOWA)
    form.rozbudowa.panele = 1
    const payload = zbudujPayloadOze(form)
    expect(payload.rozbudowa.ppoz_recznie).toBe(false)
  })

  it('Rozbudowa: istniejaca_pv_moc_kwp zerowana, gdy istniejacaPv to Nie', () => {
    const form = pustyFormularzOze(OZE_ROZBUDOWA)
    form.rozbudowa.panele = 1
    form.rozbudowa.istniejacaPv = 'Nie'
    form.rozbudowa.istniejacaPvMocKwp = 99
    expect(zbudujPayloadOze(form).rozbudowa.istniejaca_pv_moc_kwp).toBe(0)
  })

  it('Rozbudowa: istniejaca_pv_moc_kwp przechodzi, gdy istniejacaPv to Tak', () => {
    const form = pustyFormularzOze(OZE_ROZBUDOWA)
    form.rozbudowa.panele = 1
    form.rozbudowa.istniejacaPv = 'Tak'
    form.rozbudowa.istniejacaPvMocKwp = 4.2
    expect(zbudujPayloadOze(form).rozbudowa.istniejaca_pv_moc_kwp).toBe(4.2)
  })

  it('Klimatyzacja: ulga_pct zerowana niezaleznie od sel.ulgaPct, niesie wylacznie kod', () => {
    const form = pustyFormularzOze(OZE_KLIMATYZACJA)
    form.ulgaPct = 19
    form.klimatyzacja.kod = 'klima_elis_x_2_6'
    const payload = zbudujPayloadOze(form)
    expect(payload.ulga_pct).toBe(0)
    expect(payload.klimatyzacja).toEqual({ kod: 'klima_elis_x_2_6' })
    expect(payload.rozbudowa).toBeUndefined()
  })

  it('Pompa ciepla: niesie zagniezdzone grzejniki, CWU puste gdy nie wybrane', () => {
    const form = pustyFormularzOze(OZE_POMPA_CIEPLA)
    form.pompa.zapotrzebowanie = '6.5'
    form.pompa.producent = 'Midea'
    form.pompa.typ = 'Split'
    form.pompa.ogrzewanie = 'Mieszane'
    form.pompa.grzejniki['600x800'] = 2
    const payload = zbudujPayloadOze(form)
    expect(payload.pompa).toEqual({
      zapotrzebowanie: '6.5',
      producent: 'Midea',
      typ: 'Split',
      ogrzewanie: 'Mieszane',
      cwu: '',
      grzejniki: { '600x600': 0, '600x800': 2, '600x1000': 0, '600x1200': 0, '600x1600': 0 },
    })
  })

  it('Pompa ciepla: grzejniki w payloadzie to kopia, nie referencja formularza', () => {
    const form = pustyFormularzOze(OZE_POMPA_CIEPLA)
    const payload = zbudujPayloadOze(form)
    payload.pompa.grzejniki['600x600'] = 99
    expect(form.pompa.grzejniki['600x600']).toBe(0)
  })

  it('Kociol: niesie kod i cwu', () => {
    const form = pustyFormularzOze(OZE_KOCIOL)
    form.kociol.kod = 'kociol_pellet_12'
    form.kociol.cwu = '200'
    expect(zbudujPayloadOze(form).kociol).toEqual({ kod: 'kociol_pellet_12', cwu: '200' })
  })

  it('niesie wspolne pola bazowe identycznie dla kazdego rodzaju', () => {
    const form = pustyFormularzOze(OZE_KOCIOL)
    form.typKlienta = 'biznesowy'
    form.narzut = 500
    form.okresLat = 7
    form.wplataWlasna = 1000
    const payload = zbudujPayloadOze(form)
    expect(payload.typ_klienta).toBe('biznesowy')
    expect(payload.narzut).toBe(500)
    expect(payload.okres_lat).toBe(7)
    expect(payload.wplata_wlasna).toBe(1000)
  })
})

describe('grupujWewnetrzneOze', () => {
  it('zwraca puste zera/tablice dla brakujacego wewnetrzne (D2D/Backend)', () => {
    expect(grupujWewnetrzneOze(null)).toEqual({
      koszt_calkowity: 0,
      marza_proenergy: 0,
      bonus_liderski: 0,
      narzut: 0,
      marza: 0,
      zysk: 0,
      grupy: [],
      pozycje: [],
    })
  })

  it('grupuje linie wg typu i liczy sumy per grupa', () => {
    const wewnetrzne = {
      koszt_calkowity: 20200,
      marza_proenergy: 11000,
      bonus_liderski: 3000,
      narzut: 0,
      marza: 14000,
      zysk: 14000,
      linie: [
        { klucz: 'a:koszt', etykieta: 'Bufor', typ: 'Koszt', kwota: 2000 },
        { klucz: 'a:koszt2', etykieta: 'Montaż', typ: 'Koszt', kwota: 5500 },
        { klucz: 'a:marza', etykieta: 'Marża ProEnergy', typ: 'Marża Proenergy', kwota: 11000 },
        { klucz: 'a:bonus', etykieta: 'Bonus liderski', typ: 'Bonus liderski', kwota: 3000 },
      ],
      pozycje: [{ kod: 'pc_rotenso_mono_6', nazwa: 'Pompa', ilosc: 1, netto: 34200, koszt: 20200, marza: 11000, bonus: 3000 }],
    }
    const wynik = grupujWewnetrzneOze(wewnetrzne)
    expect(wynik.grupy).toHaveLength(3)
    const kosztGrupa = wynik.grupy.find((g) => g.klucz === 'Koszt')
    expect(kosztGrupa.pozycje).toHaveLength(2)
    expect(kosztGrupa.suma).toBe(7500)
    expect(wynik.grupy.find((g) => g.klucz === 'Marża Proenergy').suma).toBe(11000)
    expect(wynik.grupy.find((g) => g.klucz === 'Bonus liderski').suma).toBe(3000)
    expect(wynik.pozycje).toHaveLength(1)
    expect(wynik.zysk).toBe(14000)
  })

  it('pomija grupy bez zadnej pasujacej linii', () => {
    const wynik = grupujWewnetrzneOze({
      koszt_calkowity: 0,
      marza_proenergy: 500,
      bonus_liderski: 0,
      narzut: 0,
      marza: 500,
      zysk: 500,
      linie: [{ klucz: 'x', etykieta: 'Y', typ: 'Marża Proenergy', kwota: 500 }],
      pozycje: [],
    })
    expect(wynik.grupy.map((g) => g.klucz)).toEqual(['Marża Proenergy'])
  })
})
