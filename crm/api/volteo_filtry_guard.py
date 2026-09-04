# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Strażnik filtrów permlevel na whitelisted endpointach RDZENIA Frappe (ops#80).

Druga warstwa luki z ops#79. Tamten issue zamknął dziurę we froncie forka
(`crm.api.doc.get_data` i pokrewne) — ale handlowiec (`Volteo D2D Sales`)
może ominąć listę forka całkowicie i wywołać wprost z przeglądarki
whitelisted endpointy rdzenia Frappe, które same przyjmują `filters` bez
sprawdzenia permlevel:

  - ``frappe.client.get_list`` / ``get_count`` / ``get_value``
  - ``frappe.desk.reportview.get`` / ``get_count`` / ``export_query``
  - ``frappe.desk.search.search_link``

Rdzeniowy ``frappe.desk.reportview.validate_args`` → ``validate_filters``
sprawdza tylko, czy pole ISTNIEJE w doctypie — nie czy wolno je odczytać.
Bez tej bramki filtr typu ``{"custom_koszty_zysk_plan": [">", 0]}`` na
``CRM Deal`` (pole permlevel 2) przechodzi przez rdzeń bez problemu.

Każda funkcja poniżej ma DOKŁADNIE tę samą sygnaturę (nazwy, kolejność,
adnotacje typów — wymagane przez ``require_type_annotated_api_methods``)
co oryginał, którego podmienia przez ``override_whitelisted_methods``
(``crm/hooks.py``). Sprawdza ``filters``/``or_filters`` przez
``crm.api.doc._sprawdz_filtry`` (ops#79 — generyczne, dowolny doctype,
dowolny użytkownik; Administrator/System Manager mają wszystko dozwolone
przez ``get_permitted_fields``, więc admin nic nie traci), a potem
DELEGUJE do oryginału bez zmiany zwracanej wartości.

``frappe.desk.reportview.get`` / ``get_count`` / ``export_query`` nie mają
żadnych parametrów Pythona — rdzeń czyta je z ``frappe.local.form_dict``
(patrz ``get_form_params()``), gdzie ``filters``/``or_filters`` bywają
zserializowanym JSON-em (string) — trzeba je sparsować identycznie jak to
robi rdzeń, zanim sprawdzi się klucze.

