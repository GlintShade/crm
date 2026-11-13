// Ostrzezenie o koncie administracyjnym przy zakladaniu szansy i klienta
// (ops#337). Czyste funkcje tekstowe, bez zaleznosci od sklepu.
export function czyKontoAdministracyjne(isVolteoAdmin, isBackend) {
  return Boolean(isVolteoAdmin) || Boolean(isBackend)
}

export function tekstOstrzezenia(rodzaj) {
  if (rodzaj === 'klient') {
    return __(
      'Pracujesz na koncie administracyjnym. Klient zostanie zapisany na to konto, a nie na konto handlowca.',
    )
  }
  return __(
    'Pracujesz na koncie administracyjnym. Szansa zostanie zapisana na to konto, a nie na konto handlowca. Po utworzeniu ustaw doradcę w nagłówku szansy.',
  )
}
