# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Okno rejestracji aplikacji z kodami (drugi skladnik, ops#422), rdzen bez frappe.

Okno to znacznik czasu konca (sekundy epoch) trzymany w domyslnych wartosciach
Frappe pod kluczem `<user>_volteo_qr_do`. Okno jest otwarte, gdy znacznik jest
w przyszlosci. Konto, ktore ma juz `<user>_otplogin`, nigdy nie dostaje QR.
"""

CZAS_OKNA_S = 24 * 60 * 60
KLUCZ_OKNA = "_volteo_qr_do"


def koniec_okna(teraz: float) -> float:
	return teraz + CZAS_OKNA_S


def _do_liczby(znacznik) -> float | None:
	try:
		return float(znacznik)
	except (TypeError, ValueError):
		return None


def okno_otwarte(znacznik, teraz: float) -> bool:
	do = _do_liczby(znacznik)
	return do is not None and teraz < do


def pokazac_qr(zarejestrowane: bool, znacznik, teraz: float) -> bool:
	"""QR na stronie logowania: konto jeszcze nie zarejestrowane i okno otwarte."""
	return (not zarejestrowane) and okno_otwarte(znacznik, teraz)


def wyslac_mail_po_rejestracji(zarejestrowane: bool, znacznik) -> bool:
	"""Konto ma juz aplikacje, a klucz okna jeszcze wisi: to pierwszy kod po rejestracji."""
	return bool(zarejestrowane) and _do_liczby(znacznik) is not None


def pierwsze_haslo_otwiera_okno(objete: bool, mialo_haslo: bool, zarejestrowane: bool) -> bool:
	return bool(objete) and (not mialo_haslo) and (not zarejestrowane)
