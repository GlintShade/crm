# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Widocznosc audytu po szansie (ops#338): `Volteo Audyt` (OZE) i
`Volteo Audyt CP`.

Regula odczytu: wiersz audytu jest widoczny dla uzytkownika wtedy i tylko
wtedy, gdy widzi on szanse nadrzedna (pole `deal`). Cala logika widocznosci
szansy zostaje w `crm.permissions.org_hierarchy` (jedno zrodlo prawdy),
tu tylko delegacja przez generyczne funkcje z `faktura_visibility`.
Fail-closed: brak `deal` albo nierozwiazana szansa ukrywa wiersz.
`BYPASS_ROLES` bez zmian (widza i edytuja wszystko).

Regula zapisu (decyzja wlasciciela 2026-11-16, ops#338): po zdjeciu
`if_owner` z DocPerm `Volteo D2D Sales` samo DocPerm nie ogranicza juz
zapisu do autora, wiec ogranicza go ten hook: zapis (write/create/delete...)
wolno wykonac autorowi audytu LUB aktualnemu `deal_owner` szansy, i to tylko
przy prawie zapisu do szansy. Przelozony z `CRM Sales Hierarchy`, ktory
widzi szanse podwladnego, audyt tylko czyta.

Hook musi wejsc razem z obrazem, PRZED zdjeciem `if_owner` przez
`ops/crm-audyt-widocznosc.py` (bez hooka zdjecie `if_owner` otworzyloby
wszystkie audyty wszystkim handlowcom).
"""

import frappe

from crm.permissions.faktura_visibility import _deal_scoped_query_conditions, _has_deal_scoped_permission
from crm.permissions.org_hierarchy import BYPASS_ROLES

# Typy dostepu traktowane jak odczyt; reszta (write, create, delete, submit...)
# podlega regule autor / deal_owner.
PTYPY_ODCZYTU = frozenset({"read", "select", "report", "export", "print", "email", "share"})


def get_audyt_permission_query_conditions(user=None):
	return _deal_scoped_query_conditions("Volteo Audyt", user or frappe.session.user)


def get_audyt_cp_permission_query_conditions(user=None):
	return _deal_scoped_query_conditions("Volteo Audyt CP", user or frappe.session.user)


def czy_autor_lub_doradca(user: str, autor: str | None, deal_owner: str | None) -> bool:
	"""Czysta regula zapisu: autor albo doradca szansy. Pusty autor oznacza
	dokument jeszcze nie zapisany (tworzy go biezacy uzytkownik)."""
	return (not autor) or autor == user or (bool(deal_owner) and deal_owner == user)


def _has_audyt_permission(doc, ptype: str, user: str | None) -> bool:
	user = user or frappe.session.user

	if user == "Administrator" or set(frappe.get_roles(user)) & BYPASS_ROLES:
		return True

	# Odczyt (i fail-closed dla braku szansy) przez widocznosc szansy.
	if not _has_deal_scoped_permission(doc, "read", user, fail_open=False):
		return False
	if ptype in PTYPY_ODCZYTU:
		return True

	# Zapis: prawo zapisu do szansy ORAZ autor / doradca.
	if not _has_deal_scoped_permission(doc, ptype, user, fail_open=False):
		return False
	deal = doc.get("deal") if isinstance(doc, dict) else getattr(doc, "deal", None)
	autor = doc.get("owner") if isinstance(doc, dict) else getattr(doc, "owner", None)
	deal_owner = frappe.db.get_value("CRM Deal", deal, "deal_owner")
	return czy_autor_lub_doradca(user, autor, deal_owner)


def has_audyt_permission(doc, ptype, user=None):
	return _has_audyt_permission(doc, ptype, user)


def has_audyt_cp_permission(doc, ptype, user=None):
	return _has_audyt_permission(doc, ptype, user)
