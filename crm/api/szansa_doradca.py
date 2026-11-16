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
	czy_moze_zmienic_doradce,
	czy_moze_zmienic_doradce_zbiorczo,
	normalizuj_partie,
)

BLAD_UPRAWNIEN = "Nie masz uprawnień do zmiany doradcy szansy."


def _wymagaj_uprawnien() -> None:
	uzytkownik = frappe.session.user
	if not czy_moze_zmienic_doradce(uzytkownik, frappe.get_roles(uzytkownik)):
		frappe.throw(_(BLAD_UPRAWNIEN), frappe.PermissionError)


def _konta_doradcow() -> list[dict]:
	"""Wlaczone konta z wierszem `Has Role` roli `Volteo D2D Sales`, po `full_name`.

	Jedno zrodlo dla listy i walidacji. `Administrator` i `Guest` pomijane jawnie
	(`frappe.get_roles` zwraca dla Administratora wszystkie role)."""
	konta = frappe.get_all(
		"User",
		filters={"enabled": 1, "name": ("not in", ["Administrator", "Guest"])},
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
@rate_limit(limit=60, seconds=60)
def doradcy() -> list[dict]:
	"""Konta, ktore moga byc doradca szansy."""
	_wymagaj_uprawnien()
	return _konta_doradcow()


def _wymagaj_doradcy(doradca: str) -> str:
	"""Waliduje wskazanego doradce (wspolne dla pojedynczej i zbiorczej zmiany)."""
	doradca = (doradca or "").strip()
	if not doradca:
		frappe.throw(_("Doradca jest wymagany."))
	if doradca not in {k["user"] for k in _konta_doradcow()}:
		frappe.throw(
			_("Użytkownik {0} nie może być doradcą szansy (wymagane włączone konto handlowca).").format(
				doradca
			)
		)
	return doradca


def _ustaw_doradce(doc, doradca: str) -> bool:
	"""Wspolny zapis: ustawia `deal_owner` przez `doc.save`, zwraca czy zmieniono."""
	if doc.deal_owner == doradca:
		return False
	doc.deal_owner = doradca
	doc.save(ignore_permissions=True)
	return True


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

	doradca = _wymagaj_doradcy(doradca)
	zmieniono = _ustaw_doradce(doc, doradca)
	return {"deal": deal, "doradca": doradca, "zmieniono": zmieniono}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def zmien_doradce_zbiorczo(szanse: list, doradca: str) -> dict:
	"""Zbiorczo ustawia `deal_owner` zaznaczonych szans (tylko administratorzy).

	Kazda szansa ma wlasny savepoint: blad jednej nie przerywa reszty. Wynik:
	`{zmieniono: int, pominieto: [{deal, powod}]}`."""
	uzytkownik = frappe.session.user
	if not czy_moze_zmienic_doradce_zbiorczo(uzytkownik, frappe.get_roles(uzytkownik)):
		frappe.throw(_(BLAD_UPRAWNIEN), frappe.PermissionError)

	if isinstance(szanse, str):
		szanse = frappe.parse_json(szanse)
	try:
		nazwy = normalizuj_partie(szanse)
	except ValueError as e:
		frappe.throw(_(str(e)))
	doradca = _wymagaj_doradcy(doradca)

	zmieniono = 0
	pominieto: list[dict] = []
	bledy: list[tuple[str, str]] = []
	for i, deal in enumerate(nazwy):
		sp = f"doradca_zbiorczo_{i}"
		frappe.db.savepoint(sp)
		try:
			if not frappe.db.exists("CRM Deal", deal):
				pominieto.append({"deal": deal, "powod": _("Szansa nie istnieje.")})
				continue
			doc = frappe.get_doc("CRM Deal", deal)
			if not frappe.has_permission("CRM Deal", "read", doc=doc):
				pominieto.append({"deal": deal, "powod": _("Brak dostępu do szansy.")})
				continue
			if _ustaw_doradce(doc, doradca):
				zmieniono += 1
			else:
				pominieto.append({"deal": deal, "powod": _("Ten doradca jest już przypisany.")})
		except Exception as e:
			frappe.db.rollback(save_point=sp)
			bledy.append((deal, frappe.get_traceback()))
			pominieto.append({"deal": deal, "powod": _("Błąd zapisu: {0}").format(str(e)[:200])})

	for deal, slad in bledy:
		frappe.log_error(slad, f"Zbiorcza zmiana doradcy: {deal}")
	return {"zmieniono": zmieniono, "pominieto": pominieto}
