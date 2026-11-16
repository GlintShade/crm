# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Edycja wlasnego wpisu strumienia Montaz (`Volteo Montaz Update`, zakladka
Montaz szansy Czyste Powietrze, `AktualizacjeTab.vue`) z historia zmian
(ops#364). Wzorzec `crm.api.trify`, ale tresc to zwykly tekst (Small Text, bez
wzmianek), wiec nie ma powiadomien.

Bramki: szansa i wpis musza byc odczytywalne (DocPerm plus `if_owner` dla D2D);
brak wpisu i brak uprawnien daja ten sam blad. Edytuje wylacznie autor
(takze administrator), zapis `save(ignore_permissions=True)`, historia z wierszy
`Version` (`track_changes` wlacza `ops/crm-szansa.py`). Usuwanie: bez endpointu,
`frappe.client.delete` pod DocPerm (tylko administratorzy).
"""

import frappe
from frappe import _

from crm.api.komentarze import liczby_zmian_dokumentow
from crm.volteo_komentarze import zmiany_tresci

DOCTYPE = "Volteo Montaz Update"


def _wpis(name: str) -> dict:
	wiersz = frappe.db.get_value(DOCTYPE, name, ["deal", "owner", "tekst"], as_dict=True) if name else None
	if (
		not wiersz
		or not frappe.has_permission("CRM Deal", "read", wiersz.deal)
		or not frappe.has_permission(DOCTYPE, "read", name)
	):
		frappe.throw(_("Brak uprawnień do tego wpisu."), frappe.PermissionError)
	return wiersz


@frappe.whitelist()
def liczby_zmian(deal: str) -> dict:
	"""`{nazwa wpisu: liczba zmian tresci}` wpisow Montazu szansy widocznych dla
	wolajacego."""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)
	nazwy = frappe.get_list(DOCTYPE, filters={"deal": deal}, pluck="name", limit_page_length=0)
	return liczby_zmian_dokumentow(DOCTYPE, nazwy, "tekst")


@frappe.whitelist(methods=["POST"])
def edytuj(name: str, tekst: str) -> dict:
	"""Zmienia tresc wpisu Montazu; tylko autor. Pusta tresc odrzucona,
	niezmieniona nic nie zapisuje."""
	wiersz = _wpis(name)
	if wiersz.owner != frappe.session.user:
		frappe.throw(_("Wpis może edytować tylko jego autor."), frappe.PermissionError)
	tekst = (tekst or "").strip()
	if not tekst:
		frappe.throw(_("Treść wpisu nie może być pusta."))
	if tekst == (wiersz.tekst or "").strip():
		return {"name": name, "tekst": wiersz.tekst}
	doc = frappe.get_doc(DOCTYPE, name)
	doc.tekst = tekst
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "tekst": doc.tekst}


@frappe.whitelist()
def historia(name: str) -> list[dict]:
	"""Wczesniejsze wersje tresci wpisu Montazu (`{kto, kto_nazwa, kiedy, przed,
	po}`, rosnaco po dacie); widoczne dla kazdego, kto widzi wpis."""
	_wpis(name)
	zmiany = zmiany_tresci(
		frappe.get_all(
			"Version",
			filters={"ref_doctype": DOCTYPE, "docname": name},
			fields=["owner", "creation", "data"],
			order_by="creation asc",
			limit_page_length=0,
		),
		"tekst",
	)
	if not zmiany:
		return []
	nazwy = {
		u.name: u.full_name
		for u in frappe.get_all(
			"User",
			filters={"name": ["in", list({z["kto"] for z in zmiany if z["kto"]})]},
			fields=["name", "full_name"],
		)
	}
	return [{**z, "kto_nazwa": nazwy.get(z["kto"]) or z["kto"]} for z in zmiany]
