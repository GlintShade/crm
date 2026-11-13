// Uwaga 71: handlowiec (Volteo D2D Sales bez rol uprzywilejowanych) nie zmienia
// statusu CC leada. Czysta funkcja, wzorem serwerowego
// crm/volteo_leady_status.py::czy_moze_zmienic_status_cc (ta sama regula).
// Uwaga 81: flaga uzytkownika `custom_zmiana_statusu_cc` (ustawiana przez
// administracje w Ustawienia -> Uzytkownicy) zdejmuje blokade z wybranego handlowca.
const ROLE_ZMIANY_STATUSU_CC = [
  'Volteo Call Center',
  'Volteo Backend',
  'Volteo Core Admin',
  'System Manager',
]

// ops#351: lead z reguly bezposredniej (`custom_przydzial_bezposredni` = 1),
// ktorego wlascicielem (`lead_owner`) jest biezacy uzytkownik. `lead` to surowy
// dokument/wiersz (lead_owner jako e-mail) albo wiersz po parseRows (lead_owner
// jako obiekt z polem `name`); brak leada albo pola w bazie daje false.
export function leadBezposredniWlasny(lead, uzytkownik) {
  if (!lead || !uzytkownik) return false
  const owner = lead.lead_owner
  const email = owner && typeof owner === 'object' ? owner.name || '' : owner || ''
  if (!email || email !== uzytkownik) return false
  return Number(lead.custom_przydzial_bezposredni) === 1
}

export function mozeZmieniacStatusCC(
  roles,
  isAdminUser = false,
  flagaUzytkownika = false,
  lead = null,
  uzytkownik = '',
) {
  if (isAdminUser || flagaUzytkownika) return true
  if (leadBezposredniWlasny(lead, uzytkownik)) return true
  const lista = roles || []
  if (lista.some((r) => ROLE_ZMIANY_STATUSU_CC.includes(r))) return true
  return !lista.includes('Volteo D2D Sales')
}

// Zwraca NOWE sekcje, w ktorych pole `status` jest read_only. Nie mutuje
// wejscia (zasob sections jest wspoldzielony miedzy instancjami panelu).
export function sekcjeZeStatusemTylkoDoOdczytu(sections) {
  if (!sections?.length) return sections
  return sections.map((section) => {
    if (!section.columns?.length) return section
    return {
      ...section,
      columns: section.columns.map((column) => ({
        ...column,
        fields: (column.fields || []).map((field) =>
          field.fieldname === 'status' ? { ...field, read_only: 1 } : field,
        ),
      })),
    }
  })
}
