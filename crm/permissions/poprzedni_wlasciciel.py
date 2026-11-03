# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cienki adapter frappe dla `crm.volteo_widocznosc_wlasciciela` (b82).

Wolany z `CRMLead.on_update` i `CRMDeal.on_update`, czyli dla KAZDEJ sciezki,
ktora zmienia wlasciciela przez `doc.save()`: panel boczny (frappe.client),
`crm.api.volteo_leady.przydziel`, `crm.api.volteo_leady.przekaz_handlowcowi`,
`crm.api.kalendarz.ustaw_termin`, AssignTo.vue. Sciezki przez
`frappe.db.set_value` kontrolera nie odpalaja (patrz opis PR).
"""

import json

import frappe

from crm.volteo_widocznosc_wlasciciela import plan_odebrania_dostepu, przypisani_po_zmianie


def odbierz_dostep_poprzedniemu_wlascicielowi(doc, owner_field: str, chronieni=()) -> dict:
	"""Po zmianie `doc.<owner_field>` anuluje ToDo i usuwa DocShare poprzedniego
	wlasciciela. Wiersze nowego wlasciciela i `chronieni` zostaja.

	Zapis ToDo idzie przez `frappe.db.set_value` (bez `ToDo.save`), celowo:
	`ToDo.validate` dopisuje do leada komentarz "Przypisanie ... usuniete przez
	<pelne imie wolajacego>", co przy przekazaniu przez CC ujawnialoby imie CC
	handlowcowi. `_assign` jest przeliczane recznie ta sama regula co
	`ToDo.update_in_reference`."""
	if doc.is_new() or not doc.has_value_changed(owner_field):
		return {"todo": [], "udostepnienia": []}

	przed = doc.get_doc_before_save()
	stary = przed.get(owner_field) if przed else None
	nowy = doc.get(owner_field)
	if not stary:
		return {"todo": [], "udostepnienia": []}

	todos = frappe.get_all(
		"ToDo",
		filters={"reference_type": doc.doctype, "reference_name": doc.name},
		fields=["name", "allocated_to", "status"],
		order_by="creation asc",
	)
	udostepnienia = frappe.get_all(
		"DocShare",
		filters={"share_doctype": doc.doctype, "share_name": doc.name},
		fields=["name", "user"],
	)
	plan = plan_odebrania_dostepu(stary, nowy, todos, udostepnienia, chronieni)

	for nazwa in plan["todo"]:
		frappe.db.set_value("ToDo", nazwa, "status", "Cancelled")
	if plan["todo"]:
		przypisani = przypisani_po_zmianie(todos, plan["todo"])
		frappe.db.set_value(doc.doctype, doc.name, "_assign", json.dumps(przypisani), update_modified=False)

	for nazwa in plan["udostepnienia"]:
		frappe.delete_doc(
			"DocShare",
			nazwa,
			ignore_permissions=True,
			flags={"ignore_share_permission": True},
		)

	return plan
