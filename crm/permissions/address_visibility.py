"""
Widocznosc dokumentu Address (ops#376).

Adres jest widoczny dla nieuprzywilejowanego uzytkownika na cztery sposoby:
wskazany przez organizacje (`CRM Organization.address`, nie zawezane), powiazany z widocznym klientem/szansa/leadem (pole `Contact.address` lub wiersz
Dynamic Link), powiazany z typem, ktory nie jest dla niego zawezony, albo jest
jego wlasny i jeszcze z niczym niepowiazany. Ostatnia galez jest potrzebna, bo
w UI nowy adres powstaje PRZED zapisem kontaktu (`Contact.vue::showAddressModal`).

Hook zapytan dziala w AND z hookiem rdzenia Frappe. Hook has_permission
zwraca tylko False albo None, nigdy True (zeby nie obejsc innych regul).
Logika SQL w `crm/volteo_widocznosc_adresu.py` (bez frappe).
"""

import frappe

from crm.permissions.contact_visibility import get_contact_permission_query_conditions
from crm.permissions.org_hierarchy import (
	BYPASS_ROLES,
	get_deal_permission_query_conditions,
	get_lead_permission_query_conditions,
)
from crm.volteo_widocznosc_adresu import PTYPY_BEZ_OGRANICZEN, warunek_adresu


def _czy_bez_ograniczen(user: str) -> bool:
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & BYPASS_ROLES)


def _warunki_typow(user: str) -> dict[str, str]:
	warunki = {
		"Contact": get_contact_permission_query_conditions(user),
		"CRM Deal": get_deal_permission_query_conditions(user),
		"CRM Lead": get_lead_permission_query_conditions(user),
	}
	for typ, w in warunki.items():
		if not isinstance(w, str):
			raise TypeError(f"Warunek widocznosci {typ} nie jest tekstem.")
	return {typ: w for typ, w in warunki.items() if w}


def _warunek(user: str) -> str:
	if _czy_bez_ograniczen(user):
		return ""
	warunki = _warunki_typow(user)
	if not warunki:
		return ""
	return warunek_adresu(user, warunki)


def get_address_permission_query_conditions(user=None, doctype=None):
	if not user:
		user = frappe.session.user
	return _warunek(user)


def has_address_permission(doc, ptype="read", user=None, debug=False):
	if not user:
		user = frappe.session.user
	name = doc.get("name") if isinstance(doc, dict) else getattr(doc, "name", None)
	if ptype in PTYPY_BEZ_OGRANICZEN or not name:
		return None
	warunek = _warunek(user)
	if not warunek:
		return None
	if "%" in warunek:
		frappe.log_error(
			title="address_visibility: procent w warunku",
			message="Fail-closed: wygenerowany warunek zawiera znak procenta.",
		)
		return False
	wiersz = frappe.db.sql(
		"SELECT 1 FROM `tabAddress` WHERE `tabAddress`.`name` = %s AND " + warunek + " LIMIT 1",
		(name,),
	)
	return None if wiersz else False
