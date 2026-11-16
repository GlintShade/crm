# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Hooki dokumentu `Volteo Trify Update` (wpisy procesu Trify na szansie
Czyste Powietrze, ops#75).

Doctype tworzy `ops/crm-trify.py` w `proenergy-crm-ops` -- w tym forku go
nie ma; frontend dodaje wpisy przez `frappe.client.insert` i czyta przez
`frappe.client.get_list`, więc nie ma tu osobnego whitelisted API jak przy
`Volteo Audyt CP` -- tylko dwa hooki dokumentu wpięte w `crm/hooks.py`.

`validate` odrzuca pusty tekst i nieznany `typ` -- ostatnia linia obrony przed
tym, co frontend powinien już zablokować, na wypadek bezpośredniego wywołania
`frappe.client.insert`.

`after_insert`, nie `on_update`: DocPerm daje Backendowi `write` na ten
doctype (edycja własnej notatki), a powiadomienie o wzmiance ma iść RAZ, przy
utworzeniu wpisu -- ponowny zapis (np. korekta literówki) nie może zasypać
odbiorcy tym samym powiadomieniem drugi raz. Błąd wysyłki powiadomienia
NIGDY nie wycofuje samego wpisu Trify -- to log procesu, nie dokument
finansowy; utrata wpisu byłaby gorsza niż utrata jednego powiadomienia,
więc wyjątek jest łapany i logowany, a `after_insert` kończy się cicho.

`extract_mentions` (z `crm.api.comment`) czyta `<span data-type="mention"
data-id="...">` przez BeautifulSoup -- ten sam parser, którego już używają
komentarze na szansie, więc wzmianki w edytorze Trify mają identyczną
składnię i identyczne escapowanie jak wzmianki w komentarzach.
"""

import frappe
from frappe import _

from crm.api.comment import extract_mentions
from crm.api.komentarze import liczby_zmian_dokumentow
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.volteo_komentarze import nowe_wzmianki, zmiany_tresci
from crm.volteo_trify import TYPY, tekst_pusty, zbuduj_powiadomienie


def validate(doc, method: str | None = None) -> None:
	if tekst_pusty(doc.get("tekst")):
		frappe.throw(_("Treść wpisu nie może być pusta."))
	if doc.get("typ") not in TYPY:
		frappe.throw(_("Nieznany typ wpisu Trify: {0}").format(doc.get("typ")))


def after_insert(doc, method: str | None = None) -> None:
	try:
		autor_nazwa = frappe.get_cached_value("User", doc.owner, "full_name") or doc.owner
		for wzmianka in extract_mentions(doc.get("tekst")):
			if not wzmianka.email:
				continue
			notify_user(zbuduj_powiadomienie(doc.owner, autor_nazwa, doc.deal, doc.name, wzmianka.email))
	except Exception:
		frappe.log_error(title="Trify: powiadomienie o wzmiance", message=frappe.get_traceback())


DOCTYPE = "Volteo Trify Update"


def _wpis(name: str) -> dict:
	"""Wiersz wpisu Trify z odczytalna szansa i samym wpisem (hook
	`has_trify_permission`, fail-closed). Brak wpisu i brak uprawnien daja TEN SAM
	blad."""
	wiersz = frappe.db.get_value(DOCTYPE, name, ["deal", "owner", "tekst"], as_dict=True) if name else None
	if (
		not wiersz
		or not frappe.has_permission("CRM Deal", "read", wiersz.deal)
		or not frappe.has_permission(DOCTYPE, "read", name)
	):
		frappe.throw(_("Brak uprawnień do tego wpisu."), frappe.PermissionError)
	return wiersz


@frappe.whitelist()
def liczby_zmian(deal: str) -> dict:
	"""`{nazwa wpisu: liczba zmian tresci}` dla wpisow Trify szansy (ikona
	historii, ops#364). Tylko wpisy widoczne dla wolajacego."""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)
	nazwy = frappe.get_list(DOCTYPE, filters={"deal": deal}, pluck="name", limit_page_length=0)
	return liczby_zmian_dokumentow(DOCTYPE, nazwy, "tekst")


@frappe.whitelist(methods=["POST"])
def edytuj(name: str, tekst: str) -> dict:
	"""Zmienia tresc wpisu Trify (ops#364). TYLKO autor wpisu (takze gdy jest
	administratorem). Zapis przez `save(ignore_permissions=True)` (D2D nie ma
	`write`); `validate` sprawdza tresc i typ, `track_changes` zapisuje wersje
	(historia). Powiadomienie dostaja wylacznie osoby wzmiankowane po raz
	pierwszy w tej edycji."""
	wiersz = _wpis(name)
	if wiersz.owner != frappe.session.user:
		frappe.throw(_("Wpis może edytować tylko jego autor."), frappe.PermissionError)
	if tekst_pusty(tekst):
		frappe.throw(_("Treść wpisu nie może być pusta."))
	if tekst == wiersz.tekst:
		return {"name": name, "tekst": tekst}

	doc = frappe.get_doc(DOCTYPE, name)
	doc.tekst = tekst
	doc.save(ignore_permissions=True)

	try:
		autor_nazwa = frappe.get_cached_value("User", doc.owner, "full_name") or doc.owner
		for wzmianka in nowe_wzmianki(wiersz.tekst, tekst):
			notify_user(zbuduj_powiadomienie(doc.owner, autor_nazwa, doc.deal, doc.name, wzmianka["email"]))
	except Exception:
		frappe.log_error(title="Trify: powiadomienie o wzmiance po edycji", message=frappe.get_traceback())
	return {"name": doc.name, "tekst": doc.tekst}


@frappe.whitelist()
def historia(name: str) -> list[dict]:
	"""Wczesniejsze wersje tresci wpisu Trify (`{kto, kto_nazwa, kiedy, przed,
	po}`, rosnaco po dacie); widoczne dla kazdego, kto widzi wpis."""
	_wpis(name)
	zmiany = zmiany_tresci(
		frappe.get_all(
			"Version",
			filters={"ref_doctype": DOCTYPE, "docname": name},
			fields=["owner", "creation", "data"],
			order_by="creation asc",
			limit_page_length=0,
		),
		"tekst",
	)
	if not zmiany:
		return []
	nazwy = {
		u.name: u.full_name
		for u in frappe.get_all(
			"User",
			filters={"name": ["in", list({z["kto"] for z in zmiany if z["kto"]})]},
			fields=["name", "full_name"],
		)
	}
	return [{**z, "kto_nazwa": nazwy.get(z["kto"]) or z["kto"]} for z in zmiany]
