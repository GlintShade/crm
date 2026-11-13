# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Zmiana doradcy szansy (`CRM Deal.deal_owner`) z naglowka szansy (ops#336).

`deal_owner` ma permlevel 1, wiec zapis przez `document.save` po cichu cofa
wartosc dla Backoffice. Zmiana idzie tutaj, z wlasna bramka rol. Zapis przez
`doc.save(ignore_permissions=True)`: `CRMDeal.validate` robi share + assign dla
nowego doradcy, `on_update` zabiera poprzedniemu ToDo i DocShare, a `Version`
daje slad w Aktywnosci. Cena, koszty i rozliczenia nie sa ruszane.
"""

import frappe
from frappe import _

from crm.api.limit_zadan import rate_limit
from crm.volteo_szansa_doradca import (
	ROLA_DORADCY,
	czy_dozwolony_doradca,
	czy_moze_zmienic_doradce,
)

BLAD_UPRAWNIEN = "Nie masz uprawnień do zmiany doradcy szansy."


def _wymagaj_uprawnien() -> None:
	uzytkownik = frappe.session.user
	if not czy_moze_zmienic_doradce(uzytkownik, frappe.get_roles(uzytkownik)):
		frappe.throw(_(BLAD_UPRAWNIEN), frappe.PermissionError)


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def doradcy() -> list[dict]:
	"""Wlaczone konta z rola `Volteo D2D Sales`, posortowane po `full_name`."""
	_wymagaj_uprawnien()
	konta = frappe.get_all(
		"User",
		filters={"enabled": 1},
		fields=["name", "full_name"],
	)
	z_rola = {
		r.parent
		for r in frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "role": ROLA_DORADCY},
			fields=["parent"],
		)
	}
	lista = [
		{"user": k.name, "full_name": k.full_name or k.name}
		for k in konta
		if k.name in z_rola
	]
	return sorted(lista, key=lambda w: (w["full_name"] or "").lower())


@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def zmien_doradce(deal: str, doradca: str) -> dict:
	"""Ustawia `deal_owner` szansy `deal` na `doradca`."""
	_wymagaj_uprawnien()

	deal = (deal or "").strip()
	doradca = (doradca or "").strip()
	if not deal:
		frappe.throw(_("Szansa jest wymagana."))
	if not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Szansa {0} nie istnieje.").format(deal))

	doc = frappe.get_doc("CRM Deal", deal)
	if not frappe.has_permission("CRM Deal", "read", doc=doc):
		frappe.throw(_(BLAD_UPRAWNIEN), frappe.PermissionError)

	if not doradca:
		frappe.throw(_("Doradca jest wymagany."))
	if not frappe.db.exists("User", doradca):
		frappe.throw(_("Użytkownik {0} nie istnieje.").format(doradca))
	wlaczony = bool(frappe.db.get_value("User", doradca, "enabled"))
	if not czy_dozwolony_doradca(wlaczony, frappe.get_roles(doradca)):
		frappe.throw(
			_("Użytkownik {0} nie może być doradcą szansy (wymagane włączone konto z rolą {1}).").format(
				doradca, ROLA_DORADCY
			)
		)

	if doc.deal_owner == doradca:
		return {"deal": deal, "doradca": doradca, "zmieniono": False}

	doc.deal_owner = doradca
	doc.save(ignore_permissions=True)
	return {"deal": deal, "doradca": doradca, "zmieniono": True}
