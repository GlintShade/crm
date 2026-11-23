# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta logika kolumny "Klient" na liscie Zadan (`CRM Task`).

Modul celowo nie importuje ``frappe``, wzorem ``crm/volteo_zadania.py`` i
``crm/volteo_pipeline.py``. Warstwe frappe-owa (zapytania o `lead_name` szans
i leadow) niesie `crm.api.doc._dolacz_klienta_zadan`.

Funkcje sa immutable: zwracaja nowe struktury, nigdy nie mutuja argumentow.
"""

KLUCZ_KLIENTA = "_klient"
"""Pseudo-pole listy: nie jest DocFieldem, dzieli klucz kolumny "Klient"
z `CRMTask.default_list_data()`. Wartosc dokleja `get_data` po zapytaniu SQL."""

DOCTYPE_SZANSY = "CRM Deal"
DOCTYPE_LEADA = "CRM Lead"


def klient_zadania(
	reference_doctype: str | None,
	reference_docname: str | None,
	klienci_szans: dict,
	klienci_leadow: dict,
) -> str:
	"""Nazwa klienta zadania: `lead_name` szansy (CRM Deal) albo leada (CRM Lead).

	Brak powiazania, nieznany doctype albo brak wpisu w mapie daje pusty string.
	"""
	if not reference_doctype or not reference_docname:
		return ""
	if reference_doctype == DOCTYPE_SZANSY:
		mapa = klienci_szans
	elif reference_doctype == DOCTYPE_LEADA:
		mapa = klienci_leadow
	else:
		return ""
	return (mapa.get(reference_docname) or "").strip()


def nazwy_powiazan(wiersze: list[dict]) -> tuple[list[str], list[str]]:
	"""Unikalne nazwy szans i leadow z wierszy listy zadan.

	Zwraca `(szanse, leady)`, kazda lista w kolejnosci pierwszego wystapienia,
	bez duplikatow i bez pustych nazw.
	"""
	szanse: list[str] = []
	leady: list[str] = []
	for wiersz in wiersze:
		doctype = wiersz.get("reference_doctype")
		nazwa = wiersz.get("reference_docname")
		if not nazwa:
			continue
		if doctype == DOCTYPE_SZANSY and nazwa not in szanse:
			szanse.append(nazwa)
		elif doctype == DOCTYPE_LEADA and nazwa not in leady:
			leady.append(nazwa)
	return szanse, leady


DOCTYPE_ZADANIA = "CRM Task"
KLUCZ_PO_KTORYM_KLIENT = "title"
"""Pole paska szybkich filtrow, zaraz po ktorym staje pseudo-pole `_klient`."""

LIMIT_POWIAZAN = 2000
"""Maks. liczba szans i leadow (osobno) pasujacych do tekstu klienta."""

LIMIT_ZADAN = 5000
"""Maks. liczba zadan zwracana przez rozwiniecie filtra klienta."""


def tekst_filtra_klienta(wartosc: object) -> str | None:
	"""Tekst szukanego klienta z wartosci filtra `_klient`.

	Pasek szybkich filtrow wysyla pole tekstowe jako `["LIKE", "%tekst%"]`;
	akceptujemy tez male litery (`"like"`) i zwykly string. Znaki `%` i
	biale znaki z brzegow sa zdejmowane. Pusty tekst albo nieobslugiwany
	ksztalt (inny operator, inny typ, zla dlugosc listy) daje None.
	"""
	if isinstance(wartosc, str):
		tekst = wartosc
	elif isinstance(wartosc, (list, tuple)) and len(wartosc) == 2:
		operator, tekst = wartosc
		if not isinstance(operator, str) or operator.strip().lower() != "like":
			return None
		if not isinstance(tekst, str):
			return None
	else:
		return None
	tekst = tekst.replace("%", "").strip()
	return tekst or None


def zawez_nazwy_zadan(nazwy: list, rodzaj: str, istniejace: set) -> list:
	"""Przeciecie (rodzaj `in`) albo roznica (`not in`) nazw zadan z innym
	ograniczeniem po `name`. Nazwy zadan to liczby, a filtr z zewnatrz bywa
	tekstem, wiec porownanie idzie po `str()`; zwracane sa oryginalne wartosci
	z `nazwy` (kolejnosc zachowana)."""
	zbior = {str(n) for n in istniejace}
	if rodzaj == "not in":
		return [n for n in nazwy if str(n) not in zbior]
	return [n for n in nazwy if str(n) in zbior]


def uklad_paska_z_klientem(uklad: list, doctype: str) -> list:
	"""Globalny uklad paska szybkich filtrow listy Zadan z pseudo-polem
	`_klient` zaraz po `title`, gdy zapisany uklad go nie wymienia. Uklad,
	ktory juz wymienia `_klient`, i kazdy inny doctype wracaja bez zmian
	(nowa lista, argument nie jest mutowany). Brak `title` daje `_klient`
	na poczatku."""
	if doctype != DOCTYPE_ZADANIA or KLUCZ_KLIENTA in uklad:
		return list(uklad)
	if KLUCZ_PO_KTORYM_KLIENT in uklad:
		indeks = uklad.index(KLUCZ_PO_KTORYM_KLIENT) + 1
	else:
		indeks = 0
	return [*uklad[:indeks], KLUCZ_KLIENTA, *uklad[indeks:]]


# ops#411: osoby "Do wiadomosci" na liscie Zadan. Oba klucze to pseudo-pola (nie
# DocFieldy): `_dw` to kolumna (lista nazw uzytkownikow doklejana po zapytaniu) i
# filtr (rozwijany na `name in/not in [...]`); `_rola_ja` to sam filtr, suma
# "jestem osoba odpowiedzialna ALBO jestem na liscie Do wiadomosci".
DOCTYPE_DW = "Volteo Zadanie DW"
KLUCZ_DW = "_dw"
KLUCZ_ROLA_JA = "_rola_ja"
KLUCZE_PSEUDO_FILTRA = (KLUCZ_KLIENTA, KLUCZ_DW, KLUCZ_ROLA_JA)


def filtr_dw(wartosc: object) -> tuple[str, list[str]] | None:
	"""`(rodzaj, uzytkownicy)` z wartosci filtra `_dw`: `"in"` ("jest w") albo
	`"not in"` ("nie jest w"). Rozpoznaje skalar, `["=", u]`, `["!=", u]`,
	`["in", [...]]`, `["not in", [...]]` (operator bez wzgledu na wielkosc liter).
	Kazdy inny ksztalt albo pusta lista dostaje None (filtr po prostu znika)."""
	if isinstance(wartosc, str):
		operator, argument = "=", wartosc
	elif isinstance(wartosc, (list, tuple)) and len(wartosc) == 2 and isinstance(wartosc[0], str):
		operator, argument = wartosc[0].strip().lower(), wartosc[1]
	else:
		return None
	if operator in ("=", "!=") and isinstance(argument, str):
		argument = [argument]
	if operator not in ("=", "!=", "in", "not in") or not isinstance(argument, (list, tuple)):
		return None
	uzytkownicy = [u.strip() for u in argument if isinstance(u, str) and u.strip()]
	if not uzytkownicy:
		return None
	return ("not in" if operator in ("!=", "not in") else "in"), uzytkownicy


def polacz_filtr_name(istniejacy: tuple[str, set] | None, rodzaj: str, nazwy: list) -> tuple[str, list]:
	"""Wynikowy filtr po `name` z istniejacego (`(rodzaj, zbior)` albo None) i
	nowego (`rodzaj` in / not in, `nazwy`). Nazwy zadan to liczby, a filtr z
	zewnatrz bywa tekstem, wiec porownanie idzie po `str()`; zwracane sa
	oryginalne wartosci (kolejnosc zachowana). Nowa lista, argumenty nietkniete."""
	if istniejacy is None:
		return rodzaj, list(nazwy)
	rodzaj_e, zbior_e = istniejacy
	e = {str(n) for n in zbior_e}
	n_str = {str(n) for n in nazwy}
	if rodzaj_e == "in" and rodzaj == "in":
		return "in", [n for n in nazwy if str(n) in e]
	if rodzaj_e == "in":  # in E, not in N
		return "in", [n for n in sorted(zbior_e, key=str) if str(n) not in n_str]
	if rodzaj == "in":  # not in E, in N
		return "in", [n for n in nazwy if str(n) not in e]
	return "not in", [*sorted(zbior_e, key=str), *[n for n in nazwy if str(n) not in e]]
