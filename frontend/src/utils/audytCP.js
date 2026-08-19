// Pure helpers for the Czyste Powietrze special audit tab (AudytCPTab.vue).
//
// Frappe-free by design, same idiom as audytWeryfikacja.js: the audit stores
// two sparse JSON blobs (dokumenty_json, zdjecia_json) plus a verification
// map (weryfikacja_json, same shape as the OZE audit's — reused from
// audytWeryfikacja.js), and this module derives the element list and
// submit-readiness without importing Vue or app runtime.
//
// Unlike the OZE Audyt (AudytTab.vue), Czyste Powietrze has no variant
// matrix — the document catalog is fixed, so it is mirrored here as a plain
// constant rather than fetched via a requirements call. Element keys are the
// slot keys themselves (already namespaced `dok:...`), never wrapped in
// audytWeryfikacja.js's `pole:`/`foto:` prefixes — those prefixes exist to
// disambiguate a mixed matrix of fields and photo slots, which CP doesn't
// have (every slot here is a file, and the prefixes would just be noise on
// top of already-unique keys).

// Catalog order matters: it's the order slots render in and the order their
// keys appear in cpElements()'s output.
export const SLOTY = [
  { key: 'dok:ankieta_cp', label: 'Ankieta danych Czyste Powietrze', required: true },
  { key: 'dok:gops_zaswiadczenie', label: 'Zaświadczenie o dochodach', required: true },
  { key: 'dok:umowa_obsluga_dotacji', label: 'Umowa na obsługę dotacji', required: true },
  { key: 'dok:pelnomocnictwo_notarialne', label: 'Pełnomocnictwo notarialne', required: true },
  { key: 'dok:ankieta_trify', label: 'Ankieta kredytowa', required: true },
  { key: 'dok:zgoda_wspolwlascicieli', label: 'Zgoda współwłaścicieli', required: false },
  { key: 'dok:zgoda_wspolmalzonka', label: 'Zgoda współmałżonka', required: false },
]

export const KLUCZ_ZDJECIA = 'dok:zdjecia'
export const MAX_ZDJEC = 20
export const MAX_NOTATKA = 500

function jestZwyklymObiektem(value) {
  if (value === null || typeof value !== 'object') return false
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

// Shared parse step for both parsujMape/parsujListe: JSON.parse once, and
// again if the result is itself a JSON-encoded string (double-encoding seen
// in the wild on these *_json columns — see audytWeryfikacja.js's
// parsedMap(), same tolerance). Never throws; returns whatever it lands on
// (which may still be the wrong shape — the caller's shape check decides).
function sparsuj(raw) {
  if (raw === null || raw === undefined || raw === '') return null
  if (typeof raw !== 'string') return raw
  let parsed
  try {
    parsed = JSON.parse(raw)
  } catch (e) {
    return null
  }
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch (e) {
      // Keep the once-parsed string — the shape check below rejects it.
    }
  }
  return parsed
}

/** Tolerant parse of dokumenty_json — always returns a plain object. */
export function parsujMape(raw) {
  const parsed = sparsuj(raw)
  return jestZwyklymObiektem(parsed) ? parsed : {}
}

/** Tolerant parse of zdjecia_json — always returns an array. */
export function parsujListe(raw) {
  const parsed = sparsuj(raw)
  return Array.isArray(parsed) ? parsed : []
}

// Elements a reviewer must give a verdict to: every catalog slot that
// actually has a file attached (an empty optional slot isn't reviewable —
// there's nothing to accept or reject), in catalog order, followed by the
// single grouped photo-gallery element, always last regardless of how many
// photos exist (0 photos still blocks submission via brakiDoPrzeslania
// below — cpElements itself doesn't gate on the count).
export function cpElements(dokumenty, zdjecia) {
  const dok = jestZwyklymObiektem(dokumenty) ? dokumenty : {}
  const elementy = SLOTY.filter((slot) => typeof dok[slot.key] === 'string' && dok[slot.key]).map(
    (slot) => slot.key,
  )
  elementy.push(KLUCZ_ZDJECIA)
  return elementy
}

/** Same shape/rule as audytWeryfikacja.js's aggregate(): 0 elements never counts as fully accepted. */
export function cpAggregate(weryfikacja, elementy) {
  const map = jestZwyklymObiektem(weryfikacja) ? weryfikacja : {}
  const lista = Array.isArray(elementy) ? elementy : []
  let accepted = 0
  let errors = 0
  lista.forEach((key) => {
    const entry = map[key]
    const status = jestZwyklymObiektem(entry) && (entry.status === 'accepted' || entry.status === 'error')
      ? entry.status
      : 'waiting'
    if (status === 'accepted') accepted += 1
    if (status === 'error') errors += 1
  })
  const total = lista.length
  return {
    total,
    accepted,
    errors,
    waiting: total - accepted - errors,
    allAccepted: total > 0 && accepted === total,
  }
}

// Client-side pre-check before calling volteo_audyt_cp_submit — the server
// re-validates independently and is authoritative; this only saves a round
// trip and gives the rep a readable Polish list instead of a generic 500.
export function brakiDoPrzeslania(dokumenty, zdjecia) {
  const dok = jestZwyklymObiektem(dokumenty) ? dokumenty : {}
  const zdj = Array.isArray(zdjecia) ? zdjecia : []
  const braki = []

  SLOTY.filter((slot) => slot.required).forEach((slot) => {
    if (!(typeof dok[slot.key] === 'string' && dok[slot.key])) {
      braki.push(`Brak dokumentu: ${slot.label}`)
    }
  })

  if (zdj.length === 0) {
    braki.push('Brak zdjęć — wymagane co najmniej 1 zdjęcie')
  } else if (zdj.length > MAX_ZDJEC) {
    braki.push(`Zbyt wiele zdjęć — maksymalnie ${MAX_ZDJEC}`)
  }

  return braki
}