Doctype spoza tabeli (literówka, nieistniejący): sprawdzenie samo w sobie
NIE ma prawa zamaskować naturalnego błędu rdzenia (``frappe.DoesNotExistError``
przy ``frappe.get_meta`` wewnątrz ``get_permitted_fields``) własnym błędem —
``_sprawdz_filtry_bezpiecznie`` łapie WYŁĄCZNIE ten jeden wyjątek i w takim
wypadku po prostu NIE sprawdza filtrów, oddając głos oryginalnej metodzie
rdzenia, do której wrapper i tak zaraz potem deleguje. Żaden INNY wyjątek
(w tym ``frappe.PermissionError`` — prawidłowy wynik sprawdzenia, który musi
przejść dalej — ale też błąd we własnej logice strażnika czy przejściowy
błąd bazy) nie jest połykany: to jest bramka bezpieczeństwa, więc milczące
"fail-open" na dowolnym nieprzewidzianym wyjątku byłoby luką samo w sobie.
"""

from typing import Any

import frappe
from frappe.client import get_count as _rdzen_get_count
from frappe.client import get_list as _rdzen_get_list
from frappe.client import get_value as _rdzen_get_value
from frappe.desk import reportview as _rdzen_reportview
from frappe.desk.search import search_link as _rdzen_search_link

from crm.api.doc import _sprawdz_filtry

# _sprawdz_filtry jest oznaczona jako prywatna konwencja jednego podkreslenia
# (nie jest API poza modulem doc.py), ale ops#79/#80 celowo dzieli ja miedzy
# oba miejsca zamiast duplikowac logike sprawdzania filtrow — patrz docstring
# wyzej i brief ops#80.


def _sparsowane_filtry(wartosc: object) -> dict | list | tuple | None:
	"""Sprowadza `filters`/`or_filters` do postaci, ktora rozumie
	`niedozwolone_klucze_filtrow` (dict / lista krotek), albo `None`.

	`wartosc` moze byc juz sparsowanym dict-em/lista (typowe przy wywolaniu
	z Pythona) albo JSON-stringiem (typowe przy wywolaniu z formularza HTTP
	— tak jak robi to rdzen w `reportview.parse_json`/`get_safe_filters`).
	Pusta wartosc albo string, ktory nie jest poprawnym JSON-em (np. sama
	nazwa dokumentu przekazana do `get_value`) daje `None` — sprawdzenie
	jest wtedy pomijane, bo taki string i tak nie odwoluje sie do zadnego
	pola wprost (dopasowanie po `name`, ktore jest zawsze dozwolone)."""
	if not wartosc:
		return None
	if isinstance(wartosc, str):
		try:
			wartosc = frappe.parse_json(wartosc)
		except (TypeError, ValueError):
			return None
	if isinstance(wartosc, (dict, list, tuple)):
		return wartosc
	return None


def _sprawdz_filtry_bezpiecznie(doctype: str, filters: object) -> None:
	"""Otacza `crm.api.doc._sprawdz_filtry` (ops#79) — liczy zbior dozwolonych
	pol RAZ i rzuca `frappe.PermissionError`, jesli `filters` odwoluje sie do
	pola spoza niego. Przechwytuje WYLACZNIE `frappe.DoesNotExistError`
	(niepoprawny/nieznany doctype, np. literowka — rzucany przez
	`frappe.get_meta` wewnatrz `get_permitted_fields`): w tym jednym wypadku
	sprawdzenie jest pomijane, zeby zaraz potem oryginalna metoda rdzenia, do
	ktorej wrapper deleguje, sama zglosila swoj naturalny blad zamiast go
	zamaskowac. Kazdy INNY wyjatek (w tym `frappe.PermissionError` —
	prawidlowy wynik sprawdzenia filtrow — ale takze blad w samej logice
	sprawdzania, nieoczekiwany ksztalt filtra czy przejsciowy blad bazy)
	PROPAGUJE dalej bez zmian: to jest straznik bezpieczenstwa, wiec
	milczace `fail-open` na dowolnym nieprzewidzianym wyjatku byloby luka
	samo w sobie."""
	try:
		_sprawdz_filtry(doctype, filters)
	except frappe.DoesNotExistError:
		return


def _waliduj(doctype: str, filters: object = None, or_filters: object = None) -> None:
	"""Sprawdza `filters` i `or_filters` przekazane jako argumenty Pythona
	(endpointy `frappe.client.*` i `search_link`)."""
	parsed_filters = _sparsowane_filtry(filters)
	if parsed_filters:
		_sprawdz_filtry_bezpiecznie(doctype, parsed_filters)
	parsed_or_filters = _sparsowane_filtry(or_filters)
	if parsed_or_filters:
		_sprawdz_filtry_bezpiecznie(doctype, parsed_or_filters)


def _waliduj_form_dict() -> None:
	"""Sprawdza `filters`/`or_filters` czytane przez rdzen wprost z
	`frappe.local.form_dict` (endpointy `frappe.desk.reportview.*`, ktore
	nie maja zadnych parametrow Pythona — patrz `get_form_params()`)."""
	doctype = frappe.local.form_dict.get("doctype")
	if not doctype:
		return
	_waliduj(
		doctype,
		frappe.local.form_dict.get("filters"),
		frappe.local.form_dict.get("or_filters"),
	)


@frappe.whitelist()
def get_list(
	doctype: str,
	fields: str | list[str | dict[str, Any]] | None = None,
	filters: str | list | dict[str, Any] | None = None,
	group_by: str | list[str] | None = None,
	order_by: str | list[str] | None = None,
	limit_start: int | str | None = None,
	limit_page_length: int | str = 20,
	parent: str | None = None,
	debug: bool | int = False,
	as_dict: bool | int = True,
	or_filters: str | list[list] | dict[str, Any] | None = None,
	expand: str | list[str] | None = None,
):
	"""Strażnik nad `frappe.client.get_list` (ops#80)."""
	_waliduj(doctype, filters, or_filters)
	return _rdzen_get_list(
		doctype,
		fields=fields,
		filters=filters,
		group_by=group_by,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		parent=parent,
		debug=debug,
		as_dict=as_dict,
		or_filters=or_filters,
		expand=expand,
	)


@frappe.whitelist()
def get_count(
	doctype: str,
	filters: str | list | dict[str, Any] | None = None,
	debug: int | bool = False,
	cache: int | bool = False,
):
	"""Strażnik nad `frappe.client.get_count` (ops#80)."""
	_waliduj(doctype, filters)
	return _rdzen_get_count(doctype, filters=filters, debug=debug, cache=cache)


@frappe.whitelist()
def get_value(
	doctype: str,
	fieldname: str | list[str] | dict[str, Any],
	filters: str | list | dict[str, Any] | None = None,
	as_dict: int | bool = True,
	debug: int | bool = False,
	parent: str | None = None,
):
	"""Strażnik nad `frappe.client.get_value` (ops#80). `filters` bywa samą
	nazwą dokumentu (string, nie-JSON) — wtedy `_sparsowane_filtry` zwraca
	`None` i sprawdzenie jest pomijane, tak jak w rdzeniu (filtr po `name`
	jest zawsze dozwolony)."""
	_waliduj(doctype, filters)
	return _rdzen_get_value(doctype, fieldname, filters=filters, as_dict=as_dict, debug=debug, parent=parent)


@frappe.whitelist()
@frappe.read_only()
def get():
	"""Strażnik nad `frappe.desk.reportview.get` (ops#80). Brak parametrów
	Pythona — rdzeń czyta `doctype`/`filters`/`or_filters` z
	`frappe.local.form_dict`."""
	_waliduj_form_dict()
	return _rdzen_reportview.get()


@frappe.whitelist()
@frappe.read_only()
def reportview_get_count() -> int:
	"""Strażnik nad `frappe.desk.reportview.get_count` (ops#80). Jak wyżej —
	brak parametrów Pythona, dane z `frappe.local.form_dict`. Nazwa inna niż
	`get_count` powyżej (ta strzeże `frappe.client.get_count`), bo obie
	funkcje żyją w tym samym module — dwie definicje `def get_count` na tym
	samym poziomie modułu przesłoniłyby się nawzajem."""
	_waliduj_form_dict()
	return _rdzen_reportview.get_count()


@frappe.whitelist()
@frappe.read_only()
def export_query():
	"""Strażnik nad `frappe.desk.reportview.export_query` (ops#80). Eksport
	listy szans/klientów do CSV — jak wyżej, dane z `frappe.local.form_dict`."""
	_waliduj_form_dict()
	return _rdzen_reportview.export_query()


@frappe.whitelist()
def search_link(
	doctype: str,
	txt: str,
	query: str | None = None,
	filters: str | dict | list | None = None,
	page_length: int = 10,
	searchfield: str | None = None,
	reference_doctype: str | None = None,
	ignore_user_permissions: bool = False,
):
	"""Strażnik nad `frappe.desk.search.search_link` (ops#80) — Link-dropdowny
	(np. `userScope` w `Link.vue`) i wyszukiwarka globalna wołają ten endpoint
	wprost z przeglądarki."""
	_waliduj(doctype, filters)
	return _rdzen_search_link(
		doctype,
		txt,
		query=query,
		filters=filters,
		page_length=page_length,
		searchfield=searchfield,
		reference_doctype=reference_doctype,
		ignore_user_permissions=ignore_user_permissions,
	)
