# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Edycja komentarza na leadzie i szansie z historia zmian (ops#364) -- adapter
nad `crm.volteo_komentarze` (frappe-free), wzorowany na
`crm.api.zadania_rozmowa` (rozmowa zadania, b89).

Komentarz to zwykly `Comment` (`comment_type = "Comment"`) z
`reference_doctype` `CRM Lead` albo `CRM Deal`. Role `Volteo D2D Sales` i
`Volteo Backend` maja na `Comment` tylko `read` + `create`
(`ops/crm-uprawnienia-audyt-comment.py`), wiec dawna sciezka
`frappe.client.set_value` odmawiala autorom ("nie udalo sie zaktualizowac
komentarza"). `edytuj` zapisuje przez `save(ignore_permissions=True)` po wlasnych
bramkach: odczyt dokumentu nadrzednego SPRAWDZANY PIERWSZY, potem wylacznie
autor (bez wyjatku dla administratorow). `historia` czyta wiersze `Version`
(`Comment.track_changes`), widoczne dla kazdego, kto widzi dokument.

Maskowanie autora CC (ops#359): tylko na leadzie (`czy_dokument_maskuje_cc`);
handlowiec widzi w historii leada "Call center" zamiast osoby z rola CC, na
szansie zawsze prawdziwego autora.

Brak endpointu usuwania i brak zmian DocPerm (decyzja wlasciciela 2026-11-16).
"""

import frappe
from frappe import _

from crm.permissions.org_hierarchy import BYPASS_ROLES, czy_autor_ma_role_cc
from crm.volteo_aktywnosc import AUTOR_ZASTEPCZY_CC, czy_dokument_maskuje_cc
from crm.volteo_komentarze import czy_komentarz_edytowalny, liczba_zmian_tresci, zmiany_tresci
from crm.volteo_trify import tekst_pusty

ROLA_D2D = "Volteo D2D Sales"


def _sprawdz_dokument(doctype: str, nazwa: str) -> None:
	"""Wspolna bramka: dokument nadrzedny musi istniec i byc odczytywalny przez
	wywolujacego. Brak dokumentu i brak uprawnien daja TEN SAM blad, zeby endpoint
	nie zdradzal, ktore nazwy istnieja."""
	if (
		not nazwa
		or not frappe.db.exists(doctype, nazwa)
		or not frappe.has_permission(doctype, "read", nazwa)
	):
		frappe.throw(_("Brak uprawnień do tego dokumentu."), frappe.PermissionError)


def _wpis(komentarz: str) -> dict:
	"""Wiersz komentarza edytowalnego przez ten modul (lead albo szansa) z
	odczytalnym dokumentem nadrzednym. Komentarz nieistniejacy, innego typu albo
	na innym doctype daje ten sam blad co brak uprawnien."""
	wpis = (
		frappe.db.get_value(
			"Comment",
			komentarz,
			["reference_doctype", "reference_name", "comment_type", "owner", "content"],
			as_dict=True,
		)
		if komentarz
		else None
	)
	if not wpis or not czy_komentarz_edytowalny(wpis.reference_doctype, wpis.comment_type):
		frappe.throw(_("Brak uprawnień do tego wpisu."), frappe.PermissionError)
	_sprawdz_dokument(wpis.reference_doctype, wpis.reference_name)
	return wpis


def liczby_zmian_komentarzy(nazwy: list[str]) -> dict[str, int]:
	"""`{nazwa komentarza: liczba zmian tresci}` z wierszy `Version` (jedno
	zapytanie). Pomocnik dla `crm.api.volteo_leady.komentarze` i
	`crm.api.activities`, NIE metoda whitelist -- wolajacy sam sprawdzil odczyt
	dokumentu nadrzednego. Komentarze bez zmian nie maja klucza (`.get(nazwa, 0)`)."""
	nazwy = [nazwa for nazwa in (nazwy or []) if nazwa]
	if not nazwy:
		return {}
	wersje_per_wpis: dict[str, list[dict]] = {}
	for wersja in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Comment", "docname": ["in", nazwy]},
		fields=["docname", "owner", "creation", "data"],
		order_by="creation asc",
		limit_page_length=0,
	):
		wersje_per_wpis.setdefault(wersja.docname, []).append(wersja)
	return {
		nazwa: liczba
		for nazwa, wersje in wersje_per_wpis.items()
		if (liczba := liczba_zmian_tresci(wersje))
	}


@frappe.whitelist(methods=["POST"])
def edytuj(komentarz: str, tresc: str) -> dict:
	"""Zmienia tresc komentarza leada albo szansy. TYLKO autor wpisu (takze gdy
	jest administratorem) i tylko, gdy widzi dokument. Niezmieniona tresc nic nie
	zapisuje. `Comment.track_changes` zapisuje wiersz `Version` (historia), a
	hook `on_update` powiadamia wylacznie o wzmiankach NOWYCH wzgledem poprzedniej
	tresci (`doc.flags.volteo_tresc_przed`, patrz `crm.api.comment`)."""
	wpis = _wpis(komentarz)
	if wpis.owner != frappe.session.user:
		frappe.throw(_("Wpis może edytować tylko jego autor."), frappe.PermissionError)
	if tekst_pusty(tresc):
		frappe.throw(_("Wpis nie może być pusty."))
	if tresc == wpis.content:
		return {"name": komentarz}

	doc = frappe.get_doc("Comment", komentarz)
	doc.flags.volteo_tresc_przed = wpis.content
	doc.content = tresc
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def historia(komentarz: str) -> list[dict]:
	"""Wczesniejsze wersje tresci komentarza leada albo szansy (rosnaco po dacie
	zmiany): `{kto, kto_nazwa, kiedy, przed, po}`. Czyta `Version`, niczego nie
	zapisuje. Na leadzie autor z rola CC jest maskowany dla handlowca."""
	wpis = _wpis(komentarz)

	zmiany = zmiany_tresci(
		frappe.get_all(
			"Version",
			filters={"ref_doctype": "Comment", "docname": komentarz},
			fields=["owner", "creation", "data"],
			order_by="creation asc",
			limit_page_length=0,
		)
	)
	if not zmiany:
		return []

	role_wolajacego = frappe.get_roles()
	# frappe.get_roles("Administrator") zwraca WSZYSTKIE role, wiec Administrator
	# i BYPASS_ROLES jawnie nie sa maskowane (jak w `volteo_leady.komentarze`).
	maskuj = (
		frappe.session.user != "Administrator"
		and not (set(role_wolajacego) & BYPASS_ROLES)
		and ROLA_D2D in role_wolajacego
		and czy_dokument_maskuje_cc(wpis.reference_doctype)
	)
	cache_rol: dict[str, bool] = {}

	nazwy_autorow = {
		uzytkownik.name: uzytkownik.full_name
		for uzytkownik in frappe.get_all(
			"User",
			filters={"name": ["in", list({zmiana["kto"] for zmiana in zmiany if zmiana["kto"]})]},
			fields=["name", "full_name"],
		)
	}
	wynik = []
	for zmiana in zmiany:
		kto = zmiana["kto"]
		if maskuj and kto and czy_autor_ma_role_cc(kto, cache_rol):
			wynik.append({**zmiana, "kto": AUTOR_ZASTEPCZY_CC, "kto_nazwa": AUTOR_ZASTEPCZY_CC})
		else:
			wynik.append({**zmiana, "kto_nazwa": nazwy_autorow.get(kto) or kto})
	return wynik
