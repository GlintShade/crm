# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kalendarz spotkan na zywo (ops#331): sygnal realtime po zapisie.

Haki `doc_events` na `CRM Lead` i `Volteo Dostepnosc` (crm/hooks.py) zbieraja
daty, ktorych dotyczy zapis, w `frappe.flags` (per request) i rejestruja JEDEN callback
`after_commit` na request: masowe operacje (przydzial paczki, `ustaw_dostepnosc`
z wieloma wierszami) daja jeden sygnal, nie jeden na dokument. Po rollbacku
zebrane daty przepadaja razem z callbackiem.

Sygnal `volteo_kalendarz` to tylko `{"daty": [...]}` (bez danych leada, bez
`custom_cc`); otwarty kalendarz pobiera dane ponownie przez
`crm.api.kalendarz.spotkania`, ktory pilnuje zakresu `wszyscy`/`wlasny`.

Haki nigdy nie rzucaja: blad realtime laduje w Error Log i nie wywraca zapisu.
Decyzja "czy zmiana dotyczy kalendarza" zyje frappe-free w
`crm/volteo_kalendarz.py` (testy w `crm/test_volteo_kalendarz.py`).
"""

import frappe

from crm.volteo_kalendarz import (
	POLA_KALENDARZA_DOSTEPNOSCI,
	POLA_KALENDARZA_LEADA,
	ZDARZENIE_KALENDARZA,
	polacz_daty,
	tresc_sygnalu,
	zmiana_dostepnosci,
	zmiana_kalendarza_leada,
)

_KLUCZ_LOCAL = "volteo_kalendarz_sygnal"
_KLUCZ_IMPORTU = "volteo_kalendarz_sygnal_import"
_ODSTEP_IMPORTU_S = 5
TYTUL_BLEDU = "Kalendarz na żywo (ops#331)"


def _stan(doc, pola) -> dict | None:
	if doc is None:
		return None
	return {p: doc.get(p) for p in pola}


def _wylaczony() -> bool:
	"""Instalacja, migracja i patche: nikt nie patrzy na kalendarz."""
	flagi = frappe.flags
	return bool(flagi.in_install or flagi.in_migrate or flagi.in_patch or flagi.in_setup_wizard)


def _wyczysc() -> None:
	frappe.flags.pop(_KLUCZ_LOCAL, None)


def _wyslij() -> None:
	"""Callback `after_commit`: jeden `publish_realtime` z zebranymi datami."""
	try:
		stan = frappe.flags.pop(_KLUCZ_LOCAL, None)
		if not stan or stan.get("daty") is None:
			return
		if frappe.flags.in_import:
			# Import commituje co wiersz: najwyzej jeden sygnal na kilka sekund,
			# ostatnie zmiany dobierze polling frontu (60 s).
			if frappe.cache.get_value(_KLUCZ_IMPORTU):
				return
			frappe.cache.set_value(_KLUCZ_IMPORTU, 1, expires_in_sec=_ODSTEP_IMPORTU_S)
		frappe.publish_realtime(ZDARZENIE_KALENDARZA, tresc_sygnalu(stan["daty"]))
	except Exception:
		frappe.log_error(title=TYTUL_BLEDU, message=frappe.get_traceback())


def _zglos(daty: list[str] | None) -> None:
	"""Dopisuje daty do sygnalu requestu; pierwszy raz rejestruje callbacki."""
	if daty is None or _wylaczony():
		return
	stan = frappe.flags.get(_KLUCZ_LOCAL)
	if stan is None:
		frappe.db.after_commit.add(_wyslij)
		stan = {"daty": None}
		frappe.flags[_KLUCZ_LOCAL] = stan
		try:
			# Rollback kasuje callbacki after_commit; zebrane daty musza zniknac z nimi.
			frappe.db.after_rollback.add(_wyczysc)
		except AttributeError:
			pass
	stan["daty"] = polacz_daty(stan["daty"], daty)


def po_zapisie_leada(doc, method: str | None = None) -> None:
	"""Hak `on_update` (tez po insercie) i `on_trash` na `CRM Lead`."""
	try:
		pola = POLA_KALENDARZA_LEADA
		if method == "on_trash":
			daty = zmiana_kalendarza_leada(_stan(doc, pola), None)
		else:
			daty = zmiana_kalendarza_leada(_stan(doc.get_doc_before_save(), pola), _stan(doc, pola))
		_zglos(daty)
	except Exception:
		frappe.log_error(title=TYTUL_BLEDU, message=frappe.get_traceback())


def po_zapisie_dostepnosci(doc, method: str | None = None) -> None:
	"""Hak `on_update` (tez po insercie) i `on_trash` na `Volteo Dostepnosc`."""
	try:
		pola = POLA_KALENDARZA_DOSTEPNOSCI
		if method == "on_trash":
			daty = zmiana_dostepnosci(_stan(doc, pola), None)
		else:
			daty = zmiana_dostepnosci(_stan(doc.get_doc_before_save(), pola), _stan(doc, pola))
		_zglos(daty)
	except Exception:
		frappe.log_error(title=TYTUL_BLEDU, message=frappe.get_traceback())
