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
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
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
