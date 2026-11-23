// Logika pola "Do wiadomosci" w oknie zadania (ops#411): lista wierszy
// `[{user: <login>}]` (ksztalt kontraktu z backendem, tabela potomna
// `Volteo Zadanie DW`). Czyste funkcje, bez frappe/Vue; nic nie mutuje wejscia.

/** Loginy z wierszy `[{user}]`; puste wpisy pomijane. */
export function loginyZWierszy(wiersze) {
  return (Array.isArray(wiersze) ? wiersze : [])
    .map((w) => w?.user)
    .filter(Boolean)
}

/** Nowa lista wierszy z dodanym albo usunietym loginem (przelacznik). */
export function przelaczOsobe(wiersze, login) {
  if (!login) return Array.isArray(wiersze) ? [...wiersze] : []
  const loginy = loginyZWierszy(wiersze)
  const zostaja = loginy.includes(login)
    ? loginy.filter((l) => l !== login)
    : [...loginy, login]
  return zostaja.map((user) => ({ user }))
}

/** Opcje do wyboru: uzytkownicy CRM bez osoby odpowiedzialnej, wg nazwy, z filtrem tekstu. */
export function opcjeOsob(uzytkownicy, wykonawca, szukaj = '') {
  const fraza = (szukaj || '').trim().toLowerCase()
  return (Array.isArray(uzytkownicy) ? uzytkownicy : [])
    .filter((u) => u?.name && u.name !== wykonawca)
    .filter(
      (u) =>
        !fraza ||
        (u.full_name || '').toLowerCase().includes(fraza) ||
        u.name.toLowerCase().includes(fraza),
    )
    .sort((a, b) =>
      (a.full_name || a.name).localeCompare(b.full_name || b.name, 'pl'),
    )
}

/** Chipy: `{login, nazwa}`; nazwa = pelna nazwa, a bez niej login. */
export function chipyOsob(wiersze, pobierzUzytkownika) {
  return loginyZWierszy(wiersze).map((login) => ({
    login,
    nazwa: pobierzUzytkownika(login)?.full_name || login,
  }))
}
