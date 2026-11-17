# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Strażnik odpowiedzi: bez pól permlevel w zwracanym dokumencie (ops#180, ops#372).

Metody rdzenia Frappe `frappe.client.set_value`, `save`, `insert`, `submit`
zwracają `doc.as_dict()` bez `doc.apply_fieldlevel_read_permissions()`. Po
zapisie dowolnego pola handlowiec (`Volteo D2D Sales`) dostawał więc w
odpowiedzi pola permlevel 2 (np. `custom_cc` na `CRM Lead`,
`custom_koszty_json` na `CRM Deal`). Druga ścieżka tej samej luki to REST v1:
`PUT`/`POST /api/resource/<doctype>` też zwraca dokument bez filtra.

Od ops#372 luka jest zamykana trzema warstwami: (1) wrappery, (2) blokada
zapisu REST (v1 i v2) oraz wrapper `run_doc_method`/`runserverobj`, (3) filtr
na wyjściu KAŻDEJ odpowiedzi JSON (`after_request`), który zeruje pola
permlevel w każdym obiekcie z kluczem `doctype`.

Rozwiązanie:
  - cztery wrappery poniżej mają DOKŁADNIE tę samą sygnaturę co oryginał
    (adnotacje typów wymagane przez `require_type_annotated_api_methods`),
    podmieniają go przez `override_whitelisted_methods` (`crm/hooks.py`),
    delegują do rdzenia i filtrują zwrócony dokument;
  - `before_request` blokuje zapis przez REST (v1 i v2, ops#372) dla każdego,
    kto nie jest Administratorem ani System Managerem (decyzja w
    `crm.volteo_zapis_rest.czy_zapis_rest`);
  - `run_doc_method` filtruje dokumenty doklejone do `frappe.response.docs`;
  - `after_request` filtruje gotową odpowiedź JSON (fail-closed);
  - historia w `docinfo` (Version, komentarze, ślady Info) zostaje tylko dla
    administracji, bo niesie wartości pól tajnych oraz tożsamość CC.

To jest bramka bezpieczeństwa: żaden wyjątek nie jest połykany (fail-closed).
"""

import json
from typing import Any

import frappe
from frappe import _
from frappe.client import insert as _rdzen_insert
from frappe.client import save as _rdzen_save
from frappe.client import set_value as _rdzen_set_value
from frappe.client import submit as _rdzen_submit
from frappe.handler import run_doc_method as _rdzen_run_doc_method
from frappe.model.document import Document

from crm.volteo_odpowiedz_filtr import czy_filtrowac, oczysc_docinfo, odfiltruj
from crm.volteo_zapis_rest import czy_zapis_rest

ROLE_PELNEJ_HISTORII = frozenset({"System Manager", "Volteo Core Admin"})


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


def _czytelny(doctype: str, name: str) -> bool:
	"""Czy wywolujacy ma odczyt dokumentu, ktory wlasnie zapisal. Brak
	dokumentu (usuniety albo przemianowany w trakcie) traktujemy jak brak odczytu."""
	try:
		return bool(frappe.has_permission(doctype, "read", name))
	except frappe.DoesNotExistError:
		return False


def _odfiltruj(wynik: Any) -> Any:
	"""Zwraca `wynik` po `apply_fieldlevel_read_permissions`. Nie-słownik albo
	słownik bez `doctype` i `name` wraca bez zmian. Administrator i doctype bez
	pól permlevel > 0: szybka ścieżka bez zmian. Dokument, którego wywołujący
	nie może czytać (np. cudze `CRM Notification`), wraca tylko jako `doctype`
	i `name`, bez treści."""
	if not isinstance(wynik, dict) or not wynik.get("doctype") or not wynik.get("name"):
		return wynik
	if frappe.session.user == "Administrator":
		return wynik
	if not _czytelny(wynik["doctype"], wynik["name"]):
		return {"doctype": wynik["doctype"], "name": wynik["name"]}
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


@frappe.whitelist()
def run_doc_method(
	method: str,
	docs: Any = None,
	dt: Any = None,
	dn: Any = None,
	arg: Any = None,
	args: Any = None,
):
	"""Strażnik nad `frappe.handler.run_doc_method` (ops#372): rdzeń dokleja
	dokument do `frappe.response.docs` bez filtra pól permlevel. Adnotacje `Any`
	celowo, żeby walidacja typów nie zmieniła zachowania Desk. Rdzeń nie ogranicza
	metod HTTP dla `run_doc_method`, więc wrapper też nie; Guest nie ma dostępu (rdzeń
	go dopuszczał, potem i tak wymagał odczytu dokumentu)."""
	wynik = _rdzen_run_doc_method(method, docs=docs, dt=dt, dn=dn, arg=arg, args=args)
	for doc in frappe.response.get("docs") or []:
		if isinstance(doc, Document):
			doc.apply_fieldlevel_read_permissions()
	return wynik


def _tajne_pola_dla_uzytkownika(doctype: str, parenttype: str | None) -> frozenset[str] | None:
	"""Pola doctype, których bieżący użytkownik nie może czytać (permlevel bez
	dostępu do odczytu). None, gdy nic do usunięcia albo doctype nieznany."""
	try:
		meta = frappe.get_meta(doctype)
	except (frappe.DoesNotExistError, ImportError):
		frappe.clear_last_message()
		return None
	pola = [f for f in meta.fields if f.permlevel]
	if not pola:
		return None
	if meta.istable and not parenttype:
		# nie da się ustalić uprawnień rodzica: fail-closed
		return frozenset(f.fieldname for f in pola)
	dostep = set(meta.get_permlevel_access("read", parenttype=parenttype if meta.istable else None))
	return frozenset(f.fieldname for f in pola if f.permlevel not in dostep)


def after_request(response=None, request=None) -> None:
	"""Hook `after_request` (ops#372): zeruje pola permlevel w odpowiedzi JSON i
	czyści historię w `docinfo` dla kogoś bez roli System Manager i Volteo Core Admin.

	Frappe połyka wyjątki z `after_request` i wysłałby odpowiedź bez filtra, więc
	każdy błąd kończy się podmianą odpowiedzi na 500 (fail-closed)."""
	if response is None:
		return
	uzytkownik = getattr(getattr(frappe.local, "session", None), "user", None) or "Guest"
	if uzytkownik == "Administrator":
		return
	try:
		tresc = response.get_data()
		if not czy_filtrowac(response.content_type, tresc):
			return
		obiekt = json.loads(tresc)
		zmiany = odfiltruj(obiekt, _tajne_pola_dla_uzytkownika)
		if not (ROLE_PELNEJ_HISTORII & set(frappe.get_roles())):
			zmiany += oczysc_docinfo(obiekt)
		if zmiany:
			response.set_data(json.dumps(obiekt, separators=(",", ":")))
	except Exception:
		try:
			frappe.logger().error("ops#372: błąd filtra odpowiedzi", exc_info=True)
			response.set_data(json.dumps({"exc_type": "InternalError", "message": "Błąd filtra odpowiedzi."}))
			response.status_code = 500
		except Exception:
			response.set_data(b"{}")


def before_request() -> None:
	"""Hook `before_request`: zapis przez REST (v1 i v2) tylko dla Administratora i
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
