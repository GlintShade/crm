# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
Lookup kodu pocztowego (ops#329)
==================================

Następca Server Scriptu `volteo_postal_lookup` w forku: jeden lookup w całej
aplikacji. Front (panel leada, `ContactModal.vue`, `DaneKlientaTab.vue`) woła
`crm.api.kod_pocztowy.wyszukaj`, webhook leadów `dane_kodu` (import w
`crm.api.leady_webhook`). Server Script zostaje na razie w bazie, nikt z forka go
już nie woła; odpowiedź ma ten sam kształt:
`{found, wojewodztwo, powiat, gmina, miejscowosc, cities}`.

Dwa stopnie:
1. cache `Postal Code` po polu `kod`;
2. gdy wiersza brak ALBO brakuje w nim `cities` lub `gmina` (większość wierszy
   GeoNames), Adresy.app z timeoutem 5 s. Wynik uzupełnia cache: istniejący wiersz
   dostaje tylko puste pola (`frappe.db.set_value`, bez `modified`), brak wiersza
   to insert. Zapis cache idzie w savepoincie i jego błąd nie psuje odpowiedzi.

Błąd sieci, brak klucza API albo niepoprawna odpowiedź Adresy.app: wynik z samego
cache (albo `found: False`), wpis w Error Log tylko przy błędzie HTTP. Funkcja
`dane_kodu` nigdy nie rzuca dla poprawnego kodu poza błędem samej bazy; webhook i
tak owija ją w `try`.

Logika bez `frappe` jest w `crm/volteo_kod_pocztowy.py`.
"""

import frappe
import requests
from frappe.utils.password import get_decrypted_password

from crm.volteo_kod_pocztowy import (
	TIMEOUT_ADRESY_SEK,
	URL_ADRESY,
	normalizuj_kod,
	nowy_wiersz_cache,
	parsuj_odpowiedz_adresy,
	pola_do_uzupelnienia_cache,
	scal_wynik,
	wiersz_kompletny,
)

DOCTYPE_CACHE = "Postal Code"
DOCTYPE_USTAWIEN = "Volteo Settings"
TYTUL_BLEDU = "Kod pocztowy (Adresy.app)"
_SAVEPOINT = "volteo_kod_pocztowy_cache"


def _klucz_api() -> str:
	"""Klucz Adresy.app z `Volteo Settings.adresy_api_key` (Password albo Data)."""
	klucz = get_decrypted_password(
		DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "adresy_api_key", raise_exception=False
	)
	if not klucz:
		klucz = frappe.db.get_single_value(DOCTYPE_USTAWIEN, "adresy_api_key")
	return (klucz or "").strip()


def _zapytaj_adresy(kod: str, timeout: int) -> dict | None:
	"""Jedna próba HTTP; każdy błąd to `None` i wpis w Error Log (bez klucza API)."""
	klucz = _klucz_api()
	if not klucz:
		return None
	try:
		odp = requests.get(URL_ADRESY, params={"q": kod, "api_key": klucz}, timeout=timeout)
		odp.raise_for_status()
		return parsuj_odpowiedz_adresy(odp.json(), kod)
	except Exception as blad:
		frappe.log_error(title=TYTUL_BLEDU, message="Kod %s: %s" % (kod, type(blad).__name__))
		return None


def _zapisz_cache(kod: str, wiersz: dict | None, adresy: dict) -> None:
	"""Uzupełnia albo zakłada wiersz cache; błąd cofa tylko savepoint."""
	try:
		frappe.db.savepoint(_SAVEPOINT)
		if wiersz:
			zmiany = pola_do_uzupelnienia_cache(wiersz, adresy)
			if zmiany:
				frappe.db.set_value(DOCTYPE_CACHE, wiersz["name"], zmiany, update_modified=False)
		else:
			frappe.get_doc({"doctype": DOCTYPE_CACHE, **nowy_wiersz_cache(kod, adresy)}).insert(
				ignore_permissions=True
			)
	except Exception:
		frappe.db.rollback(save_point=_SAVEPOINT)
		frappe.log_error(title=TYTUL_BLEDU, message="Kod %s: zapis cache\n%s" % (kod, frappe.get_traceback()))


def dane_kodu(kod: str, timeout: int = TIMEOUT_ADRESY_SEK) -> dict:
	"""Wynik lookupu (`scal_wynik`) dla kodu; niepoprawny kod to `found: False`."""
	kod = normalizuj_kod(kod)
	if not kod:
		return scal_wynik(None, None)
	wiersz = frappe.db.get_value(
		DOCTYPE_CACHE,
		{"kod": kod},
		["name", "miejscowosc", "gmina", "powiat", "wojewodztwo", "cities", "lat", "lng"],
		as_dict=True,
	)
	if wiersz_kompletny(wiersz):
		return scal_wynik(wiersz, None)
	adresy = _zapytaj_adresy(kod, timeout)
	if adresy:
		_zapisz_cache(kod, wiersz, adresy)
	return scal_wynik(wiersz, adresy)


@frappe.whitelist()
def wyszukaj(kod: str) -> dict:
	"""Lookup dla panelu leada; front woła `crm.api.kod_pocztowy.wyszukaj`.

	Dostępny dla każdego zalogowanego (dane geograficzne, bez danych klienta).
	`lat`/`lng` nie wychodzą na front."""
	wynik = dane_kodu(kod)
	wynik.pop("lat", None)
	wynik.pop("lng", None)
	return wynik
