# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kalendarz spotkan handlowcow (ops#318).

Spotkanie to `CRM Lead` z `custom_termin_spotkania` i `lead_owner`; nic nowego
w schemacie. Tablica "wszyscy" (System Manager, Volteo Core Admin, Volteo
Backend, Volteo Call Center) pokazuje spotkania wszystkich aktywnych handlowcow
D2D, handlowiec widzi tylko wlasne. Logika zakresu i dat zyje w frappe-free
`crm/volteo_kalendarz.py`; ten plik to cienki adapter.

Frontend wola te metody PELNA sciezka kropkowana `crm.api.kalendarz.<metoda>`.
"""

import frappe
from frappe import _

from crm.api.volteo_leady import _aktywni_d2d_reprezentanci
from crm.volteo_kalendarz import (
	ZAKRES_WLASNY,
	ZAKRES_WSZYSCY,
	granice_czasu,
	normalizuj_handlowcow,
	normalizuj_termin,
	pogrupuj_spotkania,
	przetnij_handlowcow,
	waliduj_zakres_dat,
	zakres_kalendarza,
)

# Minimalna projekcja: nigdy `custom_cc` ani pola permlevel 2/3.
POLA_SPOTKANIA = [
	"name",
	"lead_name",
	"custom_termin_spotkania",
	"lead_owner",
	"custom_install_city",
	"status",
	"mobile_no",
]


def _zakres_wolajacego() -> str:
	zakres = zakres_kalendarza(frappe.session.user, frappe.get_roles())
	if zakres is None:
		frappe.throw(_("Brak uprawnień."), frappe.PermissionError)
	return zakres


def _spotkanie(wiersz) -> dict:
	return {
		"name": wiersz.name,
		"lead_name": wiersz.lead_name,
		"termin": str(wiersz.custom_termin_spotkania) if wiersz.custom_termin_spotkania else None,
		"lead_owner": wiersz.lead_owner,
		"miasto": wiersz.custom_install_city,
		"status": wiersz.status,
		"telefon": wiersz.mobile_no,
	}


@frappe.whitelist()
def spotkania(od: str, do: str, handlowcy: str | list | None = None) -> dict:
	"""Spotkania handlowcow w zakresie dat `od`..`do` (RRRR-MM-DD, max 62 dni).

	Zwraca `{"zakres", "handlowcy": [{user, full_name}], "spotkania": {user: [...]}}`.
	Dla zakresu "wlasny" parametr `handlowcy` jest ignorowany.
	"""
	zakres = _zakres_wolajacego()
	try:
		waliduj_zakres_dat(od, do)
		poczatek, koniec = granice_czasu(od, do)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

	if zakres == ZAKRES_WLASNY:
		user = frappe.session.user
		handlowcy_wiersze = [
			{"user": user, "full_name": frappe.db.get_value("User", user, "full_name") or user}
		]
	else:
		wszyscy = [{"user": r["name"], "full_name": r["full_name"]} for r in _aktywni_d2d_reprezentanci()]
		wybrani = przetnij_handlowcow(normalizuj_handlowcow(handlowcy), [h["user"] for h in wszyscy])
		handlowcy_wiersze = [h for h in wszyscy if h["user"] in wybrani]

	maile = [h["user"] for h in handlowcy_wiersze]
	wiersze = []
	if maile:
		# get_all celowo: CC widzi normalnie tylko leady `custom_cc == user`, a
		# tablica ma pokazac spotkania wszystkich handlowcow. Projekcja minimalna.
		wiersze = frappe.get_all(
			"CRM Lead",
			filters={
				"lead_owner": ["in", maile],
				"custom_termin_spotkania": ["between", [poczatek, koniec]],
				"converted": 0,
			},
			fields=POLA_SPOTKANIA,
			order_by="custom_termin_spotkania asc",
		)
	pogrupowane = pogrupuj_spotkania(
		[
			{"lead_owner": w.lead_owner, "custom_termin_spotkania": w.custom_termin_spotkania, "wiersz": w}
			for w in wiersze
		],
		maile,
	)
	return {
		"zakres": zakres,
		"handlowcy": handlowcy_wiersze,
		"spotkania": {user: [_spotkanie(w["wiersz"]) for w in lista] for user, lista in pogrupowane.items()},
	}


@frappe.whitelist()
def ustaw_termin(lead: str, termin: str | None = None, handlowiec: str | None = None) -> dict:
	"""Ustawia (albo czyści, gdy `termin` pusty) termin spotkania na leadzie.

	`handlowiec` (tylko zakres "wszyscy") zmienia `lead_owner` na wskazanego
	aktywnego handlowca D2D. Zapis przez `doc.save()` BEZ `ignore_permissions`:
	brak prawa zapisu = PermissionError od Frappe, a `CRMLead.on_update` wysyla
	mail o terminie (ops#182).
	"""
	zakres = _zakres_wolajacego()
	try:
		termin_norm = normalizuj_termin(termin)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

	try:
		doc = frappe.get_doc("CRM Lead", lead)
	except frappe.DoesNotExistError:
		frappe.throw(_("Nie znaleziono leada."), frappe.DoesNotExistError)

	if zakres == ZAKRES_WLASNY and doc.lead_owner != frappe.session.user:
		frappe.throw(_("Możesz ustawić termin tylko na własnym leadzie."), frappe.PermissionError)

	if zakres == ZAKRES_WSZYSCY and handlowiec and handlowiec != doc.lead_owner:
		dozwoleni = {r["name"] for r in _aktywni_d2d_reprezentanci()}
		if handlowiec not in dozwoleni:
			frappe.throw(_("Wskazany handlowiec nie jest aktywnym handlowcem z dostępem do modułu Leady."))
		doc.lead_owner = handlowiec

	doc.custom_termin_spotkania = termin_norm
	doc.save()
	return {
		"lead": doc.name,
		"termin": str(doc.custom_termin_spotkania) if doc.custom_termin_spotkania else None,
		"lead_owner": doc.lead_owner,
	}
