import { ref } from 'vue'

// Sekcja "Komentarze" w zakladce Szczegoly leada (b84) wchodzi zaraz pod
// sekcja "Spotkanie" ukladu panelu (CRM Fields Layout, name
// spotkanie_section). Rozpoznajemy ja po nazwie albo etykiecie.

export const NAZWA_SEKCJI_SPOTKANIE = 'spotkanie_section'

export function czySekcjaSpotkanie(section) {
  return (
    section?.name === NAZWA_SEKCJI_SPOTKANIE || section?.label === 'Spotkanie'
  )
}

// Hash adresu, ktory ma otworzyc sekcje komentarzy: dawna zakladka
// (#comments) albo nazwa komentarza z powiadomienia o wzmiance (#<name>),
// czyli kazdy hash, ktory nie jest nazwa zakladki.
export function hashWskazujeKomentarze(hash, nazwyZakladek) {
  const h = String(hash || '').replace(/^#/, '')
  if (!h) return false
  if (h === 'comments') return true
  return !(nazwyZakladek || []).some((n) => String(n).toLowerCase() === h)
}

// Prosba "otworz i przewin do Komentarzy" z adresu (Lead.vue ustawia, sekcja
// konsumuje, takze gdy zamontuje sie dopiero po przelaczeniu na Szczegoly).
export const przewinDoKomentarzy = ref(false)
