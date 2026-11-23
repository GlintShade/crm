// Stan i ladowanie danych grupowania listy (ops#413). Czysta logika siedzi w
// utils/grupowanieListy.js; tu tylko reaktywnosc i wywolania serwera.
// Liczniki: jedno `get_group_counts` po CALYM wyniku listy; wiersze: osobne
// `get_data` z parametrem `grupa` dla kazdej rozwinietej grupy (wspolne filtry
// listy, wiec liczniki i wiersze nie rozjezdzaja sie).
import { call, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import {
  ODMOWA_LIMIT,
  STAN_PUSTY,
  czyZwinieta,
  dlugoscStrony,
  parsujStan,
  podsumowanie,
  powiekszStrone,
  przelaczZwiniecie,
  rozwinWszystkie,
  stanZWidoku,
  ustawPokazPuste,
  ustawPole,
  wierszeGrup,
  zbudujGrupy,
  zwinWszystkie,
} from '@/utils/grupowanieListy'

const LIMIT_RownoczesnychZapytan = 3

export function useGrupowanieListy({
  doctype,
  list,
  widok,
  poleZPrzekierowania,
  widokListy,
  zapisz,
}) {
  const pola = ref([])
  const stan = ref(parsujStan(widok()?.volteo_grupowanie || null))
  const grupy = ref(null)
  const rodzaj = ref('select')
  const odmowa = ref(null)
  const strony = ref({})
  const dane = reactive({})
  let generacja = 0
  let ostatniRozmiar = null

  const rozmiar = computed(() => list.value?.data?.page_length_count || 20)
  const aktywne = computed(
    () => widokListy.value && !!stan.value.pole && !odmowa.value,
  )
  // true gdy wlaczone grupowanie czeka jeszcze na pierwsze liczniki
  const oczekuje = computed(
    () => widokListy.value && !!stan.value.pole && !odmowa.value && grupy.value === null,
  )
  const etykietaPola = computed(
    () => pola.value.find((p) => p.fieldname === stan.value.pole)?.label || '',
  )
  const grupyZbudowane = computed(() =>
    zbudujGrupy(grupy.value, stan.value, dane, rodzaj.value),
  )
  const sumy = computed(() => podsumowanie(grupy.value))

  // Prosta kolejka: nie odpalamy 30 zapytan naraz przy grupowaniu po handlowcu.
  let wolne = LIMIT_RownoczesnychZapytan
  const oczekujace = []
  function wKolejce(zadanie) {
    return new Promise((resolve) => {
      const uruchom = async () => {
        wolne--
        try {
          resolve(await zadanie())
        } finally {
          wolne++
          oczekujace.shift()?.()
        }
      }
      if (wolne > 0) uruchom()
      else oczekujace.push(uruchom)
    })
  }

  function komunikat(err) {
    return err?.messages?.[0] || __('Nie udało się wczytać grup.')
  }

  async function wczytajGrupe(klucz) {
    const pole = stan.value.pole
    const gen = generacja
    dane[klucz] = { ...dane[klucz], wczytuje: true }
    await wKolejce(async () => {
      if (gen !== generacja) return
      const dlugosc = dlugoscStrony(strony.value, klucz, rozmiar.value)
      try {
        const wynik = await call('crm.api.doc.get_data', {
          ...list.value.params,
          page_length: dlugosc,
          page_length_count: dlugosc,
          grupa: { pole, klucz },
        })
        if (gen !== generacja) return
        dane[klucz] = { wiersze: wynik?.data || [], wczytuje: false }
      } catch (err) {
        if (gen !== generacja) return
        dane[klucz] = { wiersze: dane[klucz]?.wiersze || [], wczytuje: false }
        toast.error(komunikat(err))
      }
    })
  }

  async function odswiez() {
    if (!stan.value.pole || !widokListy.value || !list.value?.params) return
    const gen = ++generacja
    const rozmiarTeraz = rozmiar.value
    if (ostatniRozmiar !== null && ostatniRozmiar !== rozmiarTeraz) {
      strony.value = {}
    }
    ostatniRozmiar = rozmiarTeraz
    const p = list.value.params
    try {
      const wynik = await call('crm.api.doc.get_group_counts', {
        doctype,
        filters: p.filters || {},
        group_field: stan.value.pole,
        show_empty: stan.value.pokazPuste,
        default_filters: p.default_filters || {},
      })
      if (gen !== generacja) return
      if (wynik?.odmowa === ODMOWA_LIMIT) {
        const nowa = !odmowa.value
        odmowa.value = wynik
        grupy.value = null
        if (nowa) toast.error(komunikatLimitu(wynik.limit))
        return
      }
      odmowa.value = null
      rodzaj.value = wynik?.rodzaj || 'select'
      grupy.value = wynik?.grupy || []
      const obecne = new Set(grupy.value.map((g) => g.klucz))
      Object.keys(dane).forEach((k) => {
        if (!obecne.has(k)) delete dane[k]
      })
      grupy.value
        .filter((g) => !czyZwinieta(stan.value, g.klucz))
        .forEach((g) => wczytajGrupe(g.klucz))
    } catch (err) {
      if (gen !== generacja) return
      grupy.value = []
      toast.error(komunikat(err))
    }
  }

  function komunikatLimitu(limit) {
    return __('Zawęź filtry do {0} leadów, aby grupować', [limit || 2000])
  }
  const komunikatOdmowy = computed(() =>
    odmowa.value ? komunikatLimitu(odmowa.value.limit) : '',
  )

  function zmienStan(nowy, { lekka = false, przeladuj = true } = {}) {
    stan.value = nowy
    zapisz(nowy, { lekka })
    if (przeladuj) {
      generacja++
      Object.keys(dane).forEach((k) => delete dane[k])
      grupy.value = null
      odmowa.value = null
      strony.value = {}
      odswiez()
    }
  }

  function ustawPolem(pole) {
    zmienStan(pole ? ustawPole(stan.value, pole) : { ...STAN_PUSTY, zwiniete: [] })
  }
  function przelaczPustych() {
    zmienStan(ustawPokazPuste(stan.value, !stan.value.pokazPuste))
  }
  function zwinWsz() {
    zmienStan(
      zwinWszystkie(stan.value, (grupy.value || []).map((g) => g.klucz)),
      { lekka: true, przeladuj: false },
    )
  }
  function rozwinWsz() {
    zmienStan(rozwinWszystkie(stan.value), { lekka: true, przeladuj: false })
    ;(grupy.value || []).forEach((g) => {
      if (!dane[g.klucz]?.wiersze) wczytajGrupe(g.klucz)
    })
  }
  function przelacz(klucz) {
    const bylaZwinieta = czyZwinieta(stan.value, klucz)
    zmienStan(przelaczZwiniecie(stan.value, klucz), { lekka: true, przeladuj: false })
    if (bylaZwinieta && !dane[klucz]?.wiersze) wczytajGrupe(klucz)
  }
  function wiecej(klucz) {
    strony.value = powiekszStrone(strony.value, klucz, rozmiar.value)
    wczytajGrupe(klucz)
  }

  // wiersze dla strony: `parsuj` zamienia surowe wiersze na komorki (parseRows)
  function wiersze(parsuj) {
    return wierszeGrup(grupyZbudowane.value, parsuj, { przelacz, wiecej })
  }

  // "Anuluj" zmian nazwanego widoku: wracamy do stanu zapisanego w widoku.
  function przywroc() {
    const nowy = stanZWidoku(widok(), pola.value.map((p) => p.fieldname), null)
    zmienStan(nowy, { lekka: true })
  }

  // Pola z serwera (juz przyciete do uprawnien roli). Po wczytaniu sprawdzamy stan
  // z widoku: pole, ktorego rola nie moze czytac, wyłącza grupowanie bez bledu.
  const polaGotowe = call('crm.api.doc.get_group_by_fields', { doctype })
    .then((wynik) => {
      pola.value = wynik || []
      const nazwy = pola.value.map((p) => p.fieldname)
      const poczatkowy = stanZWidoku(widok(), nazwy, poleZPrzekierowania())
      const zwiniete = stan.value.pole === poczatkowy.pole ? stan.value.zwiniete : poczatkowy.zwiniete
      stan.value = { ...poczatkowy, zwiniete: [...zwiniete] }
      if (stan.value.pole) odswiez()
    })
    .catch(() => {
      pola.value = []
      stan.value = { ...STAN_PUSTY, zwiniete: [] }
    })

  // Kazda nowa odpowiedz glownej listy (filtr, sortowanie, akcja zbiorcza, rozmiar
  // strony) odswieza liczniki i wiersze rozwinietych grup.
  let czasomierz = null
  watch(
    () => list.value?.data,
    () => {
      clearTimeout(czasomierz)
      czasomierz = setTimeout(() => stan.value.pole && polaGotowe.then(odswiez), 80)
    },
  )

  return {
    pola,
    stan,
    aktywne,
    oczekuje,
    odmowa,
    komunikatOdmowy,
    etykietaPola,
    sumy,
    wiersze,
    ustawPolem,
    przelaczPustych,
    zwinWsz,
    rozwinWsz,
    przelacz,
    wiecej,
    odswiez,
    przywroc,
  }
}
