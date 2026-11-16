# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""API sekcji "Rozmowa" w oknie zadania (`CRM Task`) -- adapter nad
`crm.volteo_zadania_rozmowa` (frappe-free).

Wpis rozmowy to zwykly `Comment` (`comment_type = "Comment"`,
`reference_doctype = "CRM Task"`, `reference_name` = nazwa zadania). Edycja
tresci idzie istniejaca sciezka `CommentArea.vue` (`frappe.client.set_value` na
`Comment`) -- ten modul NIE ma wlasnego endpointu edycji ani usuwania.

Frontend woła te endpointy WYLACZNIE pelna kropkowana sciezka
(`crm.api.zadania_rozmowa.*`) i z nazwa zadania jako STRING: `CRM Task` ma
nazwy liczbowe (autoincrement), a Frappe waliduje typy argumentow metod
whitelist w zadaniu HTTP.

Model uprawnien (krytyczny): KAZDY endpoint najpierw sprawdza odczyt zadania
(`_sprawdz_zadanie`) -- hook `crm.permissions.child_visibility` zawęża
`CRM Task` do widocznosci rodzica (szansa/lead; zadanie bez powiazania widzi
tylko wlasciciel i osoba przypisana, plus role z BYPASS_ROLES) -- i dopiero PO
tej bramce czyta `Comment`/`Version`/`File` przez `get_all`. `get_all` po
jawnej bramce jest tu celowe, ten sam wzorzec i uzasadnienie co
`crm.api.volteo_leady.komentarze`: straznik filtrow (`crm.api.volteo_filtry_guard`)
odrzuca `get_list` po polach `Comment` dla rol terenowych.
"""

import frappe
from frappe import _

from crm.api.comment import add_comment
from crm.volteo_trify import tekst_pusty
from crm.volteo_zadania_rozmowa import liczba_zmian_tresci, zmiany_tresci

DOCTYPE_ZADANIA = "CRM Task"
LIMIT_WPISOW = 500


def _sprawdz_zadanie(zadanie: str) -> None:
	"""Wspolna bramka: zadanie musi istniec i byc odczytywalne przez
	wywolujacego (`has_permission` laczy DocPerm z hookiem
	`child_visibility`). Brak zadania i brak uprawnien daja TEN SAM blad --
	inaczej endpoint zdradzalby, ktore numery zadan istnieja."""
	if (
		not zadanie
		or not frappe.db.exists(DOCTYPE_ZADANIA, zadanie)
		or not frappe.has_permission(DOCTYPE_ZADANIA, "read", zadanie)
	):
		frappe.throw(_("Brak uprawnień do tego zadania."), frappe.PermissionError)


@frappe.whitelist()
def lista(zadanie: str) -> list[dict]:
	"""Wpisy rozmowy zadania, rosnaco po dacie, kazdy z zalacznikami
	(`attachments`) i liczba zmian tresci (`liczba_zmian`, z wierszy `Version`)."""
	_sprawdz_zadanie(zadanie)

	wpisy = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": DOCTYPE_ZADANIA,
			"reference_name": zadanie,
			"comment_type": "Comment",
		},
		fields=["name", "owner", "comment_by", "content", "creation", "modified"],
		order_by="creation asc",
		limit_page_length=LIMIT_WPISOW,
	)
	if not wpisy:
		return []

	nazwy = [wpis.name for wpis in wpisy]

	# frappe.db.get_all (nie frappe.get_all): uprawnienia File sa owner-based, a
	# zalaczniki roznych autorow tej samej rozmowy musza byc widoczne dla
	# kazdego, kto widzi zadanie (ten sam powod co w `crm.api.notatki.feed`).
	zalaczniki_per_wpis: dict[str, list[dict]] = {}
	for plik in (
		frappe.db.get_all(
			"File",
			filters={"attached_to_doctype": "Comment", "attached_to_name": ["in", nazwy]},
			fields=["attached_to_name", "file_name", "file_url"],
		)
		or []
	):
		zalaczniki_per_wpis.setdefault(plik.attached_to_name, []).append(
			{"file_name": plik.file_name, "file_url": plik.file_url}
		)

	# Jedno zapytanie o wszystkie wersje wszystkich wpisow; liczenie zmian
	# tresci (a nie samych wierszy Version) robi czysta funkcja modulu.
	wersje_per_wpis: dict[str, list[dict]] = {}
	for wersja in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Comment", "docname": ["in", nazwy]},
		fields=["docname", "owner", "creation", "data"],
		order_by="creation asc",
		limit_page_length=0,
	):
		wersje_per_wpis.setdefault(wersja.docname, []).append(wersja)

	return [
		{
			**wpis,
			"attachments": zalaczniki_per_wpis.get(wpis.name, []),
			"liczba_zmian": liczba_zmian_tresci(wersje_per_wpis.get(wpis.name, [])),
		}
		for wpis in wpisy
	]


@frappe.whitelist(methods=["POST"])
def dodaj(zadanie: str, tresc: str, zalaczniki: list | None = None) -> dict:
	"""Dodaje wpis do rozmowy zadania. Pusta tresc (po zdjeciu znacznikow i
	bialych znakow) jest odrzucana; sam zapis, wzmianki i zalaczniki robi
	istniejace `crm.api.comment.add_comment` -- logika zalacznikow nie jest tu
	duplikowana. `zalaczniki` to lista nazw plikow (`File.name`)."""
	_sprawdz_zadanie(zadanie)
	if tekst_pusty(tresc):
		frappe.throw(_("Wpis nie może być pusty."))

	komentarz = add_comment(DOCTYPE_ZADANIA, zadanie, tresc, zalaczniki)
	return {"name": komentarz.name}


@frappe.whitelist()
def historia(komentarz: str) -> list[dict]:
	"""Wczesniejsze wersje tresci jednego wpisu rozmowy (rosnaco po dacie
	zmiany): `{kto, kto_nazwa, kiedy, przed, po}`. Czyta wiersze `Version`
	komentarza (`Comment.track_changes = 1`), niczego nie zapisuje."""
	wpis = (
		frappe.db.get_value(
			"Comment",
			komentarz,
			["reference_doctype", "reference_name", "comment_type"],
			as_dict=True,
		)
		if komentarz
		else None
	)
	# Komentarz nieistniejacy, nie-zadaniowy albo innego typu daje ten sam blad
	# co brak uprawnien (patrz `_sprawdz_zadanie`): endpoint nie moze sluzyc do
	# czytania historii komentarzy szans, leadow ani audytu.
	if not wpis or wpis.reference_doctype != DOCTYPE_ZADANIA or wpis.comment_type != "Comment":
		frappe.throw(_("Brak uprawnień do tego wpisu."), frappe.PermissionError)
	_sprawdz_zadanie(wpis.reference_name)

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

	nazwy_autorow = {
		uzytkownik.name: uzytkownik.full_name
		for uzytkownik in frappe.get_all(
			"User",
			filters={"name": ["in", list({zmiana["kto"] for zmiana in zmiany if zmiana["kto"]})]},
			fields=["name", "full_name"],
		)
	}
	return [{**zmiana, "kto_nazwa": nazwy_autorow.get(zmiana["kto"]) or zmiana["kto"]} for zmiana in zmiany]
