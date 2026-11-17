# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Strażnik odpowiedzi zapisu: bez pól permlevel w zwracanym dokumencie (ops#180).

Metody rdzenia Frappe `frappe.client.set_value`, `save`, `insert`, `submit`
zwracają `doc.as_dict()` bez `doc.apply_fieldlevel_read_permissions()`. Po
zapisie dowolnego pola handlowiec (`Volteo D2D Sales`) dostawał więc w
odpowiedzi pola permlevel 2 (np. `custom_cc` na `CRM Lead`,
`custom_koszty_json` na `CRM Deal`). Druga ścieżka tej samej luki to REST v1:
`PUT`/`POST /api/resource/<doctype>` też zwraca dokument bez filtra.

Rozwiązanie:
  - cztery wrappery poniżej mają DOKŁADNIE tę samą sygnaturę co oryginał
    (adnotacje typów wymagane przez `require_type_annotated_api_methods`),
    podmieniają go przez `override_whitelisted_methods` (`crm/hooks.py`),
    delegują do rdzenia i filtrują zwrócony dokument;
  - `before_request` blokuje zapis przez REST v1 dla każdego, kto nie jest
    Administratorem ani System Managerem (REST v2 filtruje poprawnie i nie
    jest blokowany; decyzja w `crm.volteo_zapis_rest.czy_zapis_rest`).

To jest bramka bezpieczeństwa: żaden wyjątek nie jest połykany (fail-closed).
"""

from typing import Any

import frappe
from frappe import _
from frappe.client import insert as _rdzen_insert
from frappe.client import save as _rdzen_save
from frappe.client import set_value as _rdzen_set_value
from frappe.client import submit as _rdzen_submit

from crm.volteo_zapis_rest import czy_zapis_rest


def _ma_pola_permlevel(doctype: str) -> bool:
	"""True, gdy doctype albo którakolwiek jego tabela potomna ma pole z
	permlevel > 0 (tylko wtedy filtr w ogóle może coś usunąć)."""
	meta = frappe.get_meta(doctype)
	if any(f.permlevel for f in meta.fields):
		return True
	for tabela in meta.get_table_fields():
		if any(f.permlevel for f in frappe.get_meta(tabela.options).fields):
			return True
	return False


def _odfiltruj(wynik: Any) -> Any:
	"""Zwraca `wynik` po `apply_fieldlevel_read_permissions`. Nie-słownik albo
	słownik bez `doctype` i `name` wraca bez zmian. Administrator i doctype bez
	pól permlevel > 0: szybka ścieżka bez zmian."""
	if not isinstance(wynik, dict) or not wynik.get("doctype") or not wynik.get("name"):
		return wynik
	if frappe.session.user == "Administrator":
		return wynik
	if not _ma_pola_permlevel(wynik["doctype"]):
		return wynik
	doc = frappe.get_doc(wynik["doctype"], wynik["name"])
	doc.apply_fieldlevel_read_permissions()
	return doc.as_dict()


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(
	doctype: str,
	name: str | int,
	fieldname: str | dict[str, Any],
	value: Any | None = None,
):
	"""Strażnik nad `frappe.client.set_value` (ops#180)."""
	return _odfiltruj(_rdzen_set_value(doctype, name, fieldname, value=value))


@frappe.whitelist(methods=["POST", "PUT"])
def insert(doc: str | dict[str, Any] | None = None):
	"""Strażnik nad `frappe.client.insert` (ops#180)."""
	return _odfiltruj(_rdzen_insert(doc=doc))


@frappe.whitelist(methods=["POST", "PUT"])
def save(doc: str | dict[str, Any]):
	"""Strażnik nad `frappe.client.save` (ops#180)."""
	return _odfiltruj(_rdzen_save(doc))


@frappe.whitelist(methods=["POST", "PUT"])
def submit(doc: str | dict[str, Any]):
	"""Strażnik nad `frappe.client.submit` (ops#180)."""
	return _odfiltruj(_rdzen_submit(doc))


def before_request() -> None:
	"""Hook `before_request`: zapis przez REST v1 tylko dla Administratora i
	System Managera. Reszta używa `/api/method`, gdzie działają wrappery wyżej."""
	request = getattr(frappe.local, "request", None)
	if request is None:
		return
	if not czy_zapis_rest(getattr(request, "method", ""), getattr(request, "path", "")):
		return
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
		return
	frappe.throw(
		_("Zapis przez REST jest niedostępny. Użyj /api/method."),
		frappe.PermissionError,
	)
