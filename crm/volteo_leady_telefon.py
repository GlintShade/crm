# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Filtr telefonu na liscie i mapie leadow (ops#311).

Modul celowo nie importuje ``frappe``: logike da sie przetestowac lokalnie.

Numery w bazie sa zapisane jako `+48XXXXXXXXX` (patrz
`crm.volteo_leady_import.normalizuj_telefon`), a uzytkownik wpisuje je
roznie: `604 932 720`, `604-932-720`, `+48 604 932 720`. Pasek szybkich
filtrow wysyla dla pola Data `["LIKE", "%wpisane%"]`, wiec z wnetrza wzorca
usuwamy wszystko poza cyframi, a skrajne `%` zostawiamy.
"""

POLE_TELEFONU: str = "mobile_no"
"""Pole telefonu na `CRM Lead`, ktorego filtr LIKE normalizujemy."""


def _wyczysc_wzorzec(wzorzec: str) -> str:
	poczatek = "%" if wzorzec.startswith("%") else ""
	koniec = "%" if len(wzorzec) > len(poczatek) and wzorzec.endswith("%") else ""
	wnetrze = wzorzec[len(poczatek) : len(wzorzec) - len(koniec)]
	cyfry = "".join(znak for znak in wnetrze if znak.isdigit())
	if not cyfry:
		return ""
	return f"{poczatek}{cyfry}{koniec}"


def normalizuj_filtr_telefonu(filters) -> dict:
	"""Zwraca NOWY slownik filtrow z oczyszczonym wzorcem LIKE dla `mobile_no`.

	Inne ksztalty (inny operator, rownosc, inne pola) przechodza bez zmian.
	Wzorzec, ktory po oczyszczeniu jest pusty, usuwa klucz calkowicie.
	"""
	wynik = dict(filters or {})
	wartosc = wynik.get(POLE_TELEFONU)
	if (
		isinstance(wartosc, (list, tuple))
		and len(wartosc) == 2
		and isinstance(wartosc[0], str)
		and wartosc[0].lower() == "like"
		and isinstance(wartosc[1], str)
	):
		wzorzec = _wyczysc_wzorzec(wartosc[1])
		if wzorzec:
			wynik[POLE_TELEFONU] = [wartosc[0], wzorzec]
		else:
			del wynik[POLE_TELEFONU]
	return wynik
