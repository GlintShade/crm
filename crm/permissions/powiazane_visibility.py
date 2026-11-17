# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Widocznosc listy `Comment` (ops#374).

Rdzen Frappe zawęża liste Comment tylko do DOCTYPE'ow, ktore uzytkownik moze
czytac, nie do konkretnych dokumentow, wiec handlowiec widzial komentarze do
cudzych szans, audytow i leadow oraz sladu wewnetrzne. Pojedynczy odczyt jest
juz poprawnie delegowany do dokumentu odniesienia, brakowalo listy.

Haki `permission_query_conditions` jednego doctype'u sa laczone przez AND, wiec
nasz warunek tylko zaweza. Hak `has_permission` zwraca wylacznie `False` albo
`None` (nigdy `True`): nasze haki biegna pierwsze (odwrocona kolejnosc), a
`True` zablokowalby kontrole rdzenia na dokumencie odniesienia.
Warunki SQL nie zawieraja znaku procenta (db_query formatuje je przez `%`).
"""

import frappe

from crm.volteo_aktywnosc import (
	ROLA_D2D,
	ZNACZNIK_CC,
	ZNACZNIK_D2D_UKRYTY,
	ZNACZNIKI_ADMIN,
)
from crm.volteo_widocznosc_powiazana import (
	literal_sql,
	polacz_haki,
	warunek_bez_znacznikow,
	warunek_powiazania,
)

ROLA_CC = "Volteo Call Center"


def _cache(nazwa: str) -> dict:
	c = getattr(frappe.local, nazwa, None)
	if c is None:
		c = {}
		setattr(frappe.local, nazwa, c)
	return c


def _haki_typu(doctype: str) -> list[str]:
	haki = frappe.get_hooks("permission_query_conditions", {}) or {}
	metody = haki.get(doctype, []) or []
	if isinstance(metody, str):
		metody = [metody]
	return list(metody)


def warunek_hakow(doctype: str, user: str) -> str:
	"""Polaczone (AND) warunki hakow widocznosci `doctype` dla `user`."""
	cache = _cache("volteo_warunki_hakow")
	klucz = (doctype, user)
	if klucz in cache:
		return cache[klucz]
	czesci = []
	for metoda in _haki_typu(doctype):
		wynik = frappe.call(frappe.get_attr(metoda), user, doctype=doctype)
		if wynik is None:
			continue
		assert isinstance(wynik, str), f"hak {metoda} zwrocil nie-napis"
		czesci.append(wynik)
	cache[klucz] = polacz_haki(czesci)
	return cache[klucz]


def typy_z_hakami(wlasny_doctype: str) -> list[str]:
	"""Doctype'y z hakami widocznosci (bez `*` i bez `wlasny_doctype`), istniejace."""
	cache = _cache("volteo_typy_z_hakami")
	if wlasny_doctype in cache:
		return cache[wlasny_doctype]
	haki = frappe.get_hooks("permission_query_conditions", {}) or {}
	wynik = [
		k for k in haki if k not in ("*", wlasny_doctype) and frappe.db.exists("DocType", k)
	]
	cache[wlasny_doctype] = wynik
	return wynik


def warunki_typow(tabela_doctype: str, pole_typu: str, user: str) -> dict[str, str]:
	"""{typ: warunek} dla typow z hakami faktycznie obecnych w tabeli."""
	obecne = {
		x
		for x in (frappe.get_all(tabela_doctype, pluck=pole_typu, distinct=True, ignore_permissions=True) or [])
		if x
	}
	wynik = {}
	for typ in typy_z_hakami(tabela_doctype):
		if typ in obecne:
			w = warunek_hakow(typ, user)
			if w:
				wynik[typ] = w
	return wynik


def _maskowana_publicznosc(role: set[str]) -> bool:
	from crm.permissions.org_hierarchy import BYPASS_ROLES

	return ROLA_D2D in role and not (role & BYPASS_ROLES)


def _admin_role() -> set[str]:
	from crm.api.koszty import ADMIN_ROLE

	return set(ADMIN_ROLE)


def _autorzy_cc_sql() -> str:
	return (
		"SELECT `parent` FROM `tabHas Role` WHERE `parenttype` = 'User' "
		f"AND `role` = {literal_sql(ROLA_CC)} AND `parent` != 'Administrator'"
	)


def get_comment_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	role = set(frappe.get_roles(user))
	t = "`tabComment`"
	czesci = [
		warunek_powiazania(
			"Comment",
			"reference_doctype",
			"reference_name",
			warunki_typow("Comment", "reference_doctype", user),
			galezie_dodatkowe={"Comment": f"{t}.`owner` = {literal_sql(user)}"},
		)
	]
	if not (role & _admin_role()):
		czesci.append(warunek_bez_znacznikow("Comment", "content", ZNACZNIKI_ADMIN))
	if _maskowana_publicznosc(role):
		czesci.append(warunek_bez_znacznikow("Comment", "content", {ZNACZNIK_CC, ZNACZNIK_D2D_UKRYTY}))
		cc = _autorzy_cc_sql()
		czesci.append(
			f"NOT (({t}.`reference_doctype` = 'CRM Lead' OR ({t}.`reference_doctype` = 'CRM Task' "
			f"AND {t}.`reference_name` IN (SELECT `name` FROM `tabCRM Task` WHERE `reference_doctype` = 'CRM Lead'))) "
			f"AND ({t}.`owner` IN ({cc}) OR {t}.`comment_email` IN ({cc})))"
		)
	return polacz_haki(czesci)


def has_comment_permission(doc, ptype: str = "read", user: str | None = None, debug: bool = False):
	"""False, gdy regula ukrywa wiersz; w innym razie None (nigdy True)."""
	if ptype != "read":
		return None
	user = user or frappe.session.user
	if user == "Administrator" or not doc.get("name"):
		return None
	from crm.permissions.org_hierarchy import czy_autor_ma_role_cc

	role = set(frappe.get_roles(user))
	tresc = doc.get("content") or ""
	if not (role & _admin_role()) and any(m in tresc for m in ZNACZNIKI_ADMIN):
		return False
	if not _maskowana_publicznosc(role):
		return None
	if ZNACZNIK_CC in tresc or ZNACZNIK_D2D_UKRYTY in tresc:
		return False
	typ = doc.get("reference_doctype")
	na_leadzie = typ == "CRM Lead"
	if typ == "CRM Task" and doc.get("reference_name"):
		na_leadzie = (
			frappe.db.get_value("CRM Task", doc.get("reference_name"), "reference_doctype") == "CRM Lead"
		)
	if na_leadzie:
		for autor in (doc.get("owner"), doc.get("comment_email")):
			if autor and czy_autor_ma_role_cc(autor):
				return False
	return None
